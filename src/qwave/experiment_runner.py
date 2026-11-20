"""Prespecified experiment orchestration with a global design-freeze barrier."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
import json
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from qwave.convergence import run_convergence
from qwave.diagnostics import cpu_environment, software_versions
from qwave.disorder_experiments import _base_arrays
from qwave.experiment_config import ExperimentConfig
from qwave.experiment_support import (METRICS, create_run_directory, descriptive_statistics,
    draw_from_seeds, evaluate_design, invocation_git_identity, write_table)
from qwave.experiments import _write_json
from qwave.optimization import (METHODS, CandidateEvaluator, NumericalFailure, gate_step_check,
    initializations, prepare_problem, run_multistart)
from qwave.optimization_experiments import _archive_evaluator, mode_step_check
from qwave.provenance import sha256_file, source_identity
from qwave.statistics import hypothesis_outcome, paired_bootstrap
from qwave.units import physical_constants
from qwave.wavepackets import DelaySearch

COST_FIELDS=("forward_work","forward_energy_solves","response_rhs_sweeps",
             "energy_rhs_solves","energy_factorizations","wall_seconds")


def _paired_comparisons(config: ExperimentConfig, runs: list[dict], trials: list[dict],
                        arrays: dict[str,Any]) -> list[dict]:
    """All method pairs, with the D-versus-baselines loss family fixed before data."""
    family=3*len(config.cases)*len(config.optimization["constraints"]["minimum_clean_transmission_values"])
    comparisons=[]
    for case,_ in config.resolved_cases():
        for floor in config.optimization["constraints"]["minimum_clean_transmission_values"]:
            related=[row for row in runs if row["case"]==case and row["minimum_clean_transmission"]==floor]
            by_method={row["method"]:row for row in related}
            for first,second in combinations(METHODS,2):
                a,b=by_method[first],by_method[second]
                ra=sorted([r for r in trials if r["run_id"]==a["run_id"] and r["partition"]=="heldout"],key=lambda r:r["trial_index"])
                rb=sorted([r for r in trials if r["run_id"]==b["run_id"] and r["partition"]=="heldout"],key=lambda r:r["trial_index"])
                if ra and rb and [r["seed"] for r in ra] != [r["seed"] for r in rb]:
                    raise RuntimeError("paired inference requires the same held-out seeds in the same order")
                for metric in METRICS:
                    primary=second=="D_sensitivity" and metric=="loss"
                    if not ra or not rb:
                        row={"case":case,"minimum_clean_transmission":floor,"first_method":first,"second_method":second,
                             "metric":metric,"primary":primary,"status":"unavailable_design","outcome":"unresolved",
                             "reason":"at least one method produced no feasible design; no replacement was selected",
                             "absolute_difference":None,"ci_low":None,"ci_high":None,"family_ci_low":None,"family_ci_high":None}
                    else:
                        va=np.array([np.nan if r.get(metric) is None else r[metric] for r in ra])
                        vb=np.array([np.nan if r.get(metric) is None else r[metric] for r in rb])
                        stats,boot=paired_bootstrap(va,vb,seed=config.statistics["bootstrap_seed"],
                            resamples=config.statistics["bootstrap_resamples"],
                            confidence=config.statistics["confidence_level"],family_size=family if primary else 1)
                        eligible=all(r["reported_candidate"] is not None and r["reported_candidate"]["feasible"]
                                     and r["preflight_passed"] and (r["postflight"] is None or r["postflight"]["passed"])
                                     and r["evaluation"]["failed_trials"]==0 for r in (a,b))
                        row={"case":case,"minimum_clean_transmission":floor,"first_method":first,"second_method":second,
                             "metric":metric,"primary":primary,**stats,"eligible_for_hypothesis":eligible,
                             "outcome":hypothesis_outcome(stats,practical_difference=config.statistics["practical_loss_difference"],
                                                          eligible=eligible) if primary else "exploratory",
                             "units":"ps" if metric=="estimated_delay_ps" else ("seconds" if metric=="solver_seconds" else "dimensionless"),
                             "interpretation":"loss: negative favors second; P/F: positive favors second; signed delay is not a quality score"}
                        arrays[f"paired_{len(comparisons)}_bootstrap_mean_difference"]=boot
                    comparisons.append(row)
    return comparisons


def _summary_report(output: Path, config: ExperimentConfig, summary: dict) -> None:
    """Explain favorable, unfavorable and unresolved findings under the declared model."""
    stats=config.statistics
    primary=[r for r in summary["comparisons"] if r["primary"]]
    lines=[
        "# Phaseward reproducible experiment report", "",
        f"Preset: **{config.preset}** ({config.resource_profile}). Status: **{summary['status']}**.",
        "", "These are numerical simulations of a coherent, constant-mass 1D finite-difference model with ideal discrete leads. "
        "They are not laboratory observations, a claim of novelty, or a continuum-accuracy certificate.",
        "", f"Prespecified hypothesis: D reduces held-out mean loss by more than {stats['practical_loss_difference']:g} "
        "against each of A, B and C, subject to the common clean feasibility constraints. "
        f"Loss = {config.optimization['objective']['transmission_weight']:g}(1-P) + "
        f"{1-config.optimization['objective']['transmission_weight']:g}(1-F_raw). "
        "An undefined conditional fidelity contributes zero to F in this loss only and remains explicitly undefined in the data.",
        "", f"Familywise target confidence: {100*stats['confidence_level']:g}%; paired basic bootstrap, "
        f"{stats['bootstrap_resamples']} resamples, Bonferroni across the prespecified D-versus-baseline loss comparisons. "
        "Coverage is approximate, especially with few draws. All other intervals are exploratory marginal intervals. "
        "Pairing is by disorder seed; cases share draws and must not be pooled as independent replications.",
        "", "The confidence intervals condition on these frozen designs, training set and initialization choices. "
        "They do not estimate variability across independently repeated optimization campaigns.",
        "", f"Overall hypothesis outcome: **{summary['hypothesis_outcome']}**. "
        "This applies to the specified discrete model, finite energy window, retained-KL disorder distribution, budgets, and target.",
        "", "| Case / P floor | Comparison | Mean loss difference (D − baseline) | Adjusted interval | Outcome |",
        "|---|---|---:|---|---|"]
    for row in primary:
        number=row.get("absolute_difference")
        interval="unavailable" if row.get("family_ci_low") is None else f"[{row['family_ci_low']:.6g}, {row['family_ci_high']:.6g}]"
        lines.append(f"| {row['case']} / {row['minimum_clean_transmission']:g} | D vs {row['first_method']} | "
                     f"{'undefined' if number is None else f'{number:.6g}'} | {interval} | {row['outcome']} |")
    lines += ["", "“Supports” requires the entire adjusted interval below the negative practical margin. "
              "“Contradicts” means the interval excludes the declared minimum benefit (which may include harm). "
              "Intervals spanning that margin, ineligible designs, missing states, degenerate samples, or insufficient bootstrap tail resolution are unresolved. "
              "Zero-crossing indicators, relative percent changes and paired standardized effects are in paired_differences.csv. "
              "Relative effects are undefined at a zero baseline and can be unstable near zero.",
              "", "## Frozen designs and computational costs", "",
              "| Case / floor | Method | Feasible | Search RHS sweeps | Objective evaluations | Clean P | Clean raw F | Held-out mean P | Held-out mean raw F |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    def number(value):
        return "undefined" if value is None else f"{value:.6g}"
    for row in summary["runs"]:
        candidate=row["reported_candidate"]
        clean=row.get("descriptive",{}).get("clean",{})
        held=row.get("descriptive",{}).get("heldout",{})
        mean=lambda data,key:data.get(key,{}).get("mean")
        lines.append(f"| {row['case']} / {row['minimum_clean_transmission']:g} | {row['method']} | "
                     f"{False if candidate is None else candidate['feasible']} | {row['cost']['forward_work']} | "
                     f"{row['evaluated_candidates']} | {number(mean(clean,'p_transmitted'))} | "
                     f"{number(mean(clean,'raw_fidelity'))} | {number(mean(held,'p_transmitted'))} | {number(mean(held,'raw_fidelity'))} |")
    stops=[{"run":r["run_id"],"details":entry} for r in summary["runs"] for entry in r["runs"] if not entry.get("success",False)]
    lines += ["", f"Non-successful or budget-stopped optimizer starts: **{len(stops)}**. "
              "Feasible observed trials are reported separately from optimizer convergence; none is claimed globally optimal. "
              "All stops, residuals, trial objectives, preflight/postflight tests, and phase-specific costs remain in summary.json, candidates.csv and costs.csv.",
              "", "## Numerical convergence, separate from findings", "",
              "convergence.csv and the convergence figures measure spatial, energy-quadrature, KL-truncation, derivative-step and sample-count behavior "
              "on the first case's configured fixed design. The spatial comparison uses a common interpolated physical field; the KL comparison pairs "
              "truncations with the full covariance on a fixed grid without rescaling. The highest resolution is a reference, not exact truth. "
              "The held-out distribution remains the prespecified retained-KL distribution; full-covariance diagnostics do not replace it.",
              "", "The independent free and rectangular-barrier benchmark errors are saved, including continuum phase errors above and below the barrier. "
              "Conservation alone does not prove an accurate scattering solution. More disorder samples cannot remove spatial/energy bias, omitted-mode variance, "
              "finite lead dispersion, or physical-model approximation. Convergence at all optimized devices and independent optimization replications remain future work.",
              "", "## Reproducibility and figure descriptions", "",
              "run_plan.json and its hash were written before solves; frozen_candidates.json was written before any validation or held-out draw was generated. "
              "The final test distribution was not changed, and evaluation never reselected or restarted a search. Repeating a preset repeats its seeds. "
              "Any intentional later design change needs a new configuration and a new result directory, and constitutes a new experiment.",
              "", "trials.csv / trials.json retain every clean, training, validation and held-out trial, including raw/aligned fidelity, delay, "
              "boundary flags, throughput, conservation, solve time and failures. arrays.npz retains complex amplitudes, covariance bases, potentials, "
              "gate trials, bootstrap distributions, and diagnostic arrays. manifest.json lists exact seeds, versions, hardware, UTC, source identity and output hashes.",
              "", "Figure descriptions are in figure_descriptions.json. PNG uses 300 dpi; SVG/PDF retain vector text and axes. "
              "Distribution plots show individual observations or empirical CDFs. Confidence bars apply to paired means, not individual predictions.",
              "", f"Delay alignment is restricted to [{config.delay['min_ps']:g}, {config.delay['max_ps']:g}] ps; positive lag means later arrival. "
              "Raw fidelity remains the constraint and primary loss. Boundary estimates are flagged; no unrestricted alignment hides a distorted packet."]
    changes=summary["convergence"]["observed_changes"]
    lines += ["", "## Measured diagnostic values (configured fixed design)", "",
              "| Spatial nodes | Variant | dx (nm) | max complex-t difference to finest |", "|---:|---|---:|---:|"]
    for row in changes["spatial"]:
        lines.append(f"| {row['level']} | {row['variant']} | {row['spacing_nm']:g} | {row['max_complex_t_difference_to_finest']:.6g} |")
    lines += ["", "| Energy nodes | Variant | dE (meV) | P difference to densest |", "|---:|---|---:|---:|"]
    for row in changes["energy"]:
        lines.append(f"| {row['level']} | {row['variant']} | {row['energy_spacing_mev']:g} | {row['p_transmitted_difference_to_finest']:.6g} |")
    lines += ["", "| Retained K | Integrated variance fraction | RMS weighted complex-t error to full covariance |",
              "|---:|---:|---:|"]
    for row in changes["mode_truncation"]:
        lines.append(f"| {row['retained_modes']} | {row['retained_variance_fraction']:.6g} | {row['rms_weighted_complex_t_error']:.6g} |")
    noisy=sum(row["smallest_step_error"]>row["minimum_observed_error"] for row in changes["finite_difference"])
    lines += ["", f"The smallest tested perturbation step exceeded the minimum observed derivative error in {noisy} "
              f"of {len(changes['finite_difference'])} modes. Step data and represented-direction checks are preserved.", "",
              "| Diagnostic draws | Mean loss | Basic-bootstrap interval |", "|---:|---:|---|"]
    for row in changes["sample_counts"]:
        lines.append(f"| {row['level']} | {row['mean_loss']:.6g} | [{row['ci_low']:.6g}, {row['ci_high']:.6g}] |")

    (output/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")


def run_experiment(config: ExperimentConfig, output: str | Path, *, overwrite: bool = False,
                   allow_research: bool = False, plot: bool = True, progress: Any = None) -> Path:
    """Run a complete suite locally, preserving failed outcomes and immutable analysis rules."""
    config=ExperimentConfig.from_mapping(config.to_dict())
    if config.resource_profile=="research" and not allow_research:
        raise ValueError("research profile requires explicit --research; it is never run automatically")
    output=create_run_directory(output,overwrite=overwrite)
    started=perf_counter()
    registry=config.seed_registry()
    source_at_start=source_identity()
    invocation_git=invocation_git_identity()
    plan={"created_utc":datetime.now(timezone.utc).isoformat(),"config":config.to_dict(),
          "resolved_cases":{name:cfg.to_dict() for name,cfg in config.resolved_cases()},
          "seeds":registry,"source":source_at_start,"primary_metric":"held-out mean raw packet loss",
          "hypothesis":"D reduces loss by more than the prespecified practical margin against A, B, C",
          "selection_rule":"best feasible search trial including derivative probes; validation/heldout cannot select",
          "evaluation_distribution":"same configured retained-KL Gaussian law for all methods in each case"}
    _write_json(output/"run_plan.json",plan)
    _write_json(output/"config.json",config.to_dict())
    _write_json(output/"seeds.json",registry)
    plan_hash=sha256_file(output/"run_plan.json")
    arrays: dict[str,Any]={}
    candidates: list[dict[str,Any]]=[]
    trials: list[dict[str,Any]]=[]
    costs: list[dict[str,Any]]=[]
    runs: list[dict[str,Any]]=[]
    states=[]
    summary: dict[str,Any]={"status":"incomplete"}
    def announce(value):
        if progress:progress(value)
    def account(case,method,phase,cost,evaluations=0):
        costs.append({"case":case,"method":method,"phase":phase,"objective_evaluations":evaluations,**cost})
    try:
        for name,cfg in config.resolved_cases():
            announce(f"Preparing {name}; validation and held-out draws remain unused")
            problem=prepare_problem(cfg)
            account(name,"shared","setup",problem.setup_cost)
            starts=initializations(problem)
            z,eta,training=draw_from_seeds(problem,registry["draw_seeds"]["training"])
            data=_base_arrays(problem.device)
            data.update(energy_mev=problem.device.energy_mev,energy_weights_mev=problem.packet.weights_mev,
                        incoming_A=problem.packet.amplitude,target_t=problem.target_t,initializations_mev=starts,
                        importance_density_per_mev=problem.importance_density,
                        training_z=z,training_eta_mev_sqrt_nm=eta,training_potential_mev=training)
            arrays.update({name+"_"+key:value for key,value in data.items()})
            preflight={}
            floors=cfg.constraints["minimum_clean_transmission_values"]
            for method in METHODS[1:]:
                evaluator=CandidateEvaluator(problem,method,floors[0],training,phase="preflight")
                begin=perf_counter()
                base=evaluator.evaluate(starts[0])
                try:check=gate_step_check(evaluator,starts[0])
                except NumericalFailure as error:check={"passed":False,"error":str(error)}
                check["objective_divisor_for_solver"]=max(abs(base["objective"]),1e-6)
                preflight[method]=check
                account(name,method,"preflight_gate",dict(evaluator.cache.counters(),wall_seconds=perf_counter()-begin),len(evaluator.records))
                _archive_evaluator(evaluator,name+"_preflight_"+method,arrays,candidates)
            modal,modal_arrays=mode_step_check(problem,starts[0])
            preflight["modal"]=modal
            account(name,"D_sensitivity","preflight_modal",modal["cost"])
            arrays.update({name+"_modal_"+key:value for key,value in modal_arrays.items()})
            for fi,floor in enumerate(floors):
                for method in METHODS:
                    announce(f"Searching {name}: {method}, P floor {floor:g}")
                    evaluator=CandidateEvaluator(problem,method,floor,training)
                    passed=method=="A_fixed" or preflight[method]["passed"]
                    if method=="D_sensitivity":passed=passed and modal["passed"]
                    result=run_multistart(evaluator,starts,scale=1. if method=="A_fixed" else preflight[method]["objective_divisor_for_solver"],
                                         preflight_passed=passed)
                    result.update(case=name,run_id=f"{name}_floor{fi}_{method}",postflight=None,evaluation=None)
                    result["reported_candidate"]=evaluator.records[0] if method=="A_fixed" else result["selected"]
                    runs.append(result)
                    account(name,method,f"search_floor{fi}",result["cost"],result["evaluated_candidates"])
                    _archive_evaluator(evaluator,result["run_id"],arrays,candidates)
            states.append((name,problem,training,preflight))
        # The global freeze is outside the case loop. No case's test data can
        # influence another case's optimization or numerical settings.
        frozen={"frozen_utc":datetime.now(timezone.utc).isoformat(),"run_plan_sha256":plan_hash,
                "evaluation_draws_generated":False,"candidates":[
            {"run_id":r["run_id"],"u_mev":None if r["reported_candidate"] is None else r["reported_candidate"]["u_mev"],
             "feasible":False if r["reported_candidate"] is None else r["reported_candidate"]["feasible"],
             "status":r["status"]} for r in runs]}
        _write_json(output/"frozen_candidates.json",frozen)
        frozen_hash=sha256_file(output/"frozen_candidates.json")
        for name,problem,training,preflight in states:
            for run in [r for r in runs if r["case"]==name]:
                candidate=run["reported_candidate"]
                if candidate is None or run["method"]=="A_fixed":continue
                evaluator=CandidateEvaluator(problem,run["method"],run["minimum_clean_transmission"],training,phase="postflight")
                begin=perf_counter()
                try:check=gate_step_check(evaluator,np.asarray(candidate["u_mev"]))
                except NumericalFailure as error:check={"passed":False,"error":str(error)}
                run["postflight"]=check
                account(name,run["method"],run["run_id"]+"_postflight",
                        dict(evaluator.cache.counters(),wall_seconds=perf_counter()-begin),len(evaluator.records))
                _archive_evaluator(evaluator,run["run_id"]+"_postflight",arrays,candidates)
        announce("All designs frozen; generating validation and final held-out draws")
        for name,problem,training,preflight in states:
            ensembles={"training":(registry["draw_seeds"]["training"],training)}
            for role in ("validation","heldout"):
                seeds=registry["draw_seeds"][role]
                z,eta,potentials=draw_from_seeds(problem,seeds)
                arrays.update({name+"_"+role+"_z":z,name+"_"+role+"_eta_mev_sqrt_nm":eta,
                               name+"_"+role+"_potential_mev":potentials})
                ensembles[role]=(seeds,potentials)
            for run in [r for r in runs if r["case"]==name]:
                candidate=run["reported_candidate"]
                if candidate is None:continue
                info,rows,data=evaluate_design(problem,np.asarray(candidate["u_mev"]),ensembles,
                    delay=DelaySearch(**config.delay),identity={"run_id":run["run_id"],"case":name,
                    "method":run["method"],"minimum_clean_transmission":run["minimum_clean_transmission"],
                    "clean_feasible":candidate["feasible"]})
                run["evaluation"]=info
                run["descriptive"]={part:descriptive_statistics([r for r in rows if r["partition"]==part])
                                    for part in ("clean","training","validation","heldout")}
                account(name,run["method"],run["run_id"]+"_evaluation",info["cost"])
                trials.extend(rows)
                arrays.update({run["run_id"]+"_evaluation_"+key:value for key,value in data.items()})
        if sha256_file(output/"frozen_candidates.json") != frozen_hash or sha256_file(output/"run_plan.json") != plan_hash:
            raise RuntimeError("immutable experiment plan or frozen designs changed")
        convergence,convergence_rows,convergence_arrays=run_convergence(config,progress=progress)
        account(config.cases[0]["name"],"shared","numerical_convergence",convergence["cost"])
        arrays.update({"convergence_"+key:value for key,value in convergence_arrays.items()})
        write_table(output/"convergence.csv",convergence_rows)
        _write_json(output/"convergence.json",{"summary":convergence,"rows":convergence_rows})
        comparisons=_paired_comparisons(config,runs,trials,arrays)
        checks={"all_preflight_passed":all(r["preflight_passed"] for r in runs),
                "all_postflight_passed":all(r["postflight"]["passed"] for r in runs if r["postflight"] is not None),
                "all_optimized_methods_have_feasible_design":all(r["selected"] is not None for r in runs if r["method"]!="A_fixed"),
                "all_evaluation_solves_succeeded":all(r["status"]=="ok" for r in trials),
                "convergence_forward_solves_conserved":convergence["all_forward_solves_conserved"]}
        outcomes=[r["outcome"] for r in comparisons if r["primary"]]
        outcome="supports" if outcomes and all(o=="supports" for o in outcomes) else ("contradicts" if "contradicts" in outcomes else "unresolved")
        summary={"status":"completed" if all(checks.values()) else "completed_with_failed_checks",
                 "checks":checks,"hypothesis_outcome":outcome,"runs":runs,"comparisons":comparisons,
                 "preflight":{name:preflight for name,_,_,preflight in states},
                 "packet_normalization":{name:p.packet.normalization for name,p,_,_ in states},
                 "kl":{name:p.device.modes.diagnostics for name,p,_,_ in states},
                 "convergence":convergence,"frozen_candidates_sha256":frozen_hash}
        write_table(output/"paired_differences.csv",comparisons)
        _write_json(output/"summary.json",summary)
        _summary_report(output,config,summary)
        if plot:
            from qwave.experiment_plotting import save_experiment_figures
            save_experiment_figures(output,config,summary,trials,convergence_rows,costs)
        if source_identity()["sha256"] != source_at_start["sha256"]:
            raise RuntimeError("package sources changed during this run; this bundle is not a completed experiment")
    except BaseException as error:
        summary={"status":"failed","error":f"{type(error).__name__}: {error}","runs":runs}
        _write_json(output/"failure.json",summary)
        raise
    finally:
        # Even failures retain an explicit status, seed registry and inventory.
        # A manifest's status must be read; presence alone is not success.
        _write_json(output/"trials.json",trials)
        write_table(output/"trials.csv",trials)
        write_table(output/"costs.csv",costs)
        write_table(output/"candidates.csv",candidates)
        with (output/"candidates.jsonl").open("w") as stream:
            for row in candidates:stream.write(json.dumps(row,sort_keys=True,allow_nan=False)+"\n")
        metadata={"manifest_version":2,"project":"Phaseward","stage":"PROMPT 5","status":summary["status"],
            "created_utc":datetime.now(timezone.utc).isoformat(),"run_plan_sha256":plan_hash,
            "config":config.to_dict(),"resolved_cases":plan["resolved_cases"],"seeds":registry,
            "software_versions":software_versions(),"hardware":cpu_environment(),"source":source_at_start,
            "source_at_completion":source_identity(),
            "invocation_git":invocation_git,
            "constants_SI":physical_constants(),"elapsed_seconds_before_manifest":perf_counter()-started,
            "frozen_candidates_sha256":summary.get("frozen_candidates_sha256"),
            "units":{"x":"nm","potential":"meV","energy":"meV","delay":"ps","solver_time":"s","phi":"nm^-1/2",
                     "lambda":"meV^2 nm","eta":"meV sqrt(nm)","P_F_loss_J":"dimensionless; distinct metrics"},
            "conventions":{"modes":"Phi.T W Phi=I; Var(eta)=lambda; lambda once in J",
                "phase":"fixed endpoint planes, unit flux, complex t preserved; free t=exp(ikL)",
                "packet":"energy-normalized Gaussian on the finite propagating window, positive trapezoid",
                "delay":config.delay,"test_distribution":"prespecified retained-KL Gaussian for all methods, no evaluation tuning",
                "cost":"RHS-equivalent energy sweeps; response=3; setup, audits, search and evaluation separately charged",
                "statistics":"paired basic bootstrap; Bonferroni only for the prespecified primary loss family; conditional on fixed designs",
                "convergence":"separate fixed-device diagnostics with independent seeds; not optimizer selection and not continuum proof"},
            "outputs":{}}
        np.savez_compressed(output/"arrays.npz",**arrays,
                            provenance_json=np.asarray(json.dumps(metadata,sort_keys=True,allow_nan=False)))
        metadata["outputs"]={p.name:{"sha256":sha256_file(p),"size_bytes":p.stat().st_size}
                             for p in sorted(output.iterdir()) if p.is_file() and p.name!="manifest.json"}
        _write_json(output/"manifest.json",metadata)
    return output

