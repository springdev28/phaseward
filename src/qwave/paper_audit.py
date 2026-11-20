"""Read-only consistency checks for completed, frozen experiment-suite artifacts.

An audit authenticates internal consistency, not authorship, external registration,
continuum accuracy, or the truth of physical assumptions. It never solves a device.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np

from qwave.experiment_config import ExperimentConfig
from qwave.experiment_support import descriptive_statistics
from qwave.gui_results import ResultBundle, load_bundle, strict_json
from qwave.wavepackets import DelaySearch, analyze_packet, quadrature_weights

# Serialization/replay tolerances, not physical accuracy claims. Same arrays and
# algorithm should reproduce to roundoff; allow several hundred double-precision
# ulps in reductions. Delay's separate tolerance follows the saved search xatol.
REPLAY_ATOL = 2e-13
REPLAY_RTOL = 2e-12
REPLAY_MODULES = ("experiment_config.py", "experiment_runner.py", "experiment_support.py",
                  "experiment_plotting.py", "statistics.py", "wavepackets.py", "units.py")


def require(condition: bool, message: str) -> None:
    """Fail closed with a useful artifact-specific error, including under python -O."""
    if not condition:
        raise ValueError("paper audit: " + message)


def equivalent(actual: Any, expected: Any, location: str) -> None:
    """Recursively compare serialized metrics, preserving undefined values and flags."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and actual.keys() == expected.keys(), location + " keys differ")
        for key, value in expected.items():
            equivalent(actual[key], value, location + "." + key)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), location + " lengths differ")
        for index, value in enumerate(expected):
            equivalent(actual[index], value, f"{location}[{index}]")
    elif isinstance(expected, float):
        require(isinstance(actual, (int, float)) and not isinstance(actual, bool)
                and bool(np.isclose(actual, expected, atol=REPLAY_ATOL, rtol=REPLAY_RTOL)),
                location + " numerical mismatch")
    else:
        require(type(actual) is type(expected) and actual == expected, location + " differs")


def read_csv(data: bytes) -> list[dict[str, str]]:
    """Read bounded, inventoried CSV without executing formulas or evaluating code."""
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    fields = reader.fieldnames or []
    require(len(fields) == len(set(fields)), "duplicate CSV column")
    rows = list(reader)
    require(all(None not in row and None not in row.values() for row in rows), "ragged CSV")
    return rows


def verify_csv(data: bytes, records: list[dict], name: str) -> None:
    """Check every serialized cell against its JSON record, including missing fields."""
    rows = read_csv(data)
    require(len(rows) == len(records), name + " row count differs")
    fields = set().union(*(row.keys() for row in records)) if records else set()
    for row, record in zip(rows, records):
        require(set(row) == fields, name + " fields differ")
        for key, value in row.items():
            expected = record.get(key)
            text = (json.dumps(expected, sort_keys=True, allow_nan=False) if isinstance(expected, (dict, list))
                    else "" if expected is None else str(expected))
            require(value == text, f"{name} cell {key} differs from JSON")


def numeric_csv(data: bytes) -> list[dict]:
    """Decode the suite's cost table; identifiers remain text and missing cells null."""
    rows = read_csv(data)
    for row in rows:
        for key, value in row.items():
            if value == "":
                row[key] = None
            elif key not in {"case", "method", "phase", "run_id"}:
                try:
                    row[key] = json.loads(value)
                except json.JSONDecodeError as error:
                    raise ValueError(f"invalid numeric cost cell {key}") from error
                require(type(row[key]) in (int, float) and np.isfinite(row[key]), "invalid cost value")
    return rows


def canonical_svg(data: bytes) -> str:
    """Ignore only render timestamps and random resource IDs, retaining all geometry."""
    root = ET.fromstring(data)
    for parent in root.iter():
        for child in list(parent):
            if child.tag == "{http://www.w3.org/2000/svg}metadata":
                parent.remove(child)
    ids = {node.attrib["id"]: f"resource_{index}" for index, node in enumerate(root.iter()) if "id" in node.attrib}
    for node in root.iter():
        for key, value in list(node.attrib.items()):
            if key == "id":
                node.set(key, ids[value])
            elif value.startswith("#") and value[1:] in ids:
                node.set(key, "#" + ids[value[1:]])
            else:
                node.set(key, re.sub(r"url\(#([^)]*)\)", lambda m: "url(#" + ids.get(m[1], m[1]) + ")", value))
    return ET.canonicalize(ET.tostring(root, encoding="unicode"))


def canonical_pdf(data: bytes) -> bytes:
    """Ignore only the Matplotlib creation timestamp, keeping all page streams."""
    require(len(re.findall(rb"/CreationDate \([^)]*\)", data)) == 1, "unexpected PDF creation metadata")
    return re.sub(rb"/CreationDate \([^)]*\)", b"/CreationDate (TIMESTAMP)", data)


