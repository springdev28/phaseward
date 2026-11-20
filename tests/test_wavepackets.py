"""Independent analytic packet checks, quadrature convergence, and lead Jacobians."""

import numpy as np
import pytest
from scipy.constants import elementary_charge, hbar, m_e
from scipy.integrate import quad, trapezoid

from qwave.wavepackets import (HBAR_MEV_PS, DelaySearch, analyze_packet, gaussian_packet,
                              quadrature_weights, reconstruct_lead_packet)


@pytest.fixture
def gaussian():
    """An effectively untruncated Gaussian for closed-form synthetic references."""
    energy = np.linspace(2., 38., 721)
    return gaussian_packet(energy, central_energy_mev=20, bandwidth_mev=2,
                           propagating_bounds_mev=(0, 100))


def test_positive_quadrature_matches_scipy_and_integrates_linear_function() -> None:
    """A separately implemented trapezoidal routine checks nonuniform weights."""
    x = np.array([1., 1.3, 2., 3.7, 5.])
    weights = quadrature_weights(x)
    assert np.all(weights > 0)
    assert np.dot(weights, 2*x+3) == pytest.approx(36.)
    assert np.dot(weights, np.sin(x)) == pytest.approx(trapezoid(np.sin(x), x=x))


def test_truncated_gaussian_is_a_normalized_amplitude() -> None:
    """Record substantial tail removal; amplitude squared, not amplitude, integrates to one."""
    energy = np.linspace(.1, 10, 801)
    packet = gaussian_packet(energy, central_energy_mev=1, bandwidth_mev=2,
                             propagating_bounds_mev=(0, 20))
    assert np.dot(packet.weights_mev, abs(packet.amplitude)**2) == pytest.approx(1, abs=2e-15)
    assert .6 < packet.normalization["untruncated_gaussian_mass_in_window"] < .7
    assert packet.normalization["fraction_of_common_band_mass_in_window"] < 1
    exact = quad(lambda e: np.exp(-.5*((e-1)/2)**2)/(2*np.sqrt(2*np.pi)), .1, 10,
                 epsabs=1e-13, epsrel=1e-13)[0]
    assert packet.normalization["untruncated_gaussian_mass_in_window"] == pytest.approx(exact, abs=1e-13)


def test_identical_reference_and_global_phase(gaussian) -> None:
    """The target may itself filter the spectrum; global phase never changes fidelity."""
    energy = gaussian.energy_mev
    reference = .7*np.exp(1j*.02*(energy-20)**2)
    for phase in [0., 1.73, -2.9]:
        result = analyze_packet(energy, gaussian.amplitude, np.exp(1j*phase)*reference, reference,
                                delay=DelaySearch())
        assert result.p_transmitted == pytest.approx(.49, abs=1e-14)
        assert result.raw_fidelity == pytest.approx(1, abs=2e-14)
        assert result.aligned_fidelity == pytest.approx(1, abs=2e-14)
        assert abs(result.estimated_delay_ps) < 1e-6


def test_constant_loss_retains_conditional_fidelity_but_flags_throughput(gaussian) -> None:
    """A nearly blocked device must not become a good transport result through normalization."""
    result = analyze_packet(gaussian.energy_mev, gaussian.amplitude,
                            np.full(721, 1e-7), np.ones(721), minimum_transmission_probability=1e-8)
    assert result.p_transmitted == pytest.approx(1e-14, rel=1e-14)
    assert result.raw_fidelity == pytest.approx(1, abs=2e-14)
    assert result.low_transmission and not result.low_reference_transmission


@pytest.mark.parametrize("amplitude", [0., 1e-160, 1e-200])
def test_zero_or_underflowing_transmission_has_no_fabricated_state(gaussian, amplitude: float) -> None:
    """Undefined conditional metrics are explicit, including subnormal probability."""
    result = analyze_packet(gaussian.energy_mev, gaussian.amplitude, np.full(721, amplitude),
                            np.ones(721), delay=DelaySearch())
    assert result.raw_fidelity is None and result.aligned_fidelity is None
    assert result.transmitted_state is None and result.low_transmission
    assert result.estimated_delay_ps is None


def test_zero_reference_makes_comparison_undefined(gaussian) -> None:
    """A zero target cannot be normalized or assigned a fidelity."""
    result = analyze_packet(gaussian.energy_mev, gaussian.amplitude, np.ones(721), np.zeros(721))
    assert result.raw_fidelity is None and result.target_state is None
    assert result.low_reference_transmission


