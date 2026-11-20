"""Reproducible gated-channel disorder and complex-sensitivity result bundles."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from numpy.typing import NDArray

from qwave.config import ChannelConfig, DisorderConfig, ScatterConfig, SensitivityConfig
from qwave.diagnostics import cpu_environment, software_versions
from qwave.disorder import (CovarianceModes, covariance_matrix, covariance_modes,
                            covariance_statistics, lag_correlations, sample_disorder)
from qwave.experiments import _write_json
from qwave.gates import GatePotential, build_gates, channel_indices
from qwave.potentials import sample_potential
from qwave.provenance import sha256_file, source_identity
from qwave.scattering import BAND_EDGE_FRACTION_GUARD
from qwave.sensitivity import derivative_study, validate_linearization
from qwave.units import physical_constants
from qwave.wavepackets import quadrature_weights


@dataclass(frozen=True)
class PreparedChannel:
    """Deterministic clean device and covariance basis shared by both commands."""

    model: ChannelConfig
    scatter: ScatterConfig
    x_nm: NDArray[np.float64]
    energy_mev: NDArray[np.float64]
    channel_indices: NDArray[np.int64]
    background_mev: NDArray[np.float64]
    gates: GatePotential
    modes: CovarianceModes
    embedded_shapes: NDArray[np.float64]

    @property
    def potential_mev(self) -> NDArray[np.float64]:
        """Configured background plus the bounded gate contributions."""
        return self.background_mev+self.gates.total_mev


def prepare_channel(settings: dict[str, Any]) -> PreparedChannel:
    """Build the actual physical grid, gates, and weighted covariance modes."""
    model = ChannelConfig.from_mapping(settings)
    scatter = ScatterConfig.from_mapping(model.scattering)
    x = np.linspace(scatter.x_min_nm, scatter.x_max_nm, scatter.grid_points)
    energy = np.linspace(scatter.energy_min_mev, scatter.energy_max_mev, scatter.energy_points)
    bounds = (model.channel["x_min_nm"], model.channel["x_max_nm"])
    indices = channel_indices(x, bounds)
    gates = build_gates(x, bounds, model.gates)
    covariance = covariance_matrix(x[indices], **{k: v for k, v in model.disorder.items() if k != "retained_modes"})
    modes = covariance_modes(x[indices], covariance, retained_modes=model.disorder["retained_modes"])
    embedded = np.zeros((len(x), modes.retained_modes))
    embedded[indices] = modes.retained_shapes
    return PreparedChannel(model, scatter, x, energy, indices, sample_potential(x, scatter.potential), gates, modes, embedded)


def _base_arrays(device: PreparedChannel) -> dict[str, Any]:
    """Export the complete covariance/eigenbasis, not just plotted modes."""
    modes, gates = device.modes, device.gates
    return {
        "x_nm": device.x_nm, "channel_indices": device.channel_indices, "channel_x_nm": modes.x_nm,
        "channel_weights_nm": modes.weights_nm, "background_mev": device.background_mev,
        "gate_shapes": gates.shapes, "gate_amplitudes_mev": gates.amplitudes_mev,
        "gate_contributions_mev": gates.contributions_mev, "gate_total_mev": gates.total_mev,
        "gate_normalization_factors": gates.normalization_factors, "clean_potential_mev": device.potential_mev,
        "covariance_mev2": modes.covariance_mev2, "kl_covariance_mev2": modes.retained_covariance,
        "eigenvalues_mev2_nm": modes.eigenvalues_mev2_nm, "all_phi_per_sqrt_nm": modes.shapes_per_sqrt_nm,
        "retained_phi_per_sqrt_nm": device.embedded_shapes,
    }


def _table(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write measured scalar rows without replacing null/failed outcomes."""
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _base_csv(output: Path, device: PreparedChannel) -> None:
    """Write gate contributions, normalized modes, and variance spectra with units."""
    modes, gates = device.modes, device.gates
    np.savetxt(output/"gates.csv", np.column_stack((device.x_nm, device.background_mev, gates.shapes,
               gates.contributions_mev, gates.total_mev, device.potential_mev)), delimiter=",", comments="", fmt="%.17g",
               header=",".join(["x_nm", "background_mev", *[f"g_{j+1}_dimensionless" for j in range(len(gates.names))],
                               *[f"gate_{j+1}_contribution_mev" for j in range(len(gates.names))], "gate_sum_mev", "clean_potential_mev"]))
    np.savetxt(output/"modes.csv", np.column_stack((modes.x_nm, modes.retained_shapes)), delimiter=",", comments="", fmt="%.17g",
               header=",".join(["x_nm", *[f"phi_{k+1}_per_sqrt_nm" for k in range(modes.retained_modes)]]))
    eigenvalues = modes.eigenvalues_mev2_nm
    np.savetxt(output/"eigenvalues.csv", np.column_stack((np.arange(1,len(eigenvalues)+1), eigenvalues,
               np.cumsum(eigenvalues)/modes.diagnostics["total_integrated_variance_mev2_nm"])),
               delimiter=",", comments="", fmt="%.17g", header="mode,lambda_mev2_nm,cumulative_variance_fraction")


