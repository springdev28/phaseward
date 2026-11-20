"""Normalized energy packets, conditional fidelity, and asymptotic lead states.

Energy is in meV, time in ps, position in nm. Spectra have units meV**(-1/2).
The bandwidth is the standard deviation of the untruncated energy probability
density, not of its amplitude. See docs/mathematics.md for all conventions.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.constants import hbar
from scipy.optimize import minimize_scalar
from scipy.special import ndtr

from qwave.scattering import real_vector
from qwave.units import MEV_TO_J

HBAR_MEV_PS: float = hbar / (MEV_TO_J * 1e-12)
MIN_NORMAL_PROBABILITY: float = np.finfo(np.float64).tiny


def quadrature_weights(coordinates: ArrayLike) -> NDArray[np.float64]:
    """Positive composite trapezoidal weights on a strictly increasing grid.

    These define the same discrete inner product for normalization, throughput,
    and fidelity. Positive weights retain the Cauchy-Schwarz bound on fidelity.
    """
    x = real_vector(coordinates, "quadrature coordinates", minimum_size=3)
    delta = np.diff(x)
    if np.any(delta <= 0):
        raise ValueError("quadrature coordinates must be strictly increasing")
    weights = np.empty_like(x)
    weights[0], weights[-1] = delta[0]/2, delta[-1]/2
    weights[1:-1] = (delta[:-1]+delta[1:])/2
    return weights


def _complex_vector(values: ArrayLike, size: int, name: str) -> NDArray[np.complex128]:
    """Require a finite one-dimensional spectrum with the expected length."""
    array = np.asarray(values, dtype=np.complex128)
    if array.shape != (size,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain {size} finite complex values")
    return array


def _number(value: float, name: str, *, positive: bool = False) -> float:
    """Validate finite real scalar settings without accepting boolean values."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name} must be a real number")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"{name} must be finite" + (" and positive" if positive else ""))
    return result


@dataclass(frozen=True)
class GaussianPacket:
    """A normalized amplitude sampled on a finite open-channel energy window."""

    energy_mev: NDArray[np.float64]
    amplitude: NDArray[np.complex128]
    weights_mev: NDArray[np.float64]
    central_energy_mev: float
    bandwidth_mev: float
    normalization: dict[str, float]


def gaussian_packet(
    energies_mev: ArrayLike, *, central_energy_mev: float, bandwidth_mev: float,
    propagating_bounds_mev: tuple[float, float],
) -> GaussianPacket:
    """Restrict a Gaussian to the stated window inside open lead bands and renormalize.

    The entire grid must lie strictly inside the supplied common propagating
    band. Missing tails are explicitly measured, never mistaken for reflection.
    The center must lie inside the numerical window and max spacing <= sigma/4.
    """
    energy = real_vector(energies_mev, "energies_mev", minimum_size=3)
    weights = quadrature_weights(energy)
    center = _number(central_energy_mev, "central_energy_mev")
    sigma = _number(bandwidth_mev, "bandwidth_mev", positive=True)
    low, high = (_number(value, "propagating bound") for value in propagating_bounds_mev)
    if not low < energy[0] < center < energy[-1] < high:
        raise ValueError("energy window and center must lie strictly inside the common propagating band")
    if max(np.diff(energy)) > sigma/4 * (1+1e-12):
        raise ValueError("energy grid does not resolve the Gaussian: require max spacing <= bandwidth/4")
    amplitude = np.exp(-.25*((energy-center)/sigma)**2) / ((2*np.pi)**.25 * np.sqrt(sigma))
    numerical_mass = float(np.dot(weights, amplitude**2))
    if not np.isfinite(numerical_mass) or numerical_mass <= 0:
        raise ValueError("Gaussian normalization is numerically unresolved")
    analytic_mass = float(ndtr((energy[-1]-center)/sigma)-ndtr((energy[0]-center)/sigma))
    physical_mass = float(ndtr((high-center)/sigma)-ndtr((low-center)/sigma))
    if analytic_mass <= 0 or physical_mass <= 0:
        raise ValueError("Gaussian tail masses are numerically unresolved; reduce the bandwidth or rescale units")
    normalized = (amplitude/np.sqrt(numerical_mass)).astype(np.complex128)
    return GaussianPacket(energy.copy(), normalized, weights, center, sigma, {
        "untruncated_gaussian_mass_in_common_band": physical_mass,
        "untruncated_gaussian_mass_in_window": analytic_mass,
        "fraction_of_common_band_mass_in_window": analytic_mass/physical_mass,
        "trapezoid_mass_before_normalization": numerical_mass,
        "mass_quadrature_absolute_error": abs(numerical_mass-analytic_mass),
        "normalized_spectral_norm": float(np.dot(weights, abs(normalized)**2)),
    })


