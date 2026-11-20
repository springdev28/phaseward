"""Local source and runtime provenance for reproducible result bundles."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    """Hash a file in bounded chunks without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_identity() -> dict[str, Any]:
    """Hash package sources and report Git state when running from a checkout.

    Source hashes remain useful before an initial commit or with uncommitted
    edits. A wheel install has no assumed association with the caller's Git repo.
    """
    package_dir = Path(__file__).resolve().parent
    checkout = package_dir.parent.parent
    is_checkout = package_dir.parent.name == "src" and (checkout / "pyproject.toml").is_file()
    paths = sorted(package_dir.glob("*.py")) + [package_dir / "py.typed"]
    root = checkout if is_checkout else package_dir
    if is_checkout:
        paths.append(checkout / "pyproject.toml")
    hashes = {str(path.relative_to(root)): sha256_file(path) for path in paths if path.is_file()}
    source_hash = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode("utf-8")).hexdigest()
    git: dict[str, Any] = {"commit": None, "working_tree_dirty": None, "available": False}
    if is_checkout and (checkout / ".git").exists():
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=checkout, capture_output=True, text=True, timeout=3
            )
            status = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=normal"],
                cwd=checkout, capture_output=True, text=True, timeout=3,
            )
            git = {
                "commit": commit.stdout.strip() if commit.returncode == 0 else None,
                "working_tree_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
                "available": status.returncode == 0,
            }
        except (OSError, subprocess.TimeoutExpired):
            pass  # Git is optional; the recorded source hashes are still available.
    return {"sha256": source_hash, "files_sha256": hashes, "git": git}
