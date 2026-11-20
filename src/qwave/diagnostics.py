"""Inspect the local Python and CPU environment without network access."""

from __future__ import annotations

import importlib
import os
import platform
import struct
import sys
from importlib import metadata
from typing import Any

from qwave import __version__

RUNTIME_PACKAGES: tuple[str, ...] = ("numpy", "scipy", "matplotlib")


def software_versions() -> dict[str, str | None]:
    """Record installed versions, explicitly marking unavailable distributions."""
    versions: dict[str, str | None] = {"python": platform.python_version()}
    for name in ("qwave", *RUNTIME_PACKAGES, "pytest", "pip", "setuptools"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    versions["qwave_source"] = __version__
    return versions


def cpu_environment() -> dict[str, Any]:
    """Describe this process's CPU architecture, not unverified GPU hardware."""
    machine = platform.machine()
    return {
        "operating_system": platform.system(),
        "os_release": platform.release(),
        "machine": machine,
        "processor": platform.processor() or machine,
        "logical_cpu_count": os.cpu_count(),
        "pointer_bits": struct.calcsize("P") * 8,
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "execution_backend": "CPU",
        "native_apple_silicon_process": platform.system() == "Darwin" and machine == "arm64",
    }


def doctor_report(*, require_dev: bool = False) -> dict[str, Any]:
    """Check imports and Python support; pytest is required only with ``--dev``."""
    checks: dict[str, Any] = {}
    for name in (*RUNTIME_PACKAGES, "pytest"):
        try:
            module = importlib.import_module(name)
            checks[name] = {"import_ok": True, "version": getattr(module, "__version__", None)}
        except Exception as error:
            checks[name] = {"import_ok": False, "error": f"{type(error).__name__}: {error}"}
    python_ok = sys.version_info >= (3, 11)
    runtime_ok = python_ok and all(checks[name]["import_ok"] for name in RUNTIME_PACKAGES)
    dev_ok = runtime_ok and checks["pytest"]["import_ok"]
    return {
        "ok": dev_ok if require_dev else runtime_ok,
        "python_supported": python_ok,
        "runtime_ready": runtime_ok,
        "development_ready": dev_ok,
        "software_versions": software_versions(),
        "environment": cpu_environment(),
        "package_checks": checks,
        "notes": [
            "Local CPU software; no cloud, accounts, GPU, or physical devices required.",
            "Environment checks are not validation of an electron-scattering solver.",
        ],
    }