@pytest.mark.parametrize("lag", [-.12, .12])
def test_linear_phase_has_analytic_raw_fidelity_and_signed_delay(gaussian, lag: float) -> None:
    """The Gaussian characteristic function independently fixes the sign and value."""
    phase = np.exp(1j*(gaussian.energy_mev-20)*lag/HBAR_MEV_PS)
    result = analyze_packet(gaussian.energy_mev, gaussian.amplitude, phase, np.ones(721), delay=DelaySearch())
    expected = np.exp(-(2*lag/HBAR_MEV_PS)**2)
    assert result.raw_fidelity == pytest.approx(expected, abs=2e-14)
    assert result.estimated_delay_ps == pytest.approx(lag, abs=3e-7)
    assert result.aligned_fidelity == pytest.approx(1, abs=1e-12)
    assert not result.alignment_boundary_hit


def test_bounded_alignment_reports_boundary_and_residual_distortion(gaussian) -> None:
    """The allowed interval is never expanded to force a perfect match."""
    lag = .4
    phase = np.exp(1j*(gaussian.energy_mev-20)*lag/HBAR_MEV_PS)
    settings = DelaySearch(min_ps=-.1, max_ps=.1)
    result = analyze_packet(gaussian.energy_mev, gaussian.amplitude, phase, np.ones(721), delay=settings)
    assert result.estimated_delay_ps == .1 and result.alignment_boundary_hit
    assert result.aligned_fidelity == pytest.approx(np.exp(-(2*(lag-.1)/HBAR_MEV_PS)**2), abs=2e-14)
    assert result.aligned_fidelity < .5


def test_quadratic_phase_distorts_state_without_changing_probability(gaussian) -> None:
    """A chirp has a closed-form Gaussian overlap and cannot be removed by a delay."""
    beta = .08
    t = np.exp(1j*beta*(gaussian.energy_mev-20)**2)
    result = analyze_packet(gaussian.energy_mev, gaussian.amplitude, t, np.ones(721), delay=DelaySearch())
    expected = 1/np.sqrt(1+4*beta**2*2**4)
    assert result.p_transmitted == pytest.approx(1, abs=1e-14)
    assert result.raw_fidelity == pytest.approx(expected, abs=1e-13)
    assert result.aligned_fidelity == pytest.approx(expected, abs=1e-12)


def test_amplitude_filter_changes_both_throughput_and_fidelity(gaussian) -> None:
    """A Gaussian amplitude filter has independently integrable probability and overlap."""
    width = 1.5
    t = np.exp(-(gaussian.energy_mev-20)**2/(4*width**2))
    result = analyze_packet(gaussian.energy_mev, gaussian.amplitude, t, np.ones(721))
    ratio = 2**2/width**2
    assert result.p_transmitted == pytest.approx(1/np.sqrt(1+ratio), abs=1e-13)
    assert result.raw_fidelity == pytest.approx(np.sqrt(1+ratio)/(1+ratio/2), abs=1e-13)
    assert result.raw_fidelity < 1


def test_quadrature_refinement_converges_to_independent_adaptive_integral() -> None:
    """A truncated, distorted spectrum has measurable second-order integration error."""
    def density(e):
        return np.exp(-.5*((e-15)/4)**2)

    def transmission(e):
        return .8*np.exp(-((e-15)/5)**2/4)*np.exp(1j*((e-15)*.1/HBAR_MEV_PS+.025*(e-15)**2))

    z = quad(density, 10, 30, epsabs=1e-12, epsrel=1e-12)[0]
    expected_p = quad(lambda e: density(e)*abs(transmission(e))**2, 10, 30, epsabs=1e-12, epsrel=1e-12)[0]/z
    cross = (quad(lambda e: (density(e)*transmission(e)).real, 10, 30, epsabs=1e-12, epsrel=1e-12)[0]
             + 1j*quad(lambda e: (density(e)*transmission(e)).imag, 10, 30, epsabs=1e-12, epsrel=1e-12)[0])/z
    expected_f = abs(cross)**2/expected_p
    errors = []
    for count in [41, 81, 161, 321]:
        e = np.linspace(10, 30, count)
        packet = gaussian_packet(e, central_energy_mev=15, bandwidth_mev=4, propagating_bounds_mev=(0, 100))
        result = analyze_packet(e, packet.amplitude, transmission(e), np.ones(count))
        errors.append(max(abs(result.p_transmitted-expected_p), abs(result.raw_fidelity-expected_f)))
    assert np.all(np.asarray(errors[:-1])/errors[1:] > 3.9)
    assert errors[-1] < 6e-7  # Observed study: 5.52e-7 at this fixed resolution.


