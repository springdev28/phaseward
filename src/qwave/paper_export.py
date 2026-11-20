"""Local manuscript-support export from one explicitly selected frozen run."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable

from qwave.diagnostics import cpu_environment, software_versions
from qwave.experiment_support import METRICS, write_table
from qwave.gui_results import json_bytes, safe_path
from qwave.paper_audit import audit_run, require, verify_figures, verify_csv
from qwave.provenance import sha256_file, source_identity

ASSET_ROOT = Path(__file__).with_name("paper_assets")


def latex_escape(value: Any) -> str:
    """Render data as text, never as executable LaTeX; allow long identifiers to wrap."""
    text = str(value).translate(str.maketrans({"−": "-", "–": "-", "—": "-", "²": "^2",
                                              "λ": "lambda", "η": "eta", "φ": "phi", "≈": "approximately"}))
    escapes = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
               "_": r"\_\allowbreak{}", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    escaped = "".join(escapes.get(c, c + r"\allowbreak{}" if c in ".,/" else c) for c in text)
    return re.sub(r"[0-9a-f]{32,}", lambda match: r"\allowbreak{}".join(
        match[0][i:i+8] for i in range(0, len(match[0]), 8)), escaped)


def flatten(value: Any, prefix: str = "") -> list[dict]:
    """Losslessly flatten settings; lists retain JSON and no unknown unit is inferred."""
    if isinstance(value, dict):
        return [row for key, child in value.items() for row in flatten(child, prefix + "." + key if prefix else key)]
    encoded = json.dumps(value, sort_keys=True, allow_nan=False)
    return [{"parameter": prefix, "value_json": encoded,
             "units": "as explicitly named in parameter/config; counts and flags are dimensionless"}]


def _json(path: Path, value: Any) -> None:
    path.write_bytes(json_bytes(value))


def _table(folder: Path, name: str, rows: list[dict]) -> None:
    """Publish paired JSON/CSV and immediately check every generated CSV cell."""
    _json(folder / (name + ".json"), rows)
    write_table(folder / (name + ".csv"), rows)
    verify_csv((folder / (name + ".csv")).read_bytes(), rows, "export " + name)


def _tex_table(path: Path, headings: list[str], rows: list[list[Any]], widths: list[float]) -> None:
    columns = "".join(r">{\raggedright\arraybackslash}p{" + str(w) + r"\linewidth}" for w in widths)
    lines = [r"\begin{longtable}{" + columns + "}", r"\toprule",
             " & ".join(latex_escape(h) for h in headings) + r" \\ \midrule\endhead"]
    lines += [" & ".join(latex_escape("undefined" if value is None else value) for value in row) + r" \\" for row in rows]
    lines += [r"\bottomrule\end{longtable}"]
    path.write_text("\n".join(lines) + "\n")


def _display_number(value: float | None) -> str:
    """Eight significant display digits; JSON/CSV retain every stored digit."""
    return "undefined" if value is None else format(value, ".8g")


def export_paper(run_path: Path, output: Path, *, progress: Callable[[str], None] | None = None) -> Path:
    """Audit and copy inventoried outputs only; never overwrite or mutate the source.