@dataclass(frozen=True)
class DelaySearch:
    """Declared finite delay interval and scan/refinement settings, in ps."""

    enabled: bool = True
    min_ps: float = -.25
    max_ps: float = .25
    grid_points: int = 201
    xatol_ps: float = 1e-7

    def __post_init__(self) -> None:
        """Require a bounded interval containing zero and a usable numerical scan."""
        if type(self.enabled) is not bool:
            raise ValueError("delay.enabled must be boolean")
        low = _number(self.min_ps, "delay.min_ps")
        high = _number(self.max_ps, "delay.max_ps")
        tolerance = _number(self.xatol_ps, "delay.xatol_ps", positive=True)
        if not low <= 0 <= high or high <= low:
            raise ValueError("delay bounds must be increasing and contain zero")
        if type(self.grid_points) is not int or not 3 <= self.grid_points <= 10_001:
            raise ValueError("delay.grid_points must be an integer in [3, 10001]")
        if tolerance >= (high-low)/(self.grid_points-1):
            raise ValueError("delay.xatol_ps must be smaller than the scan spacing")

    def validate_sampling(self, energies_mev: ArrayLike) -> None:
        """Reject scans or energy grids too coarse for the allowed phase rotations."""
        energy = real_vector(energies_mev, "energies_mev", minimum_size=3)
        quadrature_weights(energy)
        if not self.enabled:
            return
        scan_step = (self.max_ps-self.min_ps)/(self.grid_points-1)
        if scan_step*(energy[-1]-energy[0])/HBAR_MEV_PS > np.pi/4:
            raise ValueError("delay scan is too coarse; increase delay.grid_points")
        if max(abs(self.min_ps), abs(self.max_ps))*max(np.diff(energy))/HBAR_MEV_PS > np.pi/4:
            raise ValueError("energy grid is too coarse for the requested delay bounds")


@dataclass(frozen=True)
class PacketAnalysis:
    """Separate probabilities and conditional states; None means undefined fidelity."""

    p_transmitted: float
    p_reference: float
    raw_fidelity: float | None
    aligned_fidelity: float | None
    estimated_delay_ps: float | None
    low_transmission: bool
    low_reference_transmission: bool
    alignment_boundary_hit: bool
    alignment_status: str
    transmitted_state: NDArray[np.complex128] | None
    target_state: NDArray[np.complex128] | None
    scan_delay_ps: NDArray[np.float64]
    scan_fidelity: NDArray[np.float64]

    def summary(self) -> dict[str, Any]:
        """Return JSON-safe metrics without conflating throughput and fidelity."""
        return {name: getattr(self, name) for name in (
            "p_transmitted", "p_reference", "raw_fidelity", "aligned_fidelity", "estimated_delay_ps",
            "low_transmission", "low_reference_transmission", "alignment_boundary_hit", "alignment_status",
        )}


def analyze_packet(
    energies_mev: ArrayLike, incoming_amplitude: ArrayLike, transmission: ArrayLike,
    reference_transmission: ArrayLike, *, delay: DelaySearch | None = None,
    minimum_transmission_probability: float = 1e-8,
) -> PacketAnalysis:
    """Compute throughput and normalized output overlap, optionally aligning a delay.

    Positive delay means the output lags the target under exp(-iEt/hbar).
    Alignment removes exp(+iE*delay/hbar) from the output. Low-throughput states
    remain flagged even when conditional fidelity is high; zero/underflowing
    throughput gives undefined fidelity and no manufactured normalized state.
    """
    energy = real_vector(energies_mev, "energies_mev", minimum_size=3)
    weights = quadrature_weights(energy)
    incoming = _complex_vector(incoming_amplitude, len(energy), "incoming amplitude")
    t = _complex_vector(transmission, len(energy), "transmission")
    target_t = _complex_vector(reference_transmission, len(energy), "reference transmission")
    floor = _number(minimum_transmission_probability, "minimum_transmission_probability", positive=True)
    if floor >= 1:
        raise ValueError("minimum_transmission_probability must be below one")
    if abs(float(np.dot(weights, abs(incoming)**2))-1) > 1e-10:
        raise ValueError("incoming energy amplitude must be normalized using the energy quadrature")
    if np.any(abs(t)**2 > 1+1e-8) or np.any(abs(target_t)**2 > 1+1e-8):
        raise ValueError("elastic unit-flux transmission probabilities cannot exceed one beyond roundoff")
    search = delay or DelaySearch(enabled=False)
    search.validate_sampling(energy)
    output, target = incoming*t, incoming*target_t
    p_out = float(np.dot(weights, abs(output)**2))
    p_target = float(np.dot(weights, abs(target)**2))
    state = output/np.sqrt(p_out) if p_out >= MIN_NORMAL_PROBABILITY else None
    target_state = target/np.sqrt(p_target) if p_target >= MIN_NORMAL_PROBABILITY else None
    raw = aligned = estimated = None
    boundary = False
    status = "disabled" if not search.enabled else "undefined_unresolved_transmission"
    delays, scores = np.empty(0), np.empty(0)
    if state is not None and target_state is not None:
        cross = weights*target_state.conj()*state
        raw = float(abs(np.sum(cross))**2)
        if search.enabled:
            centered_energy = energy-float(np.dot(weights, abs(incoming)**2*energy))

            def objective(shift: float) -> float:
                return float(abs(np.sum(cross*np.exp(-1j*centered_energy*shift/HBAR_MEV_PS)))**2)

            delays = np.unique(np.append(np.linspace(search.min_ps, search.max_ps, search.grid_points), 0.))
            scores = np.asarray([objective(float(shift)) for shift in delays])
            candidates = [(0., raw), (float(delays[0]), float(scores[0])), (float(delays[-1]), float(scores[-1]))]
            if np.ptp(scores) <= 1e-12:
                estimated, aligned, status = None, raw, "unresolved_flat_scan"
            else:
                for index in range(1, len(delays)-1):
                    if scores[index] >= scores[index-1] and scores[index] >= scores[index+1]:
                        optimized = minimize_scalar(lambda shift: -objective(shift), method="bounded",
                            bounds=(delays[index-1], delays[index+1]), options={"xatol": search.xatol_ps})
                        if not optimized.success:
                            raise ValueError(f"bounded delay refinement failed: {optimized.message}")
                        candidates.extend([(float(delays[index]), float(scores[index])),
                                           (float(optimized.x), float(-optimized.fun))])
                estimated, aligned = max(candidates, key=lambda pair: (pair[1], -abs(pair[0])))
                edge_tolerance = max(10*search.xatol_ps, 1e-6*(search.max_ps-search.min_ps))
                boundary = min(abs(estimated-search.min_ps), abs(estimated-search.max_ps)) <= edge_tolerance
                status = "boundary_optimum" if boundary else "interior_optimum"
    return PacketAnalysis(p_out, p_target, raw, aligned, estimated, p_out < floor, p_target < floor,
                          boundary, status, state, target_state, delays, scores)