@dataclass
class AuditedRun:
    """Verified records and provenance, kept separate from export-time metadata."""

    bundle: ResultBundle
    config: ExperimentConfig
    summary: dict
    trials: list[dict]
    convergence: dict
    costs: list[dict]
    descriptions: dict
    arrays: dict[str, np.ndarray]
    verification: dict


def _audit_run(path: Path) -> AuditedRun:
    """Reject incomplete, changed, incompatible or internally inconsistent runs."""
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), "source path uses a symlink")
    bundle = load_bundle(path, path.parent)
    manifest = bundle.manifest
    require(manifest.get("manifest_version") == 2, "requires experiment-suite manifest version 2")
    require(manifest.get("status") in {"completed", "completed_with_failed_checks"}, "run is incomplete or failed")
    require(manifest["config"].get("experiment") == "experiment_suite", "unsupported run type; use a frozen experiment suite")
    required = {"config.json", "summary.json", "run_plan.json", "frozen_candidates.json", "seeds.json",
                "arrays.npz", "trials.json", "trials.csv", "paired_differences.csv", "convergence.json",
                "convergence.csv", "costs.csv", "candidates.jsonl", "candidates.csv", "figure_descriptions.json"}
    require(required <= set(bundle.files), "missing required frozen-run artifacts")
    config = ExperimentConfig.from_mapping(bundle.json("config.json"))
    equivalent(manifest["config"], config.to_dict(), "manifest config")
    equivalent(manifest["source"], manifest["source_at_completion"], "source changed during run")
    source_files = manifest["source"]["files_sha256"]
    for name in REPLAY_MODULES:
        recorded = source_files.get(name, source_files.get("src/qwave/" + name))
        current = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        require(recorded == current, f"{name} differs from frozen analysis code; use a compatible version")
    plan, frozen, seeds = (bundle.json(n) for n in ("run_plan.json", "frozen_candidates.json", "seeds.json"))
    equivalent(seeds, config.seed_registry(), "seed registry")
    equivalent(manifest["seeds"], seeds, "manifest seeds")
    equivalent(plan["seeds"], seeds, "plan seeds")
    equivalent(plan["config"], config.to_dict(), "plan config")
    equivalent(plan["resolved_cases"], manifest["resolved_cases"], "resolved case plans")
    resolved = dict(config.resolved_cases())
    equivalent(manifest["resolved_cases"], {name: cfg.to_dict() for name, cfg in resolved.items()}, "resolved config")
    require(frozen.get("evaluation_draws_generated") is False, "design freeze does not precede evaluation")
    plan_hash = hashlib.sha256(bundle.read("run_plan.json")).hexdigest()
    frozen_hash = hashlib.sha256(bundle.read("frozen_candidates.json")).hexdigest()
    require(plan_hash == manifest["run_plan_sha256"] == frozen["run_plan_sha256"], "plan binding differs")
    require(frozen_hash == manifest["frozen_candidates_sha256"], "frozen design binding differs")
    summary, trials, convergence = (bundle.json(n) for n in ("summary.json", "trials.json", "convergence.json"))
    require(summary["status"] == manifest["status"], "run status differs")
    require(summary["frozen_candidates_sha256"] == frozen_hash, "summary freeze binding differs")
    equivalent(convergence["summary"], summary["convergence"], "convergence summary")
    candidates = [strict_json(line) for line in bundle.read("candidates.jsonl").splitlines() if line.strip()]
    for name, rows in (("trials.csv", trials), ("paired_differences.csv", summary["comparisons"]),
                       ("convergence.csv", convergence["rows"]), ("candidates.csv", candidates)):
        verify_csv(bundle.read(name), rows, name)
    arrays = bundle.arrays("arrays.npz")
    embedded = json.loads(str(arrays["provenance_json"]))
    for name in ("config", "seeds", "source", "run_plan_sha256", "frozen_candidates_sha256"):
        equivalent(embedded[name], manifest[name], "NPZ provenance " + name)
    for case, settings in resolved.items():
        s = settings.model["scattering"]
        require(np.array_equal(arrays[case + "_energy_mev"], np.linspace(s["energy_min_mev"], s["energy_max_mev"], s["energy_points"])),
                case + " energy grid differs from configuration")
        shapes = arrays[case + "_retained_phi_per_sqrt_nm"]
        eigenvalues = arrays[case + "_eigenvalues_mev2_nm"][:shapes.shape[1]]
        for partition in ("training", "validation", "heldout"):
            z = np.stack([np.random.Generator(np.random.PCG64(seed)).standard_normal(shapes.shape[1])
                          for seed in seeds["draw_seeds"][partition]])
            eta = z * np.sqrt(eigenvalues)
            for suffix, expected in (("_z", z), ("_eta_mev_sqrt_nm", eta), ("_potential_mev", eta @ shapes.T)):
                require(np.allclose(arrays[case + "_" + partition + suffix], expected, rtol=REPLAY_RTOL, atol=REPLAY_ATOL),
                        case + " disorder draw disagrees with its seeds/mode convention")
    delay = DelaySearch(**config.delay)
    runs = summary["runs"]
    require(len({r["run_id"] for r in runs}) == len(runs), "duplicate run identifier")
    frozen_by_id = {r["run_id"]: r for r in frozen["candidates"]}
    require(len(frozen_by_id) == len(frozen["candidates"]) == len(runs), "frozen design count differs")
    require({r["run_id"] for r in trials} <= set(frozen_by_id), "trial references an unfrozen design")
    checked_metrics = 0
    for run in runs:
        rid, case = run["run_id"], run["case"]
        selected = run["reported_candidate"]
        binding = frozen_by_id[rid]
        equivalent(binding["u_mev"], None if selected is None else selected["u_mev"], rid + " frozen vector")
        require(binding["status"] == run["status"], rid + " frozen status differs")
        rows = [r for r in trials if r["run_id"] == rid]
        if selected is None:
            require(not rows, rid + " trials exist without a frozen candidate")
            continue
        require(binding["feasible"] == selected["feasible"], rid + " frozen feasibility differs")
        prefix = rid + "_evaluation_"
        require(np.array_equal(arrays[prefix + "u_mev"], selected["u_mev"]), rid + " evaluated vector differs")
        potential = arrays[case + "_background_mev"] + arrays[case + "_gate_shapes"] @ np.asarray(selected["u_mev"])
        require(np.allclose(potential, arrays[prefix + "potential_mev"], rtol=REPLAY_RTOL, atol=REPLAY_ATOL), rid + " gate potential differs")
        energy = arrays[case + "_energy_mev"]
        require(np.array_equal(quadrature_weights(energy), arrays[case + "_energy_weights_mev"]), "energy weights differ")
        for partition in ("clean", "training", "validation", "heldout"):
            expected_seeds = [None] if partition == "clean" else seeds["draw_seeds"][partition]
            part = sorted((r for r in rows if r["partition"] == partition), key=lambda r: r["trial_index"])
            require([r["trial_index"] for r in part] == list(range(len(expected_seeds))), rid + " missing/duplicate trials")
            require([r["seed"] for r in part] == expected_seeds, rid + " wrong partition seeds")
            equivalent(run["descriptive"][partition], descriptive_statistics(part), rid + " descriptive " + partition)
            t, r, valid, conservation = (arrays[prefix + partition + suffix] for suffix in ("_t", "_r", "_valid", "_conservation_error"))
            require(t.shape == r.shape == conservation.shape == (len(part), len(energy))
                    and valid.shape == (len(part),), rid + " spectral array shape differs")
            for index, row in enumerate(part):
                require(row["case"] == case and row["method"] == run["method"]
                        and row["minimum_clean_transmission"] == run["minimum_clean_transmission"]
                        and row["clean_feasible"] == selected["feasible"], rid + " trial identity differs")
                require(bool(valid[index]) == (row["status"] == "ok"), rid + " validity differs")
                if not valid[index]:
                    require(row.get("raw_fidelity") is None and row.get("p_transmitted") is None,
                            rid + " failed trial has manufactured metrics")
                    continue
                metrics = analyze_packet(energy, arrays[case + "_incoming_A"], t[index],
                                         arrays[case + "_target_t"], delay=delay).summary()
                for key, value in metrics.items():
                    if key == "estimated_delay_ps" and value is not None:
                        require(abs(row[key] - value) <= max(1e-12, delay.xatol_ps), "delay replay differs")
                    else:
                        equivalent(row[key], value, rid + " " + key)
                alpha = resolved[case].objective["transmission_weight"]
                loss = alpha*(1-metrics["p_transmitted"]) + (1-alpha)*(1-(metrics["raw_fidelity"] or 0.))
                equivalent(row["loss"], loss, rid + " loss")
                measured = abs(t[index])**2 + abs(r[index])**2 - 1
                require(np.allclose(measured, conservation[index], rtol=0, atol=REPLAY_ATOL), "conservation array differs")
                equivalent(row["max_conservation_error"], float(np.max(abs(conservation[index]))), rid + " conservation")
                checked_metrics += 1
        require(len(rows) == 1 + sum(len(seeds["draw_seeds"][p]) for p in ("training", "validation", "heldout")),
                rid + " unexpected partition")
    # Reuse the recorded analysis algorithm, never the runner or its solver.
    from qwave.experiment_runner import _paired_comparisons
    replay_arrays: dict[str, Any] = {}
    compared = _paired_comparisons(config, runs, trials, replay_arrays)
    equivalent(summary["comparisons"], compared, "paired statistics")
    for key, value in replay_arrays.items():
        require(np.array_equal(value, arrays[key]), key + " bootstrap replay differs")
    checks = {"all_preflight_passed": all(r["preflight_passed"] for r in runs),
              "all_postflight_passed": all(r["postflight"]["passed"] for r in runs if r["postflight"] is not None),
              "all_optimized_methods_have_feasible_design": all(r["selected"] is not None for r in runs if r["method"] != "A_fixed"),
              "all_evaluation_solves_succeeded": all(r["status"] == "ok" for r in trials),
              "convergence_forward_solves_conserved": convergence["summary"]["all_forward_solves_conserved"]}
    equivalent(summary["checks"], checks, "aggregate checks")
    require(summary["status"] == ("completed" if all(checks.values()) else "completed_with_failed_checks"), "aggregate status differs")
    outcomes = [r["outcome"] for r in compared if r["primary"]]
    outcome = "supports" if outcomes and all(o == "supports" for o in outcomes) else "contradicts" if "contradicts" in outcomes else "unresolved"
    require(summary["hypothesis_outcome"] == outcome, "aggregate hypothesis classification differs")
    costs = numeric_csv(bundle.read("costs.csv"))
    verification = {"status": "passed", "scope": "frozen-run integrity and analysis replay; no forward physics solves",
                    "source_manifest_sha256": bundle.fingerprint, "source_run_status": bundle.status,
                    "source_hypothesis_outcome": summary["hypothesis_outcome"],
                    "inventoried_files": len(bundle.files), "trial_rows": len(trials),
                    "packet_metrics_recomputed": checked_metrics, "paired_comparisons_recomputed": len(compared),
                    "bootstrap_arrays_recomputed": len(replay_arrays), "candidate_rows_preserved": len(candidates),
                    "replay_atol": REPLAY_ATOL, "replay_rtol": REPLAY_RTOL,
                    "replay_tolerance_meaning": "roundoff/reduction allowance, not model or continuum accuracy",
                    "limits": ["hashes do not prove authorship or prospective registration",
                               "timings and numerical convergence solves are preserved, not rerun",
                               "replayed metrics use the recorded analysis implementation, not an independent physics method",
                               "convergence diagnostics cover the declared fixed first-case device, not every optimized design"]}
    return AuditedRun(bundle, config, summary, trials, convergence, costs,
                      bundle.json("figure_descriptions.json"), arrays, verification)


