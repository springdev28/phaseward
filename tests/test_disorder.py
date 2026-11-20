"""Covariance scaling, weighted KL normalization, seed replay, and bounded gates."""

from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from qwave.disorder import (covariance_matrix, covariance_modes, covariance_statistics,
                            lag_correlations, sample_disorder)
from qwave.gates import build_gates, channel_envelope, channel_indices


@pytest.fixture
def gate_settings() -> dict:
    """The actual four-gate configuration, without an invented alternative fixture."""
    path = Path(__file__).resolve().parents[1]/"examples/disorder.json"
    return json.loads(path.read_text())["model"]["gates"]


def test_gate_contributions_bounds_and_lead_exclusion(gate_settings: dict) -> None:
    """Coefficients are peak potential energies; all contributions vanish outside the channel."""
    x = np.linspace(-40, 40, 401)
    gates = build_gates(x, (-30.,30.), gate_settings)
    assert len(gates.names) == 4
    np.testing.assert_allclose(np.max(abs(gates.shapes), axis=0), 1.)
    np.testing.assert_array_equal(gates.total_mev, gates.contributions_mev.sum(axis=1))
    np.testing.assert_array_equal(gates.contributions_mev, gates.shapes*gates.amplitudes_mev)
    assert np.all(gates.shapes[abs(x) >= 30] == 0)
    changed = deepcopy(gate_settings)
    changed["profiles"][0]["amplitude_mev"] = 31
    with pytest.raises(ValueError, match="bounds"):
        build_gates(x, (-30.,30.), changed)
    changed = deepcopy(gate_settings)
    changed["total_abs_bound_mev"] = 1.
    with pytest.raises(ValueError, match="summed"):
        build_gates(x, (-30.,30.), changed)


@pytest.mark.parametrize("shape", [
    {"kind": "raised_cosine", "center_nm": 0., "half_width_nm": 7.},
    {"kind": "tabulated", "x_nm": [-30,-10,0,10,30], "values": [0,-.5,1,.5,0], "interpolation": "pchip"},
])
def test_alternative_and_user_supplied_shapes(gate_settings: dict, shape: dict) -> None:
    """Both supported alternatives retain signs, normalization, and explicit support."""
    gate_settings["profiles"] = [{"name": "custom", "amplitude_mev": -3., "bounds_mev": [-5.,5.], "shape": shape}]
    x = np.linspace(-40,40,401)
    result = build_gates(x, (-30.,30.), gate_settings)
    assert max(abs(result.total_mev)) == pytest.approx(3.)
    assert np.all(result.total_mev[abs(x) >= 30] == 0)


def test_channel_and_gate_schema_rejections(gate_settings: dict) -> None:
    """No extrapolation, unbounded gate, or off-grid channel is silently accepted."""
    x = np.linspace(-40,40,401)
    for bounds in [(-40.,30.), (-30.01,30.), (1.,0.)]:
        with pytest.raises(ValueError):
            channel_indices(x, bounds)
    for change in [{"normalization":"integral"}, {"taper_nm":0.}, {"unknown":1}]:
        with pytest.raises(ValueError):
            build_gates(x, (-30.,30.), {**gate_settings, **change})
    duplicate = deepcopy(gate_settings)
    duplicate["profiles"][1]["name"] = duplicate["profiles"][0]["name"]
    with pytest.raises(ValueError, match="unique"):
        build_gates(x, (-30.,30.), duplicate)


@pytest.mark.parametrize("kernel,value_at_ell", [
    ("gaussian", np.exp(-.5)), ("exponential", np.exp(-1.)),
    ("matern32", (1+np.sqrt(3))*np.exp(-np.sqrt(3))),
])
def test_kernel_variance_length_scale_and_positive_semidefiniteness(kernel: str, value_at_ell: float) -> None:
    """Check the covariance formula independently at zero and one length scale."""
    x = np.linspace(-10,10,41)
    covariance = covariance_matrix(x, sigma_mev=3., correlation_length_nm=2., kernel=kernel)
    np.testing.assert_array_equal(np.diag(covariance), np.full(41,9.))
    assert covariance[20,24] == pytest.approx(9*value_at_ell, abs=1e-14)
    assert min(np.linalg.eigvalsh(covariance)) > -1e-12
    expected = covariance[0]/9
    np.testing.assert_allclose(lag_correlations(covariance), expected, atol=2e-15)


def test_boundary_taper_changes_covariance_explicitly() -> None:
    """Tapering preserves PSD but reduces local variance near channel edges."""
    x = np.linspace(-10,10,81)
    raw = covariance_matrix(x, sigma_mev=2., correlation_length_nm=3.)
    tapered = covariance_matrix(x, sigma_mev=2., correlation_length_nm=3., boundary_taper_nm=4.)
    envelope = channel_envelope(x, (-10.,10.), 4.)
    np.testing.assert_allclose(tapered, raw*envelope[:,None]*envelope[None,:], atol=0)
    np.testing.assert_allclose(np.diag(tapered), 4*envelope**2, atol=1e-15)
    assert np.all(tapered[[0,-1]] == 0)
    modes = covariance_modes(x, tapered, retained_modes=5)
    assert np.allclose(modes.retained_shapes[[0,-1]], 0, atol=1e-13)