@pytest.mark.parametrize("time", [0., .25])
def test_discrete_lead_jacobian_gives_spatial_parseval_norm(time: float) -> None:
    """The group velocity and meV/ps/nm conversion must preserve packet probability."""
    e = np.linspace(10, 80, 1601)
    packet = gaussian_packet(e, central_energy_mev=35, bandwidth_mev=3, propagating_bounds_mev=(5, 10000))
    tau = hbar**2/(2*.067*m_e*(.5e-9)**2)/(elementary_charge*1e-3)
    q = 2*np.arcsin(np.sqrt((e-5)/(4*tau)))
    k = q/.5
    velocity = 2*tau*.5*np.sin(q)/HBAR_MEV_PS*1000
    position = np.linspace(-600, 600, 2401)
    for amplitude in [1., .25]:
        reconstructed = reconstruct_lead_packet(e, amplitude*packet.amplitude, position,
            k_per_nm=k, velocity_m_s=velocity, reference_plane_nm=0, time_ps=time)
        assert reconstructed.window_probability == pytest.approx(amplitude**2, abs=1e-10)


def test_energy_to_k_jacobian_matches_analytic_position_gaussian() -> None:
    """A Gaussian in k has a known Fourier transform, independently testing the energy kernel."""
    k = np.linspace(.1, .5, 2001)
    sigma, center = .015, .3
    tau = hbar**2/(2*.067*m_e*(.5e-9)**2)/(elementary_charge*1e-3)
    energy = 2*tau*(1-np.cos(k*.5))
    velocity_nm_ps = 2*tau*.5*np.sin(k*.5)/HBAR_MEV_PS
    a_k = np.exp(-(k-center)**2/(4*sigma**2))/((2*np.pi)**.25*np.sqrt(sigma))
    a_energy = a_k/np.sqrt(HBAR_MEV_PS*velocity_nm_ps)
    positions = np.linspace(-100, 100, 401)
    result = reconstruct_lead_packet(energy, a_energy, positions, k_per_nm=k,
        velocity_m_s=velocity_nm_ps*1000, reference_plane_nm=0, time_ps=0)
    expected = (2*sigma**2/np.pi)**.25*np.exp(-sigma**2*positions**2+1j*center*positions)
    np.testing.assert_allclose(result.amplitude_per_sqrt_nm, expected, atol=2e-9, rtol=0)


@pytest.mark.parametrize("grid", [[1, 1, 2], [3, 2, 1], [1, np.nan, 3]])
def test_invalid_integration_grids_rejected(grid) -> None:
    """Positive inner products require ordered finite coordinates."""
    with pytest.raises(ValueError):
        quadrature_weights(grid)


def test_invalid_spectra_and_searches_rejected(gaussian) -> None:
    """Reject unnormalized inputs, amplifying elastic t, and under-resolved delay scans."""
    with pytest.raises(ValueError, match="normalized"):
        analyze_packet(gaussian.energy_mev, 2*gaussian.amplitude, np.ones(721), np.ones(721))
    with pytest.raises(ValueError, match="cannot exceed"):
        analyze_packet(gaussian.energy_mev, gaussian.amplitude, np.full(721, 1.1), np.ones(721))
    with pytest.raises(ValueError, match="too coarse"):
        DelaySearch(grid_points=3).validate_sampling(gaussian.energy_mev)
    with pytest.raises(ValueError, match="contain zero"):
        DelaySearch(min_ps=1, max_ps=2)
    with pytest.raises(ValueError, match="resolve"):
        gaussian_packet(np.linspace(1, 100, 11), central_energy_mev=50, bandwidth_mev=1,
                         propagating_bounds_mev=(0, 101))
    with pytest.raises(ValueError, match="propagating"):
        gaussian_packet(np.linspace(-1, 100, 1001), central_energy_mev=50, bandwidth_mev=10,
                         propagating_bounds_mev=(0, 101))
    with pytest.raises(ValueError, match="numerically unresolved"):
        gaussian_packet(np.linspace(1, 100, 101), central_energy_mev=50, bandwidth_mev=1e30,
                         propagating_bounds_mev=(0, 101))


def test_flat_delay_scan_does_not_invent_an_estimated_delay(gaussian) -> None:
    """An unidentifiable optimum reports no estimated lag, retaining the zero-shift score."""
    settings = DelaySearch(min_ps=-1e-8, max_ps=1e-8, xatol_ps=1e-12)
    result = analyze_packet(gaussian.energy_mev, gaussian.amplitude, np.ones(721), np.ones(721), delay=settings)
    assert result.alignment_status == "unresolved_flat_scan"
    assert result.estimated_delay_ps is None
    assert result.aligned_fidelity == result.raw_fidelity
