"""Optional Streamlit AppTest plus actual subprocess completion/cancellation checks."""

from dataclasses import replace
from pathlib import Path
import subprocess
import sys
from time import monotonic, sleep

import numpy as np
import pytest

pytest.importorskip("streamlit",minversion="1.67")
from streamlit.testing.v1 import AppTest

from qwave.gui import VIEWS
from qwave.gui_config import PreviewSettings, preview_request
from qwave.gui_jobs import JobManager, LocalJob
from qwave.gui_results import load_bundle


def app_at(workspace: Path) -> AppTest:
    return AppTest.from_string(f"from pathlib import Path\nfrom qwave.gui import main\nmain(Path({str(workspace)!r}))",default_timeout=30)


def test_navigation_and_slider_edits_do_not_run_scientific_work(tmp_path: Path,monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args,**kwargs):
        raise AssertionError("a scientific calculation ran without pressing Run")
    monkeypatch.setattr(JobManager,"start",forbidden)
    import qwave.scattering, qwave.disorder
    monkeypatch.setattr(qwave.scattering,"solve_scattering",forbidden)
    monkeypatch.setattr(qwave.disorder,"covariance_modes",forbidden)
    app = app_at(tmp_path).run()
    app.slider(key="length").set_value(80.).run()
    app.number_input(key="gate_meV_0").set_value(3.).run()
    for view in VIEWS[1:]:
        app.radio(key="view").set_value(view).run()
        assert not app.exception and not app.error
    app.radio(key="view").set_value(VIEWS[0]).run()
    assert app.number_input(key="gate_meV_0").value == 3.
    assert app.session_state["job_manager"].active is None
    assert not (tmp_path/"results"/"gui-jobs").exists()


def test_run_wave_exports_stale_warning_and_readonly_reopen(tmp_path: Path,monkeypatch: pytest.MonkeyPatch) -> None:
    app = app_at(tmp_path).run()
    app.radio(key="view").set_value(VIEWS[1]).run()
    app.selectbox(key="nx").set_value(81).run()
    app.button(key="run_wave").click().run()
    manager = app.session_state["job_manager"]
    assert manager.active is not None
    deadline = monotonic()+60
    while manager.poll()["status"] in ("running","cancelling") and monotonic()<deadline:
        sleep(.1)
    state = manager.poll()
    assert state["status"] == "completed",state
    app.run()
    assert not app.exception and not app.error
    bundle = app.session_state["last_wave"]
    assert bundle.status == "completed"
    metrics = bundle.json("packet/metrics.json")
    assert 0 < metrics["p_transmitted"] <= 1
    assert 0 <= metrics["raw_fidelity"] <= 1
    assert "packet/packet_position.png" in bundle.files
    data = bundle.arrays("packet/arrays.npz")
    np.testing.assert_allclose(data["transmitted_position_density_per_nm"],abs(data["transmitted_psi_per_sqrt_nm"])**2,rtol=1e-14)
    app.number_input(key="bandwidth").set_value(7.).run()
    assert any("Settings changed" in w.value for w in app.warning)
    app.button(key="zip_"+bundle.fingerprint).click().run()
    assert len(app.session_state["exports_"+bundle.fingerprint]["all"]) > 0
    def forbidden(*args,**kwargs):
        raise AssertionError("saved-result browsing tried to launch a run")
    monkeypatch.setattr(JobManager,"start",forbidden)
    app.radio(key="data_source").set_value("Open saved results").run()
    app.button(key="open_result").click().run()
    assert not app.exception and not app.error
    assert app.session_state["opened_result"].fingerprint == bundle.fingerprint
    assert app.session_state["opened_result"].manifest["config"]["preview_settings"]["bandwidth_mev"] == 6.


def test_exact_cache_reuse_and_changed_seed_starts_another_job(tmp_path: Path) -> None:
    manager = JobManager(tmp_path)
    request = preview_request(PreviewSettings(),"device")
    job,_ = manager.start(request)
    job.process.wait(timeout=45)
    assert manager.poll()["status"] == "completed"
    bundle = load_bundle(job.directory/"result",tmp_path)
    again,path = manager.start(request)
    assert again is None and path == bundle.root
    changed = preview_request(replace(PreviewSettings(),seed=600002),"device")
    next_job,path = manager.start(changed)
    assert path is None and next_job.directory != job.directory
    next_job.process.wait(timeout=45)
    assert manager.poll()["status"] == "completed"


def test_cancel_owned_process_keeps_partial_artifacts(tmp_path: Path) -> None:
    # A deterministic slow worker stand-in tests real OS signalling without wasting solver work.
    partial = tmp_path/"partial.txt"
    partial.write_text("partial work must survive")
    process = subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    job = LocalJob(tmp_path,process,"test-key")
    job.cancel()
    process.wait(timeout=10)
    assert job.poll()["status"] == "cancelled"
    assert partial.read_text() == "partial work must survive"
    assert (tmp_path/"job_status.json").exists()


def test_privacy_override_is_rejected(tmp_path: Path,monkeypatch: pytest.MonkeyPatch) -> None:
    import streamlit as st
    original = st.get_option
    monkeypatch.setattr(st,"get_option",lambda key:True if key=="browser.gatherUsageStats" else original(key))
    app = app_at(tmp_path).run()
    assert any("telemetry off" in error.value for error in app.error)
    assert not app.button


def test_all_four_views_open_a_real_experiment_without_recomputation(tmp_path: Path,monkeypatch: pytest.MonkeyPatch) -> None:
    from qwave.experiment_config import ExperimentConfig,preset_config
    from qwave.experiment_runner import run_experiment
    data = preset_config("smoke").to_dict()
    data["optimization"]["optimizer"].update(starts=1,forward_work_budget=15,maxiter=2,initialization_seed=2613001)
    data["optimization"]["ensembles"].update(training_samples=2,validation_samples=2,heldout_samples=3,
        training_seed=2613002,validation_seed=2613003,heldout_seed=2613004)
    data["convergence"].update(seed=2613005,spatial_grid_points=[41,81,161],energy_points=[41,57,81],sample_counts=[2,3,4])
    data["statistics"]["bootstrap_seed"] = 2613006
    output = tmp_path/"results"/"suite"
    run_experiment(ExperimentConfig.from_mapping(data),output,plot=False)
    def forbidden(*args,**kwargs):
        raise AssertionError("read-only browsing attempted a solve")
    import qwave.scattering, qwave.disorder
    monkeypatch.setattr(qwave.scattering,"solve_scattering",forbidden)
    monkeypatch.setattr(qwave.disorder,"covariance_modes",forbidden)
    monkeypatch.setattr(JobManager,"start",forbidden)
    app = app_at(tmp_path).run()
    app.radio(key="data_source").set_value("Open saved results").run()
    app.button(key="open_result").click().run()
    for view in VIEWS:
        app.radio(key="view").set_value(view).run()
        assert not app.exception and not app.error, [e.value for e in app.error]
    rows = app.dataframe[0].value
    assert len(rows) == 4 and rows["feasible"].notna().all()
    assert app.session_state["job_manager"].active is None
