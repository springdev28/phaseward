"""Seed isolation, paired uncertainty, reproducible presets and real suite execution."""

from copy import deepcopy
import inspect
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import bootstrap

from qwave.cli import main
from qwave.config import ConfigError, load_config
from qwave.experiment_config import (ExperimentConfig, PRESETS, child_seeds, preset_config, reject_seed_overlap)
from qwave.experiment_runner import run_experiment
from qwave.experiment_support import create_run_directory, draw_from_seeds
from qwave.optimization import prepare_problem
from qwave.provenance import sha256_file
from qwave.statistics import hypothesis_outcome, paired_bootstrap


def suite_config() -> ExperimentConfig:
    """Independent test seeds and small real numerical device, never final-preset samples."""
    config=preset_config("smoke").to_dict()
    opt=config["optimization"]
    opt["model"]["gates"]["profiles"]=opt["model"]["gates"]["profiles"][1:3]
    for profile,u in zip(opt["model"]["gates"]["profiles"],[4.,6.]):
        profile["amplitude_mev"]=u
    opt["optimizer"].update(starts=1,forward_work_budget=30,maxiter=4,initialization_seed=2510001)
    opt["ensembles"].update(training_samples=2,validation_samples=2,heldout_samples=4,
                            training_seed=2510002,validation_seed=2510003,heldout_seed=2510004)
    config["convergence"].update(seed=2510005,spatial_grid_points=[41,81,161],energy_points=[41,57,81],
                                retained_modes=[1,2,3],mode_steps_mev_sqrt_nm=[.1,.001,1e-7],sample_counts=[2,3,4])
    config["statistics"].update(bootstrap_seed=2510006,bootstrap_resamples=1200)
    return ExperimentConfig.from_mapping(config)


def test_paired_bootstrap_matches_independent_scipy_basic_implementation() -> None:
    """Check pairing, sign and interval calculation against SciPy, not duplicated formulas."""
    first=np.array([1.,3.,9.,2.,5.,4.,8.,6.])
    second=first+np.array([.2,-.1,.4,.8,-.5,.1,.2,.6])
    result,raw=paired_bootstrap(
        first,second,seed=172,resamples=4000,confidence=.95)
    keyword="rng" if "rng" in inspect.signature(bootstrap).parameters else "random_state"
    reference=bootstrap((first,second),lambda a,b,axis:np.mean(b-a,axis=axis),
                        paired=True,method="basic",n_resamples=4000,batch=256,
                        confidence_level=.95,**{keyword:np.random.Generator(np.random.PCG64(172))})
    np.testing.assert_allclose(raw,reference.bootstrap_distribution,atol=1e-15,rtol=0)
    assert result["ci_low"]==pytest.approx(reference.confidence_interval.low,abs=1e-15)
    assert result["ci_high"]==pytest.approx(reference.confidence_interval.high,abs=1e-15)
    assert result["absolute_difference"]==pytest.approx(np.mean(second-first))
    assert result["relative_percent"]==pytest.approx(100*np.mean(second-first)/np.mean(first))
    _,replayed=paired_bootstrap(first,second,seed=172,resamples=4000)
    np.testing.assert_array_equal(raw,replayed)


def test_missing_zero_baseline_and_degenerate_statistics_are_explicit() -> None:
    stats,_=paired_bootstrap([0.,0.,np.nan],[1.,2.,3.],seed=1,resamples=2000)
    assert stats["excluded_pairs"]==1 and stats["paired_samples"]==2
    assert stats["relative_difference"] is None
    assert hypothesis_outcome(stats,practical_difference=.001,eligible=True)=="unresolved"
    constant,_=paired_bootstrap([1.,1.,1.],[.5,.5,.5],seed=2,resamples=4000)
    assert constant["degenerate_empirical_distribution"]
    assert hypothesis_outcome(constant,practical_difference=.01,eligible=True)=="unresolved"
    missing,_=paired_bootstrap([np.nan],[1.],seed=2,resamples=2000)
    assert missing["status"]=="insufficient_paired_values"
    with pytest.raises(ValueError):paired_bootstrap([1,2],[1],seed=1,resamples=1000)
    with pytest.raises(ValueError):paired_bootstrap([np.inf,2],[1,2],seed=1,resamples=1000)


def test_prespecified_hypothesis_sign_practical_margin_and_multiplicity() -> None:
    first=np.full(20,.2)
    better=first+np.linspace(-.06,-.04,20)
    result,_=paired_bootstrap(first,better,seed=3,resamples=4000,family_size=3)
    assert result["family_ci_low"] <= result["ci_low"] < result["ci_high"] <= result["family_ci_high"]
    assert hypothesis_outcome(result,practical_difference=.01,eligible=True)=="supports"
    assert hypothesis_outcome(result,practical_difference=.01,eligible=False)=="unresolved"
    worse,_=paired_bootstrap(first,first+np.linspace(.02,.04,20),seed=3,resamples=4000)
    assert hypothesis_outcome(worse,practical_difference=.01,eligible=True)=="contradicts"
    near,_=paired_bootstrap(first,first+np.linspace(-.1,.1,20),seed=3,resamples=4000)
    assert near["interval_crosses_zero"]
    assert hypothesis_outcome(near,practical_difference=.001,eligible=True)=="unresolved"