def audit_run(path: Path) -> AuditedRun:
    """Public audit boundary: malformed saved structures are invalid input."""
    try:
        return _audit_run(path)
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError(f"paper audit: malformed or unsupported artifact structure: {error}") from error


def verify_figures(run: AuditedRun) -> None:
    """Replay all plots from audited tables; require exact pixels and SVG geometry.

    Original vector/raster files are copied verbatim later. PDF page streams and
    all non-timestamp bytes must match, as well as SVG geometry and PNG pixels.
"""
    from matplotlib.image import imread
    from qwave.experiment_plotting import save_experiment_figures

    require(bool(run.descriptions), "run has no recorded figures")
    figures = []
    with tempfile.TemporaryDirectory(prefix="qwave-paper-replay-") as temp:
        folder = Path(temp)
        save_experiment_figures(folder, run.config, run.summary, run.trials, run.convergence["rows"], run.costs)
        equivalent(json.loads((folder / "figure_descriptions.json").read_text()), run.descriptions, "figure descriptions")
        expected_names = {f"{name}.{ext}" for name, description in run.descriptions.items() for ext in description["formats"]}
        actual_names = {name for name in run.bundle.files if Path(name).suffix in {".png", ".pdf", ".svg"}}
        require(expected_names == actual_names, "missing or unexplained figure files")
        for name in sorted(run.descriptions):
            original_png = imread(io.BytesIO(run.bundle.read(name + ".png")), format="png")
            require(np.array_equal(original_png, imread(folder / (name + ".png"))),
                    name + " pixel replay differs; restore the recorded plotting environment")
            require(canonical_svg(run.bundle.read(name + ".svg")) == canonical_svg((folder / (name + ".svg")).read_bytes()),
                    name + " SVG geometry replay differs")
            pdf = run.bundle.read(name + ".pdf")
            require(pdf.startswith(b"%PDF-") and b"%%EOF" in pdf[-100:], name + " invalid PDF container")
            require(canonical_pdf(pdf) == canonical_pdf((folder / (name + ".pdf")).read_bytes()),
                    name + " PDF replay differs")
            figures.append({"name": name, "png": "exact pixel replay", "svg": "exact geometry after timestamp/ID normalization",
                            "pdf": "exact bytes/page streams after creation-timestamp normalization"})
    run.verification["figures"] = figures