@dataclass(frozen=True)
class LeadPacket:
    """A lead component's band-limited spatial wavefunction and finite-window norm."""

    position_nm: NDArray[np.float64]
    amplitude_per_sqrt_nm: NDArray[np.complex128]
    density_per_nm: NDArray[np.float64]
    window_probability: float


def reconstruct_lead_packet(
    energies_mev: ArrayLike, spectral_amplitude: ArrayLike, position_nm: ArrayLike, *,
    k_per_nm: ArrayLike, velocity_m_s: ArrayLike, reference_plane_nm: float,
    time_ps: float, carrier_energy_mev: float = 0.,
) -> LeadPacket:
    """Reconstruct a right-going asymptotic lead component with the energy Jacobian.

    psi(x,t)=integral B(E) exp(ik(x-x_plane)-i(E-E_carrier)t/hbar)
             /sqrt(2*pi*hbar*v(E)) dE.
    hbar is in meV ps and v in nm/ps. With discrete dispersion this is the
    band-limited continuation of the finite-difference lead state, not an
    interior scattering wavefunction. No spatial re-normalization is performed.
    """
    energy = real_vector(energies_mev, "energies_mev", minimum_size=3)
    weights = quadrature_weights(energy)
    spectrum = _complex_vector(spectral_amplitude, len(energy), "spectral_amplitude")
    position = real_vector(position_nm, "position_nm", minimum_size=3)
    position_weights = quadrature_weights(position)
    k = real_vector(k_per_nm, "k_per_nm", minimum_size=3)
    velocity = real_vector(velocity_m_s, "velocity_m_s", minimum_size=3)*1e-3
    if k.shape != energy.shape or velocity.shape != energy.shape or np.any(k <= 0) or np.any(velocity <= 0):
        raise ValueError("positive lead wave numbers and velocities must match the energy grid")
    if np.any(np.diff(k) <= 0):
        raise ValueError("lead wave numbers must increase with energy on the selected branch")
    if max(np.diff(position))*max(k) > np.pi/2:
        raise ValueError("position grid is too coarse to sample the lead wavefunction; increase position_points")
    plane = _number(reference_plane_nm, "reference_plane_nm")
    time = _number(time_ps, "time_ps")
    carrier = _number(carrier_energy_mev, "carrier_energy_mev")
    coefficient = weights*spectrum*np.exp(-1j*(energy-carrier)*time/HBAR_MEV_PS)/np.sqrt(2*np.pi*HBAR_MEV_PS*velocity)
    psi = np.empty(len(position), dtype=np.complex128)
    for start in range(0, len(position), 128):
        coordinates = position[start:start+128]-plane
        psi[start:start+128] = np.exp(1j*np.outer(coordinates, k)) @ coefficient
    density = abs(psi)**2
    return LeadPacket(position.copy(), psi, density, float(np.dot(position_weights, density)))
