"""Numerical convergence diagnostics, isolated from final method evaluation.

These use the first case's configured fixed gates and independent development
draws. Finest-grid and full-covariance comparisons are numerical references,
not observed physical truth and not a certificate for every optimized design.
"""

from __future__ import annotations

from copy import deepcopy
from time import perf_counter
from typing import Any

import numpy as np
from scipy.interpolate import PchipInterpolator

from qwave.experiment_config import ExperimentConfig, diagnostic_settings
from qwave.experiment_support import packet_metrics
from qwave.optimization import prepare_problem
from qwave.optimization_config import OptimizeConfig
from qwave.references import rectangular_transmission_amplitude
from qwave.statistics import paired_bootstrap
from qwave.wavepackets import DelaySearch


def run_convergence(config: ExperimentConfig, *, progress: Any = None) -> tuple[dict,list[dict],dict]:
    """Run all five prespecified axes; never select or modify an optimized vector."""
    started=perf_counter()
    base=diagnostic_settings(config.resolved_cases()[0][1].to_dict())
    settings=config.convergence
    seeds=config.seed_registry()["draw_seeds"]["convergence"]
    delay=DelaySearch(**config.delay)
    rows: list[dict[str,Any]]=[]
    arrays: dict[str,Any]={}
    costs=[]
    setups=[]
    def announce(value: str) -> None:
        if progress:progress("Convergence diagnostic: "+value)
    def prepare(**changes: int):
        changed=deepcopy(base)
        changed["model"]["scattering"].update(changes)
        problem=prepare_problem(OptimizeConfig.from_mapping(changed))
        setups.append(problem.setup_cost)
        return problem
    fine=prepare(grid_points=max(settings["spatial_grid_points"]))
    modes=fine.device.modes
    z=np.random.Generator(np.random.PCG64(seeds[0])).standard_normal(len(modes.eigenvalues_mev2_nm))
    fine_field=modes.shapes_per_sqrt_nm@(np.sqrt(modes.eigenvalues_mev2_nm)*z)
    interpolate=PchipInterpolator(modes.x_nm,fine_field,extrapolate=False)
    arrays.update(spatial_reference_channel_x_nm=modes.x_nm,spatial_reference_field_mev=fine_field,
                  spatial_reference_z=z,spatial_reference_lambda_mev2_nm=modes.eigenvalues_mev2_nm,
                  spatial_reference_phi_per_sqrt_nm=modes.shapes_per_sqrt_nm)
    def field(problem):
        values=np.zeros(len(problem.device.x_nm))
        values[problem.device.channel_indices]=interpolate(problem.device.modes.x_nm)
        return values
    announce("spatial spacing and independent analytical references")
    spatial=[]
    for points in settings["spatial_grid_points"]:
        problem=prepare(grid_points=points)
        cache=problem.cache()
        potential=problem.device.potential_mev
        for kind,values in (("clean",potential),("fixed_disorder_field",potential+field(problem))):
            solved,_=cache.solve(values)
            metric=packet_metrics(problem,solved.t,delay)
            row={"study":"spatial_grid","variant":kind,"level":points,
                 "spacing_nm":float(np.diff(problem.device.x_nm)[0]),**metric,
                 "max_conservation_error":float(np.max(abs(solved.conservation_error)))}
            rows.append(row);spatial.append((row,solved.t.copy()))
            prefix=f"spatial_{points}_{kind}"
            arrays.update({prefix+"_x_nm":problem.device.x_nm,prefix+"_V_mev":values,
                           prefix+"_energy_mev":problem.device.energy_mev,prefix+"_t":solved.t,prefix+"_r":solved.r})
        # Keep this benchmark separate: zero leads and rectangular potential,
        # with the same mass, explicitly declared here rather than silently
        # substituting a benchmark for the user's device.
        if problem.arguments["left_lead_mev"]==0 and problem.arguments["right_lead_mev"]==0:
            free,_=cache.solve(np.zeros(len(potential)))
            expected=np.exp(1j*free.k_left_per_nm*(problem.device.x_nm[-1]-problem.device.x_nm[0]))
            rows.append({"study":"analytical_free","variant":"exact_discrete","level":points,
                "spacing_nm":free.spacing_nm,"max_complex_t_error":float(np.max(abs(free.t-expected))),
                "max_reflection_probability":float(np.max(free.R)),
                "max_conservation_error":float(np.max(abs(free.conservation_error)))})
            # Fixed 8 nm width on the preset domain; only run when the nodes
            # exactly represent that width. Otherwise record an explicit skip.
            x=problem.device.x_nm
            width=8.
            mask=(x>=-width/2)&(x<width/2)
            represented_width=float(sum(mask)*free.spacing_nm)
            if x[0] < -4 and x[-1] > 4 and abs(represented_width-width)<1e-10:
                rect,_=cache.solve(np.where(mask,30.,0.))
                analytic=rectangular_transmission_amplitude(problem.device.energy_mev,height_mev=30.,width_nm=width,
                    effective_mass_ratio=problem.arguments["effective_mass_ratio"],reference_length_nm=float(x[-1]-x[0]))
                for regime in ("below","above"):
                    active=problem.device.energy_mev<30 if regime=="below" else problem.device.energy_mev>30
                    if np.any(active):
                        rows.append({"study":"analytical_rectangle","variant":regime,"level":points,
                            "spacing_nm":free.spacing_nm,"max_complex_t_error":float(np.max(abs(rect.t[active]-analytic[active]))),
                            "max_probability_error":float(np.max(abs(rect.T[active]-abs(analytic[active])**2))),
                            "max_conservation_error":float(np.max(abs(rect.conservation_error))),
                            "barrier_height_mev":30.,"barrier_width_nm":width})
                arrays.update({f"rect_{points}_energy_mev":problem.device.energy_mev,
                    f"rect_{points}_t":rect.t,f"rect_{points}_reference_t":analytic})
            else:
                rows.append({"study":"analytical_rectangle","level":points,"status":"skipped_width_or_domain"})
        else:
            rows.append({"study":"analytical_free","level":points,"status":"skipped_nonzero_leads"})
        costs.append(cache.counters())
    for variant in ("clean","fixed_disorder_field"):
        selected=[(row,t) for row,t in spatial if row["variant"]==variant]
        ref,reference=selected[-1]
        for row,t in selected:
            row["max_complex_t_difference_to_finest"]=float(np.max(abs(t-reference)))
            for key in ("p_transmitted","raw_fidelity","aligned_fidelity","estimated_delay_ps"):
                row[key+"_difference_to_finest"]=None if row[key] is None or ref[key] is None else row[key]-ref[key]
    announce("energy quadrature at a fixed spatial grid and physical field")
    energy_rows=[]
    for points in settings["energy_points"]:
        problem=prepare(grid_points=max(settings["spatial_grid_points"]),energy_points=points)
        cache=problem.cache()
        for variant,values in (("clean",problem.device.potential_mev),
                               ("fixed_disorder_field",problem.device.potential_mev+field(problem))):
            solved,_=cache.solve(values)
            row={"study":"energy_quadrature","variant":variant,"level":points,
                 "energy_spacing_mev":float(np.diff(problem.device.energy_mev)[0]),
                 **packet_metrics(problem,solved.t,delay),
                 "max_conservation_error":float(np.max(abs(solved.conservation_error)))}
            rows.append(row);energy_rows.append(row)
            arrays.update({f"energy_{points}_{variant}_E_mev":problem.device.energy_mev,
                           f"energy_{points}_{variant}_A":problem.packet.amplitude,
                           f"energy_{points}_{variant}_t":solved.t,
                           f"energy_{points}_{variant}_reference_t":problem.target_t})
        costs.append(cache.counters())
    for variant in ("clean","fixed_disorder_field"):
        selected=[row for row in energy_rows if row["variant"]==variant]
        ref=selected[-1]
        for row in selected:
            for key in ("p_transmitted","raw_fidelity","aligned_fidelity","estimated_delay_ps"):
                row[key+"_difference_to_finest"]=None if row[key] is None or ref[key] is None else row[key]-ref[key]
    announce("KL truncation with nested coefficients and a full-covariance reference")
    problem=prepare()
    cache=problem.cache()
    modes=problem.device.modes
    nmode=len(modes.eigenvalues_mev2_nm)
    z=np.stack([np.random.Generator(np.random.PCG64(seed)).standard_normal(nmode) for seed in seeds])
    eta=z*np.sqrt(modes.eigenvalues_mev2_nm)
    embedded=np.zeros((len(problem.device.x_nm),nmode))
    embedded[problem.device.channel_indices]=modes.shapes_per_sqrt_nm
    full=eta@embedded.T
    arrays.update(truncation_z=z,truncation_eta_mev_sqrt_nm=eta,
                  truncation_full_phi_per_sqrt_nm=embedded,truncation_lambda_mev2_nm=modes.eigenvalues_mev2_nm,
                  truncation_full_potential_disorder_mev=full)
    reference_t=np.stack([cache.solve(problem.device.potential_mev+draw)[0].t for draw in full])
    reference_metrics=[packet_metrics(problem,t,delay) for t in reference_t]
    arrays["truncation_reference_t"]=reference_t
    arrays["truncation_energy_mev"]=problem.device.energy_mev
    arrays["truncation_fixed_potential_mev"]=problem.device.potential_mev
    losses=np.array([metric["loss"] for metric in reference_metrics])
    arrays["sample_count_full_covariance_loss"]=losses
    for count in settings["retained_modes"]:
        fields=eta[:,:count]@embedded[:,:count].T
        transmission=np.stack([cache.solve(problem.device.potential_mev+draw)[0].t for draw in fields])
        arrays[f"truncation_K{count}_t"]=transmission
        retained=float(sum(modes.eigenvalues_mev2_nm[:count])/sum(modes.eigenvalues_mev2_nm))
        for index,(t,reference,ref_metric) in enumerate(zip(transmission,reference_t,reference_metrics)):
            metric=packet_metrics(problem,t,delay)
            rows.append({"study":"mode_truncation","variant":"paired_full_covariance","level":count,
                "trial_index":index,"seed":seeds[index],"retained_variance_fraction":retained,**metric,
                "full_covariance_loss":ref_metric["loss"],"loss_difference_to_full":metric["loss"]-ref_metric["loss"],
                "transmission_difference_to_full":metric["p_transmitted"]-ref_metric["p_transmitted"],
                "weighted_complex_t_error_squared":float(np.dot(problem.packet.weights_mev*abs(problem.packet.amplitude)**2,abs(t-reference)**2))})
    costs.append(cache.counters())
    announce("nested random-sample counts, kept separate from discretization bias")
    for count in settings["sample_counts"]:
        values=losses[:count]
        stats,boot=paired_bootstrap(np.zeros(count),values,seed=config.statistics["bootstrap_seed"],
            resamples=config.statistics["bootstrap_resamples"],confidence=config.statistics["confidence_level"])
        arrays[f"sample_count_N{count}_bootstrap_mean_loss"]=boot
        rows.append({"study":"sample_count","variant":"full_covariance_fixed_design","level":count,
            "mean_loss":float(np.mean(values)),"standard_error_loss":float(np.std(values,ddof=1)/np.sqrt(count)),
            "difference_to_largest_nested_mean":float(np.mean(values)-np.mean(losses)),
            "ci_low":stats["ci_low"],"ci_high":stats["ci_high"],
            "note":"nested prefixes are dependent; largest prefix is not the population truth"})
    announce("complex finite-difference steps against implicit response")
    cache=problem.cache()
    potential=problem.device.potential_mev
    _,response=cache.solve(potential,response=True)
    assert response is not None
    implicit=response.dt_dpotential_per_mev@problem.device.embedded_shapes
    arrays["steps_implicit_dt_deta"]=implicit
    for si,step in enumerate(settings["mode_steps_mev_sqrt_nm"]):
        derivatives=[]
        for k,shape in enumerate(problem.device.embedded_shapes.T):
            up,down=potential+step*shape,potential-step*shape
            plus=cache.solve(up)[0].t
            minus=cache.solve(down)[0].t
            derivative=(plus-minus)/(2*step)
            direction=float(np.max(abs((up-down)/(2*step)-shape))/np.max(abs(shape)))
            error=float(np.max(abs(derivative-implicit[:,k])))
            derivatives.append(derivative)
            rows.append({"study":"finite_difference_step","variant":"complex_modal_derivative","level":step,
                "mode":k,"step_mev_sqrt_nm":step,"max_complex_derivative_error":error,
                "represented_direction_relative_error":direction,"represented_direction_resolved":direction<.01})
        arrays[f"steps_{si}_central_dt_deta"]=np.stack(derivatives,axis=1)
    costs.append(cache.counters())
    conservation=[row["max_conservation_error"] for row in rows if "max_conservation_error" in row]
    observed={
        "spatial": [{key:row[key] for key in ("variant","level","spacing_nm","max_complex_t_difference_to_finest",
                    "p_transmitted_difference_to_finest")} for row in rows if row["study"]=="spatial_grid"],
        "energy": [{key:row[key] for key in ("variant","level","energy_spacing_mev","p_transmitted_difference_to_finest",
                   "raw_fidelity_difference_to_finest")} for row in rows if row["study"]=="energy_quadrature"],
        "mode_truncation": [{"retained_modes":k,"retained_variance_fraction":next(r["retained_variance_fraction"] for r in rows
                              if r["study"]=="mode_truncation" and r["level"]==k),
                              "rms_weighted_complex_t_error":float(np.sqrt(np.mean([r["weighted_complex_t_error_squared"] for r in rows
                              if r["study"]=="mode_truncation" and r["level"]==k])))} for k in settings["retained_modes"]],
        "finite_difference": [{"mode":k,"minimum_observed_error":min(r["max_complex_derivative_error"] for r in rows
                              if r["study"]=="finite_difference_step" and r["mode"]==k),
                              "smallest_step_error":next(r["max_complex_derivative_error"] for r in rows
                              if r["study"]=="finite_difference_step" and r["mode"]==k
                              and r["level"]==min(settings["mode_steps_mev_sqrt_nm"]))} for k in range(implicit.shape[1])],
        "sample_counts": [row for row in rows if row["study"]=="sample_count"],
        "analytical_references": [row for row in rows if row["study"].startswith("analytical_")]}
    summary={
        "scope":"NUMERICAL CONVERGENCE, not physical findings; configured fixed gates of the first case only",
        "configured_gates_mev":problem.device.gates.amplitudes_mev.tolist(),
        "all_forward_solves_conserved":all(cost["max_conservation_error"] <= problem.device.scatter.conservation_tolerance for cost in costs),
        "maximum_reported_conservation_error":max(conservation),
        "observed_changes":observed,
        "cost":{"forward_work":sum(cost["forward_work"] for cost in costs),
                "forward_energy_solves":sum(cost["forward_energy_solves"] for cost in costs),
                "response_rhs_sweeps":sum(cost["response_rhs_sweeps"] for cost in costs),
                "energy_rhs_solves":sum(cost["energy_rhs_solves"] for cost in costs),
                "energy_factorizations":sum(cost["energy_factorizations"] for cost in costs),
                "setup_forward_work":sum(cost["forward_work"] for cost in setups),
                "setup_energy_factorizations":sum(cost["energy_factorizations"] for cost in setups),
                "setup_wall_seconds":sum(cost["wall_seconds"] for cost in setups),
                "wall_seconds":perf_counter()-started},
        "conventions":{
            "spatial":"same PCHIP field from one full-covariance draw on the finest channel grid, zero outside; finest result is only a numerical reference",
            "energy":"same finest spatial grid, same finite energy window, renormalized Gaussian and positive trapezoidal weights",
            "modes":"same full covariance eigensystem and per-draw z prefixes; omitted variance is not rescaled; full covariance differs from held-out retained-KL model",
            "step":"real centered perturbations of complex t, compared with independently assembled implicit response; tiny steps may get worse",
            "samples":"independent convergence partition; nested prefixes of full-covariance fixed-design losses; sample uncertainty cannot remove solver bias",
            "analytical":"exact discrete free propagation and separate continuum 30 meV x 8 nm rectangle above/below; continuum errors are measured, not compared to a physical-law tolerance"},
        "limitations":"Does not establish continuum accuracy for every optimized design or optimizer variability; no study changes a search or final distribution."}
    return summary,rows,arrays

