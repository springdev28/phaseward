"""Reproduce the PROMPT 1 continuum convergence and independent-method checks.

Run with: python examples/validate_scattering.py --output results/scattering-validation
Every curve and report is calculated; no stored success values are substituted.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from scipy.constants import elementary_charge, hbar, m_e

from qwave.diagnostics import cpu_environment, software_versions
from qwave.potentials import sample_potential
from qwave.provenance import sha256_file, source_identity
from qwave.references import (continuum_ode_reference, rectangular_probability,
                              rectangular_transmission_amplitude)
from qwave.scattering import BAND_EDGE_FRACTION_GUARD, solve_scattering
from qwave.units import physical_constants


def run_validation(output: Path) -> dict[str, Any]:
    """Export raw amplitudes and measured convergence, failing if checks regress."""
    output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    mass = .067
    rows: list[dict[str, Any]] = []
    arrays: dict[str, Any] = {}
    parameters = {
        "effective_mass_ratio": mass,
        "lead_potentials_mev": [0., 0.],
        "free": {"domain_nm": [-40, 40], "energies_mev": [5., 20., 80.], "grid_points": [81, 161, 321, 641, 1281]},
        "rectangular": {"domain_nm": [-40, 40], "height_mev": 40., "width_nm": 10., "center_nm": 0.,
                        "energies_mev": [5., 10., 20., 39., 40., 41., 60., 100.], "grid_points": [81, 161, 321, 641, 1281]},
        "gaussian": {"domain_nm": [-30, 30], "height_mev": 20., "sigma_nm": 3., "center_nm": 0.,
                     "energies_mev": [10., 25., 50., 80.], "grid_points": [121, 241, 481, 961]},
        "reference_ode": {"method": "DOP853", "rtol": 1e-11, "atol": 1e-13,
                          "tight_rtol": 1e-12, "tight_atol": 1e-14, "condition_limit": 1e10},
        "band_edge_fraction_guard": BAND_EDGE_FRACTION_GUARD,
    }

    def gaussian(position: float) -> float:
        return float(20*np.exp(-.5*(position/3)**2))

    ode = np.array([continuum_ode_reference(e, gaussian, x_min_nm=-30, x_max_nm=30,
                                           effective_mass_ratio=mass) for e in parameters["gaussian"]["energies_mev"]])
    ode_tight = np.array([continuum_ode_reference(e, gaussian, x_min_nm=-30, x_max_nm=30,
                                                 effective_mass_ratio=mass, rtol=1e-12, atol=1e-14)
                          for e in parameters["gaussian"]["energies_mev"]])
    arrays["gaussian_ode_t_r"] = ode
    arrays["gaussian_ode_t_r_tight"] = ode_tight
    for case in ("free", "rectangular", "gaussian"):
        settings = parameters[case]
        energies = np.asarray(settings["energies_mev"])
        left, right = settings["domain_nm"]
        length = right-left
        if case == "free":
            continuum_k = np.sqrt(2*mass*m_e*energies*1e-3*elementary_charge)/hbar
            exact_t = np.exp(1j*continuum_k*length*1e-9)
            exact_T = np.ones_like(energies)
            exact_r = np.zeros_like(exact_t)
            spec = {"kind": "free", "offset_mev": 0.}
        elif case == "rectangular":
            exact_t = rectangular_transmission_amplitude(energies, height_mev=40, width_nm=10,
                                                         effective_mass_ratio=mass, reference_length_nm=length)
            exact_T = rectangular_probability(energies, height_mev=40, width_nm=10, effective_mass_ratio=mass)
            exact_r = None  # Probability is benchmarked; no invented reflection-phase oracle.
            spec = dict(kind=case, offset_mev=0., height_mev=40., width_nm=10., center_nm=0.)
        else:
            exact_t, exact_r = ode[:, 0], ode[:, 1]
            exact_T = abs(exact_t)**2
            spec = dict(kind=case, offset_mev=0., height_mev=20., sigma_nm=3., center_nm=0.)
        arrays[f"{case}_energies_mev"] = energies
        arrays[f"{case}_reference_t"] = exact_t
        arrays[f"{case}_reference_T"] = exact_T
        if exact_r is not None:
            arrays[f"{case}_reference_r"] = exact_r
        for points in settings["grid_points"]:
            x = np.linspace(left, right, points)
            potential = sample_potential(x, spec)
            result = solve_scattering(x, potential, energies, effective_mass_ratio=mass)
            label = f"{case}_{points}"
            for key, value in {"x_nm": x, "potential_mev": potential, "t": result.t, "r": result.r,
                               "T": result.T, "R": result.R, "conservation": result.conservation_error,
                               "relative_residual": result.relative_residual}.items():
                arrays[f"{label}_{key}"] = value
            discrete_free_error = None
            if case == "free":
                tau = hbar**2/(2*mass*m_e*(result.spacing_nm*1e-9)**2)
                q = 2*np.arcsin(np.sqrt(energies*1e-3*elementary_charge/(4*tau)))
                discrete_free_error = float(max(abs(result.t-np.exp(1j*q*(points-1)))))
            rows.append({
                "case": case, "grid_points": points, "spacing_nm": result.spacing_nm,
                "max_T_absolute_error": float(max(abs(result.T-exact_T))),
                "max_t_absolute_error": float(max(abs(result.t-exact_t))),
                "max_r_absolute_error": None if exact_r is None else float(max(abs(result.r-exact_r))),
                "max_conservation_error": float(max(result.conservation_error)),
                "max_relative_residual": float(max(result.relative_residual)),
                "max_discrete_free_t_error": discrete_free_error,
            })
    finest = {case: [row for row in rows if row["case"] == case][-1] for case in ("free", "rectangular", "gaussian")}
    ratios = {}
    for case in finest:
        errors = [row["max_t_absolute_error"] for row in rows if row["case"] == case]
        ratios[case] = (np.asarray(errors[:-1])/errors[1:]).tolist()
    ode_tight_change = float(np.max(abs(ode-ode_tight)))
    checks = {
        "free_discrete_complex_phase": all(row["max_discrete_free_t_error"] < 1e-10 for row in rows if row["case"] == "free"),
        "conservation": all(row["max_conservation_error"] < 1e-10 for row in rows),
        "linear_residual": all(row["max_relative_residual"] < 1e-14 for row in rows),
        "rectangle_probability_finest": finest["rectangular"]["max_T_absolute_error"] < 4e-5,
        "rectangle_complex_t_finest": finest["rectangular"]["max_t_absolute_error"] < 1.1e-3,
        "gaussian_complex_t_finest": finest["gaussian"]["max_t_absolute_error"] < 6e-4,
        "gaussian_complex_r_finest": finest["gaussian"]["max_r_absolute_error"] < 5e-5,
        "second_order_complex_amplitude_convergence": all(3.8 < value < 4.3 for values in ratios.values() for value in values),
        "ode_tolerance_tightening": ode_tight_change < 1e-8,
    }
    report = {"checks": checks, "all_passed": all(checks.values()), "rows": rows,
              "complex_t_error_reduction_ratios": ratios, "ode_tolerance_tightening_max_change": ode_tight_change,
              "thresholds": {"conservation": 1e-10, "linear_residual": 1e-14, "free_discrete_t": 1e-10,
                             "rectangle_finest_T": 4e-5, "rectangle_finest_t": 1.1e-3,
                             "gaussian_finest_t": 6e-4, "gaussian_finest_r": 5e-5,
                             "convergence_ratio_range": [3.8, 4.3], "ode_tightening": 1e-8},
              "interpretation": "Resolution-specific numerical regression guards, not universal physical accuracy requirements.",
              "provenance_file": "manifest.json"}
    metadata = {
        "project": "Phaseward", "stage": "PROMPT 1 numerical validation", "manifest_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(), "parameters": parameters,
        "constants_SI": physical_constants(), "units": {"position": "nm", "energy": "meV", "amplitudes": "dimensionless"},
        "randomness": {"used": False, "seeds": []}, "software_versions": software_versions(),
        "environment": cpu_environment(), "source": source_identity(),
        "driver_sha256": sha256_file(Path(__file__)),
        "approximations": {"primary": "centered finite difference with exact discrete leads; no imaginary broadening",
                           "rectangle_sampling": "cell averages", "smooth_sampling": "point values",
                           "gaussian_truncation_nm": [-30, 30], "reference": "continuum analytic formulas and adaptive ODE matching",
                           "phase": "lead reference planes at each domain endpoint; free propagation phase retained"},
    }
    np.savez_compressed(output/"arrays.npz", **arrays, provenance_json=np.asarray(json.dumps(metadata, sort_keys=True)))
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    with (output/"convergence.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(10, 4.5), layout="constrained")
    FigureCanvasAgg(figure)
    t_axes, T_axes = figure.subplots(1, 2)
    for case in finest:
        subset = [row for row in rows if row["case"] == case]
        spacings = [row["spacing_nm"] for row in subset]
        t_axes.loglog(spacings, [row["max_t_absolute_error"] for row in subset], "o-", label=case)
        if case != "free":
            T_axes.loglog(spacings, [row["max_T_absolute_error"] for row in subset], "o-", label=case)
    for axes in (t_axes, T_axes):
        axes.set_xlabel("Grid spacing (nm)")
        axes.grid(which="both", alpha=.2)
        axes.legend()
    t_axes.set(title="Complex amplitude convergence", ylabel="Maximum |t − t_reference|")
    T_axes.set(title="Probability convergence", ylabel="Maximum |T − T_reference|")
    figure.suptitle("Phaseward · measured numerical convergence (specified test energies)")
    for extension in ("png", "svg", "pdf"):
        figure.savefig(output/f"convergence.{extension}", dpi=160)
    metadata["outputs"] = {path.name: {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
                            for path in sorted(output.iterdir())}
    metadata["elapsed_seconds_before_manifest"] = perf_counter()-started
    (output/"manifest.json").write_text(json.dumps(metadata, indent=2, allow_nan=False)+"\n")
    return report


def main() -> int:
    """Run the explicit modest validation preset and print measured summaries."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_validation(args.output)
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))
    print(f"Full arrays, convergence table, figures, and manifest: {args.output.resolve()}")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
