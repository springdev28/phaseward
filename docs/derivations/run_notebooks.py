"""Execute the four trusted ordinary-Python notebooks without a Jupyter install."""

from __future__ import annotations

import argparse
import base64
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path
from time import perf_counter
from typing import Any

# Use a writable, ephemeral cache when the user has not configured one.
_cache = tempfile.TemporaryDirectory(prefix="qwave-learning-mpl-")
os.environ.setdefault("MPLCONFIGDIR", _cache.name)

import matplotlib

matplotlib.use("Agg")

from verification import GUIDE, inventory, runtime_record, write_json

NOTEBOOKS = (
    "01_scattering", "02_packets", "03_covariance", "04_sensitivity_objective",
)


def execute_notebook(source: Path, output: Path) -> dict[str, Any]:
    """Execute cells sequentially and embed outputs actually produced by them.

    No kernel or IPython semantics are claimed. A failing cell stops execution;
    its traceback is saved in the executed notebook and propagated to the caller.
    """
    document = json.loads(source.read_text(encoding="utf-8"))
    if document.get("nbformat") != 4:
        raise ValueError("Only nbformat 4 ordinary-Python notebooks are supported")
    executed = copy.deepcopy(document)
    for cell in executed["cells"]:
        if cell["cell_type"] == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
    namespace: dict[str, Any] = {"__name__": "__main__", "RUN_OUTPUT": output / source.stem}
    started = perf_counter()
    number = 0
    figure_count = 0
    for cell in executed["cells"]:
        if cell["cell_type"] != "code":
            continue
        number += 1
        code = "".join(cell["source"])
        cell["execution_count"] = number
        cell["outputs"] = []
        stdout, stderr = io.StringIO(), io.StringIO()
        failure: Exception | None = None
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(compile(code, f"{source.name}:cell-{number}", "exec"), namespace)
        except Exception as error:
            failure = error
            cell["outputs"].append({"output_type": "error", "ename": type(error).__name__,
                                    "evalue": str(error), "traceback": traceback.format_exc().splitlines()})
        for name, stream in (("stdout", stdout), ("stderr", stderr)):
            if stream.getvalue():
                cell["outputs"].append({"output_type": "stream", "name": name,
                                        "text": stream.getvalue().splitlines(keepends=True)})
        bundle = namespace.get("bundle")
        if bundle is not None:
            for figure in bundle.figures[figure_count:]:
                cell["outputs"].append({"output_type": "display_data", "metadata": {}, "data": {
                    "image/png": base64.b64encode(Path(figure["png"]).read_bytes()).decode("ascii"),
                    "text/plain": [figure["description"]]}})
            figure_count = len(bundle.figures)
        # Checkpoint even failed notebooks. Never mark unexecuted cells as run.
        write_json(output / (source.stem + ".executed.ipynb"), executed)
        if failure is not None:
            raise RuntimeError(f"{source.name}, code cell {number}: {failure}") from failure
    if bundle is None or not bundle.finished:
        raise RuntimeError(f"{source.name} did not finish a verification bundle")
    return {"notebook": source.name, "executed_code_cells": number, "checks": len(bundle.checks),
            "wall_seconds": perf_counter() - started, "figures": figure_count, "status": "passed"}


def run(output: Path, names: tuple[str, ...] = NOTEBOOKS) -> dict[str, Any]:
    """Run a fresh, auditable batch, retaining failures without overwriting it."""
    if not names or any(name not in NOTEBOOKS for name in names) or len(set(names)) != len(names):
        raise ValueError("Choose unique notebook names from the supported list")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    try:
        environment = runtime_record()
        write_json(output / "environment.json", environment)
        write_json(output / "invocation.json", {"argv": sys.argv, "selected_notebooks": names,
                                                "runner": "ordinary Python exec; no IPython or kernel"})
        results = []
        for name in names:
            print(f"Running {name} …", flush=True)
            result = execute_notebook(GUIDE / "notebooks" / (name + ".ipynb"), output)
            results.append(result)
            print(f"  {result['checks']} checks passed in {result['wall_seconds']:.2f} s", flush=True)
        report = ["# Phaseward educational verification", "",
                  "All results below are computed software/mathematical checks. They are not",
                  "evidence that an optimized design improves a real semiconductor.", "",
                  "| Notebook | Checks | Time (s) |", "| --- | ---: | ---: |"]
        for result in results:
            stem = Path(result["notebook"]).stem
            report.append(f"| [{stem}]({stem}.executed.ipynb) | {result['checks']} | {result['wall_seconds']:.3f} |")
        report += ["", "Each subdirectory contains its exact configuration, check criteria, raw arrays,",
                   "figure descriptions and a provenance manifest. Existing outputs were not overwritten.", ""]
        (output / "report.md").write_text("\n".join(report), encoding="utf-8")
        manifest = {"schema_version": 1, "status": "complete", "scope": "educational numerical verification",
                    "runtime": environment, "results": results, "wall_seconds": perf_counter() - started,
                    "random_seeds": {name: json.loads((output / name / "config.json").read_text()).get("seeds", [])
                                     for name in names},
                    "inventory": inventory(output), "inventory_note": "Excludes this top-level manifest itself."}
        write_json(output / "manifest.json", manifest)
        return manifest
    except Exception as error:
        write_json(output / "failure.json", {"status": "failed", "error": str(error),
                                            "traceback": traceback.format_exc(),
                                            "wall_seconds": perf_counter() - started})
        raise


def main() -> int:
    """CLI entry for local teaching notebooks; a fresh destination is mandatory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--notebook", choices=NOTEBOOKS, action="append",
                        help="Select one or more; by default run all four in order")
    args = parser.parse_args()
    try:
        run(args.output, tuple(args.notebook) if args.notebook else NOTEBOOKS)
    except Exception as error:
        print(f"Verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Complete: {args.output.resolve() / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
