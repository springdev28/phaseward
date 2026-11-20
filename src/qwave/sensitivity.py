"""Complex transmission derivatives at fixed real potential, mass, and lead basis.

Primary diagnostic: centered real-parameter perturbations, preserving complex t.
An independent implicit derivative of the discrete boundary-value system checks
the step study and supplies a local potential gradient. No phase unwrapping or
absolute value is taken before differentiation. See docs/sensitivity.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.linalg import solve_banded

from qwave.scattering import ScatteringResult, real_vector, solve_scattering, uniform_grid
from qwave.wavepackets import quadrature_weights


@dataclass(frozen=True)
class SpatialResponse:
    """Discrete site derivative dt/dV_j (1/meV); complex amplitudes retain their basis."""

    baseline: ScatteringResult
    dt_dpotential_per_mev: NDArray[np.complex128]
    max_reassembled_t_difference: float
    max_response_solve_residual: float


def transmission_gradient(x_nm: ArrayLike, potential_mev: ArrayLike, energies_mev: ArrayLike, *,
                          effective_mass_ratio: float, left_lead_mev: float = 0.,
                          right_lead_mev: float = 0.) -> SpatialResponse:
    """Differentiate A psi=b: dt/dV_j = sqrt(vR/vL) (A^-T eR)_j psi_j / tau.

    A is the dimensionless complex-symmetric scattering system. The transpose
    is not a Hermitian adjoint: this is a complex-amplitude derivative. Leads
    and their source/self-energies remain fixed during potential perturbations.
    """
    x, spacing = uniform_grid(x_nm)
    potential = real_vector(potential_mev, "potential_mev", minimum_size=3)
    energy = real_vector(energies_mev, "energies_mev")
    baseline = solve_scattering(x, potential, energy, effective_mass_ratio=effective_mass_ratio,
                                left_lead_mev=left_lead_mev, right_lead_mev=right_lead_mev)
    gradient = np.empty((len(energy), len(x)), dtype=np.complex128)
    amplitude_difference, residuals = [], []
    for index, value in enumerate(energy):
        ql = baseline.k_left_per_nm[index]*spacing
        qr = baseline.k_right_per_nm[index]*spacing
        diagonal = ((value-potential)/baseline.hopping_mev-2).astype(complex)
        diagonal[0] += np.exp(1j*ql)
        diagonal[-1] += np.exp(1j*qr)
        band = np.zeros((3, len(x)), dtype=complex)
        band[0, 1:], band[1], band[2, :-1] = 1., diagonal, 1.
        sources = np.zeros((len(x), 2), dtype=complex)
        sources[0, 0] = 2j*np.sin(ql)
        sources[-1, 1] = 1.
        solutions = solve_banded((1, 1), band, sources, check_finite=False)
        psi, response = solutions.T
        flux = np.sqrt(baseline.velocity_right_m_s[index]/baseline.velocity_left_m_s[index])
        gradient[index] = flux*response*psi/baseline.hopping_mev
        amplitude_difference.append(abs(flux*psi[-1]-baseline.t[index]))
        discrepancy = diagonal[:, None]*solutions-sources
        discrepancy[:-1] += solutions[1:]
        discrepancy[1:] += solutions[:-1]
        rows = abs(diagonal)+2
        rows[[0, -1]] -= 1
        residuals.append(float(np.max(abs(discrepancy))/(max(rows)*np.max(abs(solutions))+np.max(abs(sources)))))
    return SpatialResponse(baseline, gradient, float(max(amplitude_difference)), float(max(residuals)))


@dataclass(frozen=True)
class SensitivityStudy:
    """Finite-difference arrays have axes (step, energy, mode); eta is meV sqrt(nm)."""

    steps_mev_sqrt_nm: NDArray[np.float64]
    finite_difference: NDArray[np.complex128]
    t_plus: NDArray[np.complex128]
    t_minus: NDArray[np.complex128]
    linear_response: NDArray[np.complex128]
    spatial_response: SpatialResponse
    step_rows: list[dict[str, Any]]
    mode_rows: list[dict[str, Any]]
    unresolved_perturbations: NDArray[np.bool_]
    potential_direction_relative_error: NDArray[np.float64]
    max_conservation_error: float


def derivative_study(x_nm: ArrayLike, potential_mev: ArrayLike, energies_mev: ArrayLike,
                     mode_shapes_per_sqrt_nm: ArrayLike, steps_mev_sqrt_nm: ArrayLike, *,
                     effective_mass_ratio: float, left_lead_mev: float = 0.,
                     right_lead_mev: float = 0.) -> SensitivityStudy:
    """Study centered complex-t differences against implicit discrete linear response.

    h is a real eta perturbation in meV sqrt(nm). Imaginary potential steps would
    change the lossless model and are not used. All complex differences are saved.
    """
    x, _ = uniform_grid(x_nm)
    potential = real_vector(potential_mev, "potential_mev", minimum_size=3)
    energy = real_vector(energies_mev, "energies_mev")
    raw = np.asarray(mode_shapes_per_sqrt_nm)
    if np.iscomplexobj(raw) or raw.dtype.kind not in "iuf":
        raise ValueError("mode shapes must be real")
    shapes = np.asarray(raw, dtype=float)
    if shapes.ndim != 2 or shapes.shape[0] != len(x) or shapes.shape[1] < 1 or not np.all(np.isfinite(shapes)):
        raise ValueError("mode shapes must have shape (spatial nodes, modes) and finite values")
    steps = real_vector(steps_mev_sqrt_nm, "steps_mev_sqrt_nm", minimum_size=3)
    if np.any(steps <= 0) or np.any(np.diff(steps) >= 0):
        raise ValueError("steps must be positive and strictly decreasing")
    arguments = dict(effective_mass_ratio=effective_mass_ratio, left_lead_mev=left_lead_mev,
                     right_lead_mev=right_lead_mev)
    response = transmission_gradient(x, potential, energy, **arguments)
    reference = response.dt_dpotential_per_mev @ shapes
    plus = np.empty((len(steps), len(energy), shapes.shape[1]), dtype=complex)
    minus = np.empty_like(plus)
    unresolved = np.zeros((len(steps), shapes.shape[1]), dtype=bool)
    direction_error = np.zeros_like(unresolved, dtype=float)
    conservation = float(max(response.baseline.conservation_error))
    for si, step in enumerate(steps):
        for k in range(shapes.shape[1]):
            perturbation = step*shapes[:, k]
            p_up, p_down = potential+perturbation, potential-perturbation
            shape_norm = float(max(abs(shapes[:, k])))
            direction_error[si, k] = (float(max(abs((p_up-p_down)/(2*step)-shapes[:, k])))/shape_norm
                                      if shape_norm > 0 else 0.)
            unresolved[si, k] = (np.array_equal(p_up, potential) or np.array_equal(p_down, potential)
                                 or direction_error[si, k] > .01)
            upper = solve_scattering(x, p_up, energy, **arguments)
            lower = solve_scattering(x, p_down, energy, **arguments)
            plus[si, :, k], minus[si, :, k] = upper.t, lower.t
            conservation = max(conservation, float(max(upper.conservation_error)), float(max(lower.conservation_error)))
    derivative = (plus-minus)/(2*steps[:, None, None])
    errors = abs(derivative-reference)
    rows = []
    for index, step in enumerate(steps):
        rows.append({"step_mev_sqrt_nm": float(step), "max_complex_derivative_error": float(np.max(errors[index])),
                     "rms_complex_derivative_error": float(np.sqrt(np.mean(errors[index]**2))),
                     "subtraction_roundoff_scale": float(np.max(np.finfo(float).eps*(abs(plus[index])+abs(minus[index]))/(2*step))),
                     "max_potential_direction_relative_error": float(max(direction_error[index])),
                     "unresolved_mode_perturbations": int(np.count_nonzero(unresolved[index]))})
    mode_rows = []
    for k in range(shapes.shape[1]):
        error = np.max(errors[:, :, k], axis=1)
        best = int(np.argmin(error))
        noise = best < len(steps)-1 and error[-1] > 4*max(error[best], np.finfo(float).eps)
        zero = not np.any(abs(plus[:, :, k])+abs(minus[:, :, k]))
        mode_rows.append({"mode": k+1, "best_tested_step_mev_sqrt_nm": float(steps[best]),
                          "minimum_max_energy_error": float(error[best]), "smallest_step_max_energy_error": float(error[-1]),
                          "small_step_error_growth_detected": bool(noise),
                          "all_transmission_amplitudes_zero": bool(zero)})
    return SensitivityStudy(steps, derivative, plus, minus, reference, response, rows, mode_rows, unresolved, direction_error, conservation)


@dataclass(frozen=True)
class LinearizationStudy:
    """Full and first-order complex amplitudes for paired draws across strength scales."""

    full_t: NDArray[np.complex128]
    linear_t: NDArray[np.complex128]
    full_covariance_t: NDArray[np.complex128] | None
    rows: list[dict[str, Any]]
    per_sample_rms_error: NDArray[np.float64]
    max_conservation_error: float


def validate_linearization(x_nm: ArrayLike, potential_mev: ArrayLike, energies_mev: ArrayLike,
                           mode_shapes_per_sqrt_nm: ArrayLike, coefficients_mev_sqrt_nm: ArrayLike,
                           scales: ArrayLike, baseline_t: ArrayLike, derivatives: ArrayLike, *,
                           effective_mass_ratio: float, left_lead_mev: float = 0.,
                           right_lead_mev: float = 0., full_disorder_mev: ArrayLike | None = None) -> LinearizationStudy:
    """Compare first order with new full solves, retaining failure of the approximation.

    Coefficients contain variance already; no eigenvalue factor is added here.
    Reusing paired draws at each strength isolates scaling from sampling changes.
    """
    x, _ = uniform_grid(x_nm)
    potential = real_vector(potential_mev, "potential_mev", minimum_size=3)
    energy = real_vector(energies_mev, "energies_mev", minimum_size=3)
    weights = quadrature_weights(energy)/(energy[-1]-energy[0])
    shapes = np.asarray(mode_shapes_per_sqrt_nm)
    eta = np.asarray(coefficients_mev_sqrt_nm)
    scale = real_vector(scales, "scales", minimum_size=2)
    t0 = np.asarray(baseline_t, dtype=complex)
    derivative = np.asarray(derivatives, dtype=complex)
    if np.iscomplexobj(shapes) or np.iscomplexobj(eta) or shapes.ndim != 2 or eta.ndim != 2:
        raise ValueError("mode shapes and coefficients must be real matrices")
    if shapes.shape[0] != len(x) or eta.shape[1] != shapes.shape[1] or len(eta) < 1:
        raise ValueError("mode, coefficient, and grid dimensions disagree")
    if t0.shape != energy.shape or derivative.shape != (len(energy), shapes.shape[1]):
        raise ValueError("baseline/derivative dimensions disagree with energy and mode grids")
    if any(not np.all(np.isfinite(a)) for a in (shapes, eta, t0, derivative)):
        raise ValueError("linearization inputs must be finite")
    if np.any(scale < 0) or np.any(np.diff(scale) <= 0):
        raise ValueError("disorder scales must be nonnegative and strictly increasing")
    untruncated = None
    if full_disorder_mev is not None:
        untruncated = np.asarray(full_disorder_mev)
        if np.iscomplexobj(untruncated) or untruncated.shape != (len(eta), len(x)) or not np.all(np.isfinite(untruncated)):
            raise ValueError("full disorder must be a real (draws, spatial nodes) matrix")
    full = np.empty((len(scale), len(eta), len(energy)), dtype=complex)
    linear = np.empty_like(full)
    full_covariance_t = None if untruncated is None else np.empty_like(full)
    per_sample = np.empty((len(scale), len(eta)))
    changes = eta @ derivative.T
    potentials = eta @ shapes.T
    rows, conservation = [], 0.
    for si, strength in enumerate(scale):
        linear[si] = t0[None, :]+strength*changes
        for sample in range(len(eta)):
            result = solve_scattering(x, potential+strength*potentials[sample], energy,
                                      effective_mass_ratio=effective_mass_ratio,
                                      left_lead_mev=left_lead_mev, right_lead_mev=right_lead_mev)
            full[si, sample] = result.t
            conservation = max(conservation, float(max(result.conservation_error)))
            if untruncated is not None:
                untruncated_result = solve_scattering(x, potential+strength*untruncated[sample], energy,
                                                      effective_mass_ratio=effective_mass_ratio,
                                                      left_lead_mev=left_lead_mev, right_lead_mev=right_lead_mev)
                full_covariance_t[si, sample] = untruncated_result.t
                conservation = max(conservation, float(max(untruncated_result.conservation_error)))
        errors = abs(full[si]-linear[si])**2
        per_sample[si] = np.sqrt(errors @ weights)
        rms = float(np.sqrt(np.mean(errors @ weights)))
        actual_change = float(np.sqrt(np.mean(abs(full[si]-t0)**2 @ weights)))
        rows.append({"disorder_scale": float(strength), "rms_complex_error": rms,
                     "median_sample_rms_error": float(np.median(per_sample[si])),
                     "max_sample_rms_error": float(max(per_sample[si])),
                     "rms_full_change": actual_change,
                     "error_relative_to_full_change": rms/actual_change if actual_change > 1e-14 else None,
                     "rms_linear_prediction_change": float(np.sqrt(np.mean(abs(strength*changes)**2 @ weights))),
                     "linearized_probability_above_one_count": int(np.count_nonzero(abs(linear[si])**2 > 1+1e-10))})
        if full_covariance_t is not None:
            rows[-1].update(
                kl_truncation_rms_error=float(np.sqrt(np.mean(abs(full_covariance_t[si]-full[si])**2 @ weights))),
                combined_prediction_rms_error=float(np.sqrt(np.mean(abs(full_covariance_t[si]-linear[si])**2 @ weights))),
            )
    return LinearizationStudy(full, linear, full_covariance_t, rows, per_sample, conservation)
