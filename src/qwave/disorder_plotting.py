"""Headless figures of computed gate, covariance, and complex-sensitivity data."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from qwave.disorder_experiments import PreparedChannel


def _figure(width: float, height: float) -> Figure:
    """Create an explicit CPU Agg figure without a display or global pyplot state."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(width, height), layout="constrained")
    FigureCanvasAgg(figure)
    return figure


def _save(figure: Figure, output: Path, stem: str) -> None:
    """Export identical computed data in raster and vector formats."""
    for extension in ("png", "svg", "pdf"):
        figure.savefig(output/f"{stem}.{extension}", dpi=160)


def _common(device: PreparedChannel, output: Path) -> None:
    """Show gate contributions, retained covariance eigenvalues, and normalized shapes."""
    figure = _figure(10, 4.6)
    axes = figure.subplots()
    for j, name in enumerate(device.gates.names):
        axes.plot(device.x_nm, device.gates.contributions_mev[:, j], label=f"{name}: {device.gates.amplitudes_mev[j]:g} meV")
    axes.plot(device.x_nm, device.gates.total_mev, "k-", linewidth=2, label="Gate sum")
    if np.any(device.background_mev):
        axes.plot(device.x_nm, device.potential_mev, "k--", label="Background + gates")
    axes.axvspan(device.x_nm[0], device.modes.x_nm[0], color="#eeeeee", zorder=0)
    axes.axvspan(device.modes.x_nm[-1], device.x_nm[-1], color="#eeeeee", zorder=0)
    axes.set(xlabel="Position (nm)", ylabel="Potential energy (meV)",
             title="Phaseward · bounded gate contributions\nPeak-normalized shapes; shaded buffers are outside the gated channel")
    axes.grid(alpha=.2)
    axes.legend(ncols=3, fontsize=9)
    _save(figure, output, "gates")

    modes = device.modes
    eigenvalues = modes.eigenvalues_mev2_nm
    indices = np.arange(1, len(eigenvalues)+1)
    figure = _figure(10, 7)
    spectrum, cumulative, shapes, variance = figure.subplots(2, 2).ravel()
    positive = eigenvalues > 0
    spectrum.semilogy(indices[positive], eigenvalues[positive], color="#335c81")
    spectrum.axvline(modes.retained_modes, color="#c57b18", linestyle="--", label=f"K={modes.retained_modes}")
    spectrum.set(xlabel="Mode index", ylabel="λ (meV² nm)", title="Covariance eigenvalue decay")
    spectrum.legend()
    cumulative.plot(indices, np.cumsum(eigenvalues)/modes.diagnostics["total_integrated_variance_mev2_nm"], color="#335c81")
    cumulative.scatter([modes.retained_modes], [modes.diagnostics["retained_variance_fraction"]], color="#c57b18")
    cumulative.set(xlabel="Retained mode count", ylabel="Integrated variance fraction", ylim=(0, 1.05),
                   title=f"K modes retain {100*modes.diagnostics['retained_variance_fraction']:.3f}%")
    for k in range(min(4, modes.retained_modes)):
        shapes.plot(modes.x_nm, modes.retained_shapes[:, k], label=f"φ{k+1}")
    shapes.set(xlabel="Position (nm)", ylabel="φ (nm⁻¹ᐟ²)", title="Shapes: ∫ φⱼ φₖ dx = δⱼₖ")
    shapes.legend(ncols=2)
    variance.plot(modes.x_nm, np.diag(modes.covariance_mev2), label="Full covariance", color="#335c81")
    variance.plot(modes.x_nm, np.diag(modes.retained_covariance), "--", label="K-mode covariance", color="#c57b18")
    variance.set(xlabel="Position (nm)", ylabel="Pointwise variance (meV²)", title="Discarded variance is not restored")
    variance.legend()
    for axes in (spectrum, cumulative, shapes, variance):
        axes.grid(alpha=.2)
    figure.suptitle("Phaseward · covariance modes\nδV = Σ ηₖφₖ; Var(ηₖ) = λₖ")
    _save(figure, output, "covariance_modes")


