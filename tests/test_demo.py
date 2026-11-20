"""Independent numerical references and result-bundle reproducibility checks."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

from qwave.config import DemoConfig, load_config
from qwave.experiments import compute_demo, run_demo


@pytest.mark.parametrize("grid_points", [2, 3, 17, 257])
def test_trapezoid_against_analytical_error(grid_points: int) -> None:
    """For x² on [0,1], trapezoidal error is exactly h²/6 before roundoff."""
    result = compute_demo(DemoConfig(grid_points=grid_points))
    expected = 1 / 3 + 1 / (6 * (grid_points - 1) ** 2)
    assert math.isclose(result.metrics["trapezoid_integral"], expected, rel_tol=0, abs_tol=2e-16)


def test_grid_refinement_has_second_order_error() -> None:
    """Halving spacing reduces this polynomial's truncation error by four."""
    coarse = compute_demo(DemoConfig(grid_points=129))
    fine = compute_demo(DemoConfig(grid_points=257))
    ratio = coarse.metrics["trapezoid_absolute_error"] / fine.metrics["trapezoid_absolute_error"]
    assert math.isclose(ratio, 4, rel_tol=1e-9)


def test_seed_reproducibility_and_independence() -> None:
    """A recorded seed reproduces samples without changing NumPy's global RNG."""
    before = np.random.get_state()
    first = compute_demo(DemoConfig(seed=123))
    second = compute_demo(DemoConfig(seed=123))
    different = compute_demo(DemoConfig(seed=124))
    after = np.random.get_state()
    np.testing.assert_array_equal(first.sample_x, second.sample_x)
    np.testing.assert_array_equal(first.x, different.x)
    assert first.metrics == second.metrics
    assert not np.array_equal(first.sample_x, different.sample_x)
    assert before[0] == after[0] and before[2:] == after[2:]
    np.testing.assert_array_equal(before[1], after[1])


def test_monte_carlo_is_computed_from_recorded_samples() -> None:
    """Verify the reported estimate independently with Python's accurate summation."""
    result = compute_demo(DemoConfig(monte_carlo_samples=1000))
    assert len(result.sample_x) == 1000
    assert np.all((result.sample_x >= 0) & (result.sample_x < 1))
    independent = math.fsum(float(x) ** 2 for x in result.sample_x) / 1000
    assert math.isclose(result.metrics["monte_carlo_integral"], independent, rel_tol=1e-15)


def test_result_formats_and_provenance_agree(tmp_path: Path) -> None:
    """Round-trip public formats and ensure every artifact has verifiable provenance."""
    config = DemoConfig(seed=42, grid_points=17, monte_carlo_samples=31)
    output = run_demo(config, tmp_path / "demo")
    manifest = json.loads((output / "manifest.json").read_text())
    metrics = json.loads((output / "metrics.json").read_text())
    assert load_config(output / "config.json") == config
    assert manifest["config"] == config.to_dict()
    assert manifest["physics_model"] is None
    assert manifest["randomness"]["seeds"] == [42]
    assert manifest["randomness"]["bit_generator"] == "PCG64"
    assert manifest["created_utc"].endswith("+00:00")
    assert manifest["approximations"]["grid_spacing"] == 1 / 16
    assert manifest["units"] == {"x": "1", "f_x": "1", "integral": "1"}
    assert manifest["environment"]["execution_backend"] == "CPU"
    assert manifest["elapsed_seconds_before_manifest"] >= 0
    for name in ("python", "numpy", "scipy", "matplotlib", "qwave"):
        assert manifest["software_versions"][name]
    assert manifest["source"]["files_sha256"]
    assert len(manifest["source"]["sha256"]) == 64
    assert metrics["provenance_file"] == "manifest.json"
    assert "no electron scattering or fidelity" in metrics["scope"]
    for name, info in manifest["outputs"].items():
        content = (output / name).read_bytes()
        assert info["sha256"] == hashlib.sha256(content).hexdigest()
        assert info["size_bytes"] == len(content)
    grid = np.loadtxt(output / "grid.csv", delimiter=",", skiprows=1)
    samples = np.loadtxt(output / "samples.csv", delimiter=",", skiprows=1)
    with np.load(output / "arrays.npz", allow_pickle=False) as arrays:
        np.testing.assert_array_equal(grid[:, 0], arrays["x"])
        np.testing.assert_array_equal(grid[:, 1], arrays["f_x"])
        np.testing.assert_array_equal(samples[:, 0], arrays["sample_x"])
        np.testing.assert_array_equal(samples[:, 1], arrays["sample_f_x"])
        embedded = json.loads(str(arrays["provenance_json"]))
        assert embedded["config"] == manifest["config"]
        assert embedded["source"] == manifest["source"]
        assert embedded["software_versions"] == manifest["software_versions"]


@pytest.mark.parametrize("has_file", [False, True])
def test_existing_output_is_never_overwritten(tmp_path: Path, has_file: bool) -> None:
    """Protect both empty and populated directories without an implicit overwrite."""
    output = tmp_path / "existing"
    output.mkdir()
    if has_file:
        (output / "keep.txt").write_text("original", encoding="utf-8")
    with pytest.raises(FileExistsError):
        run_demo(DemoConfig(), output)
    assert sorted(path.name for path in output.iterdir()) == (["keep.txt"] if has_file else [])
    if has_file:
        assert (output / "keep.txt").read_text() == "original"


def test_headless_plot_is_in_the_manifest(tmp_path: Path) -> None:
    """The optional figure is generated from the demo and included in the inventory."""
    output = run_demo(DemoConfig(), tmp_path / "with-plot", plot=True)
    assert (output / "demo.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    manifest = json.loads((output / "manifest.json").read_text())
    assert "demo.png" in manifest["outputs"]
    assert manifest["options"]["plot"] is True
