"""Reproducible packet experiments using Phaseward's validated scattering basis."""

from __future__ import annotations

import csv
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from qwave.config import PacketConfig, ScatterConfig
from qwave.diagnostics import cpu_environment, software_versions
from qwave.experiments import _write_json
from qwave.potentials import sample_potential
from qwave.provenance import sha256_file, source_identity
from qwave.scattering import (BAND_EDGE_FRACTION_GUARD, PHASE_AMPLITUDE_FLOOR,
                             solve_scattering, transmission_phase)
from qwave.units import physical_constants
from qwave.wavepackets import (HBAR_MEV_PS, MIN_NORMAL_PROBABILITY, DelaySearch,
                              analyze_packet, gaussian_packet, quadrature_weights,
                              reconstruct_lead_packet)


def run_packet(config: PacketConfig, output: str | Path, *, plot: bool = True) -> Path:
    """Solve an actual and declared clean-reference device, then archive packet metrics.

    The reference changes only the potential; mass, grid, leads, energies, and
    reference planes are identical. A coarse nested quadrature comparison and
    optional lead reconstruction diagnostics are saved without forcing agreement.
    """
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"output directory already exists: {output}")
    started = perf_counter()
    device = ScatterConfig.from_mapping(config.scattering)
    reference = replace(device, potential=config.reference_potential)
    x = np.linspace(device.x_min_nm, device.x_max_nm, device.grid_points)
    energy = np.linspace(device.energy_min_mev, device.energy_max_mev, device.energy_points)
    potential = sample_potential(x, device.potential)
    reference_potential = sample_potential(x, reference.potential)
    arguments = dict(effective_mass_ratio=device.effective_mass_ratio,
                     left_lead_mev=device.left_lead_mev, right_lead_mev=device.right_lead_mev)
    actual = solve_scattering(x, potential, energy, **arguments)
    clean = solve_scattering(x, reference_potential, energy, **arguments)
    common_band = config.propagating_bounds_mev()
    delay = DelaySearch(**config.delay_alignment)
    floor = config.minimum_transmission_probability
    packet = gaussian_packet(energy, central_energy_mev=config.central_energy_mev,
                             bandwidth_mev=config.bandwidth_mev, propagating_bounds_mev=common_band)
    # Position the incoming component upstream at t=0; this common phase cancels in fidelity.
    launch_phase = np.exp(-1j*actual.k_left_per_nm*config.reconstruction["source_offset_nm"])
    incoming = packet.amplitude*launch_phase
    analysis = analyze_packet(energy, incoming, actual.t, clean.t, delay=delay,
                              minimum_transmission_probability=floor)
    coarse_packet = gaussian_packet(energy[::2], central_energy_mev=config.central_energy_mev,
                                    bandwidth_mev=config.bandwidth_mev, propagating_bounds_mev=common_band)
    coarse_incoming = coarse_packet.amplitude*launch_phase[::2]
    coarse_analysis = analyze_packet(energy[::2], coarse_incoming, actual.t[::2], clean.t[::2],
                                     delay=delay, minimum_transmission_probability=floor)
    coarse_difference = {
        name: None if analysis.summary()[name] is None or coarse_analysis.summary()[name] is None
        else abs(analysis.summary()[name]-coarse_analysis.summary()[name])
        for name in ("p_transmitted", "p_reference", "raw_fidelity", "aligned_fidelity", "estimated_delay_ps")
    }
    reflected_probability = float(np.dot(packet.weights_mev, abs(incoming*actual.r)**2))
    reference_reflected = float(np.dot(packet.weights_mev, abs(incoming*clean.r)**2))
    bandwidth_rows = []
    for bandwidth in config.bandwidth_sweep_mev:
        sweep_packet = gaussian_packet(energy, central_energy_mev=config.central_energy_mev,
                                       bandwidth_mev=bandwidth, propagating_bounds_mev=common_band)
        sweep = analyze_packet(energy, sweep_packet.amplitude*launch_phase, actual.t, clean.t,
                                delay=delay, minimum_transmission_probability=floor)
        bandwidth_rows.append({"bandwidth_mev": bandwidth, **sweep.summary(),
                               "gaussian_window_mass": sweep_packet.normalization["untruncated_gaussian_mass_in_window"]})
    relative_phase_product = actual.t*clean.t.conj()
    phase_resolved = (abs(actual.t) > PHASE_AMPLITUDE_FLOOR) & (abs(clean.t) > PHASE_AMPLITUDE_FLOOR)
    relative_phase_product = np.where(phase_resolved, relative_phase_product, 0.)
    phase_difference = transmission_phase(relative_phase_product, amplitude_floor=PHASE_AMPLITUDE_FLOOR**2)
    delay_phase_pivot = float(np.dot(packet.weights_mev, abs(incoming)**2*energy))
    aligned_phase = np.full_like(energy, np.nan)
    if analysis.estimated_delay_ps is not None:
        aligned_phase = phase_difference-(energy-delay_phase_pivot)*analysis.estimated_delay_ps/HBAR_MEV_PS
    arrays: dict[str, Any] = {
        "energy_mev": energy, "weights_mev": packet.weights_mev,
        "incoming_A": incoming, "transmitted_unnormalized": incoming*actual.t,
        "reference_unnormalized": incoming*clean.t, "device_t": actual.t, "device_r": actual.r,
        "reference_t": clean.t, "reference_r": clean.r,
        "incoming_density_per_mev": abs(incoming)**2,
        "transmitted_density_per_mev": abs(incoming*actual.t)**2,
        "reference_density_per_mev": abs(incoming*clean.t)**2,
        "phase_difference_rad": phase_difference, "aligned_phase_difference_rad": aligned_phase,
        "x_nm": x, "potential_mev": potential, "reference_potential_mev": reference_potential,
        "k_left_per_nm": actual.k_left_per_nm, "k_right_per_nm": actual.k_right_per_nm,
        "velocity_left_m_s": actual.velocity_left_m_s, "velocity_right_m_s": actual.velocity_right_m_s,
        "device_conservation_error": actual.conservation_error, "reference_conservation_error": clean.conservation_error,
        "device_relative_residual": actual.relative_residual, "reference_relative_residual": clean.relative_residual,
        "delay_scan_ps": analysis.scan_delay_ps, "delay_scan_fidelity": analysis.scan_fidelity,
    }
    if analysis.transmitted_state is not None:
        arrays["normalized_transmitted_spectrum"] = analysis.transmitted_state
    if analysis.target_state is not None:
        arrays["normalized_target_spectrum"] = analysis.target_state
    reconstruction_info: dict[str, Any] = {"enabled": config.reconstruction["enabled"]}
    if config.reconstruction["enabled"]:
        settings = config.reconstruction
        left_positions = np.linspace(x[0]-settings["lead_extent_nm"], x[0], settings["position_points"])
        right_positions = np.linspace(x[-1], x[-1]+settings["lead_extent_nm"], settings["position_points"])
        for name, spectrum, coarse_spectrum, positions, k, velocity, plane, time in (
            ("incident", incoming, coarse_incoming, left_positions, actual.k_left_per_nm, actual.velocity_left_m_s, x[0], 0.),
            ("transmitted", incoming*actual.t, coarse_incoming*actual.t[::2], right_positions,
             actual.k_right_per_nm, actual.velocity_right_m_s, x[-1], settings["observation_time_ps"]),
            ("reference", incoming*clean.t, coarse_incoming*clean.t[::2], right_positions,
             clean.k_right_per_nm, clean.velocity_right_m_s, x[-1], settings["observation_time_ps"]),
        ):
            common = dict(reference_plane_nm=float(plane), time_ps=time, carrier_energy_mev=config.central_energy_mev)
            reconstructed = reconstruct_lead_packet(energy, spectrum, positions, k_per_nm=k, velocity_m_s=velocity, **common)
            coarse = reconstruct_lead_packet(energy[::2], coarse_spectrum, positions,
                                              k_per_nm=k[::2], velocity_m_s=velocity[::2], **common)
            arrays[f"{name}_position_nm"] = positions
            arrays[f"{name}_psi_per_sqrt_nm"] = reconstructed.amplitude_per_sqrt_nm
            arrays[f"{name}_position_density_per_nm"] = reconstructed.density_per_nm
            reconstruction_info[name] = {
                "time_ps": time, "window_probability": reconstructed.window_probability,
                "coarse_energy_window_probability": coarse.window_probability,
                "coarse_fine_density_l1_difference": float(np.dot(quadrature_weights(positions),
                    abs(reconstructed.density_per_nm-coarse.density_per_nm))),
            }
    conservation_error = max(float(max(actual.conservation_error)), float(max(clean.conservation_error)))
    diagnostics = {
        "max_stationary_conservation_error": conservation_error,
        "max_stationary_relative_residual": max(float(max(actual.relative_residual)), float(max(clean.relative_residual))),
        "p_reflected": reflected_probability, "p_reference_reflected": reference_reflected,
        "packet_probability_conservation_error": abs(analysis.p_transmitted+reflected_probability-1),
        "reference_packet_probability_conservation_error": abs(analysis.p_reference+reference_reflected-1),
        "conservation_tolerance": device.conservation_tolerance,
        "conservation_passed": conservation_error <= device.conservation_tolerance,
        "energy_quadrature": {"fine_points": len(energy), "coarse_points": len(energy[::2]),
                              "fine_minus_coarse_absolute_differences": coarse_difference,
                              "coarse_metrics": coarse_analysis.summary(),
                              "note": "A nested energy-quadrature diagnostic; not a spatial-convergence or universal accuracy certificate."},
        "reconstruction": reconstruction_info,
    }
    metrics = {**analysis.summary(), "minimum_transmission_probability": floor, "delay_phase_pivot_mev": delay_phase_pivot,
               "gaussian_normalization": packet.normalization, "diagnostics": diagnostics,
               "provenance_file": "manifest.json"}
    provenance: dict[str, Any] = {
        "manifest_version": 1, "project": "Phaseward", "stage": "PROMPT 2",
        "created_utc": datetime.now(timezone.utc).isoformat(), "config": config.to_dict(),
        "reference_device_config": reference.to_dict(),
        "physics_model": "Elastic coherent constant-effective-mass 1D Schrodinger scattering; spectral superposition in the same discrete leads",
        "constants_SI": physical_constants(), "hbar_meV_ps": HBAR_MEV_PS,
        "software_versions": software_versions(), "environment": cpu_environment(), "source": source_identity(),
        "randomness": {"used": False, "seeds": [], "reason": "deterministic spectral calculation"},
        "units": {"energy": "meV", "position": "nm", "time_and_delay": "ps", "A": "meV^(-1/2)",
                  "spectral_density": "1/meV", "spatial_wavefunction": "nm^(-1/2)", "spatial_density": "1/nm",
                  "probabilities_and_fidelities": "dimensionless", "velocity": "m/s"},
        "normalization": {"incoming": "integral |A(E)|^2 dE = 1", "bandwidth": "standard deviation of untruncated |A|^2",
                          "transmitted_state": "A*t/sqrt(P_transmitted)", "target_state": "A*t_reference/sqrt(P_reference)",
                          "fidelity": "squared modulus of normalized complex spectral overlap; always separate from transmission",
                          "lead_basis": "exp(ik(x-x_plane))/sqrt(2*pi*hbar*v), energy normalized",
                          "energy_to_k_jacobian": "dE/dk=hbar*v; A_k=A_E*sqrt(hbar*v)",
                          "gaussian_truncation": packet.normalization},
        "phase_convention": {"left_plane_nm": float(x[0]), "right_plane_nm": float(x[-1]),
                             "scattering_phase": "free propagation phase retained; same basis for actual and reference",
                             "launch_phase": "A=A_gaussian*exp(-i*k_left*source_offset_nm)",
                             "time_dependence": "exp(-i*(E-central_energy)*time/hbar); carrier removal is a global phase",
                             "delay_phase_pivot_mev": delay_phase_pivot,
                             "positive_estimated_delay": "output lags target; alignment multiplies output by exp(-i*(E-mean_incoming_energy)*delay/hbar)"},
        "approximations": {
            "stationary_method": "second-order centered finite difference with exact retarded discrete leads and pivoted banded solve",
            "spacing_nm": actual.spacing_nm, "hopping_mev": actual.hopping_mev,
            "common_lead_band_mev": list(common_band), "band_edge_fraction_guard": BAND_EDGE_FRACTION_GUARD,
            "potential_sampling": "cell-averaged rectangular edges, point-sampled smooth profiles; uniform leads outside finite domain",
            "energy_window_mev": [float(energy[0]), float(energy[-1])],
            "quadrature": "positive composite trapezoidal weights, shared by norms, probabilities, and overlaps",
            "phase_display_amplitude_floor": PHASE_AMPLITUDE_FLOOR,
            "unresolved_probability_floor": MIN_NORMAL_PROBABILITY,
            "delay_search": {**config.delay_alignment, "method": "grid including zero and endpoints; bounded local refinement of all scan maxima",
                             "global_optimum_guarantee": False, "flat_scan_tolerance": 1e-12},
            "position_reconstruction": "band-limited continuation of right-going finite-difference lead modes with exact discrete k and group velocity",
            "display_boundaries": "incident component in left lead at t=0, outgoing components in right lead at declared later time; no device-interior or reflected density",
            "spatial_normalization": "unconditional; finite display windows are not renormalized",
            "spatial_sampling_guard": "max position step times max k must be <= pi/2",
            "dtype": "complex128/float64", "artificial_imaginary_broadening_mev": 0.,
        },
        "metrics": metrics, "options": {"plot": plot},
    }
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output/"config.json", config.to_dict())
    _write_json(output/"metrics.json", metrics)
    np.savez_compressed(output/"arrays.npz", **arrays,
                        provenance_json=np.asarray(json.dumps(provenance, sort_keys=True, allow_nan=False)))
    conditional = np.full(len(energy), np.nan) if analysis.transmitted_state is None else abs(analysis.transmitted_state)**2
    target_density = np.full(len(energy), np.nan) if analysis.target_state is None else abs(analysis.target_state)**2
    np.savetxt(output/"spectrum.csv", np.column_stack((energy, incoming.real, incoming.imag, abs(incoming)**2,
               abs(incoming*actual.t)**2, abs(incoming*clean.t)**2, conditional, target_density,
               actual.t.real, actual.t.imag, clean.t.real, clean.t.imag, phase_difference, aligned_phase)),
               delimiter=",", comments="", fmt="%.17g",
               header="energy_mev,A_real,A_imag,incident_density_per_mev,transmitted_density_per_mev,reference_density_per_mev,conditional_transmitted_density_per_mev,conditional_target_density_per_mev,t_real,t_imag,t_reference_real,t_reference_imag,phase_difference_rad,aligned_phase_difference_rad")
    np.savetxt(output/"potential.csv", np.column_stack((x, potential, reference_potential)),
               delimiter=",", comments="", fmt="%.17g", header="x_nm,potential_mev,reference_potential_mev")
    with (output/"bandwidth.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(bandwidth_rows[0]))
        writer.writeheader()
        writer.writerows(bandwidth_rows)
    np.savetxt(output/"delay_scan.csv", np.column_stack((analysis.scan_delay_ps, analysis.scan_fidelity)),
               delimiter=",", comments="", fmt="%.17g", header="delay_ps,conditional_fidelity")
    names = ["config.json", "metrics.json", "arrays.npz", "spectrum.csv", "potential.csv", "bandwidth.csv", "delay_scan.csv"]
    if config.reconstruction["enabled"]:
        for component in ("incident", "transmitted", "reference"):
            name = f"{component}_packet.csv"
            psi = arrays[f"{component}_psi_per_sqrt_nm"]
            np.savetxt(output/name, np.column_stack((arrays[f"{component}_position_nm"], psi.real, psi.imag,
                       arrays[f"{component}_position_density_per_nm"])), delimiter=",", comments="", fmt="%.17g",
                       header="position_nm,psi_real_per_sqrt_nm,psi_imag_per_sqrt_nm,probability_density_per_nm")
            names.append(name)
    if plot:
        from qwave.plotting import save_packet_plots

        names.extend(path.name for path in save_packet_plots(arrays, metrics, bandwidth_rows, config.to_dict(), output))
    provenance["outputs"] = {name: {"sha256": sha256_file(output/name), "size_bytes": (output/name).stat().st_size}
                             for name in names}
    provenance["elapsed_seconds_before_manifest"] = perf_counter()-started
    _write_json(output/"manifest.json", provenance)
    return output