Success means a data-support package, not a successful hypothesis or publication.
On an export I/O failure, no export_manifest.json is written: the directory is
incomplete and must not be presented as verified. Choose a new destination.
"""
    output = Path(output).absolute()
    source = Path(run_path).absolute()
    require(not any(p.is_symlink() for p in (output, *output.parents)), "output path uses a symlink")
    require(not (output.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(output.resolve())),
            "source and output must be disjoint directories")
    if output.exists():
        raise FileExistsError(f"{output} exists; choose a new paper-export directory")
    required_assets = ("paper.tex", "support.tex", "sections/results.tex", "verified_references.bib",
                       "literature_matrix.csv", "literature_matrix_template.csv", "literature_sources.json",
                       "preregistration_template.md", "research_checklist.md", "verify_package.py")
    require(all((ASSET_ROOT / name).is_file() for name in required_assets), "installation is missing paper assets")
    exporter_source = source_identity()
    notify = progress or (lambda _: None)
    notify("Checking frozen configuration, seeds, amplitudes, tables and paired statistics...")
    run = audit_run(source)
    notify("Replaying all recorded figures from saved data; no scattering or optimization solves...")
    verify_figures(run)
    # Read all files again before creating any output; later reads check concurrent changes too.
    run.bundle.read("manifest.json")
    for name in run.bundle.files:
        run.bundle.read(name)
    output.mkdir(parents=True, exist_ok=False)
    for directory in ("source_run", "tables", "manuscript", "literature", "protocol"):
        (output / directory).mkdir()
    for name in ["manifest.json", *run.bundle.files]:
        destination = safe_path(output / "source_run", name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(run.bundle.read(name))
    asset_inventory = {}
    for asset in sorted(ASSET_ROOT.rglob("*")):
        if not asset.is_file() or asset.suffix not in {".md", ".tex", ".bib", ".json", ".csv", ".py"}:
            continue
        name = asset.relative_to(ASSET_ROOT).as_posix()
        if name.startswith("sections/") or name in {"paper.tex", "support.tex", "verified_references.bib"}:
            relative = "manuscript/" + name
        elif name.startswith("literature_"):
            relative = "literature/" + name
        elif name == "verify_package.py":
            relative = name
        else:
            relative = "protocol/" + name
        destination = safe_path(output, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(asset.read_bytes())
        asset_inventory[relative] = sha256_file(destination)
    tables = output / "tables"
    parameters, algorithms = [], []
    for case, config in run.config.resolved_cases():
        settings = config.to_dict()
        parameters += [{"case": case, **row} for row in flatten({"model": settings["model"], "packet": settings["packet"], "target_potential": settings["target_potential"]})]
        algorithms += [{"case": case, **row} for row in flatten({k: v for k, v in settings.items() if k not in {"model", "packet", "target_potential"}})]
    algorithms += [{"case": "suite", **row} for row in flatten({k: v for k, v in run.config.to_dict().items() if k != "optimization"})]
    _table(tables, "parameters", parameters)
    _table(tables, "algorithm_settings", algorithms)
    _table(tables, "paired_statistics", run.summary["comparisons"])
    _table(tables, "computation_costs", run.costs)
    _table(tables, "numerical_convergence", run.convergence["rows"])
    descriptive, constraints = [], []
    for row in run.summary["runs"]:
        for partition, values in row.get("descriptive", {}).items():
            for metric in METRICS:
                descriptive.append({"run_id": row["run_id"], "method": row["method"], "case": row["case"],
                                    "partition": partition, "metric": metric, **values[metric],
                                    "failed_trials": values["failed_trials"], "low_transmission_count": values["low_transmission_count"],
                                    "delay_boundary_count": values["delay_boundary_count"]})
        candidate = row["reported_candidate"]
        constraints.append({"run_id": row["run_id"], "method": row["method"], "status": row["status"],
                            "feasible": None if candidate is None else candidate["feasible"],
                            "candidate": candidate, "preflight_passed": row["preflight_passed"], "postflight": row["postflight"],
                            "search_work": row["cost"]["forward_work"], "search_budget": row["budget_forward_work"],
                            "evaluated_candidates": row["evaluated_candidates"], "optimizer_starts": row["runs"]})
    _table(tables, "descriptive_statistics", descriptive)
    _table(tables, "constraints_and_search_status", constraints)
    _tex_table(tables / "parameters.tex", ["Case / parameter", "JSON value (units in parameter name)"],
               [[r["case"] + " / " + r["parameter"], r["value_json"]] for r in parameters], [.44, .48])
    _tex_table(tables / "algorithm_settings.tex", ["Case / setting", "JSON value"],
               [[r["case"] + " / " + r["parameter"], r["value_json"]] for r in algorithms], [.44, .48])
    _tex_table(tables / "primary_comparisons.tex", ["Case / comparison", "Mean loss difference", "Family-adjusted interval", "Outcome"],
               [[r["case"] + ": " + r["second_method"] + " - " + r["first_method"],
                 _display_number(r["absolute_difference"]),
                 "[" + _display_number(r["family_ci_low"]) + ", " + _display_number(r["family_ci_high"]) + "]", r["outcome"]]
                for r in run.summary["comparisons"] if r["primary"]], [.28, .16, .30, .15])
    index = []
    captions = ["# Caption drafts from the selected frozen run", "", "These are data descriptions, not a Results narrative. Every original figure is included.", ""]
    caption_tex = []
    for number, (name, description) in enumerate(sorted(run.descriptions.items()), 1):
        caption = description["description"] + " Source: the selected frozen run; see source_run/config.json and source_run/summary.json."
        entry = {"figure_id": f"F{number}", "stem": name, "caption_draft": caption,
                 "source_manifest_sha256": run.bundle.fingerprint,
                 "files": [{"path": "source_run/" + name + "." + ext,
                            **run.bundle.manifest["outputs"][name + "." + ext]} for ext in description["formats"]]}
        index.append(entry)
        captions += [f"## F{number}: {name}", "", caption, ""]
        caption_tex += [r"\begin{figure}[p]\centering", r"\includegraphics[width=\linewidth]{../source_run/" + name + ".pdf}",
                        r"\caption{" + latex_escape(caption) + "}", r"\end{figure}"]
    _table(output, "figure_index", index)
    (output / "captions.md").write_text("\n".join(captions))
    (output / "manuscript" / "caption_figures.tex").write_text("\n".join(caption_tex) + "\n")
    manifest = run.bundle.manifest
    statements = [
        "This package describes numerical simulations, not hardware observations. The manuscript Results section is deliberately unfilled.",
        f"Source run: {source.name}. Frozen manifest SHA-256: {run.bundle.fingerprint}. Run UTC timestamp: {manifest['created_utc']}.",
        f"Recorded run status: {run.bundle.status}. Recorded hypothesis classification: {run.summary['hypothesis_outcome']}. Failed, infeasible, missing and unfavorable records remain included.",
        "The source_run directory contains only the original manifest and its inventoried outputs, byte for byte. Extra files beside the selected run are excluded. SHA-256 detects change relative to the recorded inventory; it does not prove authorship or external pre-registration.",
        "The full configuration, resolved cases, exact seed lists, software versions, hardware, source hashes, approximation conventions and units remain in source_run/manifest.json. Configuration and source identity at export are recorded separately in export_manifest.json.",
        "The study uses coherent constant-mass one-dimensional finite-difference scattering with ideal semi-infinite discrete leads. The finite lead band, finite energy window, spatial grid, truncated covariance representation and bounded delay search are model/numerical approximations. Gate parameters are energies in meV, not electrode voltages.",
        "Transmission P and normalized conditional fidelity F are distinct. Undefined fidelities remain null; low-throughput and delay-boundary flags remain visible. The primary loss uses raw fidelity. Covariance shapes obey Phi.T W Phi = I, Var(eta_k) = lambda_k; the sensitivity objective is a surrogate, not a failure probability.",
        "Designs were locally frozen before evaluation according to the recorded plan. These files are not evidence of a publicly time-stamped prospective registration. Previously inspected draws cannot become a new confirmatory test set. No configuration, design or test distribution was changed by this export.",
        "Paired basic-bootstrap intervals and raw resamples were replayed using the recorded seed and implementation. Family correction applies only to the declared primary comparisons. Inference conditions on these frozen designs and their training/initialization choices, not independent repetitions of the optimization campaign. Missing counts, relative effects undefined at zero baselines, and zero-crossing flags are retained.",
        "All four-method costs and unsuccessful optimizer starts are retained. Elapsed timings and convergence forward solves are historical recorded observations, not recomputed by the export. Fixed-device convergence does not certify all optimized devices or remove physical-model bias.",
        "PNG pixels, SVG geometry and PDF page streams were replayed exactly from saved tables; only render timestamps and SVG resource IDs were normalized for comparison. All original files retain their original hashes. Packet metrics were recomputed from saved complex amplitudes; no new scattering solves or optimization were run.",
        "To check the shared directory offline, run python3 verify_package.py. For the full metric/figure replay, install a compatible qwave checkout, then run qwave paper-export --run source_run --output ../new-audited-package. The exporter requires the recorded analysis/plotting source hashes and may reject a changed rendering environment instead of silently substituting figures.",
        "Code-release prerequisite: archive the original scientific implementation and dependency environment alongside a future publication. This support bundle records their identities but is not itself a complete historical source release. The current repository supplies the compatible analysis implementation. No DOI, repository deposit, author identity or code availability claim is invented.",
        "Literature entries are an initial primary-source metadata/abstract screening, not an exhaustive systematic review. Full-text-only details and novelty gaps are explicitly unresolved. No external credentials, paid tools or network are needed to use the exported package."
    ]
    (output / "reproducibility.md").write_text("# Reproducibility statement draft\n\n" + "\n\n".join(statements) + "\n")
    (output / "manuscript" / "reproducibility.tex").write_text("\n\n".join(latex_escape(s) for s in statements) + "\n")
    _json(output / "verification.json", run.verification)
    (output / "README.md").write_text(
        "# Phaseward manuscript-support package\n\n"
        "This is an audited data package and an unfilled paper scaffold, not a finished paper or discovery claim.\n\n"
        "- `source_run/`: complete inventoried frozen evidence, including unfavorable outcomes and raw trials.\n"
        "- `figure_index.csv/json`, `captions.md`: every source figure, its hash and descriptive caption.\n"
        "- `tables/`: exact parameters, algorithms, constraints, costs, convergence and paired/descriptive statistics.\n"
        "- `literature/`: blank matrix, screened matrix and primary-source verification records.\n"
        "- `protocol/`: preregistration template, conditional contributions and research-error checklist.\n"
        "- `manuscript/paper.tex`: intentionally unfilled Results. `support.tex` is a separate measured-data appendix.\n"
        "- `verification.json`, `reproducibility.md`: checks and their limits.\n\n"
        "Verify with `python3 verify_package.py`. Compile locally (optional free TeX):\n\n"
        "```sh\ncd manuscript\npdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error paper.tex\nbibtex paper\n"
        "pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error paper.tex\n"
        "pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error support.tex\n```\n\n"
        "Exit 0 from paper-export certifies the stated export checks, not favorable research results. "
        "A missing export_manifest.json means an incomplete export. Original manifests are unsigned; "
        "internal consistency is not an external provenance attestation.\n")
    # Final read detects changes while replay/copy ran. Copy hashes must equal original.
    run.bundle.read("manifest.json")
    for name in run.bundle.files:
        data = run.bundle.read(name)
        require((output / "source_run" / name).read_bytes() == data, name + " changed during copy")
    outputs = {p.relative_to(output).as_posix(): {"sha256": sha256_file(p), "size_bytes": p.stat().st_size}
               for p in sorted(output.rglob("*")) if p.is_file()}
    require(source_identity()["sha256"] == exporter_source["sha256"], "exporter source changed during export")
    _json(output / "export_manifest.json", {
        "schema_version": 1, "status": "verified_support_package", "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_run_name": source.name, "source_manifest_sha256": run.bundle.fingerprint,
        "source_run_status": run.bundle.status, "source_hypothesis_outcome": run.summary["hypothesis_outcome"],
        "exporter": {"software_versions": software_versions(), "hardware": cpu_environment(), "source": exporter_source},
        "assets_sha256": asset_inventory, "outputs": outputs,
        "limitations": run.verification["limits"], "results_section": "unfilled"})
    notify(f"Verified {len(run.verification['figures'])} figure groups, {len(run.trials)} trial rows, and {len(run.summary['comparisons'])} paired comparisons.")
    return output
