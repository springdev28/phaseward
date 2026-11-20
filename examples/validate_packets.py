"""Deterministic synthetic packet benchmarks, distinct from device research results.

Run: python examples/validate_packets.py --output results/packet-validation
The references are Gaussian integrals, independent adaptive quadrature, and an
analytic position-space Gaussian. All reported values are computed on each run.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from scipy.constants import elementary_charge, hbar, m_e
from scipy.integrate import quad

from qwave.diagnostics import cpu_environment, software_versions
from qwave.provenance import sha256_file, source_identity
from qwave.units import physical_constants
from qwave.wavepackets import (HBAR_MEV_PS, DelaySearch, analyze_packet, gaussian_packet,
                              reconstruct_lead_packet)


def run_validation(output: Path) -> dict[str, Any]:
    """Save every synthetic spectrum, analytic prediction, measured error, and figure."""
    output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    energy = np.linspace(2, 38, 721)
    packet = gaussian_packet(energy, central_energy_mev=20, bandwidth_mev=2,
                             propagating_bounds_mev=(0, 100))
    q = 2**2/1.5**2
    default_search = DelaySearch()
    cases = [
        ("identical_reference", np.ones_like(energy), 1., 1., 1., 0., default_search),
        ("global_phase", np.exp(1.73j)*np.ones_like(energy), 1., 1., 1., 0., default_search),
        ("linear_delay", np.exp(1j*(energy-20)*.12/HBAR_MEV_PS), 1., np.exp(-(2*.12/HBAR_MEV_PS)**2), 1., .12, default_search),
        ("delay_outside_bounds", np.exp(1j*(energy-20)*.4/HBAR_MEV_PS), 1., np.exp(-(2*.4/HBAR_MEV_PS)**2),
         np.exp(-(2*.3/HBAR_MEV_PS)**2), .1, DelaySearch(min_ps=-.1, max_ps=.1)),
        ("quadratic_phase", np.exp(1j*.08*(energy-20)**2), 1., 1/np.sqrt(1+4*.08**2*2**4),
         1/np.sqrt(1+4*.08**2*2**4), 0., default_search),
        ("amplitude_filter", np.exp(-(energy-20)**2/(4*1.5**2)), 1/np.sqrt(1+q), np.sqrt(1+q)/(1+q/2),
         np.sqrt(1+q)/(1+q/2), 0., default_search),
        ("tiny_throughput", np.full_like(energy, 1e-7), 1e-14, 1., 1., 0., default_search),
        ("zero_throughput", np.zeros_like(energy), 0., None, None, None, default_search),
    ]
    arrays: dict[str, Any] = {"synthetic_energy_mev": energy, "synthetic_incoming_A": packet.amplitude}
    rows = []
    checks: dict[str, bool] = {}
    for name, t, expected_p, expected_raw, expected_aligned, expected_delay, search in cases:
        result = analyze_packet(energy, packet.amplitude, t, np.ones_like(energy), delay=search)
        probability_ok = math.isclose(result.p_transmitted, expected_p, rel_tol=2e-12, abs_tol=0.)
        raw_ok = result.raw_fidelity is None if expected_raw is None else abs(result.raw_fidelity-expected_raw) < 2e-12
        aligned_ok = result.aligned_fidelity is None if expected_aligned is None else abs(result.aligned_fidelity-expected_aligned) < 2e-12
        delay_ok = result.estimated_delay_ps is None if expected_delay is None else abs(result.estimated_delay_ps-expected_delay) < 3e-7
        checks[name] = bool(probability_ok and raw_ok and aligned_ok and delay_ok)
        if name in {"tiny_throughput", "zero_throughput"}:
            checks[name] = checks[name] and result.low_transmission
        if name == "delay_outside_bounds":
            checks[name] = checks[name] and result.alignment_boundary_hit
        rows.append({"case": name, **result.summary(), "analytic_p_transmitted": expected_p,
                     "analytic_raw_fidelity": expected_raw, "analytic_aligned_fidelity": expected_aligned,
                     "analytic_delay_ps": expected_delay, "passed": checks[name]})
        arrays[f"{name}_t"] = t
        arrays[f"{name}_transmitted_spectrum"] = packet.amplitude*t
        arrays[f"{name}_scan_delay_ps"] = result.scan_delay_ps
        arrays[f"{name}_scan_fidelity"] = result.scan_fidelity

    def density(e: float) -> float:
        return float(np.exp(-.5*((e-15)/4)**2))

    def filtered(e):
        return .8*np.exp(-((e-15)/5)**2/4)*np.exp(1j*((e-15)*.1/HBAR_MEV_PS+.025*(e-15)**2))

    z = quad(density, 10, 30, epsabs=1e-12, epsrel=1e-12)[0]
    reference_p = quad(lambda e: density(e)*abs(filtered(e))**2, 10, 30, epsabs=1e-12, epsrel=1e-12)[0]/z
    cross = (quad(lambda e: (density(e)*filtered(e)).real, 10, 30, epsabs=1e-12, epsrel=1e-12)[0]
             + 1j*quad(lambda e: (density(e)*filtered(e)).imag, 10, 30, epsabs=1e-12, epsrel=1e-12)[0])/z
    reference_f = abs(cross)**2/reference_p
    convergence = []
    for count in [41, 81, 161, 321]:
        e = np.linspace(10, 30, count)
        sampled = gaussian_packet(e, central_energy_mev=15, bandwidth_mev=4, propagating_bounds_mev=(0, 100))
        result = analyze_packet(e, sampled.amplitude, filtered(e), np.ones_like(e))
        convergence.append({"points": count, "spacing_mev": float(e[1]-e[0]),
                            "p_transmitted": result.p_transmitted, "raw_fidelity": result.raw_fidelity,
                            "p_absolute_error": abs(result.p_transmitted-reference_p),
                            "f_absolute_error": abs(result.raw_fidelity-reference_f)})
        arrays[f"quadrature_{count}_energy_mev"] = e
        arrays[f"quadrature_{count}_A"] = sampled.amplitude
        arrays[f"quadrature_{count}_t"] = filtered(e)
    errors = np.array([max(row["p_absolute_error"], row["f_absolute_error"]) for row in convergence])
    ratios = errors[:-1]/errors[1:]
    checks["quadrature_refinement"] = bool(np.all((ratios > 3.9) & (ratios < 4.1)) and errors[-1] < 6e-7)

    # Analytic Fourier check from a Gaussian in k, transformed to energy with its Jacobian.
    k = np.linspace(.1, .5, 2001)
    sigma_k, central_k, spacing_nm, mass = .015, .3, .5, .067
    tau = hbar**2/(2*mass*m_e*(spacing_nm*1e-9)**2)/(elementary_charge*1e-3)
    e = 2*tau*(1-np.cos(k*spacing_nm))
    velocity_nm_ps = 2*tau*spacing_nm*np.sin(k*spacing_nm)/HBAR_MEV_PS
    amplitude_k = np.exp(-(k-central_k)**2/(4*sigma_k**2))/((2*np.pi)**.25*np.sqrt(sigma_k))
    amplitude_energy = amplitude_k/np.sqrt(HBAR_MEV_PS*velocity_nm_ps)
    positions = np.linspace(-300, 300, 1201)
    reconstructed = reconstruct_lead_packet(e, amplitude_energy, positions, k_per_nm=k,
        velocity_m_s=velocity_nm_ps*1000, reference_plane_nm=0., time_ps=0.)
    analytic_psi = (2*sigma_k**2/np.pi)**.25*np.exp(-sigma_k**2*positions**2+1j*central_k*positions)
    spatial_error = float(max(abs(reconstructed.amplitude_per_sqrt_nm-analytic_psi)))
    checks["energy_k_jacobian_and_analytic_wavefunction"] = spatial_error < 2e-9
    checks["spatial_parseval_norm"] = abs(reconstructed.window_probability-1) < 1e-8
    arrays.update(reconstruction_k_per_nm=k, reconstruction_energy_mev=e, reconstruction_A=amplitude_energy,
                  reconstruction_velocity_m_s=velocity_nm_ps*1000, position_nm=positions,
                  reconstructed_psi=reconstructed.amplitude_per_sqrt_nm, analytic_psi=analytic_psi)
    parameters = {
        "synthetic_packet": {"center_mev": 20., "sigma_mev": 2., "window_mev": [2., 38.], "points": 721,
                             "declared_open_band_mev": [0., 100.], "reference_t": 1.},
        "synthetic_transmissions": {"global_phase_rad": 1.73, "linear_delay_ps": .12, "out_of_bounds_delay_ps": .4,
                                    "quadratic_beta_per_mev_squared": .08, "amplitude_filter_width_mev": 1.5,
                                    "tiny_constant_amplitude": 1e-7, "zero_constant_amplitude": 0.},
        "delay_search": {"default_bounds_ps": [-.25, .25], "restricted_bounds_ps": [-.1, .1],
                         "grid_points": 201, "xatol_ps": 1e-7, "low_transmission_threshold": 1e-8},
        "quadrature": {"center_mev": 15., "sigma_mev": 4., "window_mev": [10., 30.], "points": [41,81,161,321],
                       "t_formula": "0.8 exp(-(E-15)^2/(4*5^2)) exp(i*((E-15)*0.1/hbar+0.025*(E-15)^2))",
                       "reference": "scipy.integrate.quad, epsabs=epsrel=1e-12; real/imag separately"},
        "reconstruction": {"k_window_per_nm": [.1, .5], "k_points": 2001, "sigma_k_per_nm": sigma_k,
                           "center_k_per_nm": central_k, "spacing_nm": spacing_nm, "mass_ratio": mass,
                           "position_window_nm": [-300., 300.], "position_points": 1201, "time_ps": 0.},
    }
    report = {"scope": "Synthetic deterministic mathematical checks; not research findings about a semiconductor device.",
              "all_passed": all(checks.values()), "checks": checks, "cases": rows, "quadrature_rows": convergence,
              "independent_quad_reference": {"p_transmitted": reference_p, "raw_fidelity": reference_f},
              "quadrature_error_reduction_ratios": ratios.tolist(), "max_spatial_amplitude_error": spatial_error,
              "spatial_window_probability": reconstructed.window_probability, "provenance_file": "manifest.json"}
    metadata = {"manifest_version": 1, "project": "Phaseward", "stage": "PROMPT 2 synthetic validation",
                "scope": report["scope"], "created_utc": datetime.now(timezone.utc).isoformat(), "parameters": parameters,
                "constants_SI": physical_constants(), "hbar_meV_ps": HBAR_MEV_PS,
                "software_versions": software_versions(), "environment": cpu_environment(), "source": source_identity(),
                "driver_sha256": sha256_file(Path(__file__)), "randomness": {"used": False, "seeds": []},
                "units": {"energy": "meV", "time": "ps", "position": "nm", "A": "meV^(-1/2)", "psi": "nm^(-1/2)"},
                "approximations": {"energy_quadrature": "positive composite trapezoid", "gaussian_normalization": packet.normalization,
                                   "synthetic_analytic_fidelity": "untruncated Gaussian formulas; the synthetic window spans +/-9 sigma",
                                   "reconstruction": "discrete lead dispersion, exact velocity Jacobian, numerical energy quadrature, finite spatial window"}}
    np.savez_compressed(output/"arrays.npz", **arrays, provenance_json=np.asarray(json.dumps(metadata, sort_keys=True)))
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    for filename, data in (("synthetic_cases.csv", rows), ("quadrature.csv", convergence)):
        with (output/filename).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(10, 4.5), layout="constrained")
    FigureCanvasAgg(figure)
    integral_axes, spatial_axes = figure.subplots(1, 2)
    steps = [row["spacing_mev"] for row in convergence]
    integral_axes.loglog(steps, [row["p_absolute_error"] for row in convergence], "o-", label="Transmission probability error")
    integral_axes.loglog(steps, [row["f_absolute_error"] for row in convergence], "s--", label="Raw fidelity error")
    integral_axes.set(xlabel="Energy spacing (meV)", ylabel="Absolute error", title="Independent quadrature reference")
    spatial_axes.plot(positions, abs(analytic_psi)**2, label="Analytic Gaussian in position")
    spatial_axes.plot(positions, reconstructed.density_per_nm, "--", label="Energy-basis reconstruction")
    spatial_axes.set(xlabel="Position (nm)", ylabel="Probability density (1/nm)", title="Jacobian and Fourier normalization")
    for axes in (integral_axes, spatial_axes):
        axes.grid(alpha=.2)
        axes.legend()
    figure.suptitle("Phaseward · synthetic deterministic packet checks")
    for extension in ("png", "svg", "pdf"):
        figure.savefig(output/f"packet_validation.{extension}", dpi=160)
    metadata["outputs"] = {path.name: {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
                            for path in sorted(output.iterdir())}
    metadata["elapsed_seconds_before_manifest"] = perf_counter()-started
    (output/"manifest.json").write_text(json.dumps(metadata, indent=2, allow_nan=False)+"\n")
    return report


def main() -> int:
    """Execute the explicit local validation preset and report actual checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    report = run_validation(arguments.output)
    print(json.dumps({key: value for key, value in report.items() if key not in {"cases", "quadrature_rows"}}, indent=2))
    print(f"Synthetic benchmark arrays, metrics, and figures: {arguments.output.resolve()}")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