@pytest.mark.parametrize("name",PRESETS)
def test_all_presets_load_from_installed_code_and_example_configs(name: str) -> None:
    default=preset_config(name)
    example=Path(__file__).parents[1]/"examples"/("experiment_"+name.replace("-","_")+".json")
    assert load_config(example).to_dict()==default.to_dict()
    assert preset_config(name,research=True).resource_profile=="research"
    assert default.resource_profile=="laptop"
    assert len(default.seed_registry()["draw_seeds"]["heldout"])==default.optimization["ensembles"]["heldout_samples"]


def test_seed_registry_rejects_roots_children_and_duplicate_draws(monkeypatch: pytest.MonkeyPatch) -> None:
    config=suite_config().to_dict()
    config["optimization"]["ensembles"]["heldout_seed"]=config["convergence"]["seed"]
    with pytest.raises(ConfigError,match="seed overlap"):ExperimentConfig.from_mapping(config)
    with pytest.raises(ConfigError,match="seed overlap"):reject_seed_overlap({"training":[1,2],"heldout":[3,2]})
    with pytest.raises(ConfigError,match="seed overlap"):reject_seed_overlap({"heldout":[3,3]})
    import qwave.experiment_config as module
    monkeypatch.setattr(module,"child_seeds",lambda root,count:[42]*count)
    with pytest.raises(ConfigError,match="seed overlap"):suite_config()


def test_draw_seeds_have_prefix_stability_and_exact_kl_scaling() -> None:
    config=suite_config()
    problem=prepare_problem(config.resolved_cases()[0][1])
    registry=config.seed_registry()
    allseeds=[seed for partition in registry["draw_seeds"].values() for seed in partition]
    assert len(allseeds)==len(set(allseeds))
    assert child_seeds(19,3)==child_seeds(19,8)[:3]
    z,eta,field=draw_from_seeds(problem,registry["draw_seeds"]["heldout"])
    np.testing.assert_array_equal(z[0],np.random.Generator(np.random.PCG64(registry["draw_seeds"]["heldout"][0])).standard_normal(3))
    np.testing.assert_allclose(eta,z*np.sqrt(problem.device.modes.retained_eigenvalues),rtol=0,atol=0)
    np.testing.assert_allclose(field,eta@problem.device.embedded_shapes.T,rtol=0,atol=0)


@pytest.mark.parametrize("change",[
    {"cases":[{"name":"bad","overrides":{"optimizer":{"forward_work_budget":800}}}]},
    {"cases":[{"name":"bad","overrides":{"model":{"disorder":{"unknown":1}}}}]},
    {"cases":[{"name":"../escape","overrides":{}}]},
    {"convergence":{"sample_counts":[4,2,8]}},
    {"statistics":{"confidence_level":1}},
])
def test_suite_rejects_ambiguous_or_invalid_designs(change: dict) -> None:
    config=suite_config().to_dict()
    for key,value in change.items():
        if isinstance(value,dict):config[key].update(value)
        else:config[key]=value
    with pytest.raises(ValueError):ExperimentConfig.from_mapping(config)


def test_research_and_overwrite_are_explicit_and_protect_other_files(tmp_path: Path) -> None:
    config=suite_config().to_dict();config["resource_profile"]="research"
    with pytest.raises(ValueError,match="explicit --research"):
        run_experiment(ExperimentConfig.from_mapping(config),tmp_path/"research",plot=False)
    assert not (tmp_path/"research").exists()
    foreign=tmp_path/"unrelated";foreign.mkdir();(foreign/"notes.txt").write_text("keep")
    with pytest.raises(ValueError,match="only replaces"):create_run_directory(foreign,overwrite=True)
    assert (foreign/"notes.txt").read_text()=="keep"
    owned=create_run_directory(tmp_path/"owned",overwrite=False)
    (owned/"old").write_text("old")
    with pytest.raises(FileExistsError):create_run_directory(owned,overwrite=False)
    create_run_directory(owned,overwrite=True)
    assert not (owned/"old").exists()
    link=tmp_path/"link";link.symlink_to(owned,target_is_directory=True)
    with pytest.raises(ValueError,match="symlink"):create_run_directory(link,overwrite=True)


