"""Local provenance and artifact helpers for the teaching notebooks; no physics.

All transport, packet, covariance, and sensitivity calculations belong to qwave.
This module only verifies source identity and records numerical work and figures.
"""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping, Sequence

import numpy as np

import qwave
from qwave.diagnostics import cpu_environment, software_versions
from qwave.provenance import sha256_file, source_identity
from qwave.units import physical_constants

ROOT = Path(__file__).resolve().parents[2]
GUIDE = Path(__file__).resolve().parent


def json_default(value: Any) -> Any:
    """Convert explicit NumPy scalars/arrays and paths without hiding NaNs."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def write_json(path: Path, value: Any) -> None:
    """Write portable strict JSON; complex arrays belong in NPZ, not JSON."""
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False,
                               default=json_default) + "\n", encoding="utf-8")


def verify_workspace_source() -> dict[str, Any]:
    """Reject a stale installed library, including missing or extra source files."""
    installed = Path(qwave.__file__).resolve().parent
    expected = ROOT / "src" / "qwave"
    local = {p.name: sha256_file(p) for p in sorted(expected.glob("*.py"))}
    active = {p.name: sha256_file(p) for p in sorted(installed.glob("*.py"))}
    local["py.typed"] = sha256_file(expected / "py.typed")
    if (installed / "py.typed").is_file():
        active["py.typed"] = sha256_file(installed / "py.typed")
    mismatch = sorted(k for k in local.keys() | active.keys() if local.get(k) != active.get(k))
    if mismatch:
        raise RuntimeError(f"Imported qwave differs from workspace: {mismatch}; reinstall before verification")
    return {"workspace_matches": True, "imported_package": str(installed),
            "workspace_package": str(expected), "file_count": len(local),
            "source": source_identity()}


def source_record() -> dict[str, Any]:
    """Record package and learning-source identity, including pre-commit work."""
    record = verify_workspace_source()
    inputs = sorted(p for p in GUIDE.rglob("*") if p.suffix in {".py", ".md", ".ipynb", ".json"})
    record["learning_source_sha256"] = {str(p.relative_to(ROOT)): sha256_file(p) for p in inputs}
    record["verification_tests_sha256"] = {str(p.relative_to(ROOT)): sha256_file(p)
                                            for p in sorted((ROOT / "tests").glob("*.py"))}
    record["pyproject_sha256"] = sha256_file(ROOT / "pyproject.toml")
    record["workspace_git"] = {"commit": None, "dirty": None,
                               "note": "A missing commit is recorded as null; source hashes remain available."}
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                text=True, timeout=5, check=False)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                                text=True, timeout=5, check=False)
        record["workspace_git"].update(commit=commit.stdout.strip() if commit.returncode == 0 else None,
                                       dirty=bool(status.stdout.strip()) if status.returncode == 0 else None)
    except (OSError, subprocess.TimeoutExpired):
        pass  # Git is optional; the explicit source hashes remain authoritative.
    return record


def inventory(folder: Path) -> dict[str, dict[str, Any]]:
    """Hash all current files, excluding the top manifest being constructed."""
    return {str(p.relative_to(folder)): {"sha256": sha256_file(p), "bytes": p.stat().st_size}
            for p in sorted(folder.rglob("*")) if p.is_file() and p != folder / "manifest.json"}


def runtime_record() -> dict[str, Any]:
    """Record the execution environment and physical constants, with no network."""
    return {"utc_timestamp": datetime.now(timezone.utc).isoformat(),
            "software_versions": software_versions(), "hardware": cpu_environment(),
            "physical_constants": physical_constants(), "source_identity": source_record()}


class VerificationBundle:
    """Fresh, auditable output directory for one educational verification notebook."""

    def __init__(self, output: Path, config: Mapping[str, Any], *, scope: str) -> None:
        self.output = output.resolve()
        self.output.mkdir(parents=True, exist_ok=False)
        self.config = dict(config)
        self.scope = scope
        self.started = perf_counter()
        self.runtime = runtime_record()
        self.checks: list[dict[str, Any]] = []
        self.figures: list[dict[str, str]] = []
        self.finished = False
        self.json("config", self.config)
        self.json("environment", self.runtime)

    def _path(self, name: str, suffix: str) -> Path:
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("Artifact names must be simple base names")
        path = self.output / (name + suffix)
        if path.exists():
            raise FileExistsError(f"Artifact already exists: {path}")
        return path

    def json(self, name: str, value: Any) -> None:
        """Save strict JSON without silent replacement."""
        write_json(self._path(name, ".json"), value)

    def arrays(self, name: str, *, units: Mapping[str, str], **arrays: Any) -> None:
        """Save raw arrays and explicit per-array units (including complex data)."""
        if set(units) != set(arrays):
            raise ValueError("Every array must have an explicit units entry")
        np.savez_compressed(self._path(name, ".npz"), **arrays)
        self.json(name + "-arrays", {key: {"units": units[key], "shape": list(np.shape(value)),
                                         "dtype": str(np.asarray(value).dtype)}
                                   for key, value in arrays.items()})

    def table(self, name: str, rows: Sequence[Mapping[str, Any]]) -> None:
        """Save rectangular trial/check data as CSV; units belong in field names."""
        if not rows:
            raise ValueError("A CSV table needs at least one row")
        fields = list(rows[0])
        if any(set(row) != set(fields) for row in rows):
            raise ValueError("CSV rows must have the same fields")
        with self._path(name, ".csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def figure(self, figure: Any, name: str, description: str) -> None:
        """Save the actual Matplotlib figure in three formats with a caption."""
        import matplotlib.pyplot as plt
        for suffix in (".png", ".svg", ".pdf"):
            figure.savefig(self._path(name, suffix), dpi=180, bbox_inches="tight")
        self.figures.append({"name": name, "description": description,
                             "png": str(self.output / (name + ".png"))})
        # A real local Jupyter kernel may display the already saved image.
        # The standard-library runner embeds this same PNG after cell execution.
        try:
            from IPython import get_ipython
            from IPython.display import Image, display
            if get_ipython() is not None:
                display(Image(filename=str(self.output / (name + ".png"))))
        except ImportError:
            pass
        plt.close(figure)

    def check(self, name: str, passed: bool, *, measured: Any, criterion: str) -> None:
        """Record actual measured evidence and its prespecified numerical criterion."""
        self.checks.append({"name": name, "passed": bool(passed), "measured": measured,
                            "criterion": criterion})

    def finish(self) -> None:
        """Write a completion manifest only if all recorded checks passed."""
        self.json("checks", self.checks)
        self.json("figures", [{"name": f["name"], "description": f["description"]} for f in self.figures])
        if not self.checks or not all(c["passed"] for c in self.checks):
            raise AssertionError("Notebook verification failed; inspect checks.json; no completion manifest written")
        self.json("manifest", {"schema_version": 1, "status": "complete", "scope": self.scope,
                               "config": self.config, "random_seeds": self.config.get("seeds", []),
                               "seed_role": "educational verification, not experimental evaluation",
                               "runtime": self.runtime, "wall_seconds": perf_counter() - self.started,
                               "check_count": len(self.checks), "all_checks_passed": True,
                               "inventory": inventory(self.output),
                               "inventory_note": "The manifest excludes its own hash."})
        self.finished = True
        print(f"PASS: {len(self.checks)} numerical checks; artifacts: {self.output}")

