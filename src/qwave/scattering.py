"""Stationary scattering with exact retarded semi-infinite discrete leads.

Complex flux amplitudes refer to extrapolated lead planes x[0] and x[-1].
See docs/scattering.md for the derivation, dispersion, and limitations.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.constants import hbar, m_e
from scipy.linalg import LinAlgError, solve_banded

from qwave.units import MEV_TO_J, NM_TO_M

BAND_EDGE_FRACTION_GUARD: float = 64 * np.finfo(np.float64).eps
PHASE_AMPLITUDE_FLOOR: float = 1e-12


class ScatteringError(ValueError):
    """Unsupported input or a failed numerical solve, never a fallback model."""


def real_vector(values: ArrayLike, name: str, *, minimum_size: int = 1) -> NDArray[np.float64]:
    """Validate finite 1D real data without discarding imaginary parts."""
    raw = np.asarray(values)
    if np.iscomplexobj(raw) or raw.dtype.kind not in "iuf":
        raise ScatteringError(f"{name} must contain real numeric values")
    array = np.asarray(raw, dtype=np.float64)
    if array.ndim != 1 or array.size < minimum_size or not np.all(np.isfinite(array)):
        raise ScatteringError(f"{name} must be a finite 1D array with at least {minimum_size} entries")
    return array


def uniform_grid(x_nm: ArrayLike) -> tuple[NDArray[np.float64], float]:
    """Validate increasing uniform node positions and return spacing in nm."""
    x = real_vector(x_nm, "x_nm", minimum_size=3)
    spacing = float((x[-1] - x[0]) / (len(x) - 1))
    if spacing <= 0 or not np.allclose(np.diff(x), spacing, rtol=1e-10, atol=1e-12 * spacing):
        raise ScatteringError("x_nm must be strictly increasing and uniformly spaced")
    return x, spacing


def _finite_scalar(value: float, name: str, *, positive: bool = False) -> float:
    """Reject complex, boolean, nonfinite, and optionally nonpositive scalars."""
    if isinstance(value, (bool, np.bool_)) or not np.isscalar(value) or np.iscomplexobj(value):
        raise ScatteringError(f"{name} must be a finite real scalar")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ScatteringError(f"{name} must be a finite real scalar") from error
    if not np.isfinite(number) or (positive and number <= 0):
        raise ScatteringError(f"{name} must be finite" + (" and positive" if positive else ""))
    return number


@dataclass(frozen=True)
class ScatteringResult:
    """Energy-resolved complex flux amplitudes and unmodified diagnostics."""

    energies_mev: NDArray[np.float64]
    t: NDArray[np.complex128]
    r: NDArray[np.complex128]
    T: NDArray[np.float64]
    R: NDArray[np.float64]
    k_left_per_nm: NDArray[np.float64]
    k_right_per_nm: NDArray[np.float64]
    velocity_left_m_s: NDArray[np.float64]
    velocity_right_m_s: NDArray[np.float64]
    conservation_error: NDArray[np.float64]
    relative_residual: NDArray[np.float64]
    hopping_mev: float
    spacing_nm: float


def solve_scattering(
    x_nm: ArrayLike, potential_mev: ArrayLike, energies_mev: ArrayLike, *,
    effective_mass_ratio: float, left_lead_mev: float = 0.0, right_lead_mev: float = 0.0,
) -> ScatteringResult:
    """Solve real elastic scattering with one constant positive mass everywhere.

    Both leads must propagate at every energy. Closed channels and energies
    within 64 machine epsilons of a normalized band edge are unsupported. This
    guard is numerical, not a physical gap. No imaginary broadening, absorbing
    potential, or probability clipping is used. Cost per energy is O(nodes).
    """
    x, spacing = uniform_grid(x_nm)
    potential = real_vector(potential_mev, "potential_mev", minimum_size=3)
    energies = real_vector(energies_mev, "energies_mev")
    if len(potential) != len(x):
        raise ScatteringError("potential_mev and x_nm must have the same length")
    mass_ratio = _finite_scalar(effective_mass_ratio, "effective_mass_ratio", positive=True)
    left = _finite_scalar(left_lead_mev, "left_lead_mev")
    right = _finite_scalar(right_lead_mev, "right_lead_mev")
    mass_kg = mass_ratio * m_e
    a_m = spacing * NM_TO_M
    hopping_j = hbar**2 / (2 * mass_kg * a_m**2)
    if not np.isfinite(hopping_j) or hopping_j <= 0:
        raise ScatteringError("grid/mass gives an unrepresentable kinetic coefficient")
    hopping_mev = hopping_j / MEV_TO_J
    phases: list[NDArray[np.float64]] = []
    for label, lead in (("left", left), ("right", right)):
        fraction = ((energies - lead) * MEV_TO_J) / (4 * hopping_j)
        allowed = (fraction > BAND_EDGE_FRACTION_GUARD) & (fraction < 1 - BAND_EDGE_FRACTION_GUARD)
        if not np.all(allowed):
            bad = energies[~allowed][:5].tolist()
            raise ScatteringError(
                f"{label} lead requires {lead:g} < E < {lead + 4 * hopping_mev:g} meV "
                f"with a {BAND_EDGE_FRACTION_GUARD:g} fractional band-edge guard; rejected {bad}"
            )
        phases.append(2 * np.arcsin(np.sqrt(fraction)))
    q_left, q_right = phases
    size = len(x)
    transmission = np.empty(len(energies), dtype=np.complex128)
    reflection = np.empty_like(transmission)
    residual = np.empty(len(energies), dtype=np.float64)
    for index, energy in enumerate(energies):
        # Divide (E-H-Sigma) and the incident source by hopping_j for scaling.
        diagonal = ((energy - potential) * MEV_TO_J / hopping_j - 2).astype(np.complex128)
        diagonal[0] += np.exp(1j * q_left[index])
        diagonal[-1] += np.exp(1j * q_right[index])
        band = np.zeros((3, size), dtype=np.complex128)
        band[0, 1:] = 1
        band[1] = diagonal
        band[2, :-1] = 1
        source = np.zeros(size, dtype=np.complex128)
        source[0] = 2j * np.sin(q_left[index])
        try:
            psi = solve_banded((1, 1), band, source, check_finite=False)
        except LinAlgError as error:
            raise ScatteringError(f"singular scattering system at E={energy:g} meV") from error
        if not np.all(np.isfinite(psi)):
            raise ScatteringError(f"nonfinite wave amplitudes at E={energy:g} meV")
        reflection[index] = psi[0] - 1
        transmission[index] = np.sqrt(np.sin(q_right[index]) / np.sin(q_left[index])) * psi[-1]
        discrepancy = diagonal * psi - source
        discrepancy[:-1] += psi[1:]
        discrepancy[1:] += psi[:-1]
        row_norms = np.abs(diagonal) + 2
        row_norms[[0, -1]] -= 1
        denominator = np.max(row_norms) * np.max(np.abs(psi)) + np.max(np.abs(source))
        residual[index] = np.max(np.abs(discrepancy)) / denominator
    T = np.abs(transmission) ** 2
    R = np.abs(reflection) ** 2
    return ScatteringResult(
        energies_mev=energies.copy(), t=transmission, r=reflection, T=T, R=R,
        k_left_per_nm=q_left / spacing, k_right_per_nm=q_right / spacing,
        velocity_left_m_s=2 * hopping_j * a_m * np.sin(q_left) / hbar,
        velocity_right_m_s=2 * hopping_j * a_m * np.sin(q_right) / hbar,
        conservation_error=np.abs(T + R - 1), relative_residual=residual,
        hopping_mev=float(hopping_mev), spacing_nm=spacing,
    )


def transmission_phase(t: ArrayLike, *, amplitude_floor: float = PHASE_AMPLITUDE_FLOOR) -> NDArray[np.float64]:
    """Unwrap arg(t) on resolved segments; mask tiny amplitudes with NaN.

    Input must be ordered by increasing energy. The floor affects phase display
    only, never the complex amplitudes. No phase is inferred from probabilities.
    """
    values = np.asarray(t, dtype=np.complex128)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ScatteringError("t must be a finite 1D complex array")
    floor = _finite_scalar(amplitude_floor, "amplitude_floor", positive=True)
    phase = np.full(len(values), np.nan)
    indices = np.flatnonzero(np.abs(values) > floor)
    for segment in np.split(indices, np.flatnonzero(np.diff(indices) != 1) + 1):
        if len(segment):
            phase[segment] = np.unwrap(np.angle(values[segment]))
    return phase
