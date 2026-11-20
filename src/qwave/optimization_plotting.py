"""Measured trade-offs and work counts; no fitted or invented Pareto frontier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from qwave.optimization import METHODS, OptimizationProblem


def save_optimization_plots(problem: OptimizationProblem, metrics: dict[str,Any], candidates: list[dict[str,Any]],
                            arrays: dict[str,Any], output: Path) -> None:
    """Plot computed candidate/ensemble metrics, failures, costs, and derivative diagnostics."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = dict(zip(METHODS,["#555555","#0072B2","#009E73","#D55E00"]))
    def save(fig: Any, name: str) -> None:
        for extension in ("png","svg","pdf"):
            fig.savefig(output/(name+"."+extension),dpi=150)
        plt.close(fig)

    fig,axes = plt.subplots(2,2,figsize=(12,9),layout="constrained")
    for row in metrics["runs"]:
        data = row["evaluation"]
        if data is None:
            continue
        method = row["method"]
        feasible = row["reported_candidate"]["feasible"]
        marker = "o" if feasible else "x"
        label = f"{method}, Pmin={row['minimum_clean_transmission']:g}"+(" (infeasible)" if not feasible else "")
        clean,held = data["clean"],data["ensembles"]["heldout"]
        axes[0,0].scatter(clean["p_transmitted"],clean["raw_fidelity"],color=colors[method],marker=marker,label=label)
        if held["mean_fidelity_defined"] is not None:
            axes[0,1].errorbar(held["mean_transmission"],held["mean_fidelity_defined"],
                xerr=held["se_transmission"],yerr=held["se_fidelity_defined"],fmt=marker,color=colors[method],capsize=3)
        axes[1,0].errorbar(row["cost"]["forward_work"],held["mean_loss"],yerr=held["se_loss"],
                          fmt=marker,color=colors[method],capsize=3)
        axes[1,1].errorbar(data["sensitivity_J"],held["mean_loss"],yerr=held["se_loss"],fmt=marker,color=colors[method],capsize=3)
    for ax in axes.flat:
        ax.grid(alpha=.25)
    axes[0,0].set(xlabel="Clean transmitted probability",ylabel="Clean conditional target fidelity",title="Observed feasible/infeasible designs")
    axes[0,1].set(xlabel="Held-out mean transmitted probability",ylabel="Held-out mean defined target fidelity",title="Independent draws; bars = one sample SE")
    axes[1,0].set(xlabel="Search RHS-equivalent energy sweeps",ylabel="Held-out mean loss (lower is better)",title="Search cost / measured robustness")
    axes[1,1].set(xlabel="Sensitivity J (dimensionless)",ylabel="Held-out mean loss (lower is better)",title="Surrogate versus measured loss")
    handles,labels = axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="outside lower center",ncol=2,fontsize=8)
    fig.suptitle("Phaseward · observed trade-offs\nFixed candidates; no held-out selection or claimed Pareto frontier")
    save(fig,"optimization_tradeoffs")

    fig,axes = plt.subplots(1,3,figsize=(14,4.5),layout="constrained")
    for ax,method in zip(axes,METHODS[1:]):
        for row in metrics["runs"]:
            if row["method"]!=method:
                continue
            records = [value for value in candidates if value["run_id"]==row["run_id"]]
            best = np.inf
            x,y = [],[]
            for value in records:
                if value["feasible"]:
                    best=min(best,value["objective"])
                if np.isfinite(best):
                    x.append(value["work_at_evaluation"]);y.append(best)
            if x:
                ax.step(x,y,where="post",label=f"Pmin={row['minimum_clean_transmission']:g}")
            else:
                ax.text(.03,.1+len(ax.texts)*.12,f"Pmin={row['minimum_clean_transmission']:g}: no feasible point",transform=ax.transAxes,fontsize=8)
        ax.set(xlabel="Search RHS-equivalent sweeps",ylabel="Best feasible observed objective",title=method)
        ax.grid(alpha=.25)
        if ax.lines:ax.legend()
    fig.suptitle("Budgeted progress · each panel uses its own declared objective")
    save(fig,"optimization_progress")

    fig,axes = plt.subplots(1,2,figsize=(12,4.8),layout="constrained")
    for field,ax in zip(("forward_work","wall_seconds"),axes):
        search,preflight,evaluation = [],[],[]
        for method in METHODS:
            rows=[row for row in metrics["runs"] if row["method"]==method]
            search.append(sum(row["cost"][field] for row in rows))
            before = 0 if method=="A_fixed" else metrics["preflight"][method]["cost"][field]
            if method=="D_sensitivity":before+=metrics["preflight"]["modal_complex_derivative"]["cost"][field]
            preflight.append(before)
            evaluation.append(sum(row["evaluation"]["cost"][field] for row in rows if row["evaluation"] is not None)
                              +sum(row["postflight"]["cost"][field] for row in rows if row["postflight"] is not None))
        ax.bar(METHODS,preflight,label="Numerical preflight")
        ax.bar(METHODS,search,bottom=preflight,label="Search (all floors)")
        ax.bar(METHODS,evaluation,bottom=np.asarray(preflight)+search,label="Frozen-design audit/evaluation")
        ax.set(ylabel="RHS-equivalent sweeps" if field=="forward_work" else "Measured seconds",title="Costs by phase")
        ax.tick_params(axis="x",rotation=18);ax.legend(fontsize=8)
    fig.suptitle("All measured method costs · shared target setup recorded separately")
    save(fig,"optimization_costs")

    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout="constrained")
    for method in METHODS[1:]:
        row=metrics["preflight"][method]
        if "max_errors_relative_to_half_step" in row:
            h=np.asarray(row["steps_mev"]);error=np.asarray(row["max_errors_relative_to_half_step"],dtype=float)
            mask=error>0
            axes[0].loglog(h[mask],error[mask],"o-",label=method,color=colors[method])
    modes=metrics["preflight"]["modal_complex_derivative"]
    for k,error in enumerate(np.asarray(modes["max_energy_derivative_errors_by_step_mode"]).T):
        axes[1].loglog(modes["steps_mev_sqrt_nm"],error,".-",label=f"Mode {k+1}")
    axes[0].set(xlabel="Gate step (meV)",ylabel="Max Jacobian difference (component units / meV)",title="Objective/P/F gate-step diagnostic")
    axes[1].set(xlabel="Mode step (meV sqrt(nm))",ylabel="Max complex derivative error (1/(meV sqrt(nm)))",title="Centered complex t versus implicit derivative")
    for ax in axes:ax.grid(alpha=.25,which="both");ax.legend(fontsize=8)
    fig.suptitle("Numerical diagnostics at the common configured start")
    save(fig,"optimization_steps")

    floors=problem.config.constraints["minimum_clean_transmission_values"]
    fig,axes=plt.subplots(len(floors),1,figsize=(10,3.5*len(floors)),layout="constrained",squeeze=False)
    for ax,floor in zip(axes[:,0],floors):
        for row in metrics["runs"]:
            if row["minimum_clean_transmission"]==floor and row["evaluation"] is not None:
                ax.plot(problem.device.x_nm,arrays[row["run_id"]+"_final_potential_mev"],
                        label=row["method"]+(" (infeasible)" if not row["reported_candidate"]["feasible"] else ""),color=colors[row["method"]])
        ax.set(xlabel="Position (nm)",ylabel="Clean potential energy (meV)",title=f"Frozen designs, clean P minimum = {floor:g}")
        ax.legend(fontsize=8);ax.grid(alpha=.25)
    save(fig,"optimized_potentials")