def _finish(output: Path, config: DisorderConfig | SensitivityConfig, device: PreparedChannel,
            arrays: dict[str, Any], metrics: dict[str, Any], randomness: dict[str, Any],
            started: float, *, plot: bool) -> Path:
    """Save all arrays and exact settings, then write the hashed manifest last."""
    metadata = {
        "manifest_version": 1, "project": "Phaseward", "stage": "PROMPT 3", "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": config.to_dict(), "physics_model": "Constant-mass coherent elastic 1D Schrodinger model with real nodal potential energies",
        "constants_SI": physical_constants(), "software_versions": software_versions(), "environment": cpu_environment(),
        "source": source_identity(), "randomness": randomness,
        "units": {"position": "nm", "potential_energy": "meV", "gate_shapes": "dimensionless", "covariance": "meV^2",
                  "phi": "nm^(-1/2)", "lambda": "meV^2 nm", "eta": "meV sqrt(nm)", "z": "dimensionless",
                  "dt_deta": "1/(meV sqrt(nm))", "dt_dV_node": "1/meV", "functional_derivative_density": "1/(meV nm)",
                  "transmission_amplitudes_and_errors": "dimensionless"},
        "mode_convention": "phi.T W phi=I; eta=sqrt(lambda)*z; Var(z)=I; deltaV=sum eta_k phi_k; lambda is NOT in phi",
        "gate_convention": "sampled peak absolute shape=1; u in meV; bounds checked without clipping; not electrode voltage",
        "phase_convention": {"left_plane_nm": float(device.x_nm[0]), "right_plane_nm": float(device.x_nm[-1]),
                             "normalization": "same flux-normalized complex t as stationary solver; free phase retained"},
        "approximations": {
            "spatial_rule": "uniform centered finite difference; exact semi-infinite discrete leads; no imaginary broadening",
            "spacing_nm": float(device.x_nm[1]-device.x_nm[0]), "band_edge_fraction_guard": BAND_EDGE_FRACTION_GUARD,
            "covariance_rule": "nodal covariance C; trapezoidal W; symmetric eigendecomposition of sqrt(W) C sqrt(W)",
            "eigenvalue_handling": "negative eigenvalues within 64*N*eps*maxabs(lambda) clipped to zero and reported; no jitter",
            "mode_sign_rule": "largest-magnitude weighted eigenvector entry positive; degenerate eigenspaces need not be unique across libraries",
            "kl_truncation": "first K modes, no rescaling to restore discarded variance",
            "disorder_boundaries": "zero outside declared channel; boundary_taper_nm=0 is a hard cutoff, positive taper modifies covariance",
            "gates": "C1 raised-cosine channel envelope; tabulated shapes use declared PCHIP; peak normalization is grid dependent",
            "derivative": "centered real eta steps on complex t, checked against discrete implicit linear response; leads held fixed",
            "position_sensitivity": "dt/dV_j divided by full-grid quadrature weight for plotted functional derivative density",
            "linearization": "paired full solves of retained disorder; separate full-covariance solves isolate KL truncation error",
            "step_noise_flag": "smallest-step error > 4*max(best tested error,eps), with best step not last; heuristic, not certified error bound",
            "subtraction_noise_scale": "eps*(abs(t_plus)+abs(t_minus))/(2h), excludes amplification of solve errors",
            "unresolved_potential_perturbation": "unchanged potential or >1% infinity-norm relative error in represented (Vplus-Vminus)/(2h) direction",
            "sampling_checks": "max absolute mean and variance error < 6 Gaussian standard errors and covariance error < 4 expected Frobenius RMS",
            "dtype": "float64/complex128",
        },
        "metrics": metrics, "plot_enabled": plot,
    }
    _write_json(output/"config.json", config.to_dict())
    _write_json(output/"metrics.json", metrics)
    _base_csv(output, device)
    np.savez_compressed(output/"arrays.npz", **arrays,
                        provenance_json=np.asarray(json.dumps(metadata, sort_keys=True, allow_nan=False)))
    metadata["outputs"] = {path.name: {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
                           for path in sorted(output.iterdir()) if path.is_file()}
    metadata["elapsed_seconds_before_manifest"] = perf_counter()-started
    _write_json(output/"manifest.json", metadata)
    return output


def run_disorder(config: DisorderConfig, output: str | Path, *, plot: bool = True) -> Path:
    """Sample full/KL disorder and check empirical variance and correlation against both targets."""
    started, output = perf_counter(), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    device = prepare_channel(config.model)
    modes = device.modes
    samples = sample_disorder(modes, sample_count=config.sample_count, seed=config.seed)
    full = covariance_statistics(samples.full_mev, modes.covariance_mev2)
    retained = covariance_statistics(samples.retained_mev, modes.retained_covariance)
    arrays = _base_arrays(device)
    arrays.update(standard_normals=samples.standard_normals, eta_mev_sqrt_nm=samples.coefficients_mev_sqrt_nm,
                  full_samples_mev=samples.full_mev, retained_samples_mev=samples.retained_mev,
                  empirical_covariance_mev2=full["empirical_covariance_mev2"],
                  empirical_kl_covariance_mev2=retained["empirical_covariance_mev2"])
    for name, matrix in (("target", modes.covariance_mev2), ("empirical", full["empirical_covariance_mev2"]),
                         ("kl_target", modes.retained_covariance), ("kl_empirical", retained["empirical_covariance_mev2"])):
        arrays[f"{name}_lag_correlation"] = lag_correlations(matrix)
    arrays["lag_nm"] = modes.x_nm-modes.x_nm[0]
    passed = all(s["summary"]["max_abs_mean_in_standard_errors"] < 6 and
                 s["summary"]["max_abs_variance_error_in_standard_errors"] < 6 and
                 s["summary"]["frobenius_error_in_expected_sampling_rms"] < 4 for s in (full, retained))
    metrics = {"kl": modes.diagnostics, "full_sampling": full["summary"], "kl_sampling": retained["summary"],
               "sampling_checks_passed": passed, "gate_count": len(device.gates.names),
               "observed_mean_omitted_integrated_variance_mev2_nm": float(np.mean((samples.full_mev-samples.retained_mev)**2 @ modes.weights_nm)),
               "provenance_file": "manifest.json"}
    lag_index = int(np.argmin(abs(arrays["lag_nm"]-device.model.disorder["correlation_length_nm"])))
    metrics["correlation_near_requested_length"] = {
        "separation_nm": float(arrays["lag_nm"][lag_index]),
        **{name: float(arrays[f"{name}_lag_correlation"][lag_index])
           if np.isfinite(arrays[f"{name}_lag_correlation"][lag_index]) else None
           for name in ("target", "empirical", "kl_target", "kl_empirical")},
    }
    np.savetxt(output/"variance.csv", np.column_stack((modes.x_nm, np.diag(modes.covariance_mev2),
               np.diag(full["empirical_covariance_mev2"]), np.diag(modes.retained_covariance),
               np.diag(retained["empirical_covariance_mev2"]), full["mean_mev"], retained["mean_mev"])), delimiter=",", comments="", fmt="%.17g",
               header="x_nm,target_variance_mev2,empirical_variance_mev2,kl_target_variance_mev2,kl_empirical_variance_mev2,full_mean_mev,kl_mean_mev")
    np.savetxt(output/"correlation.csv", np.column_stack((arrays["lag_nm"], *[arrays[f"{name}_lag_correlation"]
               for name in ("target", "empirical", "kl_target", "kl_empirical")])), delimiter=",", comments="", fmt="%.17g",
               header="lag_nm,target_correlation,empirical_correlation,kl_target_correlation,kl_empirical_correlation")
    count = min(5, config.sample_count)
    np.savetxt(output/"representative_samples.csv", np.column_stack((modes.x_nm, samples.full_mev[:count].T,
               samples.retained_mev[:count].T)), delimiter=",", comments="", fmt="%.17g",
               header=",".join(["x_nm", *[f"full_sample_{i}_mev" for i in range(count)], *[f"kl_sample_{i}_mev" for i in range(count)]]))
    if plot:
        from qwave.disorder_plotting import save_disorder_plots

        save_disorder_plots(device, arrays, metrics, output)
    randomness = {"used": True, "seeds": [config.seed], "seed_roles": {"covariance_validation": config.seed},
                  "bit_generator": "PCG64", "distribution": "independent standard normal z; eta_k=sqrt(lambda_k)*z_k",
                  "draw_shape": list(samples.standard_normals.shape), "representative_sample_indices": list(range(count)),
                  "training_or_optimization": False}
    return _finish(output, config, device, arrays, metrics, randomness, started, plot=plot)


def run_sensitivity(config: SensitivityConfig, output: str | Path, *, plot: bool = True) -> Path:
    """Study complex derivatives and measure Taylor versus KL truncation errors separately."""
    started, output = perf_counter(), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    device = prepare_channel(config.model)
    scatter, modes = device.scatter, device.modes
    arguments = dict(effective_mass_ratio=scatter.effective_mass_ratio,
                     left_lead_mev=scatter.left_lead_mev, right_lead_mev=scatter.right_lead_mev)
    study = derivative_study(device.x_nm, device.potential_mev, device.energy_mev, device.embedded_shapes,
                             config.steps_mev_sqrt_nm, **arguments)
    selected_index = config.steps_mev_sqrt_nm.index(config.selected_step_mev_sqrt_nm)
    derivative = study.finite_difference[selected_index]
    samples = sample_disorder(modes, sample_count=config.validation_samples, seed=config.validation_seed)
    eta = samples.coefficients_mev_sqrt_nm[:, :modes.retained_modes]
    full_disorder = np.zeros((config.validation_samples, len(device.x_nm)))
    full_disorder[:, device.channel_indices] = samples.full_mev
    validation = validate_linearization(device.x_nm, device.potential_mev, device.energy_mev,
        device.embedded_shapes, eta, config.disorder_scales, study.spatial_response.baseline.t, derivative,
        full_disorder_mev=full_disorder, **arguments)
    arrays = _base_arrays(device)
    arrays.update(energy_mev=device.energy_mev, baseline_t=study.spatial_response.baseline.t,
                  baseline_r=study.spatial_response.baseline.r, steps_mev_sqrt_nm=study.steps_mev_sqrt_nm,
                  dt_deta_finite_difference=study.finite_difference, t_plus=study.t_plus, t_minus=study.t_minus,
                  dt_deta_linear_response=study.linear_response, dt_deta_selected=derivative,
                  dt_dz_selected=derivative*np.sqrt(modes.retained_eigenvalues),
                  dt_dV_node=study.spatial_response.dt_dpotential_per_mev,
                  functional_derivative_density=study.spatial_response.dt_dpotential_per_mev/quadrature_weights(device.x_nm),
                  unresolved_perturbations=study.unresolved_perturbations,
                  potential_direction_relative_error=study.potential_direction_relative_error,
                  standard_normals=samples.standard_normals, eta_all_mev_sqrt_nm=samples.coefficients_mev_sqrt_nm,
                  retained_validation_eta_mev_sqrt_nm=eta, full_validation_disorder_mev=full_disorder,
                  disorder_scales=np.asarray(config.disorder_scales), full_solve_kl_t=validation.full_t,
                  first_order_t=validation.linear_t, full_solve_full_covariance_t=validation.full_covariance_t,
                  per_sample_rms_linearization_error=validation.per_sample_rms_error,
                  predicted_mean_squared_delta_t=np.sum(modes.retained_eigenvalues*abs(derivative)**2, axis=1))
    conservation = max(study.max_conservation_error, validation.max_conservation_error)
    metrics = {"kl": modes.diagnostics, "gate_count": len(device.gates.names),
               "selected_step_mev_sqrt_nm": config.selected_step_mev_sqrt_nm,
               "selected_step_max_derivative_error": float(np.max(abs(derivative-study.linear_response))),
               "selected_step_unresolved_perturbations": int(np.count_nonzero(study.unresolved_perturbations[selected_index])),
               "step_study": study.step_rows, "per_mode_step_diagnostics": study.mode_rows,
               "modes_with_small_step_error_growth": sum(row["small_step_error_growth_detected"] for row in study.mode_rows),
               "response_reassembled_t_difference": study.spatial_response.max_reassembled_t_difference,
               "response_solve_relative_residual": study.spatial_response.max_response_solve_residual,
               "max_conservation_error_full_solves": conservation,
               "conservation_passed": conservation <= scatter.conservation_tolerance,
               "linearization": validation.rows,
               "first_order_variance_convention": "E[|delta t|^2] = sum lambda_k |dt/deta_k|^2, for independent eta of variance lambda",
               "error_interpretation": "Taylor error compares full K-mode solves; KL truncation error compares paired full-covariance solves; no fidelity computed",
               "provenance_file": "manifest.json"}
    _table(output/"derivative_steps.csv", study.step_rows)
    _table(output/"mode_diagnostics.csv", study.mode_rows)
    _table(output/"linearization.csv", validation.rows)
    np.savetxt(output/"mode_derivatives.csv", np.column_stack((np.repeat(device.energy_mev, modes.retained_modes),
               np.tile(np.arange(1, modes.retained_modes+1), len(device.energy_mev)), derivative.real.ravel(), derivative.imag.ravel(),
               study.linear_response.real.ravel(), study.linear_response.imag.ravel())), delimiter=",", comments="", fmt="%.17g",
               header="energy_mev,mode,dt_deta_real_per_mev_sqrt_nm,dt_deta_imag_per_mev_sqrt_nm,linear_response_real,linear_response_imag")
    gradient = study.spatial_response.dt_dpotential_per_mev
    np.savetxt(output/"position_derivatives.csv", np.column_stack((np.repeat(device.energy_mev, len(device.x_nm)),
               np.tile(device.x_nm, len(device.energy_mev)), gradient.real.ravel(), gradient.imag.ravel())), delimiter=",", comments="", fmt="%.17g",
               header="energy_mev,x_nm,dt_dV_node_real_per_mev,dt_dV_node_imag_per_mev")
    if plot:
        from qwave.disorder_plotting import save_sensitivity_plots

        save_sensitivity_plots(device, arrays, metrics, output)
    randomness = {"used": True, "seeds": [config.validation_seed], "seed_roles": {"linearization_validation": config.validation_seed},
                  "bit_generator": "PCG64", "distribution": "independent standard normal z; eta=sqrt(lambda)*z",
                  "draw_shape": list(samples.standard_normals.shape), "same_draws_across_strengths_and_full_KL": True,
                  "training_or_optimization": False}
    return _finish(output, config, device, arrays, metrics, randomness, started, plot=plot)
