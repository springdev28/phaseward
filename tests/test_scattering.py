"""Independent scattering references, conservation, units, and invalid domains."""

import numpy as np
import pytest
from scipy.constants import elementary_charge, hbar, m_e

from qwave.potentials import sample_potential
from qwave.references import (continuum_ode_reference, rectangular_probability,
                              rectangular_transmission_amplitude)
from qwave.scattering import ScatteringError, solve_scattering, transmission_phase


@pytest.mark.parametrize("mass_ratio", [0.067, 0.2, 1.0])
def test_free_channel_complex_phase_and_flux(mass_ratio: float) -> None:
    """Check the independently calculated discrete phase, not just unit probability."""
    x = np.linspace(-20, 20, 801)
    energy = np.array([5., 20., 80.])
    spacing_m = (x[1]-x[0])*1e-9
    hopping_j = hbar**2/(2*mass_ratio*m_e*spacing_m**2)
    q = 2*np.arcsin(np.sqrt(energy*1e-3*elementary_charge/(4*hopping_j)))
    exact_t = np.exp(1j*q*(len(x)-1))
    result = solve_scattering(x, np.zeros_like(x), energy, effective_mass_ratio=mass_ratio)
    np.testing.assert_allclose(result.t, exact_t, atol=1e-10, rtol=0)
    np.testing.assert_allclose(result.r, 0, atol=1e-10, rtol=0)
    np.testing.assert_allclose(result.T, 1, atol=1e-10, rtol=0)
    assert max(result.relative_residual) < 1e-14


def test_free_phase_converges_to_continuum() -> None:
    """Discrete dispersion approaches continuum dispersion, including propagation phase."""
    energy = np.array([5., 20., 80.])
    continuum_k = np.sqrt(2*.067*m_e*energy*1e-3*elementary_charge)/hbar
    exact_t = np.exp(1j*continuum_k*80e-9)
    errors = []
    for points in (161, 321, 641):
        x = np.linspace(-40, 40, points)
        result = solve_scattering(x, 0*x, energy, effective_mass_ratio=.067)
        errors.append(np.max(abs(result.t-exact_t)))
    assert np.all((np.array(errors[:-1])/errors[1:] > 3.8) & (np.array(errors[:-1])/errors[1:] < 4.3))


def test_barrier_above_below_and_at_top_converges() -> None:
    """Verify probabilities and complex t against two continuum closed forms."""
    energies = np.array([5., 10., 20., 39., 40., 41., 60., 100.])
    settings = dict(kind="rectangular", offset_mev=0., height_mev=40., center_nm=0., width_nm=10.)
    exact_T = rectangular_probability(energies, height_mev=40, width_nm=10, effective_mass_ratio=.067)
    exact_t = rectangular_transmission_amplitude(energies, height_mev=40, width_nm=10,
                                                 effective_mass_ratio=.067, reference_length_nm=80)
    np.testing.assert_allclose(abs(exact_t)**2, exact_T, atol=1e-14, rtol=0)
    errors = []
    for points in (321, 641, 1281):
        x = np.linspace(-40, 40, points)
        result = solve_scattering(x, sample_potential(x, settings), energies, effective_mass_ratio=.067)
        errors.append(np.max(abs(result.T-exact_T)))
        assert max(result.conservation_error) < 1e-10
    assert np.all(np.array(errors[:-1])/errors[1:] > 3.8)
    # Measured dx=.0625 nm study gives 2.575e-5 in T and 8.966e-4 in complex t.
    assert errors[-1] < 4e-5
    assert max(abs(result.t-exact_t)) < 1.1e-3
    np.testing.assert_allclose(result.R, 1-exact_T, atol=4e-5, rtol=0)


def test_gaussian_matches_independent_continuum_ode() -> None:
    """Cross-check both complex amplitudes against adaptive continuum ODE matching."""
    energies = np.array([10., 25., 50., 80.])
    x = np.linspace(-30, 30, 961)

    def potential(position):
        return 20*np.exp(-.5*(position/3)**2)

    expected = np.array([continuum_ode_reference(e, potential, x_min_nm=-30, x_max_nm=30,
                                                effective_mass_ratio=.067) for e in energies])
    result = solve_scattering(x, potential(x), energies, effective_mass_ratio=.067)
    # Resolution-specific guards from the recorded convergence study, not physical laws.
    np.testing.assert_allclose(result.t, expected[:, 0], atol=6e-4, rtol=0)
    np.testing.assert_allclose(result.r, expected[:, 1], atol=5e-5, rtol=0)
    assert max(result.conservation_error) < 1e-10


