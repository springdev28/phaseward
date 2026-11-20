"""Offline byte-integrity check; run from anywhere with Python 3.11+ stdlib only.

This checks the exported inventory, not signatures, physics or statistical truth.
For data/figure replay, use qwave paper-export on this package's source_run.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath


def verify(root: Path) -> int:
    """Verify every listed file, the source manifest and its original inventory."""
    manifest = json.loads((root / "export_manifest.json").read_text())
    if manifest.get("status") != "verified_support_package":
        raise ValueError("incomplete support package")
    for name, record in manifest["outputs"].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise ValueError("unsafe inventory path")
        path = root
        for part in relative.parts:
            path = path / part
            if path.is_symlink():
                raise ValueError("symlink in package")
        data = path.read_bytes()
        if len(data) != record["size_bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("integrity mismatch: " + name)
    original = (root / "source_run/manifest.json").read_bytes()
    if hashlib.sha256(original).hexdigest() != manifest["source_manifest_sha256"]:
        raise ValueError("original manifest binding mismatch")
    source = json.loads(original)
    for name, record in source["outputs"].items():
        if manifest["outputs"].get("source_run/" + name) != record:
            raise ValueError("original output binding mismatch: " + name)
    return len(manifest["outputs"])


if __name__ == "__main__":
    count = verify(Path(__file__).resolve().parent)
    print(f"Verified {count} inventoried files and original run binding. Hashes are unsigned; extra files are not verified.")