def test_real_cli_exports_distributions_convergence_pairs_hashes_and_raw_trials(tmp_path: Path) -> None:
    config=suite_config()
    config_path=tmp_path/"config.json";config_path.write_text(json.dumps(config.to_dict()))
    output=tmp_path/"suite"
    assert main(["experiment","smoke","--config",str(config_path),"--output",str(output)])==0
    summary=json.loads((output/"summary.json").read_text())
    manifest=json.loads((output/"manifest.json").read_text())
    trials=json.loads((output/"trials.json").read_text())
    assert summary["status"]=="completed"
    assert manifest["config"]==config.to_dict()
    assert manifest["source"]["files_sha256"]
    assert manifest["run_plan_sha256"]==sha256_file(output/"run_plan.json")
    assert manifest["frozen_candidates_sha256"]==sha256_file(output/"frozen_candidates.json")
    for name,data in manifest["outputs"].items():
        assert sha256_file(output/name)==data["sha256"]
    for run in summary["runs"]:
        held=[r for r in trials if r["run_id"]==run["run_id"] and r["partition"]=="heldout"]
        assert [r["seed"] for r in held]==config.seed_registry()["draw_seeds"]["heldout"]
        assert all(r["status"]=="ok" for r in held)
        assert all(r["aligned_fidelity"]>=r["raw_fidelity"]-1e-14 for r in held)
        assert all(config.delay["min_ps"]<=r["estimated_delay_ps"]<=config.delay["max_ps"] for r in held)
        assert run["cost"]["forward_work"]<=30
        assert run["descriptive"]["heldout"]["p_transmitted"]["mean"]==pytest.approx(np.mean([r["p_transmitted"] for r in held]))
    assert len([r for r in summary["comparisons"] if r["primary"]])==3
    conv=json.loads((output/"convergence.json").read_text())
    assert {r["study"] for r in conv["rows"]} >= {"spatial_grid","energy_quadrature","mode_truncation","finite_difference_step","sample_count","analytical_rectangle"}
    spatial=[r for r in conv["rows"] if r["study"]=="analytical_rectangle" and r.get("variant")=="below"]
    assert spatial[-1]["max_complex_t_error"] < spatial[0]["max_complex_t_error"]
    with np.load(output/"arrays.npz",allow_pickle=False) as archive:
        assert np.iscomplexobj(archive["declared_device_floor0_D_sensitivity_evaluation_heldout_t"])
        assert archive["convergence_truncation_reference_t"].shape[0]==4
    figures=json.loads((output/"figure_descriptions.json").read_text())
    assert len(figures)==4
    for name in figures:
        for extension in ("svg","pdf","png"):
            assert (output/(name+"."+extension)).stat().st_size>1000
    before=sha256_file(output/"manifest.json")
    assert main(["experiment","smoke","--config",str(config_path),"--output",str(output)])==2
    assert before==sha256_file(output/"manifest.json")


def test_all_cases_freeze_before_any_evaluation_and_training_is_isolated(tmp_path: Path,monkeypatch: pytest.MonkeyPatch) -> None:
    import qwave.experiment_runner as runner
    config=suite_config().to_dict()
    config["cases"].append({"name":"different_sigma","overrides":{"model":{"disorder":{"sigma_mev":1.5}}}})
    config=ExperimentConfig.from_mapping(config)
    output=tmp_path/"global_freeze"
    seeds=config.seed_registry()["draw_seeds"]
    actual=runner.draw_from_seeds
    calls=[]
    def observed(problem,values):
        calls.append(values)
        if values in (seeds["validation"],seeds["heldout"]):
            frozen=json.loads((output/"frozen_candidates.json").read_text())
            assert len(frozen["candidates"])==8
            assert frozen["evaluation_draws_generated"] is False
            assert all("u_mev" in row for row in frozen["candidates"])
        else:
            assert values==seeds["training"]
            assert not (output/"frozen_candidates.json").exists()
        return actual(problem,values)
    monkeypatch.setattr(runner,"draw_from_seeds",observed)
    run_experiment(config,output,plot=False)
    assert calls==[seeds["training"],seeds["training"],seeds["validation"],seeds["heldout"],seeds["validation"],seeds["heldout"]]


def test_infeasibility_and_interruption_preserve_failure_manifests(tmp_path: Path,monkeypatch: pytest.MonkeyPatch) -> None:
    config=suite_config().to_dict()
    config["optimization"]["optimizer"]["forward_work_budget"]=1
    config["optimization"]["constraints"]["minimum_clean_transmission_values"]=[1.]
    config["optimization"]["constraints"]["minimum_clean_fidelity"]=1.
    output=run_experiment(ExperimentConfig.from_mapping(config),tmp_path/"infeasible",plot=False)
    summary=json.loads((output/"summary.json").read_text())
    assert summary["status"]=="completed_with_failed_checks"
    assert summary["hypothesis_outcome"]=="unresolved"
    assert all(r["outcome"]=="unresolved" for r in summary["comparisons"] if r["primary"])
    import qwave.experiment_runner as runner
    def interrupted(*args,**kwargs):raise RuntimeError("test interruption")
    monkeypatch.setattr(runner,"prepare_problem",interrupted)
    with pytest.raises(RuntimeError,match="test interruption"):
        run_experiment(suite_config(),tmp_path/"failed",plot=False)
    manifest=json.loads((tmp_path/"failed"/"manifest.json").read_text())
    assert manifest["status"]=="failed"
    assert "failure.json" in manifest["outputs"]

