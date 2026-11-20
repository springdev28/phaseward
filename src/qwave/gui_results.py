"""Read-only, hash-verified local result browsing and bounded portable exports.

Nothing in this module imports a solver or executes saved code. Symlinks and
paths outside the selected results root are rejected. NPZ never enables pickle.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any
import zipfile

import numpy as np

MAX_EXPORT_BYTES = 256 * 1024**2


def json_bytes(value: Any) -> bytes:
    """Canonical, standards-compliant JSON for exports and exact cache identities."""
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+"\n").encode()


def strict_json(data: bytes | str) -> Any:
    """Reject duplicate keys and nonstandard NaN/Infinity in imported configurations."""
    def pairs(items: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def invalid(value: str) -> None:
        raise ValueError(f"invalid JSON number: {value}")
    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def safe_path(root: Path, relative: str) -> Path:
    """Resolve an inventory entry without permitting traversal or symlink escapes."""
    name = PurePosixPath(relative)
    if not relative or name.is_absolute() or ".." in name.parts or "\\" in relative:
        raise ValueError(f"unsafe result path: {relative}")
    path = root
    for part in name.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("symbolic links are not accepted in result bundles")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("result path escapes its root")
    return path


@dataclass(frozen=True)
class ResultBundle:
    """A verified manifest and exact file inventory; reads recheck current bytes."""

    root: Path
    manifest: dict[str, Any]
    manifest_bytes: bytes
    fingerprint: str

    @property
    def files(self) -> list[str]:
        """Only inventoried files, not arbitrary extra files beside a run."""
        return sorted(self.manifest["outputs"])

    @property
    def status(self) -> str:
        """Older manifests predate explicit statuses; do not imply checks all passed."""
        return self.manifest.get("status", "legacy_completed_check_metrics")

    def read(self, name: str) -> bytes:
        """Read a bounded file and reject changes since the recorded run."""
        if name == "manifest.json":
            if safe_path(self.root,name).read_bytes() != self.manifest_bytes:
                raise ValueError("manifest changed; reopen this result")
            return self.manifest_bytes
        record = self.manifest["outputs"][name]
        path = safe_path(self.root, name)
        if path.stat().st_size > MAX_EXPORT_BYTES:
            raise ValueError("file exceeds the 256 MiB panel limit; use the local filesystem")
        data = path.read_bytes()
        if len(data) != record["size_bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError(f"integrity check failed: {name}; original results were not modified by the panel")
        return data

    def json(self, name: str) -> Any:
        """Load an inventoried JSON artifact."""
        return strict_json(self.read(name))

    def arrays(self, name: str) -> dict[str, np.ndarray]:
        """Load numeric arrays only, with a bound on uncompressed NPZ contents."""
        data = self.read(name)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > MAX_EXPORT_BYTES:
                raise ValueError("expanded NPZ exceeds the 256 MiB panel limit")
        with np.load(io.BytesIO(data), allow_pickle=False) as arrays:
            return {key:arrays[key] for key in arrays.files}

    def archive(self, category: str = "all") -> bytes:
        """Portable ZIP preserving original bytes, child manifests and folder names."""
        suffixes = {"data":{ ".csv", ".npz", ".json", ".md"}, "plots":{ ".png", ".pdf", ".svg"}}
        if category not in ("all", *suffixes):
            raise ValueError("archive category must be all, data or plots")
        names = [n for n in self.files if category == "all" or Path(n).suffix in suffixes[category]]
        if sum(self.manifest["outputs"][n]["size_bytes"] for n in names) > MAX_EXPORT_BYTES:
            raise ValueError("export exceeds 256 MiB; use this run's local folder")
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", self.read("manifest.json"))
            for name in names:
                archive.writestr(name, self.read(name))
        return stream.getvalue()


def load_bundle(path: Path, results_root: Path) -> ResultBundle:
    """Open a completed or failed run read-only and verify every inventoried file."""
    if results_root.is_symlink():
        raise ValueError("symbolic links are not accepted for the results root")
    results_root = results_root.resolve()
    try:
        relative = path.absolute().relative_to(results_root)
    except ValueError as error:
        raise ValueError("select a directory inside this workspace's results folder") from error
    root = safe_path(results_root, relative.as_posix())
    manifest_path = safe_path(root, "manifest.json")
    if manifest_path.stat().st_size > 8*1024**2:
        raise ValueError("manifest exceeds the 8 MiB panel limit")
    raw = manifest_path.read_bytes()
    manifest = strict_json(raw)
    if not isinstance(manifest,dict) or not isinstance(manifest.get("config"),dict):
        raise ValueError("manifest must be an object with a recorded configuration")
    for name in ("scope","status","created_utc"):
        if name in manifest and not isinstance(manifest[name],str):
            raise ValueError(f"manifest {name} must be text")
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict) or len(outputs) > 5000 or "manifest.json" in outputs:
        raise ValueError("unsupported manifest inventory")
    total = 0
    for name, record in outputs.items():
        if not isinstance(record, dict) or set(record) != {"sha256", "size_bytes"}:
            raise ValueError("each output must have a SHA-256 and size_bytes")
        if type(record["size_bytes"]) is not int or record["size_bytes"] < 0:
            raise ValueError("invalid output size")
        total += record["size_bytes"]
        safe_path(root, name)
    if total > MAX_EXPORT_BYTES:
        raise ValueError("run exceeds the 256 MiB panel limit; inspect it with the CLI/filesystem")
    bundle = ResultBundle(root, manifest, raw, hashlib.sha256(raw).hexdigest())
    for name in bundle.files:
        bundle.read(name)
    return bundle


def discover_results(results_root: Path) -> list[Path]:
    """Find local manifests without following links or scanning environments/caches."""
    if not results_root.is_dir() or results_root.is_symlink():
        return []
    found = []
    for directory, subdirs, files in os.walk(results_root, followlinks=False):
        subdirs[:] = sorted(d for d in subdirs if not d.startswith(".") and not (Path(directory)/d).is_symlink())
        if "manifest.json" in files and not (Path(directory)/"manifest.json").is_symlink():
            found.append(Path(directory))
            subdirs[:] = []  # A GUI envelope inventories its child run manifests.
        if len(found) >= 500:
            break
    return sorted(found, key=lambda p:p.stat().st_mtime_ns, reverse=True)