def save_disorder_plots(device: PreparedChannel, arrays: dict[str, Any], metrics: dict[str, Any], output: Path) -> None:
    """Plot paired raw samples, empirical covariance, variance, and lag correlations."""
    _common(device, output)
    figure = _figure(10, 4.8)
    full_axes, kl_axes = figure.subplots(1, 2, sharey=True)
    for sample in range(min(5, len(arrays["full_samples_mev"]))):
        full_axes.plot(device.modes.x_nm, arrays["full_samples_mev"][sample], label=f"Draw {sample}")
        kl_axes.plot(device.modes.x_nm, arrays["retained_samples_mev"][sample], label=f"Draw {sample}")
    for axes in (full_axes, kl_axes):
        axes.set(xlabel="Position (nm)", ylabel="Disorder potential (meV)")
        axes.grid(alpha=.2)
    full_axes.set_title("Full covariance samples")
    kl_axes.set_title(f"Paired {device.modes.retained_modes}-mode samples")
    full_axes.legend(ncols=2, fontsize=8)
    figure.suptitle("Phaseward · reproducible Gaussian disorder\nSame coefficient draws; no sample-wise normalization or clipping")
    _save(figure, output, "disorder_samples")

    figure = _figure(10, 8)
    target_axes, empirical_axes, variance_axes, correlation_axes = figure.subplots(2, 2).ravel()
    coords = device.modes.x_nm
    target = arrays["covariance_mev2"]
    empirical = arrays["empirical_covariance_mev2"]
    limits = (min(float(np.min(target)), float(np.min(empirical))), max(float(np.max(target)), float(np.max(empirical))))
    for axes, data, title in ((target_axes, target, "Target covariance"), (empirical_axes, empirical, "Unbiased sample covariance")):
        plot = axes.imshow(data, origin="lower", extent=[coords[0],coords[-1],coords[0],coords[-1]],
                           vmin=limits[0], vmax=limits[1], cmap="viridis", aspect="equal")
        axes.set(title=title, xlabel="x (nm)", ylabel="x′ (nm)")
        figure.colorbar(plot, ax=axes, label="Covariance (meV²)")
    for matrix, label, style in ((target,"Full target","-"), (empirical,"Full samples","--"),
                                  (arrays["kl_covariance_mev2"],"KL target","-"),
                                  (arrays["empirical_kl_covariance_mev2"],"KL samples","--")):
        variance_axes.plot(coords, np.diag(matrix), style, label=label)
    for name, label, style in (("target","Full target","-"), ("empirical","Full samples","--"),
                              ("kl_target","KL target","-"), ("kl_empirical","KL samples","--")):
        correlation_axes.plot(arrays["lag_nm"], arrays[f"{name}_lag_correlation"], style, label=label)
    variance_axes.set(xlabel="Position (nm)", ylabel="Variance (meV²)", title="Variance scaling")
    correlation_axes.set(xlabel="Separation (nm)", ylabel="Mean pair correlation", title="Correlation length and truncation")
    for axes in (variance_axes, correlation_axes):
        axes.grid(alpha=.2)
        axes.legend(ncols=2, fontsize=8)
    figure.suptitle(f"Phaseward · covariance validation, {metrics['full_sampling']['sample_count']} independent draws")
    _save(figure, output, "covariance_validation")


def save_sensitivity_plots(device: PreparedChannel, arrays: dict[str, Any], metrics: dict[str, Any], output: Path) -> None:
    """Show complex derivative magnitudes only after differentiation, step noise, and actual errors."""
    _common(device, output)
    figure = _figure(11, 4.8)
    position_axes, mode_axes = figure.subplots(1, 2)
    energy, x = device.energy_mev, device.x_nm
    local = position_axes.pcolormesh(x, energy, abs(arrays["functional_derivative_density"]), shading="auto", cmap="viridis")
    position_axes.set(xlabel="Position (nm)", ylabel="Energy (meV)", title="Local complex-t response density")
    figure.colorbar(local, ax=position_axes, label="|δt/δV(x)| [1/(meV nm)]")
    count = device.modes.retained_modes
    modal = mode_axes.pcolormesh(np.arange(1,count+1), energy, abs(arrays["dt_dz_selected"]), shading="auto", cmap="viridis")
    mode_axes.set(xlabel="Covariance mode", ylabel="Energy (meV)", title="Response per coefficient standard deviation")
    figure.colorbar(modal, ax=mode_axes, label="|√λₖ ∂t/∂ηₖ| (dimensionless)")
    figure.suptitle("Phaseward · position, mode, and energy sensitivity\nComplex derivatives are retained in CSV/NPZ")
    _save(figure, output, "sensitivity_maps")

    figure = _figure(8, 5)
    axes = figure.subplots()
    steps = arrays["steps_mev_sqrt_nm"]
    error = abs(arrays["dt_deta_finite_difference"]-arrays["dt_deta_linear_response"])
    for k in range(count):
        measured = np.max(error[:, :, k], axis=1)
        valid = measured > 0
        axes.loglog(steps[valid], measured[valid], "o-", markersize=3, label=f"Mode {k+1}")
    axes.axvline(metrics["selected_step_mev_sqrt_nm"], color="black", linestyle="--", label="Selected step")
    axes.set(xlabel="Real coefficient step h (meV √nm)", ylabel="Max energy error in complex ∂t/∂η [1/(meV √nm)]",
             title="Phaseward · centered-difference convergence\nReference: implicit derivative of the discrete scattering equations")
    axes.legend(ncols=3, fontsize=8)
    axes.grid(alpha=.2, which="both")
    _save(figure, output, "derivative_convergence")

    figure = _figure(10, 4.8)
    error_axes, ratio_axes = figure.subplots(1, 2)
    rows = [row for row in metrics["linearization"] if row["disorder_scale"] > 0]
    sigma = device.model.disorder["sigma_mev"]
    strength = np.array([row["disorder_scale"]*sigma for row in rows])
    for name, label, style in (("rms_complex_error","Taylor error within K modes","o-"),
                              ("kl_truncation_rms_error","KL truncation error","s--"),
                              ("combined_prediction_rms_error","Total error vs full covariance","^-")):
        values = np.array([row[name] for row in rows])
        valid = values > 0
        error_axes.loglog(strength[valid], values[valid], style, label=label)
    ratio = np.array([np.nan if row["error_relative_to_full_change"] is None else row["error_relative_to_full_change"] for row in rows])
    ratio_axes.semilogx(strength, ratio, "o-", color="#6d4c91")
    error_axes.set(ylabel="RMS complex-amplitude error", title="Separate Taylor and omitted-mode errors")
    ratio_axes.set(ylabel="Taylor error / RMS actual change", title="Measured first-order validity")
    error_axes.legend(fontsize=8)
    for axes in (error_axes, ratio_axes):
        axes.set_xlabel("Nominal disorder σ × scale (meV)")
        axes.grid(alpha=.2, which="both")
    figure.suptitle("Phaseward · full solves versus first order\nSame random draws across strengths; no forced agreement")
    _save(figure, output, "linearization_error")
