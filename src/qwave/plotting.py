"""Headless Phaseward figures from computed arrays with explicit units."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from numpy.typing import NDArray
import numpy as np

if TYPE_CHECKING:
    from qwave.scattering import ScatteringResult


def save_demo_plot(x: NDArray[np.float64], f_x: NDArray[np.float64], path: Path) -> Path:
    """Plot supplied dimensionless data using Matplotlib's CPU Agg canvas."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(6.4, 4.0), layout="constrained")
    FigureCanvasAgg(figure)
    axes = figure.subplots()
    axes.plot(x, f_x, label="Computed grid values: f(x) = x²")
    axes.set(xlabel="x (dimensionless)", ylabel="f(x) (dimensionless)",
             title="Numerical placeholder: polynomial quadrature\nNo electron-scattering model")
    axes.legend()
    axes.grid(alpha=0.25)
    figure.savefig(path, dpi=150, metadata={"Description": "Dimensionless polynomial demo; see manifest.json."})
    return path


def save_scattering_plots(
    x_nm: NDArray[np.float64], potential_mev: NDArray[np.float64], result: ScatteringResult,
    phase_rad: NDArray[np.float64], output: Path,
) -> list[Path]:
    """Export potential, T, R, and unwrapped complex-t phase as PNG/SVG/PDF."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(10, 7), layout="constrained")
    FigureCanvasAgg(figure)
    potential_axes, transmission_axes, reflection_axes, phase_axes = figure.subplots(2, 2).ravel()
    potential_axes.plot(x_nm, potential_mev, color="#335c81")
    potential_axes.set(title="Sampled finite-region potential", xlabel="Position x (nm)", ylabel="V (meV)")
    transmission_axes.plot(result.energies_mev, result.T, color="#226f54")
    transmission_axes.set(title="Transmission probability", xlabel="Energy E (meV)", ylabel="T = |t|²")
    reflection_axes.plot(result.energies_mev, result.R, color="#9e2a2b")
    reflection_axes.set(title="Reflection probability", xlabel="Energy E (meV)", ylabel="R = |r|²")
    phase_axes.plot(result.energies_mev, phase_rad, color="#6d4c91")
    phase_axes.set(title="Unwrapped phase of complex t", xlabel="Energy E (meV)", ylabel="arg(t) (rad)")
    for axes in (potential_axes, transmission_axes, reflection_axes, phase_axes):
        axes.grid(alpha=0.2)
    figure.suptitle(f"Phaseward · coherent 1D scattering\nReference planes: {x_nm[0]:g} → {x_nm[-1]:g} nm; propagation phase retained")
    paths = [output / f"scattering.{extension}" for extension in ("png", "svg", "pdf")]
    for path in paths:
        figure.savefig(path, dpi=160)
    return paths


def save_packet_plots(
    arrays: dict[str, Any], metrics: dict[str, Any], bandwidth_rows: list[dict[str, Any]],
    config: dict[str, Any], output: Path,
) -> list[Path]:
    """Plot computed spectra, phase, throughput/fidelity, and optional lead densities."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    paths: list[Path] = []

    def export(figure: Figure, stem: str) -> None:
        """Save each scientific figure in matching raster and vector formats."""
        for extension in ("png", "svg", "pdf"):
            path = output/f"{stem}.{extension}"
            figure.savefig(path, dpi=160)
            paths.append(path)

    def metric(value: float | None) -> str:
        return "undefined" if value is None else f"{value:.6g}"

    summary = (f"P(transmitted) = {metrics['p_transmitted']:.6g}; "
               f"conditional F(raw) = {metric(metrics['raw_fidelity'])}; "
               f"F(aligned) = {metric(metrics['aligned_fidelity'])}")
    if metrics["low_transmission"] or metrics["low_reference_transmission"]:
        summary += "\nLOW TRANSMISSION: conditional fidelity alone does not establish useful transport"
    energy = arrays["energy_mev"]
    figure = Figure(figsize=(11, 4.8), layout="constrained")
    FigureCanvasAgg(figure)
    spectrum_axes, phase_axes = figure.subplots(1, 2)
    spectrum_axes.plot(energy, arrays["incoming_density_per_mev"], label="Incoming |A|²", color="#335c81")
    spectrum_axes.plot(energy, arrays["transmitted_density_per_mev"], label="Transmitted |At|²", color="#226f54")
    spectrum_axes.plot(energy, arrays["reference_density_per_mev"], "--", label="Reference |At_ref|²", color="#777777")
    spectrum_axes.set(title="Unconditional energy densities", xlabel="Energy E (meV)", ylabel="Probability density (1/meV)")
    phase_axes.plot(energy, arrays["phase_difference_rad"], label="arg(t) − arg(t_ref)", color="#6d4c91")
    if metrics["estimated_delay_ps"] is not None:
        phase_axes.plot(energy, arrays["aligned_phase_difference_rad"], "--", label="After bounded delay removal", color="#c57b18")
    phase_axes.set(title="Phase relative to the target", xlabel="Energy E (meV)", ylabel="Phase difference (rad)")
    for axes in (spectrum_axes, phase_axes):
        axes.grid(alpha=.2)
        axes.legend()
    figure.suptitle(f"Phaseward · normalized incoming packet\n{summary}")
    export(figure, "packet_spectra")

    figure = Figure(figsize=(10, 4.8), layout="constrained")
    FigureCanvasAgg(figure)
    fidelity_axes, throughput_axes = figure.subplots(1, 2)
    widths = [row["bandwidth_mev"] for row in bandwidth_rows]
    raw = [np.nan if row["raw_fidelity"] is None else row["raw_fidelity"] for row in bandwidth_rows]
    aligned = [np.nan if row["aligned_fidelity"] is None else row["aligned_fidelity"] for row in bandwidth_rows]
    fidelity_axes.plot(widths, raw, "o-", label="Raw conditional fidelity", color="#6d4c91")
    if any(row["aligned_fidelity"] is not None for row in bandwidth_rows):
        fidelity_axes.plot(widths, aligned, "s--", label="Delay-aligned fidelity", color="#c57b18")
    fidelity_axes.set(title="Conditional state fidelity", ylabel="Fidelity (dimensionless)")
    throughput_axes.plot(widths, [row["p_transmitted"] for row in bandwidth_rows], "o-", label="Actual transmission", color="#226f54")
    throughput_axes.plot(widths, [row["p_reference"] for row in bandwidth_rows], "s--", label="Reference transmission", color="#777777")
    throughput_axes.set(title="Transmitted probability", ylabel="Probability (dimensionless)")
    for axes in (fidelity_axes, throughput_axes):
        axes.set_xlabel("Energy-density standard deviation σ_E (meV)")
        axes.grid(alpha=.2)
        axes.legend()
    figure.suptitle("Phaseward · bandwidth sweep\nConditional fidelity must be interpreted alongside throughput")
    export(figure, "packet_bandwidth")

    if len(arrays["delay_scan_ps"]):
        figure = Figure(figsize=(7.5, 4.5), layout="constrained")
        FigureCanvasAgg(figure)
        axes = figure.subplots()
        axes.plot(arrays["delay_scan_ps"], arrays["delay_scan_fidelity"], label="Bounded scan", color="#6d4c91")
        axes.scatter([0], [metrics["raw_fidelity"]], label="No alignment", color="#335c81")
        if metrics["estimated_delay_ps"] is not None:
            axes.scatter([metrics["estimated_delay_ps"]], [metrics["aligned_fidelity"]],
                         label=f"Selected delay: {metrics['estimated_delay_ps']:.6g} ps", color="#c57b18")
        axes.set(xlabel="Removed output delay (ps); positive = lag", ylabel="Conditional fidelity",
                 title=f"Phaseward · declared delay search [{config['delay_alignment']['min_ps']:g}, {config['delay_alignment']['max_ps']:g}] ps\n{metrics['alignment_status']}")
        axes.grid(alpha=.2)
        axes.legend()
        export(figure, "packet_delay")

    if config["reconstruction"]["enabled"]:
        figure = Figure(figsize=(11, 4.8), layout="constrained")
        FigureCanvasAgg(figure)
        incident_axes, outgoing_axes = figure.subplots(1, 2, sharey=True)
        incident_axes.plot(arrays["incident_position_nm"], arrays["incident_position_density_per_nm"], color="#335c81", label="Incoming component")
        incident_axes.set(title="Left lead, t = 0 ps", xlabel="Position x (nm)", ylabel="Unconditional |Ψ|² (1/nm)")
        outgoing_axes.plot(arrays["transmitted_position_nm"], arrays["transmitted_position_density_per_nm"], color="#226f54", label="Actual outgoing component")
        outgoing_axes.plot(arrays["reference_position_nm"], arrays["reference_position_density_per_nm"], "--", color="#777777", label="Clean-reference outgoing component")
        outgoing_axes.set(title=f"Right lead, t = {config['reconstruction']['observation_time_ps']:g} ps", xlabel="Position x (nm)")
        for axes in (incident_axes, outgoing_axes):
            axes.grid(alpha=.2)
            axes.legend()
        figure.suptitle(f"Phaseward · reconstructed lead components\n{summary}")
        export(figure, "packet_position")
    return paths
