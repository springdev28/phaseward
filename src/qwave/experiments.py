"""Run the separate polynomial demo or stationary scattering with provenance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import trapezoid

from qwave.config import DemoConfig, ScatterConfig
from qwave.diagnostics import cpu_environment, software_versions
from qwave.provenance import sha256_file, source_identity
from qwave.units import demo_units

DEMO_SCOPE = "Numerical placeholder only: integrate f(x)=x^2 on [0,1]; no electron scattering or fidelity."


@dataclass(frozen=True)
class DemoResult:
    """Computed arrays and estimates; all quantities are dimensionless."""

    x: NDArray[np.float64]
    f_x: NDArray[np.float64]
    sample_x: NDArray[np.float64]
    sample_f_x: NDArray[np.float64]
    metrics: dict[str, float]


def compute_demo(config: DemoConfig) -> DemoResult:
    """Evaluate grid quadrature and seeded uniform Monte Carlo independently.

    The reference integral is 1/3 from the antiderivative x**3/3. Monte Carlo
    error is measured, not required to improve or beat grid quadrature.
    """
    x = np.linspace(0.0, 1.0, config.grid_points, dtype=np.float64)
    f_x = np.square(x)
    rng = np.random.Generator(np.random.PCG64(config.seed))
    sample_x = rng.random(config.monte_carlo_samples)
    sample_f_x = np.square(sample_x)
    reference = float(Fraction(1, 3))
    grid_integral = float(trapezoid(f_x, x=x))
    sample_integral = float(np.mean(sample_f_x, dtype=np.float64))
    return DemoResult(
        x=x, f_x=f_x, sample_x=sample_x, sample_f_x=sample_f_x,
        metrics={
            "reference_integral": reference,
            "trapezoid_integral": grid_integral,
            "trapezoid_absolute_error": abs(grid_integral - reference),
            "monte_carlo_integral": sample_integral,
            "monte_carlo_absolute_error": abs(sample_integral - reference),
        },
    )


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write readable, standards-compliant JSON without NaN or Infinity."""
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def run_demo(config: DemoConfig, output: str | Path, *, plot: bool = False) -> Path:
    """Create a new result directory; a final manifest marks a completed run.

    Existing directories, including empty ones, are refused. If an I/O error
    interrupts a run, retain the incomplete directory for diagnosis.
    """
    started = perf_counter()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result = compute_demo(config)
    provenance: dict[str, Any] = {
        "manifest_version": 1,
        "stage": "PROMPT 0",
        "scope": DEMO_SCOPE,
        "physics_model": None,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": config.to_dict(),
        "units": demo_units(),
        "numerical_parameters": {"interval": [0.0, 1.0], "polynomial_degree": 2, "dtype": "float64"},
        "randomness": {"seeds": [config.seed], "bit_generator": "PCG64", "distribution": "Uniform[0,1)"},
        "approximations": {
            "grid_rule": "composite trapezoidal; uniform endpoint-inclusive grid",
            "grid_spacing": 1.0 / (config.grid_points - 1),
            "monte_carlo_rule": "arithmetic mean of f(x) at independent uniform samples; interval length 1",
            "reference": "exact polynomial antiderivative x^3/3, evaluated using Fraction(1, 3)",
            "floating_point": "IEEE-754 float64; reference rounded to float64",
            "physical_approximations": [],
        },
        "software_versions": software_versions(),
        "environment": cpu_environment(),
        "source": source_identity(),
        "options": {"plot": plot},
    }
    _write_json(output / "config.json", config.to_dict())
    _write_json(output / "metrics.json", {
        "scope": DEMO_SCOPE, "unit_system": config.unit_system,
        "provenance_file": "manifest.json", "metrics": result.metrics,
    })
    np.savetxt(output / "grid.csv", np.column_stack((result.x, result.f_x)),
               delimiter=",", header="x_dimensionless,f_x_dimensionless", comments="", fmt="%.17g")
    np.savetxt(output / "samples.csv", np.column_stack((result.sample_x, result.sample_f_x)),
               delimiter=",", header="x_dimensionless,f_x_dimensionless", comments="", fmt="%.17g")
    np.savez_compressed(
        output / "arrays.npz", x=result.x, f_x=result.f_x,
        sample_x=result.sample_x, sample_f_x=result.sample_f_x,
        provenance_json=np.asarray(json.dumps(provenance, sort_keys=True, allow_nan=False)),
    )
    artifacts = ["config.json", "metrics.json", "grid.csv", "samples.csv", "arrays.npz"]
    if plot:
        from qwave.plotting import save_demo_plot

        save_demo_plot(result.x, result.f_x, output / "demo.png")
        artifacts.append("demo.png")
    provenance["outputs"] = {
        name: {"sha256": sha256_file(output / name), "size_bytes": (output / name).stat().st_size}
        for name in artifacts
    }
    provenance["elapsed_seconds_before_manifest"] = perf_counter() - started
    _write_json(output / "manifest.json", provenance)
    return output


