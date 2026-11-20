"""One owned CPU subprocess per browser session, exact preview cache and cancellation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from time import monotonic
from typing import Any
from uuid import uuid4

from qwave.diagnostics import cpu_environment, software_versions
from qwave.gui_results import json_bytes, load_bundle
from qwave.provenance import source_identity


def runtime_identity() -> dict[str, Any]:
    """Include source, versions, architecture and fixed worker thread settings in keys."""
    try:
        streamlit_version = version("streamlit")
    except PackageNotFoundError:
        streamlit_version = None
    return {"source":source_identity(), "versions":{**software_versions(),"streamlit":streamlit_version},
            "environment":cpu_environment(), "worker_threads":1}


def request_key(request: dict, identity: dict) -> str:
    """Hash full scientific inputs and runtime without rounding floats or seeds."""
    return hashlib.sha256(json_bytes({"request":request,"runtime":identity})).hexdigest()


@dataclass
class LocalJob:
    """An owned process handle, never an arbitrary saved PID to signal."""

    directory: Path
    process: subprocess.Popen
    cache_key: str
    started: float = field(default_factory=monotonic)
    cancelled_at: float | None = None
    killed: bool = False

    def cancel(self) -> None:
        """Interrupt once; poll escalates to terminate/kill after a bounded grace period."""
        if self.process.poll() is None and self.cancelled_at is None:
            self.cancelled_at = monotonic()
            self.process.send_signal(signal.SIGINT)

    def poll(self) -> dict[str, Any]:
        """Report actual elapsed time, log tail and terminal outcome, never guessed progress."""
        code = self.process.poll()
        if code is None and self.cancelled_at is not None:
            age = monotonic()-self.cancelled_at
            if age > 5:
                self.process.kill()
                self.killed = True
            elif age > 3:
                self.process.terminate()
        log = self.directory/"worker.log"
        tail = ""
        if log.exists():
            with log.open("rb") as stream:
                stream.seek(max(0, log.stat().st_size-6000))
                tail = stream.read().decode("utf-8", errors="replace")
        if code is None:
            status = "cancelling" if self.cancelled_at is not None else "running"
        elif code == 0:
            status = "completed"
        else:
            status = "cancelled" if self.cancelled_at is not None else "failed"
        result = {"status":status,"return_code":code,"elapsed_seconds":monotonic()-self.started,
                  "output":str(self.directory/"result"),"log_tail":tail,"forced_stop":self.killed}
        if code is not None:
            status_path = self.directory/"job_status.json"
            if not status_path.exists():
                status_path.write_bytes(json_bytes(result))
        return result


class JobManager:
    """Session-local cache; experiment suites always create a fresh, unique run."""

    def __init__(self, results_root: Path) -> None:
        self.results_root = results_root.resolve()
        self.active: LocalJob | None = None
        self.cache: dict[str, Path] = {}

    def start(self, request: dict[str, Any], *, reuse_preview: bool = True) -> tuple[LocalJob | None, Path | None]:
        """Start only on an explicit UI action; return a verified exact cache hit if allowed."""
        from qwave.gui_worker import validate_request

        validate_request(request)
        if self.active is not None and self.active.poll()["status"] in ("running","cancelling"):
            raise ValueError("one local job is already running; finish or cancel it first")
        identity = runtime_identity()
        key = request_key(request, identity)
        if reuse_preview and request["scope"] == "illustrative_preview" and key in self.cache:
            bundle = load_bundle(self.cache[key], self.results_root)
            if bundle.status == "completed":
                return None, bundle.root
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid4().hex[:10]
        directory = self.results_root/"gui-jobs"/name
        directory.mkdir(parents=True, exist_ok=False)
        (directory/"request.json").write_bytes(json_bytes({"request":request,"runtime":identity,"cache_key":key}))
        env = dict(os.environ, MPLBACKEND="Agg", MPLCONFIGDIR=str(self.results_root/".matplotlib-gui"),
                   OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1", MKL_NUM_THREADS="1")
        # Use the same interpreter and imported package origin as the panel. No shell and no network.
        env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
        with (directory/"worker.log").open("wb") as stream:
            process = subprocess.Popen([sys.executable,"-u","-m","qwave.gui_worker",str(directory/"request.json")],
                                       cwd=directory, env=env, stdout=stream, stderr=subprocess.STDOUT)
        self.active = LocalJob(directory, process, key)
        return self.active, None

    def poll(self) -> dict[str, Any] | None:
        """Cache only a completed immutable bundle; failures and cancellations are never hits."""
        if self.active is None:
            return None
        result = self.active.poll()
        if result["status"] == "completed" and self.active.cache_key not in self.cache:
            bundle = load_bundle(Path(result["output"]), self.results_root)
            if bundle.status == "completed" and bundle.manifest["scope"] == "illustrative_preview":
                self.cache[self.active.cache_key] = bundle.root
        return result
