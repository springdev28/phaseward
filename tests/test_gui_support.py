"""Headless GUI adapters, manifest integrity and no dependency on Streamlit in the CLI."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
import pytest

from qwave.config import ConfigError, PacketConfig
from qwave.gui_config import PreviewSettings, device_arrays, preview_model, preview_request
from qwave.gui_jobs import request_key
from qwave.gui_results import discover_results, json_bytes, load_bundle, safe_path, strict_json
from qwave.gui_worker import validate_request


def test_voltage_mapping_is_explicit_signed_and_bounded() -> None:
    settings = PreviewSettings()
    with pytest.raises(ConfigError,match="coupling"):
        replace(settings,gate_input_unit="mV")
    voltage = replace(settings,gate_input_unit="mV",coupling_mev_per_mv=-.5)
    np.testing.assert_array_equal(voltage.amplitudes_mev,[-4.,-7.5,-6.,-3.])
    reference = device_arrays(preview_model(settings))
    actual = device_arrays(preview_model(voltage))
    np.testing.assert_allclose(actual["potential_mev"],-.5*reference["potential_mev"],rtol=0,atol=1e-14)
    with pytest.raises(ValueError,match="bound"):
        preview_model(replace(settings,gate_values=(26.,0.,0.,0.)))
    outside = abs(reference["x_nm"]) >= settings.length_nm/2
    assert not reference["potential_mev"][outside].any()


def test_packet_adapter_preserves_nodal_potential_and_phase_basis() -> None:
    from qwave.potentials import sample_potential
    settings = PreviewSettings(seed=600031)
    request = preview_request(settings,"wave")
    packet = PacketConfig.from_mapping(request["packet"])
    arrays = device_arrays(preview_model(settings))
    np.testing.assert_array_equal(sample_potential(arrays["x_nm"],packet.scattering["potential"]),arrays["potential_mev"])
    assert packet.scattering["left_lead_mev"] == packet.scattering["right_lead_mev"] == 0
    assert packet.scattering["x_min_nm"] == arrays["x_nm"][0]
    assert packet.delay_alignment["max_ps"] == .1
    assert packet.reference_potential == {"kind":"free","offset_mev":0.}


@pytest.mark.parametrize("operation",["device","wave","disorder"])
def test_exported_preview_roundtrip_and_tamper_rejection(operation: str) -> None:
    request = preview_request(PreviewSettings(),operation)
    loaded = strict_json(json_bytes(request))
    validate_request(loaded)
    assert loaded == request
    changed = deepcopy(request)
    changed["model"]["scattering"]["effective_mass_ratio"] = .08
    with pytest.raises(ValueError,match="differ"):
        validate_request(changed)
    with pytest.raises(ValueError,match="duplicate"):
        strict_json('{"seed":1,"seed":2}')
    with pytest.raises(ValueError,match="invalid JSON"):
        strict_json('{"seed":NaN}')


def test_cache_keys_do_not_mix_seed_physics_operation_or_runtime() -> None:
    base = preview_request(PreviewSettings(),"wave")
    runtime = {"source":"first","version":"0.7"}
    key = request_key(base,runtime)
    assert key == request_key(strict_json(json_bytes(base)),runtime)
    for settings in (replace(PreviewSettings(),seed=600002),replace(PreviewSettings(),bandwidth_mev=6.001),
                     replace(PreviewSettings(),gate_values=(8.+1e-10,15.,12.,6.)),replace(PreviewSettings(),grid_points=81)):
        assert key != request_key(preview_request(settings,"wave"),runtime)
    assert key != request_key(preview_request(PreviewSettings(),"device"),runtime)
    assert key != request_key(base,{"source":"second","version":"0.7"})


def make_bundle(root: Path) -> Path:
    """Small actual numeric array export for reader tests, not a scientific result."""
    output = root/"reader_fixture"
    output.mkdir(parents=True)
    np.savez_compressed(output/"arrays.npz",test_values=np.arange(4))
    (output/"config.json").write_bytes(json_bytes({"test_fixture":True}))
    manifest = {"config":{"test_fixture":True},"status":"completed","outputs":{
        p.name:{"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"size_bytes":p.stat().st_size}
        for p in output.iterdir()}}
    (output/"manifest.json").write_bytes(json_bytes(manifest))
    return output


def test_manifest_reader_is_read_only_and_export_preserves_exact_bytes(tmp_path: Path) -> None:
    output = make_bundle(tmp_path)
    before = {p.name:p.read_bytes() for p in output.iterdir()}
    bundle = load_bundle(output,tmp_path)
    np.testing.assert_array_equal(bundle.arrays("arrays.npz")["test_values"],np.arange(4))
    with zipfile.ZipFile(io.BytesIO(bundle.archive())) as archive:
        assert set(archive.namelist()) == set(before)
        for name,data in before.items():
            assert archive.read(name) == data
    assert before == {p.name:p.read_bytes() for p in output.iterdir()}
    assert discover_results(tmp_path) == [output]
    (output/"config.json").write_text("changed")
    with pytest.raises(ValueError,match="integrity"):
        bundle.read("config.json")
    with pytest.raises(ValueError,match="integrity"):
        load_bundle(output,tmp_path)


def test_manifest_rejects_traversal_symlinks_and_pickle_arrays(tmp_path: Path) -> None:
    output = make_bundle(tmp_path)
    with pytest.raises(ValueError,match="unsafe"):
        safe_path(output,"../outside")
    with pytest.raises(ValueError,match="unsafe"):
        safe_path(output,"/etc/passwd")
    (output/"link").symlink_to(output/"config.json")
    with pytest.raises(ValueError,match="symbolic"):
        safe_path(output,"link")
    np.savez_compressed(output/"arrays.npz",unsafe=np.array([{}],dtype=object))
    manifest = strict_json((output/"manifest.json").read_bytes())
    file = output/"arrays.npz"
    manifest["outputs"]["arrays.npz"] = {"sha256":hashlib.sha256(file.read_bytes()).hexdigest(),"size_bytes":file.stat().st_size}
    (output/"manifest.json").write_bytes(json_bytes(manifest))
    with pytest.raises(ValueError,match="Object arrays"):
        load_bundle(output,tmp_path).arrays("arrays.npz")


def test_cli_does_not_import_optional_streamlit() -> None:
    script = '''
import importlib.abc, sys
class DenyGUI(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] == 'streamlit':
   raise ImportError('GUI intentionally unavailable')
sys.meta_path.insert(0,DenyGUI())
from qwave.cli import main
assert main(['config-check','examples/demo.json']) == 0
assert 'streamlit' not in sys.modules
'''
    result = subprocess.run([sys.executable,"-c",script],capture_output=True,text=True)
    assert result.returncode == 0,result.stderr


def test_experiment_request_rejects_implicit_research_and_seed_overlap() -> None:
    from qwave.experiment_config import preset_config
    request = {"schema_version":1,"scope":"saved_research_run","operation":"experiment",
               "experiment":preset_config("smoke",research=True).to_dict(),"allow_research":False}
    with pytest.raises(ValueError,match="opt-in"):
        validate_request(request)
    request["allow_research"] = True
    validate_request(request)
    ensembles = request["experiment"]["optimization"]["ensembles"]
    ensembles["heldout_seed"] = ensembles["training_seed"]
    with pytest.raises(ConfigError,match="overlap|distinct"):
        validate_request(request)
