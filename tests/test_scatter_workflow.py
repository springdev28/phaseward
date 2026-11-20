"""Physical configuration, supported potential profiles, and reproducible exports."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from qwave.cli import main
from qwave.config import ConfigError, ScatterConfig, load_config
from qwave.experiments import run_scatter
from qwave.potentials import sample_callable, sample_potential
from qwave.scattering import ScatteringError, solve_scattering


@pytest.fixture
def config() -> ScatterConfig:
    """Use the actual checked-in example with a smaller workflow-only sweep."""
    path = Path(__file__).resolve().parents[1]/"examples/barrier.json"
    loaded = load_config(path)
    assert isinstance(loaded, ScatterConfig)
    return replace(loaded, grid_points=161, energy_points=9)


@pytest.mark.parametrize("spec", [
    dict(kind="free", offset_mev=0.),
    dict(kind="rectangular", offset_mev=0., height_mev=40., center_nm=0., width_nm=10.),
    dict(kind="gaussian", offset_mev=0., height_mev=40., center_nm=0., sigma_nm=3.),
    dict(kind="double_barrier", offset_mev=0., height_mev=40., center_nm=0., width_nm=4., separation_nm=12.),
    dict(kind="tabulated", x_nm=[-40, -10, 0, 10, 40], values_mev=[0, 0, 30, 0, 0], interpolation="pchip"),
])
def test_supported_profiles_conserve_probability(spec: dict) -> None:
    """Every exposed profile reaches the same physical solver without model substitution."""
    x = np.linspace(-40, 40, 801)
    potential = sample_potential(x, spec)
    result = solve_scattering(x, potential, np.linspace(2, 100, 53), effective_mass_ratio=.067)
    assert max(result.conservation_error) < 1e-10
    assert np.all(result.T >= 0) and np.all(result.R >= 0)


def test_rectangle_cell_averages_preserve_area() -> None:
    """Avoid a whole-node width bias even when edges fall on grid nodes."""
    for center in [0., .037]:
        x = np.linspace(-40, 40, 801)
        values = sample_potential(x, dict(kind="rectangular", offset_mev=0., height_mev=40., center_nm=center, width_nm=10.))
        assert np.isclose(np.sum(values)*.1, 400., atol=1e-10, rtol=0)


def test_callable_and_tabulated_domains() -> None:
    """User-defined smooth profiles retain supplied values and reject unsafe extrapolation."""
    x = np.linspace(-10, 10, 101)
    potential = sample_callable(x, lambda positions: 5*np.cos(positions/10)**2)
    np.testing.assert_allclose(potential, 5*np.cos(x/10)**2)
    with pytest.raises(ScatteringError):
        sample_callable(x, lambda positions: positions+1j)
    with pytest.raises(ScatteringError, match="cover"):
        sample_potential(x, dict(kind="tabulated", x_nm=[-5,0,5], values_mev=[0,1,0], interpolation="pchip"))


@pytest.mark.parametrize(("field", "value"), [
    ("effective_mass_ratio", 0), ("grid_points", True), ("energy_points", 1),
    ("energy_min_mev", 0), ("energy_max_mev", 1e9), ("right_lead_mev", 3),
    ("unit_system", "SI"), ("x_max_nm", -100), ("conservation_tolerance", -1),
])
def test_invalid_physical_configs_fail(config: ScatterConfig, field: str, value: object) -> None:
    """Reject invalid units, domains, types, and closed channels before producing results."""
    with pytest.raises(ConfigError):
        replace(config, **{field: value})


def test_scattering_bundle_roundtrip(config: ScatterConfig, tmp_path: Path) -> None:
    """JSON/CSV/NPZ retain complex amplitudes, conventions, parameters, and source identity."""
    output = run_scatter(config, tmp_path/"scatter", plot=False)
    manifest = json.loads((output/"manifest.json").read_text())
    assert manifest["config"] == config.to_dict()
    assert manifest["project"] == "Phaseward"
    assert manifest["randomness"]["seeds"] == []
    assert manifest["constants_SI"]["hbar_J_s"] > 0
    assert manifest["phase_convention"]["left_plane_nm"] == config.x_min_nm
    assert manifest["diagnostics"]["conservation_passed"]
    data = np.loadtxt(output/"scattering.csv", delimiter=",", skiprows=1)
    with np.load(output/"arrays.npz", allow_pickle=False) as arrays:
        np.testing.assert_array_equal(data[:,1]+1j*data[:,2], arrays["t"])
        np.testing.assert_array_equal(data[:,3]+1j*data[:,4], arrays["r"])
        np.testing.assert_allclose(data[:,5]+data[:,6], 1, atol=1e-10)
        assert json.loads(str(arrays["provenance_json"]))["config"] == manifest["config"]
    for name, info in manifest["outputs"].items():
        assert hashlib.sha256((output/name).read_bytes()).hexdigest() == info["sha256"]
    with pytest.raises(FileExistsError):
        run_scatter(config, output, plot=False)


def test_scatter_cli_and_figures(config: ScatterConfig, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Run the public command and require all requested physical figures and formats."""
    path = tmp_path/"config.json"
    path.write_text(json.dumps(config.to_dict()))
    assert main(["config-check", str(path)]) == 0
    capsys.readouterr()
    output = tmp_path/"cli"
    assert main(["scatter", "--config", str(path), "--output", str(output)]) == 0
    assert "Phaseward" in capsys.readouterr().out
    for extension in ["png", "svg", "pdf"]:
        assert (output/f"scattering.{extension}").stat().st_size > 1000
    assert main(["demo", "--config", str(path)]) == 2
    assert "demo requires" in capsys.readouterr().err


def test_demo_config_cannot_silently_run_physics(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """An experiment-type mismatch must fail before generating a result."""
    demo = Path(__file__).resolve().parents[1]/"examples/demo.json"
    assert main(["scatter", "--config", str(demo), "--output", str(tmp_path/"no")]) == 2
    assert "stationary_scattering configuration" in capsys.readouterr().err
    assert not (tmp_path/"no").exists()
