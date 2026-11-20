"""Auditable optimization runs, frozen-design evaluation, and result manifests."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from itertools import combinations
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from numpy.typing import NDArray

from qwave.diagnostics import cpu_environment, software_versions
from qwave.disorder_experiments import _base_arrays, _base_csv
from qwave.experiments import _write_json
from qwave.optimization import (METHODS, CandidateEvaluator, NumericalFailure, OptimizationProblem,
    disorder_draws, gate_step_check, initializations, prepare_problem, run_multistart)
from qwave.optimization_config import OptimizeConfig
from qwave.provenance import sha256_file, source_identity
from qwave.units import physical_constants
from qwave.wavepackets import analyze_packet


def mode_step_check(problem: OptimizationProblem, u: NDArray) -> tuple[dict[str,Any],dict[str,NDArray]]:
    """Independent central complex differences verify the implicit modal derivative."""
    started = perf_counter()
    cache = problem.cache()
    potential = problem.potential(u)
    _,response = cache.solve(potential,response=True)
    assert response is not None
    reference = response.dt_dpotential_per_mev@problem.device.embedded_shapes
    steps = np.array(problem.config.diagnostics["mode_steps_mev_sqrt_nm"])
    plus = np.empty((len(steps),*reference.shape),dtype=complex)
    minus = np.empty_like(plus)
    direction_errors = np.empty((len(steps),reference.shape[1]))
    for si,h in enumerate(steps):
        for k,shape in enumerate(problem.device.embedded_shapes.T):
            up,down = potential+h*shape,potential-h*shape
            direction_errors[si,k] = max(abs((up-down)/(2*h)-shape))/max(abs(shape))
            plus[si,:,k] = cache.solve(up)[0].t
            minus[si,:,k] = cache.solve(down)[0].t
    derivative = (plus-minus)/(2*steps[:,None,None])
    errors = np.max(abs(derivative-reference),axis=1)
    usable = direction_errors < .01
    mode_ok = np.any((errors <= problem.config.diagnostics["mode_derivative_atol"]) & usable,axis=0)
    summary = {"passed":bool(np.all(mode_ok)),"steps_mev_sqrt_nm":steps.tolist(),
               "max_energy_derivative_errors_by_step_mode":errors.tolist(),
               "direction_relative_errors":direction_errors.tolist(),
               "cost":{**cache.counters(),"wall_seconds":perf_counter()-started}}
    arrays = {"steps_mev_sqrt_nm":steps,"t_plus":plus,"t_minus":minus,"central_dt_deta":derivative,
              "implicit_dt_deta":reference,"direction_relative_errors":direction_errors}
    return summary,arrays


def _archive_evaluator(evaluator: CandidateEvaluator, prefix: str, arrays: dict[str,Any],
                       candidate_rows: list[dict[str,Any]]) -> None:
    """Every evaluated vector, residual, objective, and used complex amplitude is preserved."""
    for row in evaluator.records:
        candidate_rows.append({"run_id":prefix,**row})
    if not evaluator.data:
        return
    for key in evaluator.data[0]:
        arrays[prefix+"_"+key] = np.stack([value[key] for value in evaluator.data])


def _ensemble_statistics(problem: OptimizationProblem, transmission: NDArray, clean_t: NDArray) -> tuple[dict[str,Any],NDArray]:
    """Raw per-draw metrics and finite-sample descriptive statistics, with undefined states explicit."""
    rows = []
    target = problem.packet.amplitude*problem.target_t
    target = target/np.sqrt(np.dot(problem.packet.weights_mev,abs(target)**2))
    for t in transmission:
        metrics = problem.packet_metrics(t)
        own = analyze_packet(problem.device.energy_mev,problem.packet.amplitude,t,clean_t)
        fidelity = metrics["raw_fidelity"]
        # This equals P*F when F is defined, but requires no normalization of
        # the transmitted state and can remain nonzero at subnormal throughput.
        overlap_probability = float(abs(np.dot(problem.packet.weights_mev*target.conj(),problem.packet.amplitude*t))**2)
        rows.append([metrics["p_transmitted"],np.nan if fidelity is None else fidelity,
                     problem.clean_loss(metrics),overlap_probability,
                     np.nan if own.raw_fidelity is None else own.raw_fidelity,
                     float(np.dot(problem.packet.weights_mev*problem.importance_density,abs(t-clean_t)**2))])
    values = np.asarray(rows)
    p,f,loss = values[:,0],values[:,1],values[:,2]
    defined = np.isfinite(f)
    return {"samples":len(values),"mean_transmission":float(np.mean(p)),
            "se_transmission":float(np.std(p,ddof=1)/np.sqrt(len(p))),"min_transmission":float(min(p)),
            "mean_fidelity_defined":float(np.mean(f[defined])) if np.any(defined) else None,
            "se_fidelity_defined":float(np.std(f[defined],ddof=1)/np.sqrt(sum(defined))) if sum(defined)>1 else None,
            "undefined_fidelity_count":int(sum(~defined)),"min_fidelity_defined":float(min(f[defined])) if np.any(defined) else None,
            "mean_loss":float(np.mean(loss)),"se_loss":float(np.std(loss,ddof=1)/np.sqrt(len(loss))),
            "mean_probability_times_fidelity":float(np.mean(values[:,3])),
            "mean_weighted_complex_amplitude_change_squared":float(np.mean(values[:,5])),
            "statistical_note":"sample standard errors, not a confidence guarantee; common random numbers across designs"},values


def evaluate_frozen(problem: OptimizationProblem, u: NDArray, ensembles: dict[str,NDArray]) -> tuple[dict[str,Any],dict[str,NDArray]]:
    """Score a previously frozen design; this function cannot change optimizer selection."""
    started = perf_counter()
    cache = problem.cache()
    potential = problem.potential(u)
    clean,response = cache.solve(potential,response=True)
    assert response is not None
    raw,normalized,derivative = problem.sensitivity(response)
    summary = {"clean":problem.packet_metrics(clean.t),"sensitivity_J":raw,"sensitivity_J_per_mev2":normalized,
               "ensembles":{}}
    arrays = {"u_mev":u,"potential_mev":potential,"clean_t":clean.t,"clean_r":clean.r,"dt_deta":derivative}
    for name,potentials in ensembles.items():
        transmission = np.stack([cache.solve(potential+draw)[0].t for draw in potentials])
        stats,values = _ensemble_statistics(problem,transmission,clean.t)
        summary["ensembles"][name] = stats
        arrays[name+"_t"] = transmission
        arrays[name+"_metrics_P_F_loss_PF_ownF_delta_t2"] = values
    summary["cost"] = {**cache.counters(),"wall_seconds":perf_counter()-started}
    return summary,arrays


def run_optimization(config: OptimizeConfig, output: str | Path, *, plot: bool = True,
                     progress: Any = None) -> Path:
    """Run all four methods under identical constraints; preserve failures and freeze before evaluation."""
    started,output = perf_counter(),Path(output)
    output.mkdir(parents=True,exist_ok=False)
    _write_json(output/"config.json",config.to_dict())
    problem = prepare_problem(config)
    arrays = _base_arrays(problem.device)
    arrays.update(energy_mev=problem.device.energy_mev,energy_weights_mev=problem.packet.weights_mev,
                  incoming_A=problem.packet.amplitude,importance_density_per_mev=problem.importance_density,
                  target_t=problem.target_t)
    starts = initializations(problem)
    arrays["initial_gate_vectors_mev"] = starts
    ensemble_settings = config.ensembles
    z,eta,training = disorder_draws(problem,ensemble_settings["training_samples"],ensemble_settings["training_seed"])
    arrays.update(training_z=z,training_eta_mev_sqrt_nm=eta,training_potential_mev=training)
    candidate_rows: list[dict[str,Any]] = []
    preflight: dict[str,Any] = {}
    floors = config.constraints["minimum_clean_transmission_values"]
    for method in METHODS[1:]:
        if progress:
            progress(f"Checking gate-step stability for {method}")
        evaluator = CandidateEvaluator(problem,method,floors[0],training,phase="preflight")
        begin = perf_counter()
        base = evaluator.evaluate(starts[0])
        try:
            diagnostics = gate_step_check(evaluator,starts[0])
        except NumericalFailure as error:
            diagnostics = {"passed":False,"error":str(error)}
        diagnostics.update(objective_divisor_for_solver=max(abs(base["objective"]),1e-6),
                           cost={**evaluator.cache.counters(),"wall_seconds":perf_counter()-begin})
        preflight[method] = diagnostics
        _archive_evaluator(evaluator,"preflight_"+method,arrays,candidate_rows)
    mode_diagnostics,mode_arrays = mode_step_check(problem,starts[0])
    preflight["modal_complex_derivative"] = mode_diagnostics
    arrays.update({"mode_check_"+key:value for key,value in mode_arrays.items()})
    _write_json(output/"preflight.json",preflight)
    runs = []
    for si,floor in enumerate(floors):
        for method in METHODS:
            prefix = f"sweep{si}_{method}"
            if progress:
                progress(f"Searching {method}, clean transmission floor {floor:g}")
            evaluator = CandidateEvaluator(problem,method,floor,training)
            passed = (method=="A_fixed" or preflight[method]["passed"])
            if method=="D_sensitivity":
                passed = passed and mode_diagnostics["passed"]
            result = run_multistart(evaluator,starts,
                scale=1. if method=="A_fixed" else preflight[method]["objective_divisor_for_solver"],preflight_passed=passed)
            result["run_id"] = prefix
            # Fixed A is always reported, even if it violates the common constraints.
            result["reported_candidate"] = evaluator.records[0] if method=="A_fixed" else result["selected"]
            runs.append(result)
            _archive_evaluator(evaluator,prefix,arrays,candidate_rows)
    frozen = [{"run_id":row["run_id"],"method":row["method"],"status":row["status"],
               "u_mev":None if row["reported_candidate"] is None else row["reported_candidate"]["u_mev"],
               "feasible":False if row["reported_candidate"] is None else row["reported_candidate"]["feasible"]} for row in runs]
    _write_json(output/"frozen_candidates.json",{"frozen_utc":datetime.now(timezone.utc).isoformat(),
               "selection_uses":"search objectives and clean feasibility only; no validation or held-out samples generated yet",
               "candidates":frozen})
    frozen_hash = sha256_file(output/"frozen_candidates.json")
    # Numerical audits at frozen designs cannot reselect or tune their search.
    for row in runs:
        candidate = row["reported_candidate"]
        row["postflight"] = None
        if candidate is None or row["method"]=="A_fixed":
            continue
        audit = CandidateEvaluator(problem,row["method"],row["minimum_clean_transmission"],training,phase="postflight")
        begin = perf_counter()
        try:
            check = gate_step_check(audit,np.asarray(candidate["u_mev"]))
        except NumericalFailure as error:
            check = {"passed":False,"error":str(error)}
        check["cost"] = {**audit.cache.counters(),"wall_seconds":perf_counter()-begin}
        row["postflight"] = check
        _archive_evaluator(audit,row["run_id"]+"_postflight",arrays,candidate_rows)
    # Evaluation seeds are first consumed HERE, after all methods and floors freeze.
    ensembles = {"training":training}
    for name in ("validation","heldout"):
        z,eta,potentials = disorder_draws(problem,ensemble_settings[name+"_samples"],ensemble_settings[name+"_seed"])
        arrays.update({name+"_z":z,name+"_eta_mev_sqrt_nm":eta,name+"_potential_mev":potentials})
        ensembles[name] = potentials
    if progress:
        progress("All designs frozen; evaluating shared independent validation and held-out draws")
    for row in runs:
        candidate = row["reported_candidate"]
        if candidate is None:
            row["evaluation"] = None
            continue
        summary,data = evaluate_frozen(problem,np.asarray(candidate["u_mev"]),ensembles)
        row["evaluation"] = summary
        arrays.update({row["run_id"]+"_final_"+key:value for key,value in data.items()})
    assert sha256_file(output/"frozen_candidates.json")==frozen_hash
    paired = []
    for floor in floors:
        compared = [row for row in runs if row["minimum_clean_transmission"]==floor and row["evaluation"] is not None]
        for first,second in combinations(compared,2):
            a = arrays[first["run_id"]+"_final_heldout_metrics_P_F_loss_PF_ownF_delta_t2"][:,2]
            b = arrays[second["run_id"]+"_final_heldout_metrics_P_F_loss_PF_ownF_delta_t2"][:,2]
            difference = b-a
            paired.append({"minimum_clean_transmission":floor,"first_method":first["method"],"second_method":second["method"],
                "both_clean_feasible":first["reported_candidate"]["feasible"] and second["reported_candidate"]["feasible"],
                "mean_loss_second_minus_first":float(np.mean(difference)),
                "paired_standard_error":float(np.std(difference,ddof=1)/np.sqrt(len(difference))),"samples":len(difference)})
    if paired:
        with (output/"paired_heldout.csv").open("w",newline="") as stream:
            writer = csv.DictWriter(stream,fieldnames=list(paired[0]));writer.writeheader();writer.writerows(paired)
    checks = {"preflight_gate_steps":all(preflight[name]["passed"] for name in METHODS[1:]),
              "preflight_modal_derivative":mode_diagnostics["passed"],
              "postflight_gate_steps":all(row["postflight"]["passed"] for row in runs if row["postflight"] is not None),
              "all_optimized_comparisons_have_feasible_candidate":all(row["selected"] is not None for row in runs if row["method"]!="A_fixed")}
    method_costs = {}
    for method in METHODS:
        related = [row for row in runs if row["method"]==method]
        phases = {"preflight":[],"search":[row["cost"] for row in related],
                  "postflight":[row["postflight"]["cost"] for row in related if row["postflight"] is not None],
                  "evaluation":[row["evaluation"]["cost"] for row in related if row["evaluation"] is not None]}
        if method!="A_fixed":phases["preflight"].append(preflight[method]["cost"])
        if method=="D_sensitivity":phases["preflight"].append(mode_diagnostics["cost"])
        fields = ("forward_work","forward_energy_solves","energy_rhs_solves","energy_factorizations","wall_seconds")
        totals = {name:{field:sum(cost[field] for cost in costs) for field in fields} for name,costs in phases.items()}
        totals["total"] = {field:sum(phase[field] for phase in totals.values()) for field in fields}
        method_costs[method] = totals
    metrics = {"checks":checks,"all_checks_passed":all(checks.values()),"preflight":preflight,"runs":runs,"method_costs":method_costs,
               "paired_heldout_loss_differences":paired,"setup_cost":problem.setup_cost,"kl":problem.device.modes.diagnostics,
               "packet_normalization":problem.packet.normalization,"scope":"Finite-budget exploratory comparison; no superiority or global optimum assumed"}
    _write_json(output/"metrics.json",metrics)
    with (output/"candidates.jsonl").open("w") as stream:
        for row in candidate_rows:
            stream.write(json.dumps(row,sort_keys=True,allow_nan=False)+"\n")
    with (output/"candidates.csv").open("w",newline="") as stream:
        if candidate_rows:
            writer = csv.DictWriter(stream,fieldnames=list(candidate_rows[0]));writer.writeheader()
            writer.writerows({key:json.dumps(value,allow_nan=False) if isinstance(value,(list,dict)) else value
                             for key,value in row.items()} for row in candidate_rows)
    comparison = []
    for row in runs:
        evaluation = row["evaluation"]
        heldout = {} if evaluation is None else evaluation["ensembles"]["heldout"]
        comparison.append({"run_id":row["run_id"],"method":row["method"],"minimum_clean_transmission":row["minimum_clean_transmission"],
            "feasible":False if row["reported_candidate"] is None else row["reported_candidate"]["feasible"],
            "search_work":row["cost"]["forward_work"],"search_wall_seconds":row["cost"]["wall_seconds"],
            "clean_P":None if evaluation is None else evaluation["clean"]["p_transmitted"],
            "clean_F":None if evaluation is None else evaluation["clean"]["raw_fidelity"],
            "J":None if evaluation is None else evaluation["sensitivity_J"],
            "heldout_mean_P":heldout.get("mean_transmission"),"heldout_mean_F_defined":heldout.get("mean_fidelity_defined"),
            "heldout_mean_loss":heldout.get("mean_loss"),"heldout_se_loss":heldout.get("se_loss")})
    with (output/"comparison.csv").open("w",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=list(comparison[0]));writer.writeheader();writer.writerows(comparison)
    _base_csv(output,problem.device)
    if plot:
        from qwave.optimization_plotting import save_optimization_plots
        save_optimization_plots(problem,metrics,candidate_rows,arrays,output)
    metadata = {"manifest_version":1,"project":"Phaseward","stage":"PROMPT 4","created_utc":datetime.now(timezone.utc).isoformat(),
        "config":config.to_dict(),"software_versions":software_versions(),"source":source_identity(),"constants_SI":physical_constants(),
        "environment":cpu_environment(),"frozen_candidates_sha256":frozen_hash,"setup_cost":problem.setup_cost,
        "randomness":{"generator":"NumPy PCG64","initialization_seed":config.optimizer["initialization_seed"],**config.ensembles,
                      "evaluation_order":"validation and heldout generated only after all search selections frozen",
                      "training_draw_shape":list(arrays["training_z"].shape),"common_random_numbers":"same draws for every method/floor"},
        "units":{"x":"nm","gate_potential":"meV, not electrode voltage","phi":"nm^-1/2","lambda":"meV^2 nm",
                 "eta":"meV sqrt(nm)","dt_deta":"1/(meV sqrt(nm))","J":"dimensionless","J_over_sigma2":"meV^-2",
                 "w":"meV^-1","probability_fidelity":"dimensionless, reported separately"},
        "mode_convention":"Phi.T W Phi=I; eta=sqrt(lambda)z; Var(eta)=lambda; lambda appears exactly once in J",
        "objective_definitions":{"A_fixed":"no optimization; clean loss reported",
             "B_clean":"alpha*(1-P_clean)+(1-alpha)*(1-F_clean)",
             "C_monte_carlo":"training mean of the identical B loss with retained-KL disorder",
             "D_sensitivity":"sum lambda_k integral w(E)|dt/deta_k|^2 dE; optional divide by nominal sigma^2",
             "importance_weighting":config.objective["weighting"],"importance_weight_integral":float(np.dot(problem.packet.weights_mev,problem.importance_density)),
             "undefined_fidelity_loss_rule":"use zero ONLY for loss; retain undefined raw fidelity and flag infeasible"},
        "approximations":{"physics":"constant-mass, coherent elastic real 1D potential; unchanged FD Hamiltonian and exact discrete leads",
             "phase":"fixed endpoint planes and unit-flux t; no phase removal or delay alignment",
             "energy_quadrature":"positive composite trapezoid on the configured finite propagating energy window",
             "disorder":"same retained-KL model for C training and every post-freeze ensemble; no full-covariance robustness claim",
             "modal_derivative":"independent implicit linear response checked against centered complex differences before optimization",
             "gate_gradient":"bounded real second-order differences; selected/half-step audits before search and at frozen designs, with no reselection",
             "constraints":"explicit individual bounds, signed nodal sum/gradient linear inequalities, clean P and raw F nonlinear inequalities",
             "feasibility":"separate scaled residual test, independent of SLSQP success; all trial points saved",
             "selection":"lowest-objective feasible observed trial including derivative probes; no validation-based reselection",
             "work_budget":"same RHS-equivalent sweep cap per B/C/D per constraint floor, equally allocated over starts; unused capacity is not refilled",
             "cost":"one forward sweep costs 1, implicit response costs 3 including baseline; actual forward solves, factorizations, wall times also stored",
             "cache":"method-local exact arrays/dtype/shape and full config/constants/source hash; candidate keys also hash immutable copied training samples; no rounded gate keys; bounded LRU",
             "objective_scaling":"SLSQP divides each method objective by max(abs(initial objective),1e-6); does not change rankings",
             "limitations":"finite-grid/energy/ensemble, truncated disorder, local optima, finite budget; no certified Pareto frontier or superiority"},
        "plot_enabled":plot,"checks":checks}
    np.savez_compressed(output/"arrays.npz",**arrays,provenance_json=np.asarray(json.dumps(metadata,sort_keys=True,allow_nan=False)))
    metadata["outputs"] = {path.name:{"sha256":sha256_file(path),"size_bytes":path.stat().st_size}
                           for path in sorted(output.iterdir()) if path.is_file()}
    metadata["elapsed_seconds_before_manifest"] = perf_counter()-started
    _write_json(output/"manifest.json",metadata)
    return output
