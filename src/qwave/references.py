"""Independent continuum references for validation, not the production solver.

Closed-form rectangular-barrier formulas and a separate ODE matching method
never call the finite-difference solver. The ODE method is restricted to modest
barriers because a fundamental matrix becomes ill-conditioned for opaque ones.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.constants import elementary_charge, hbar, m_e
from scipy.integrate import solve_ivp


def rectangular_transmission_amplitude(
    energies_mev: ArrayLike, *, height_mev: float, width_nm: float,
    effective_mass_ratio: float, reference_length_nm: float,
) -> NDArray[np.complex128]:
    """Exact continuum t at planes separated by L, with identical zero-potential leads.

    A barrier of height >=0 and width d lies between the planes. Free padding
    contributes exp(ik(L-d)). The E=height limit is treated analytically; the
    tunneling branch uses decaying exponentials to avoid cosh/sinh overflow.
    """
    energy = np.atleast_1d(np.asarray(energies_mev, dtype=float))
    if (not np.all(np.isfinite(energy)) or np.any(energy <= 0) or height_mev < 0
            or width_nm <= 0 or effective_mass_ratio <= 0 or reference_length_nm < width_nm):
        raise ValueError("reference requires positive energies/mass/width, nonnegative barrier, and L >= width")
    # Independent SI conversion, not a call to production unit/dispersion helpers.
    factor = 2 * (effective_mass_ratio * m_e) * (1e-3 * elementary_charge) / hbar**2
    k = np.sqrt(factor * energy) * 1e-9
    result = np.empty(energy.shape, dtype=np.complex128)
    above = energy > height_mev
    below = energy < height_mev
    equal = energy == height_mev
    q = np.sqrt(factor * (energy[above] - height_mev)) * 1e-9
    z = q * width_nm
    result[above] = 1 / (np.cos(z) - 1j * (k[above]**2 + q**2) * np.sin(z) / (2 * k[above] * q))
    kappa = np.sqrt(factor * (height_mev - energy[below])) * 1e-9
    z = kappa * width_nm
    decay = np.exp(-z)
    sinh_scaled = -np.expm1(-2 * z)
    coefficient = (k[below]**2 - kappa**2) / (2 * k[below] * kappa)
    result[below] = 2 * decay / (1 + decay**2 - 1j * coefficient * sinh_scaled)
    result[equal] = 1 / (1 - 0.5j * k[equal] * width_nm)
    return result * np.exp(1j * k * (reference_length_nm - width_nm))


def rectangular_probability(
    energies_mev: ArrayLike, *, height_mev: float, width_nm: float, effective_mass_ratio: float,
) -> NDArray[np.float64]:
    """Independent real closed-form barrier probability for moderate validation cases."""
    energy = np.atleast_1d(np.asarray(energies_mev, dtype=float))
    if np.any(energy <= 0) or height_mev < 0 or width_nm <= 0 or effective_mass_ratio <= 0:
        raise ValueError("invalid continuum barrier reference parameters")
    coefficient = 2 * effective_mass_ratio * m_e * (1e-3 * elementary_charge) * (width_nm * 1e-9)**2 / hbar**2
    result = np.ones_like(energy)
    if height_mev == 0:
        return result
    below, above, equal = energy < height_mev, energy > height_mev, energy == height_mev
    z = np.sqrt(coefficient * (height_mev - energy[below]))
    # log(sinh(z)) is stable both for small z and for opaque reference barriers.
    log_sinh = z + np.log(-np.expm1(-2 * z)) - np.log(2)
    log_ratio = 2*np.log(height_mev) + 2*log_sinh - np.log(4*energy[below]*(height_mev-energy[below]))
    result[below] = np.exp(-np.logaddexp(0, log_ratio))
    z = np.sqrt(coefficient * (energy[above] - height_mev))
    result[above] = 1 / (1 + height_mev**2 * np.sin(z)**2 / (4 * energy[above] * (energy[above] - height_mev)))
    result[equal] = 1 / (1 + coefficient * height_mev / 4)
    return result


def continuum_ode_reference(
    energy_mev: float, potential: Callable[[float], float], *, x_min_nm: float,
    x_max_nm: float, effective_mass_ratio: float, left_lead_mev: float = 0.0,
    right_lead_mev: float = 0.0, rtol: float = 1e-11, atol: float = 1e-13,
) -> tuple[complex, complex]:
    """Independently integrate continuum fundamental solutions and match lead waves.

    Derivatives use the nm coordinate after explicit SI conversion. DOP853 is
    adaptive; no finite-difference lattice or lead band is used. The method is
    only a validation reference; poorly conditioned matching is rejected.
    """
    if min(energy_mev - left_lead_mev, energy_mev - right_lead_mev) <= 0:
        raise ValueError("both continuum reference leads must propagate")
    factor = 2 * effective_mass_ratio * m_e * (1e-3 * elementary_charge) * 1e-18 / hbar**2
    k_left = np.sqrt(factor * (energy_mev - left_lead_mev))
    k_right = np.sqrt(factor * (energy_mev - right_lead_mev))

    def rhs(x: float, state: NDArray[np.complex128]) -> NDArray[np.complex128]:
        matrix = state.reshape(2, 2)
        return np.vstack((matrix[1], factor * (potential(x) - energy_mev) * matrix[0])).reshape(-1)

    solution = solve_ivp(rhs, (x_min_nm, x_max_nm), np.eye(2, dtype=complex).reshape(-1),
                         method="DOP853", rtol=rtol, atol=atol)
    if not solution.success:
        raise RuntimeError(solution.message)
    fundamental = solution.y[:, -1].reshape(2, 2)
    incident = fundamental @ np.array([1, 1j*k_left])
    reflected = fundamental @ np.array([1, -1j*k_left])
    matching = np.column_stack((reflected, -np.array([1, 1j*k_right])))
    if np.linalg.cond(matching) > 1e10:
        raise ValueError("continuum ODE reference is too ill-conditioned for this case")
    reflection, transmitted_wave_amplitude = np.linalg.solve(matching, -incident)
    return complex(np.sqrt(k_right / k_left) * transmitted_wave_amplitude), complex(reflection)
