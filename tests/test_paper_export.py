"""Real frozen-run export, tamper rejection, statistical replay and paper honesty."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np
import pytest

from qwave.cli import main
from qwave.experiment_runner import run_experiment
from qwave.experiment_config import ExperimentConfig
from qwave.experiment_support import write_table
from qwave.paper_audit import audit_run, canonical_pdf, canonical_svg, verify_figures
from qwave.paper_export import ASSET_ROOT, export_paper, latex_escape
from qwave.provenance import sha256_file
from test_experiment_suite import suite_config


@pytest.fixture(scope="module")
def frozen_paper_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Use real small numerical experiments, with test-only independent seeds."""
    folder = tmp_path_factory.mktemp("paper-run") / "frozen"
    config = suite_config()
    run_experiment(config, folder)
    return folder


@pytest.fixture(scope="module")
def exported_paper(frozen_paper_run: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    import qwave.scattering as scattering
    import qwave.optimization as optimization

    def forbidden(*args, **kwargs):
        raise AssertionError("paper export must not solve or optimize a device")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(scattering, "solve_scattering", forbidden)
        patch.setattr(optimization, "prepare_problem", forbidden)
        patch.setattr(optimization, "run_multistart", forbidden)
        return export_paper(frozen_paper_run, tmp_path_factory.mktemp("paper-export") / "package")


def copied_run(source: Path, destination: Path) -> Path:
    return Path(shutil.copytree(source, destination / "copy"))


def rehash(folder: Path, filename: str) -> None:
    """Simulate consistent rehashing to test semantic checks beyond byte integrity."""
    path = folder / filename
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["outputs"][filename] = {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
    (folder / "manifest.json").write_text(json.dumps(manifest))


def test_real_export_preserves_every_original_and_all_analysis(frozen_paper_run: Path, exported_paper: Path) -> None:
    original = json.loads((frozen_paper_run / "manifest.json").read_text())
    for name in ["manifest.json", *original["outputs"]]:
        assert (exported_paper / "source_run" / name).read_bytes() == (frozen_paper_run / name).read_bytes()
    verification = json.loads((exported_paper / "verification.json").read_text())
    summary = json.loads((frozen_paper_run / "summary.json").read_text())
    assert verification["source_hypothesis_outcome"] == summary["hypothesis_outcome"]
    assert verification["packet_metrics_recomputed"] == verification["trial_rows"]
    assert verification["paired_comparisons_recomputed"] == 42
    assert len(verification["figures"]) == 4
    assert all("page streams" in row["pdf"] for row in verification["figures"])
    manifest = json.loads((exported_paper / "export_manifest.json").read_text())
    assert manifest["results_section"] == "unfilled"
    assert manifest["source_manifest_sha256"] == sha256_file(frozen_paper_run / "manifest.json")
    assert (exported_paper / "tables/paired_statistics.json").read_text()
    assert json.loads((exported_paper / "tables/paired_statistics.json").read_text()) == summary["comparisons"]
    assert json.loads((exported_paper / "tables/constraints_and_search_status.json").read_text())[0]["status"] == summary["runs"][0]["status"]
    assert not any("__pycache__" in name for name in manifest["outputs"])


def test_standalone_verifier_is_offline_and_detects_tampering(exported_paper: Path, tmp_path: Path) -> None:
    copied = copied_run(exported_paper, tmp_path)
    command = [sys.executable, "-I", str(copied / "verify_package.py")]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "Verified" in result.stdout
    (copied / "captions.md").write_text("altered captions")
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0 and "integrity mismatch" in result.stderr


def test_output_is_new_disjoint_and_symlink_free(frozen_paper_run: Path, exported_paper: Path, tmp_path: Path) -> None:
    with pytest.raises(FileExistsError):
        export_paper(frozen_paper_run, exported_paper)
    with pytest.raises(ValueError, match="disjoint"):
        export_paper(frozen_paper_run, frozen_paper_run / "paper")
    link = tmp_path / "link"
    link.symlink_to(frozen_paper_run, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        audit_run(link)


def test_uninventoried_files_never_enter_exports(frozen_paper_run: Path, exported_paper: Path) -> None:
    manifest = json.loads((exported_paper / "export_manifest.json").read_text())
    original = json.loads((frozen_paper_run / "manifest.json").read_text())
    copied = {name.removeprefix("source_run/") for name in manifest["outputs"] if name.startswith("source_run/")}
    assert copied == {"manifest.json", *original["outputs"]}


def test_hash_tamper_fails_before_output_creation(frozen_paper_run: Path, tmp_path: Path) -> None:
    run = copied_run(frozen_paper_run, tmp_path)
    (run / "trials.json").write_text("[]")
    output = tmp_path / "rejected"
    assert main(["paper-export", "--run", str(run), "--output", str(output)]) == 2
    assert not output.exists()


def test_rehashed_wrong_metric_is_rejected(frozen_paper_run: Path, tmp_path: Path) -> None:
    run = copied_run(frozen_paper_run, tmp_path)
    rows = json.loads((run / "trials.json").read_text())
    rows[0]["p_transmitted"] *= .8
    (run / "trials.json").write_text(json.dumps(rows))
    write_table(run / "trials.csv", rows)
    for name in ("trials.json", "trials.csv"):
        rehash(run, name)
    with pytest.raises(ValueError, match="descriptive|p_transmitted"):
        audit_run(run)


def test_wrong_bootstrap_array_is_rejected_even_with_new_hash(frozen_paper_run: Path, tmp_path: Path) -> None:
    run = copied_run(frozen_paper_run, tmp_path)
    with np.load(run / "arrays.npz", allow_pickle=False) as saved:
        arrays = {name: saved[name] for name in saved.files}
    arrays["paired_0_bootstrap_mean_difference"] = arrays["paired_0_bootstrap_mean_difference"] + .1
    np.savez_compressed(run / "arrays.npz", **arrays)
    rehash(run, "arrays.npz")
    with pytest.raises(ValueError, match="bootstrap replay"):
        audit_run(run)


def test_wrong_seed_partition_is_rejected(frozen_paper_run: Path, tmp_path: Path) -> None:
    run = copied_run(frozen_paper_run, tmp_path)
    seeds = json.loads((run / "seeds.json").read_text())
    seeds["draw_seeds"]["heldout"][0] = seeds["draw_seeds"]["training"][0]
    (run / "seeds.json").write_text(json.dumps(seeds))
    rehash(run, "seeds.json")
    with pytest.raises(ValueError, match="seed registry"):
        audit_run(run)


def test_pdf_substitution_rejected_even_if_manifest_rehashed(frozen_paper_run: Path, tmp_path: Path) -> None:
    run = copied_run(frozen_paper_run, tmp_path)
    (run / "paired_effects.pdf").write_bytes((run / "computation_costs.pdf").read_bytes())
    rehash(run, "paired_effects.pdf")
    audited = audit_run(run)
    with pytest.raises(ValueError, match="PDF replay differs"):
        verify_figures(audited)


@pytest.mark.parametrize("change", ["incomplete", "unsupported", "traversal", "missing_field"])
def test_invalid_bundle_schema_fails_closed(frozen_paper_run: Path, tmp_path: Path, change: str) -> None:
    run = copied_run(frozen_paper_run, tmp_path)
    manifest = json.loads((run / "manifest.json").read_text())
    if change == "incomplete":
        manifest["status"] = "failed"
    elif change == "unsupported":
        manifest["manifest_version"] = 1
    elif change == "missing_field":
        del manifest["source"]
    else:
        manifest["outputs"]["../outside.json"] = {"sha256": "0"*64, "size_bytes": 0}
    (run / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        audit_run(run)


def test_bibliography_and_matrix_are_linked_and_review_limits_explicit() -> None:
    registry = json.loads((ASSET_ROOT / "literature_sources.json").read_text())
    keys = {record["citation_key"] for record in registry["records"]}
    bib = (ASSET_ROOT / "verified_references.bib").read_text()
    assert set(re.findall(r"@article\{([^,]+),", bib)) == keys
    for record in registry["records"]:
        assert record["doi"] in bib
        assert record["primary_urls"] and not record["full_text_review_complete"]
    with (ASSET_ROOT / "literature_matrix.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(keys) == 5
    assert set(rows[0]) == {"citation/DOI", "physical model", "target metric", "disorder assumptions",
                            "optimization method", "gate count/constraints", "key results", "overlap with our proposal", "verified gaps"}
    for row in rows:
        assert row["citation/DOI"].split(";")[0] in keys
    paper = (ASSET_ROOT / "paper.tex").read_text()
    assert {key for group in re.findall(r"\\cite\{([^}]+)\}", paper) for key in group.split(",")} <= keys
    assert "Results deliberately unfilled" in (ASSET_ROOT / "sections/results.tex").read_text()
    assert "DRAFT — NOT REGISTERED" in (ASSET_ROOT / "preregistration_template.md").read_text()


def test_latex_data_are_escaped_and_figure_normalization_is_narrow() -> None:
    value = latex_escape(r"\input{evil}% $x&y_1")
    assert r"\input{evil}" not in value
    assert r"\textbackslash{}input\{evil\}\%" in value
    svg1 = b'<svg xmlns="http://www.w3.org/2000/svg"><defs><path id="abc" d="M 1 2"/></defs><use href="#abc"/></svg>'
    assert canonical_svg(svg1) == canonical_svg(svg1.replace(b"abc", b"def"))
    assert canonical_svg(svg1) != canonical_svg(svg1.replace(b"M 1 2", b"M 2 3"))
    first = b"%PDF-1.4\n/CreationDate (D:20261120)\nPAGE A\n%%EOF"
    assert canonical_pdf(first) == canonical_pdf(first.replace(b"20261120", b"20261121"))
    assert canonical_pdf(first) != canonical_pdf(first.replace(b"PAGE A", b"PAGE B"))


def test_completed_infeasible_study_is_preserved_without_manufactured_comparisons(tmp_path: Path) -> None:
    config = suite_config().to_dict()
    opt = config["optimization"]
    opt["constraints"]["minimum_clean_transmission_values"] = [1.]
    opt["constraints"]["minimum_clean_fidelity"] = 1.
    for gate in opt["model"]["gates"]["profiles"]:
        gate["bounds_mev"] = [4., 20.]
    original = tmp_path / "infeasible"
    run_experiment(ExperimentConfig.from_mapping(config), original)
    summary = json.loads((original / "summary.json").read_text())
    assert summary["status"] == "completed_with_failed_checks"
    assert any(r["reported_candidate"] is None for r in summary["runs"])
    exported = export_paper(original, tmp_path / "support")
    exported_manifest = json.loads((exported / "export_manifest.json").read_text())
    assert exported_manifest["source_run_status"] == "completed_with_failed_checks"
    comparisons = json.loads((exported / "tables/paired_statistics.json").read_text())
    assert all(row["outcome"] == "unresolved" for row in comparisons if row["primary"])
    statuses = json.loads((exported / "tables/constraints_and_search_status.json").read_text())
    assert any(row["candidate"] is None and row["feasible"] is None for row in statuses)
