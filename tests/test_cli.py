"""Exercise the installed CLI from outside the repository and failure paths."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from qwave import __version__
from qwave.cli import main
from qwave.config import DemoConfig
from qwave.diagnostics import doctor_report


def test_installed_entrypoint_and_module(tmp_path: Path) -> None:
    """Both entry paths must resolve the installed src-layout package."""
    entrypoint = Path(sys.executable).parent / "qwave"
    for command in ([str(entrypoint), "--version"], [sys.executable, "-m", "qwave", "--version"]):
        result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=True)
        assert result.stdout.strip() == f"qwave {__version__}"


def test_doctor_checks_actual_cpu_and_packages(capsys: pytest.CaptureFixture[str]) -> None:
    """Development readiness requires usable imports, not just metadata."""
    assert main(["doctor", "--dev"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] and report["python_supported"] and report["development_ready"]
    assert report["environment"]["machine"]
    assert report["environment"]["logical_cpu_count"] >= 1
    assert all(check["import_ok"] for check in report["package_checks"].values())


@pytest.mark.parametrize(("missing", "expected_runtime"), [("scipy", False), ("pytest", True)])
def test_doctor_reports_missing_dependencies(monkeypatch: pytest.MonkeyPatch, missing: str, expected_runtime: bool) -> None:
    """An unusable runtime fails; absent development tooling is separately reported."""
    import qwave.diagnostics as diagnostics

    original_import = diagnostics.importlib.import_module

    def selective_import(name: str):
        if name == missing:
            raise ImportError("simulated missing dependency")
        return original_import(name)

    monkeypatch.setattr(diagnostics.importlib, "import_module", selective_import)
    report = doctor_report()
    assert report["runtime_ready"] is expected_runtime
    assert report["ok"] is expected_runtime
    assert not doctor_report(require_dev=True)["ok"]


def test_config_check_and_demo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A validated configuration drives the actual CLI export."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(DemoConfig(seed=99).to_dict()), encoding="utf-8")
    assert main(["config-check", str(config_path)]) == 0
    assert json.loads(capsys.readouterr().out)["config"]["seed"] == 99
    output = tmp_path / "output"
    assert main(["demo", "--config", str(config_path), "--output", str(output)]) == 0
    assert "Numerical placeholder" in capsys.readouterr().out
    assert json.loads((output / "manifest.json").read_text())["randomness"]["seeds"] == [99]
    assert main(["demo", "--output", str(output)]) == 2
    assert "File exists" in capsys.readouterr().err


def test_invalid_configuration_has_no_traceback_or_outputs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Malformed input fails before making a misleading result directory."""
    path = tmp_path / "bad.json"
    path.write_text('{"experiment":"scattering"}', encoding="utf-8")
    output = tmp_path / "not-created"
    assert main(["demo", "--config", str(path), "--output", str(output)]) == 2
    error = capsys.readouterr().err
    assert "configuration fields" in error and "Traceback" not in error
    assert not output.exists()


def test_default_demo_works_without_example_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A wheel-installed CLI can run its default demo from any working directory."""
    monkeypatch.chdir(tmp_path)
    assert main(["demo"]) == 0
    assert len(list((tmp_path / "results").glob("demo-*/manifest.json"))) == 1