def test_unequal_lead_flux_normalization_against_discrete_step() -> None:
    """Omitting the outgoing velocity factor must fail this exact lattice step check."""
    x = np.linspace(-30, 30, 601)
    energy = np.array([20., 40., 80.])
    result = solve_scattering(x, np.where(x < 0, 0., 15.), energy, effective_mass_ratio=.067,
                              left_lead_mev=0, right_lead_mev=15)
    ql, qr = result.k_left_per_nm*.1, result.k_right_per_nm*.1
    exact_R = (np.sin((ql-qr)/2)/np.sin((ql+qr)/2))**2
    np.testing.assert_allclose(result.R, exact_R, atol=1e-10, rtol=0)
    np.testing.assert_allclose(result.T, 1-exact_R, atol=1e-10, rtol=0)
    assert np.all(result.velocity_right_m_s < result.velocity_left_m_s)


def test_opaque_barrier_has_no_transfer_matrix_overflow() -> None:
    """Very strong evanescence can underflow t but must not overflow or violate flux."""
    x = np.linspace(-600, 600, 4801)
    spec = dict(kind="rectangular", offset_mev=0., height_mev=1000., center_nm=0., width_nm=1000.)
    result = solve_scattering(x, sample_potential(x, spec), [1., 5., 10.], effective_mass_ratio=.067)
    assert np.all(np.isfinite(result.t)) and np.all(np.isfinite(result.r))
    assert np.all(result.T < 1e-250)
    assert np.all(np.isnan(transmission_phase(result.t)))
    assert max(result.conservation_error) < 1e-10


@pytest.mark.parametrize("fraction", [-0.1, 0., 1e-16, 1., 1.1])
def test_forbidden_discrete_lead_energies_rejected(fraction: float) -> None:
    """The finite lattice band and numerically unresolved band edges are explicit."""
    x = np.linspace(-10, 10, 21)
    hopping_mev = hbar**2/(2*.067*m_e*1e-18)/(elementary_charge*1e-3)
    with pytest.raises(ScatteringError, match="lead requires"):
        solve_scattering(x, x*0, [4*hopping_mev*fraction], effective_mass_ratio=.067)


def test_closed_right_channel_is_explicitly_unsupported() -> None:
    """A closed outgoing channel must not be silently assigned a propagating wave."""
    x = np.linspace(-10, 10, 101)
    with pytest.raises(ScatteringError, match="right lead"):
        solve_scattering(x, x*0, [10], effective_mass_ratio=.067, right_lead_mev=20)


@pytest.mark.parametrize("bad_mass", [0, -1, True, np.nan, np.inf, 1j])
def test_invalid_mass_rejected(bad_mass) -> None:
    """The effective mass is explicit, finite, real, and positive."""
    x = np.linspace(-10, 10, 101)
    with pytest.raises(ScatteringError):
        solve_scattering(x, x*0, [10], effective_mass_ratio=bad_mass)


def test_complex_potential_and_nonuniform_grid_rejected() -> None:
    """Do not silently switch to absorption or nonuniform finite differences."""
    x = np.linspace(-10, 10, 101)
    with pytest.raises(ScatteringError):
        solve_scattering(x, x*0+1j, [10], effective_mass_ratio=.067)
    x[40] += .01
    with pytest.raises(ScatteringError, match="uniformly"):
        solve_scattering(x, x*0, [10], effective_mass_ratio=.067)


def test_phase_uses_complex_data_and_masks_disconnected_segments() -> None:
    """Unwrap a real phase crossing; do not bridge zeros or infer phase from T."""
    values = np.array([np.exp(3j), np.exp(3.3j), 0, np.exp(-2j), np.exp(-1.5j)])
    phase = transmission_phase(values)
    np.testing.assert_allclose(phase[:2], [3, 3.3], atol=1e-14)
    assert np.isnan(phase[2])
    np.testing.assert_allclose(phase[3:], [-2, -1.5], atol=1e-14)
