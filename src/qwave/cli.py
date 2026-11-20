"""Offline Phaseward CLI: diagnostics, configuration, scattering, and packets."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from qwave import __version__
from qwave.config import (ConfigError, DemoConfig, ScatterConfig, PacketConfig,
                          DisorderConfig, SensitivityConfig, load_config)
from qwave.diagnostics import doctor_report


def build_parser() -> argparse.ArgumentParser:
    """Define only implemented commands; no speculative physics commands."""
    parser = argparse.ArgumentParser(prog="qwave", description="Phaseward — local CPU electron-wave research toolkit.")
    parser.add_argument("--version", action="version", version=f"qwave {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Check Python, package imports, and the CPU environment")
    doctor.add_argument("--dev", action="store_true", help="Also require pytest for success")
    check = commands.add_parser("config-check", help="Validate a complete experiment JSON configuration")
    check.add_argument("path", type=Path)
    paper = commands.add_parser("paper-export", help="Audit a frozen experiment and export manuscript support without new solves")
    paper.add_argument("--run", type=Path, required=True, help="Completed experiment_suite directory with manifest v2")
    paper.add_argument("--output", type=Path, required=True, help="New directory; existing outputs are never overwritten")
    demo = commands.add_parser("demo", help="Run a dimensionless polynomial placeholder, not electron scattering")
    demo.add_argument("--config", type=Path, help="JSON file; otherwise use documented built-in defaults")
    demo.add_argument("--output", type=Path, help="New directory; default: results/demo-<UTC timestamp>")
    demo.add_argument("--plot", action="store_true", help="Save a headless PNG of the computed polynomial grid")
    from qwave.experiment_config import PRESETS
    suite = commands.add_parser("experiment", help="Run a prespecified comparison and numerical convergence suite")
    suite.add_argument("preset", choices=PRESETS)
    suite.add_argument("--config", type=Path, help="Complete experiment_suite config; preset name must match")
    suite.add_argument("--output", type=Path, required=True, help="New local result directory")
    suite.add_argument("--overwrite", action="store_true", help="Explicitly replace an existing experiment-owned directory")
    suite.add_argument("--research", action="store_true", help="Explicitly select/authorize the slower research profile")
    scatter = commands.add_parser("scatter", help="Solve stationary coherent 1D electron scattering")
    scatter.add_argument("--config", type=Path, required=True, help="Complete scattering JSON configuration")
    scatter.add_argument("--output", type=Path, required=True, help="New result directory, including data and plots")
    packet = commands.add_parser("packet", help="Compute normalized packet spectra, transmission, and conditional fidelity")
    packet.add_argument("--config", type=Path, required=True, help="Complete packet JSON configuration")
    packet.add_argument("--output", type=Path, required=True, help="New result directory, including spectra, metrics, and plots")
    for name, help_text in (("disorder", "Sample correlated channel disorder and validate covariance/KL scaling"),
                            ("sensitivity", "Study complex transmission derivatives and first-order validity"),
                            ("optimize", "Compare constrained gate optimizers under recorded CPU solve budgets")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--config", type=Path, required=True, help="Complete experiment JSON configuration")
        command.add_argument("--output", type=Path, required=True, help="New result directory, including data, diagnostics, and plots")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run a command; return 0 on success, 1 for failed checks, 2 for invalid input/I/O."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "paper-export":
            from qwave.paper_export import export_paper

            path = export_paper(args.run, args.output, progress=lambda message: print(message, flush=True))
            print(f"Verified manuscript-support package: {path}")
            print("Results remains unfilled. Export verification does not establish a scientific discovery.")
            return 0
        if args.command == "doctor":
            report = doctor_report(require_dev=args.dev)
            print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
            return 0 if report["ok"] else 1
        if args.command == "config-check":
            config = load_config(args.path)
            print(json.dumps({"valid": True, "config": config.to_dict()}, indent=2, sort_keys=True))
            return 0
        if args.command == "experiment":
            from qwave.experiment_config import ExperimentConfig, preset_config
            from qwave.experiment_runner import run_experiment

            config = load_config(args.config) if args.config else preset_config(args.preset, research=args.research)
            if not isinstance(config, ExperimentConfig) or config.preset != args.preset:
                raise ConfigError("experiment requires an experiment_suite config with the matching preset")
            path = run_experiment(config, args.output, overwrite=args.overwrite, allow_research=args.research,
                                  progress=lambda value: print(value, flush=True))
            summary = json.loads((path / "summary.json").read_text())
            print(f"Phaseward {args.preset} saved: {path.resolve()}")
            print(f"Status: {summary['status']}; conditional hypothesis outcome: {summary['hypothesis_outcome']}")
            print("Read report.md for paired intervals, failures, feasibility, and separate convergence diagnostics.")
            return 0 if summary["status"] == "completed" else 1
        if args.command == "demo":
            from qwave.experiments import DEMO_SCOPE, run_demo

            config = load_config(args.config) if args.config else DemoConfig()
            if not isinstance(config, DemoConfig):
                raise ConfigError("demo requires a numerical_demo configuration; use scatter for physics")
            output = args.output or Path("results") / f"demo-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}"
            path = run_demo(config, output, plot=args.plot)
            print(DEMO_SCOPE)
            print(f"Saved result bundle: {path.resolve()}")
            print("Keep manifest.json with the CSV, JSON, NPZ, and any figure.")
            return 0
        if args.command == "scatter":
            from qwave.experiments import run_scatter

            config = load_config(args.config)
            if not isinstance(config, ScatterConfig):
                raise ConfigError("scatter requires a stationary_scattering configuration")
            path = run_scatter(config, args.output)
            diagnostics = json.loads((path / "diagnostics.json").read_text())
            print(f"Phaseward stationary scattering saved: {path.resolve()}")
            print(f"Maximum |T+R-1|: {diagnostics['max_abs_T_plus_R_minus_one']:.6g}")
            print("Complex amplitudes, units, phase convention, and approximations are saved with the data.")
            if diagnostics["phase_sampling_warning"]:
                print("Phase sampling warning: refine the energy grid before interpreting the unwrapped phase.")
            return 0 if diagnostics["conservation_passed"] else 1
        if args.command == "packet":
            from qwave.packet_experiments import run_packet

            config = load_config(args.config)
            if not isinstance(config, PacketConfig):
                raise ConfigError("packet requires a wave_packet configuration")
            path = run_packet(config, args.output)
            metrics = json.loads((path/"metrics.json").read_text())
            print(f"Phaseward packet saved: {path.resolve()}")
            print(f"Transmitted probability: {metrics['p_transmitted']:.8g}")
            print(f"Reference transmitted probability: {metrics['p_reference']:.8g}")
            print(f"Raw conditional fidelity: {metrics['raw_fidelity']}")
            print(f"Delay-aligned conditional fidelity: {metrics['aligned_fidelity']}")
            print(f"Estimated output lag (ps): {metrics['estimated_delay_ps']} ({metrics['alignment_status']})")
            if metrics["low_transmission"] or metrics["low_reference_transmission"]:
                print("LOW TRANSMISSION: conditional fidelity alone does not establish useful transport.")
            if metrics["raw_fidelity"] is None:
                print("Conditional fidelity is undefined because an output probability is numerically unresolved.")
            if metrics["alignment_boundary_hit"]:
                print("The delay optimum is at the declared search boundary; the unconstrained delay is not inferred.")
            return 0 if metrics["diagnostics"]["conservation_passed"] else 1
        if args.command == "optimize":
            from qwave.optimization_config import OptimizeConfig
            from qwave.optimization_experiments import run_optimization

            config = load_config(args.config)
            if not isinstance(config, OptimizeConfig):
                raise ConfigError("optimize requires a gate_optimization configuration")
            path = run_optimization(config,args.output,progress=lambda value:print(value,flush=True))
            metrics = json.loads((path/"metrics.json").read_text())
            print(f"Phaseward optimization comparison saved: {path.resolve()}")
            for row in metrics["runs"]:
                candidate = row["reported_candidate"]
                print(f"{row['run_id']}: {row['status']}; search work={row['cost']['forward_work']}; "
                      f"objective={None if candidate is None else candidate['objective']}; "
                      f"minimum scaled residual={None if candidate is None else candidate['minimum_scaled_residual']}")
            print("Held-out evaluation occurs after every candidate is frozen; no method is assumed to win.")
            return 0 if metrics["all_checks_passed"] else 1
        if args.command in {"disorder", "sensitivity"}:
            from qwave.disorder_experiments import run_disorder, run_sensitivity

            config = load_config(args.config)
            expected = DisorderConfig if args.command == "disorder" else SensitivityConfig
            if not isinstance(config, expected):
                raise ConfigError(f"{args.command} requires a {expected.__name__} configuration")
            path = (run_disorder if args.command == "disorder" else run_sensitivity)(config, args.output)
            metrics = json.loads((path/"metrics.json").read_text())
            print(f"Phaseward {args.command} saved: {path.resolve()}")
            print(f"Retained disorder variance fraction: {metrics['kl']['retained_variance_fraction']:.8g}")
            print("Mode convention: integral phi_j phi_k dx = delta_jk; Var(eta_k) = lambda_k.")
            if args.command == "disorder":
                print(f"Full-sample mean variance / target: {metrics['full_sampling']['mean_variance_ratio_on_active_nodes']:.8g}")
                print(f"Empirical sampling checks: {metrics['sampling_checks_passed']}")
                return 0 if metrics['sampling_checks_passed'] else 1
            print(f"Selected centered-difference step (meV sqrt(nm)): {config.selected_step_mev_sqrt_nm:g}")
            print(f"Selected-step max complex derivative error vs linear response: {metrics['selected_step_max_derivative_error']:.8g}")
            print(f"Modes with small-step error growth: {metrics['modes_with_small_step_error_growth']}")
            if metrics["selected_step_unresolved_perturbations"]:
                print("Selected-step perturbations are unresolved in floating point; this derivative baseline is not usable.")
            for row in metrics["linearization"]:
                print(f"Disorder scale {row['disorder_scale']:g}: RMS complex-t approximation error {row['rms_complex_error']:.8g}")
            print("First-order errors are saved at every strength; linearized amplitudes are not forced to be lossless.")
            return 0 if metrics["conservation_passed"] and not metrics["selected_step_unresolved_perturbations"] else 1
    except (ValueError, OSError, ImportError) as error:
        print(f"qwave: {error}", file=sys.stderr)
        return 2
    return 2