def test_weighted_kl_orthogonality_covariance_reconstruction_and_variance_fraction() -> None:
    """Grid spacing belongs in the eigenproblem, and coefficient variance belongs in eta."""
    x = np.linspace(-10,10,81)
    covariance = covariance_matrix(x, sigma_mev=2., correlation_length_nm=2.)
    modes = covariance_modes(x, covariance, retained_modes=5)
    phi, weights, eigenvalues = modes.shapes_per_sqrt_nm, modes.weights_nm, modes.eigenvalues_mev2_nm
    np.testing.assert_allclose(phi.T @ (weights[:,None]*phi), np.eye(81), atol=2e-14)
    np.testing.assert_allclose((phi*eigenvalues) @ phi.T, covariance, atol=2e-13)
    assert sum(eigenvalues) == pytest.approx(4*20, abs=2e-12)
    assert np.dot(weights, np.diag(modes.retained_covariance)) == pytest.approx(sum(eigenvalues[:5]), abs=2e-12)
    assert modes.diagnostics["retained_variance_fraction"] == pytest.approx(sum(eigenvalues[:5])/(4*20))
    assert np.all(np.diag(modes.retained_covariance) <= 4+1e-13)


def test_covariance_eigenvalues_converge_with_physical_grid_weights() -> None:
    """Refining the grid must not multiply the covariance operator eigenvalues by node count."""
    spectra = []
    for count in [41,81,161]:
        x = np.linspace(-10,10,count)
        modes = covariance_modes(x, covariance_matrix(x,sigma_mev=2.,correlation_length_nm=2.), retained_modes=5)
        spectra.append(modes.retained_eigenvalues)
    difference = np.linalg.norm(spectra[0]-spectra[1])/np.linalg.norm(spectra[1]-spectra[2])
    assert 3.8 < difference < 4.2
    assert np.max(abs(spectra[1]/spectra[2]-1)) < .001


@pytest.mark.parametrize("kernel", ["gaussian", "exponential", "matern32"])
def test_seeded_covariance_scaling_and_statistical_error(kernel: str) -> None:
    """Empirical variance/correlation must agree within independently derived Gaussian errors."""
    x = np.linspace(-10,10,41)
    covariance = covariance_matrix(x, sigma_mev=2., correlation_length_nm=2., kernel=kernel)
    modes = covariance_modes(x, covariance, retained_modes=5)
    draws = sample_disorder(modes,sample_count=6000,seed=74527)
    repeated = sample_disorder(modes,sample_count=6000,seed=74527)
    np.testing.assert_array_equal(draws.full_mev, repeated.full_mev)
    np.testing.assert_array_equal(draws.coefficients_mev_sqrt_nm, draws.standard_normals*np.sqrt(modes.eigenvalues_mev2_nm))
    np.testing.assert_allclose(draws.full_mev @ (modes.weights_nm[:,None]*modes.retained_shapes),
                               draws.coefficients_mev_sqrt_nm[:,:5], atol=2e-13)
    for data, target in ((draws.full_mev, covariance), (draws.retained_mev, modes.retained_covariance)):
        statistics = covariance_statistics(data,target)
        summary = statistics["summary"]
        assert summary["max_abs_mean_in_standard_errors"] < 6
        assert summary["max_abs_variance_error_in_standard_errors"] < 6
        assert summary["frobenius_error_in_expected_sampling_rms"] < 4
        # One covariance entry has this variance under Gaussian sampling (Wishart law).
        i,j=20,24
        standard_error=np.sqrt((target[i,j]**2+target[i,i]*target[j,j])/(6000-1))
        assert abs(statistics["empirical_covariance_mev2"][i,j]-target[i,j]) < 6*standard_error
    residual = draws.full_mev-draws.retained_mev
    actual = np.mean(residual**2 @ modes.weights_nm)
    tail = modes.eigenvalues_mev2_nm[5:]
    standard_error = np.sqrt(2*np.sum(tail**2)/6000)
    assert abs(actual-sum(tail)) < 6*standard_error
    assert not np.allclose(draws.full_mev.mean(axis=1), 0)  # Samples are not recentered spatially.


def test_covariance_amplitude_scaling_is_not_sample_normalization() -> None:
    """Multiplying sigma by two multiplies covariance by four and paired realizations by two."""
    x=np.linspace(-10,10,41)
    first=covariance_modes(x,covariance_matrix(x,sigma_mev=1.,correlation_length_nm=2.),retained_modes=5)
    second=covariance_modes(x,covariance_matrix(x,sigma_mev=2.,correlation_length_nm=2.),retained_modes=5)
    a=sample_disorder(first,sample_count=32,seed=19)
    b=sample_disorder(second,sample_count=32,seed=19)
    np.testing.assert_allclose(b.full_mev,2*a.full_mev,atol=0,rtol=0)


def test_invalid_covariance_and_sampler_inputs_are_rejected() -> None:
    """Reject indefinite, nonsymmetric, unresolved, or unseeded requests."""
    x=np.linspace(-1,1,3)
    for matrix in (np.zeros((3,3)), np.full((3,3),2.)-np.eye(3),
                   np.array([[1,1,0],[0,1,0],[0,0,1]]), np.eye(3).astype(complex)):
        with pytest.raises(ValueError):
            covariance_modes(x,matrix,retained_modes=1)
    with pytest.raises(ValueError,match="resolved"):
        covariance_modes(x,np.ones((3,3)),retained_modes=2)
    assert np.all(covariance_matrix(x,sigma_mev=0.,correlation_length_nm=1.) == 0)
    for change in ({"sigma_mev":-1.}, {"correlation_length_nm":0.}, {"kernel":"unknown"}):
        with pytest.raises(ValueError):
            covariance_matrix(x,**{"sigma_mev":1.,"correlation_length_nm":1.,**change})
    modes=covariance_modes(x,np.eye(3),retained_modes=2)
    with pytest.raises(ValueError,match="seed"):
        sample_disorder(modes,sample_count=32,seed=True)
