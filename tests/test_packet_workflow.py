"""Packet CLI, target conventions, provenance, optional display, and strict config."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from qwave.cli import main
from qwave.config import ConfigError, PacketConfig, load_config
from qwave.packet_experiments import run_packet


@pytest.fixture
def config() -> PacketConfig:
    """A reduced version of the real example for workflow tests."""
    path = Path(__file__).resolve().parents[1]/"examples/wavepacket.json"
    settings = json.loads(path.read_text())
    settings["scattering"]["grid_points"] = 161
    settings["scattering"]["energy_points"] = 401
    settings["bandwidth_sweep_mev"] = [2., 4., 8.]
    settings["reconstruction"]["enabled"] = False
    return PacketConfig.from_mapping(settings)


def test_exact_example_config_loads() -> None:
    """The user-facing example is complete and validates without default substitutions."""
    path = Path(__file__).resolve().parents[1]/"examples/wavepacket.json"
    assert isinstance(load_config(path), PacketConfig)


def test_packet_exports_preserve_complex_spectra_and_metrics(config: PacketConfig, tmp_path: Path) -> None:
    """Round-trip archived spectra, normalized states, target, seeds, and checksums."""
    output = run_packet(config, tmp_path/"packet", plot=False)
    metrics = json.loads((output/"metrics.json").read_text())
    manifest = json.loads((output/"manifest.json").read_text())
    assert manifest["config"] == config.to_dict()
    assert manifest["reference_device_config"]["potential"] == config.reference_potential
    assert manifest["reference_device_config"]["left_lead_mev"] == config.scattering["left_lead_mev"]
    assert manifest["randomness"]["seeds"] == []
    assert manifest["normalization"]["bandwidth"] == "standard deviation of untruncated |A|^2"
    assert metrics["diagnostics"]["conservation_passed"]
    assert 0 < metrics["p_transmitted"] < .6
    assert metrics["raw_fidelity"] > .8
    assert not np.isclose(metrics["p_transmitted"], metrics["raw_fidelity"])
    data = np.loadtxt(output/"spectrum.csv", delimiter=",", skiprows=1)
    with np.load(output/"arrays.npz", allow_pickle=False) as arrays:
        np.testing.assert_array_equal(data[:,1]+1j*data[:,2], arrays["incoming_A"])
        weights = arrays["weights_mev"]
        assert np.dot(weights, abs(arrays["incoming_A"])**2) == pytest.approx(1, abs=1e-14)
        assert np.dot(weights, abs(arrays["normalized_transmitted_spectrum"])**2) == pytest.approx(1, abs=1e-14)
        measured = abs(np.dot(weights, arrays["normalized_target_spectrum"].conj()*arrays["normalized_transmitted_spectrum"]))**2
        assert metrics["raw_fidelity"] == pytest.approx(measured, abs=1e-14)
        assert json.loads(str(arrays["provenance_json"]))["config"] == config.to_dict()
    for name, info in manifest["outputs"].items():
        assert hashlib.sha256((output/name).read_bytes()).hexdigest() == info["sha256"]
    assert load_config(output/"config.json") == config
    with pytest.raises(FileExistsError):
        run_packet(config, output, plot=False)


def test_actual_equals_declared_target_has_unit_fidelity(config: PacketConfig, tmp_path: Path) -> None:
    """An undistorted output matches the target even though the device reflects probability."""
    matched = replace(config, reference_potential=config.scattering["potential"])
    output = run_packet(matched, tmp_path/"same", plot=False)
    metrics = json.loads((output/"metrics.json").read_text())
    assert metrics["p_transmitted"] < 1
    assert metrics["raw_fidelity"] == pytest.approx(1, abs=1e-13)
    assert metrics["aligned_fidelity"] == pytest.approx(1, abs=1e-13)


def test_disabled_alignment_is_explicit(config: PacketConfig, tmp_path: Path) -> None:
    """Optional alignment never silently changes the primary raw metric."""
    settings = {**config.delay_alignment, "enabled": False}
    output = run_packet(replace(config, delay_alignment=settings), tmp_path/"raw", plot=False)
    metrics = json.loads((output/"metrics.json").read_text())
    assert metrics["raw_fidelity"] is not None
    assert metrics["aligned_fidelity"] is None and metrics["estimated_delay_ps"] is None
    assert metrics["alignment_status"] == "disabled"


def test_packet_cli_creates_physical_plots_and_exact_config(config: PacketConfig, tmp_path: Path, capsys) -> None:
    """Run the actual command, including velocity-correct lead reconstruction."""
    config = replace(config, reconstruction={**config.reconstruction, "enabled": True, "position_points": 401})
    path = tmp_path/"packet.json"
    path.write_text(json.dumps(config.to_dict()))
    assert main(["config-check", str(path)]) == 0
    capsys.readouterr()
    output = tmp_path/"results"
    assert main(["packet", "--config", str(path), "--output", str(output)]) == 0
    text = capsys.readouterr().out
    assert "Transmitted probability" in text and "Raw conditional fidelity" in text
    for stem in ("packet_spectra", "packet_bandwidth", "packet_delay", "packet_position"):
        for extension in ("png", "svg", "pdf"):
            assert (output/f"{stem}.{extension}").stat().st_size > 1000
    assert json.loads((output/"config.json").read_text()) == config.to_dict()
    position = np.loadtxt(output/"transmitted_packet.csv", delimiter=",", skiprows=1)
    assert np.all(position[:,0] >= config.scattering["x_max_nm"])
    assert np.all(position[:,3] >= 0)


@pytest.mark.parametrize("change", [
    {"unit_system": "nm_meV"}, {"bandwidth_mev": 0}, {"central_energy_mev": -1},
    {"bandwidth_sweep_mev": [4, 2]}, {"bandwidth_sweep_mev": [True, 4]},
    {"minimum_transmission_probability": 0}, {"extra_physics": "decoherence"},
])
def test_invalid_packet_settings_fail(config: PacketConfig, change: dict) -> None:
    """Reject invalid conventions, unresolved bandwidths, and unknown model requests."""
    with pytest.raises(ConfigError):
        PacketConfig.from_mapping({**config.to_dict(), **change})


def test_nested_configuration_and_resolution_guards(config: PacketConfig) -> None:
    """Shared lead basis, numerical budgets, and strict nested schemas are enforced."""
    with pytest.raises(ConfigError):
        replace(config, scattering={**config.scattering, "energy_points": 400})
    with pytest.raises(ConfigError):
        replace(config, delay_alignment={**config.delay_alignment, "unbounded": True})
    with pytest.raises(ConfigError):
        replace(config, delay_alignment={**config.delay_alignment, "grid_points": 3})
    with pytest.raises(ConfigError):
        replace(config, reconstruction={**config.reconstruction, "source_offset_nm": 10})
    with pytest.raises(ConfigError):
        replace(config, reference_potential={"kind": "free", "offset_mev": 0, "mass": .2})


def test_scatter_config_cannot_run_as_packet(tmp_path: Path, capsys) -> None:
    """No implicit packet distribution or target is selected for another experiment type."""
    path = Path(__file__).resolve().parents[1]/"examples/barrier.json"
    output = tmp_path/"no-output"
    assert main(["packet", "--config", str(path), "--output", str(output)]) == 2
    assert "wave_packet configuration" in capsys.readouterr().err
    assert not output.exists()