def run_scatter(config: ScatterConfig, output: str | Path, *, plot: bool = True) -> Path:
    """Save a stationary-scattering run, raw complex amplitudes, and diagnostics.

    Inputs are checked before output creation. Existing directories are refused.
    Conservation diagnostics measure consistency, not continuum accuracy.
    """
    from qwave.potentials import sample_potential
    from qwave.scattering import (BAND_EDGE_FRACTION_GUARD, PHASE_AMPLITUDE_FLOOR,
                                 solve_scattering, transmission_phase)
    from qwave.units import physical_constants

    output = Path(output)
    if output.exists():
        raise FileExistsError(f"output directory already exists: {output}")
    started = perf_counter()
    x = np.linspace(config.x_min_nm, config.x_max_nm, config.grid_points)
    energy = np.linspace(config.energy_min_mev, config.energy_max_mev, config.energy_points)
    potential = sample_potential(x, config.potential)
    result = solve_scattering(x, potential, energy, effective_mass_ratio=config.effective_mass_ratio,
                              left_lead_mev=config.left_lead_mev, right_lead_mev=config.right_lead_mev)
    phase = transmission_phase(result.t)
    raw_phase_steps = np.abs(np.angle(result.t[1:] * result.t[:-1].conj()))
    diagnostics = {
        "max_abs_T_plus_R_minus_one": float(np.max(result.conservation_error)),
        "max_relative_linear_residual": float(np.max(result.relative_residual)),
        "T_min": float(np.min(result.T)), "T_max": float(np.max(result.T)),
        "R_min": float(np.min(result.R)), "R_max": float(np.max(result.R)),
        "conservation_tolerance": config.conservation_tolerance,
        "conservation_passed": bool(np.all(result.conservation_error <= config.conservation_tolerance)),
        "masked_phase_points": int(np.count_nonzero(~np.isfinite(phase))),
        "max_principal_phase_step_rad": float(np.max(raw_phase_steps)),
        "phase_sampling_warning": bool(np.any(raw_phase_steps > 0.8 * np.pi)),
        "left_endpoint_potential_jump_mev": float(potential[0] - config.left_lead_mev),
        "right_endpoint_potential_jump_mev": float(config.right_lead_mev - potential[-1]),
        "note": "Conservation and residuals do not establish continuum convergence or wave-packet fidelity.",
    }
    provenance: dict[str, Any] = {
        "manifest_version": 1, "project": "Phaseward", "stage": "PROMPT 1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "physics_model": "Elastic coherent single-electron 1D Schrodinger equation; constant effective mass; real scalar potential; uniform semi-infinite leads",
        "config": config.to_dict(), "constants_SI": physical_constants(),
        "units": {"position": "nm", "energy_and_potential": "meV", "mass": "m_e",
                  "velocity": "m/s", "wavenumber": "1/nm", "t_r_T_R": "dimensionless", "phase": "rad"},
        "randomness": {"seeds": [], "used": False, "reason": "deterministic stationary solve"},
        "software_versions": software_versions(), "environment": cpu_environment(), "source": source_identity(),
        "normalization": "unit incoming flux; t=sqrt(v_right/v_left)*psi_last, r=psi_first-1; T=|t|^2, R=|r|^2",
        "phase_convention": {"left_plane_nm": float(x[0]), "right_plane_nm": float(x[-1]),
                             "lead_waves": "left: (exp(ik_L(x-x_L))+r exp(-ik_L(x-x_L)))/sqrt(v_L); right: t exp(ik_R(x-x_R))/sqrt(v_R)",
                             "free_channel_t": "exp(ik_discrete*(x_R-x_L)); no free propagation phase removed"},
        "approximations": {
            "method": "second-order centered finite difference; pivoted complex tridiagonal solve via scipy.linalg.solve_banded",
            "spacing_nm": result.spacing_nm, "hopping_mev": result.hopping_mev,
            "lead_band_left_mev": [config.left_lead_mev, config.left_lead_mev + 4*result.hopping_mev],
            "lead_band_right_mev": [config.right_lead_mev, config.right_lead_mev + 4*result.hopping_mev],
            "lead_dispersion": "E=V_lead+2*tau*(1-cos(k*a)); open bands only",
            "band_edge_fraction_guard": BAND_EDGE_FRACTION_GUARD,
            "potential_sampling": "cell averages for rectangular edges; point samples for smooth Gaussian/PCHIP",
            "domain": "potential represented only inside the finite region; exact uniform leads outside; endpoint jumps are retained",
            "phase_amplitude_floor": PHASE_AMPLITUDE_FLOOR,
            "phase_unwrap": "separate contiguous resolved segments in increasing energy; refine energy sampling to check aliasing",
            "dtype": "complex128/float64", "artificial_imaginary_broadening_mev": 0.0,
            "limitations": ["constant mass only", "both leads must propagate", "no inelasticity, absorption, decoherence, or many-electron effects"],
        },
        "diagnostics": diagnostics, "options": {"plot": plot},
    }
    arrays = {
        "x_nm": x, "potential_mev": potential, "energy_mev": energy,
        "t": result.t, "r": result.r, "T": result.T, "R": result.R, "phase_rad": phase,
        "k_left_per_nm": result.k_left_per_nm, "k_right_per_nm": result.k_right_per_nm,
        "velocity_left_m_s": result.velocity_left_m_s, "velocity_right_m_s": result.velocity_right_m_s,
        "conservation_error": result.conservation_error, "relative_residual": result.relative_residual,
    }
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "config.json", config.to_dict())
    _write_json(output / "diagnostics.json", {"provenance_file": "manifest.json", **diagnostics})
    np.savetxt(output / "potential.csv", np.column_stack((x, potential)), delimiter=",",
               header="x_nm,potential_mev", comments="", fmt="%.17g")
    np.savetxt(output / "scattering.csv", np.column_stack((energy, result.t.real, result.t.imag,
               result.r.real, result.r.imag, result.T, result.R, phase, result.conservation_error,
               result.relative_residual, result.k_left_per_nm, result.k_right_per_nm,
               result.velocity_left_m_s, result.velocity_right_m_s)), delimiter=",", comments="", fmt="%.17g",
               header="energy_mev,t_real,t_imag,r_real,r_imag,T,R,phase_rad,conservation_error,relative_residual,k_left_per_nm,k_right_per_nm,velocity_left_m_s,velocity_right_m_s")
    np.savez_compressed(output / "arrays.npz", **arrays,
                        provenance_json=np.asarray(json.dumps(provenance, sort_keys=True, allow_nan=False)))
    names = ["config.json", "diagnostics.json", "potential.csv", "scattering.csv", "arrays.npz"]
    if plot:
        from qwave.plotting import save_scattering_plots

        names.extend(path.name for path in save_scattering_plots(x, potential, result, phase, output))
    provenance["outputs"] = {name: {"sha256": sha256_file(output/name), "size_bytes": (output/name).stat().st_size}
                             for name in names}
    provenance["elapsed_seconds_before_manifest"] = perf_counter() - started
    _write_json(output / "manifest.json", provenance)
    return output
