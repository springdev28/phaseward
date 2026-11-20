"""Publication-exportable figures drawn exclusively from recorded trial arrays."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from qwave.experiment_config import ExperimentConfig
from qwave.experiments import _write_json
from qwave.optimization import METHODS


def save_experiment_figures(output: Path, config: ExperimentConfig, summary: dict, trials: list[dict],
                            convergence: list[dict], costs: list[dict]) -> None:
    """Export raw distributions, paired intervals, phase costs and numerical diagnostics."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors=dict(zip(METHODS,["#555555","#0072B2","#009E73","#D55E00"]))
    descriptions={}
    with plt.rc_context({"font.size":10,"axes.labelsize":10,"axes.titlesize":11,"svg.fonttype":"none",
                         "pdf.fonttype":42,"savefig.dpi":300,"axes.spines.top":False,"axes.spines.right":False}):
        def save(fig: Any, name: str, caption: str) -> None:
            for extension in ("svg","pdf","png"):
                fig.savefig(output/(name+"."+extension),dpi=300)
            descriptions[name]={"description":caption,"formats":["svg","pdf","png"],"png_dpi":300,
                                "data":"trials.csv, paired_differences.csv, convergence.csv or costs.csv as specified"}
            plt.close(fig)
        labels={"p_transmitted":"Transmitted probability P (dimensionless)",
                "raw_fidelity":"Raw conditional fidelity (dimensionless)",
                "aligned_fidelity":"Delay-aligned fidelity (dimensionless)",
                "estimated_delay_ps":"Estimated output lag (ps)",
                "loss":"Raw packet loss (dimensionless)",
                "max_conservation_error":"Maximum |T + R − 1| (dimensionless)"}
        for case,_ in config.resolved_cases():
            for fi,floor in enumerate(config.optimization["constraints"]["minimum_clean_transmission_values"]):
                fig,axes=plt.subplots(2,3,figsize=(12.5,7.2),layout="constrained")
                for ax,metric in zip(axes.flat,labels):
                    for method in METHODS:
                        selected=[r for r in trials if r["case"]==case and r["minimum_clean_transmission"]==floor
                                  and r["method"]==method and r["partition"]=="heldout"]
                        data=np.sort([r[metric] for r in selected if r.get(metric) is not None])
                        if len(data):
                            suffix="" if all(r["clean_feasible"] for r in selected) else ", infeasible"
                            ax.step(data,np.arange(1,len(data)+1)/len(data),where="post",color=colors[method],
                                    label=f"{method} (n={len(data)}{suffix})")
                            ax.scatter(data,np.arange(1,len(data)+1)/len(data),color=colors[method],s=9)
                    ax.set(xlabel=labels[metric],ylabel="Empirical cumulative fraction",ylim=(0,1.03))
                    if metric=="max_conservation_error":
                        ax.set_xlabel("Max |T + R − 1| (dimensionless)",labelpad=17)
                        ax.ticklabel_format(axis="x",style="sci",scilimits=(-2,2),useMathText=True)
                    ax.grid(alpha=.2)
                    if not ax.lines:ax.text(.1,.5,"No defined values",transform=ax.transAxes)
                handles,legend=axes[0,0].get_legend_handles_labels()
                if handles:fig.legend(handles,legend,loc="outside lower center",ncol=2,fontsize=9)
                fig.suptitle(f"Phaseward · held-out distributions · {case} · P floor {floor:g}\n"
                             "Frozen designs; paired disorder draws; undefined values counted in the tables")
                save(fig,f"distributions_{case}_{fi}",
                     "Empirical CDFs and every defined held-out observation, without smoothing. Data: trials.csv. "
                     "Each method uses the same disorder seeds. Conditional fidelity is separate from throughput. "
                     "Delay estimates are bounded as declared in config.json; boundary and missing counts are in summary.json. "
                     "The CDF starts at its first observed mass; no population distribution is fitted.")
        primary=[r for r in summary["comparisons"] if r["primary"]]
        fig,ax=plt.subplots(figsize=(11,max(4.2,.55*len(primary)+2)),layout="constrained")
        for i,row in enumerate(primary):
            if row.get("absolute_difference") is None:
                ax.text(0,i,"unavailable / unresolved",fontsize=9)
                continue
            lo,hi=row["family_ci_low"],row["family_ci_high"]
            ax.plot([lo,hi],[i,i],color="#0072B2",linewidth=2)
            ax.plot(row["absolute_difference"],i,"o",color="#D55E00")
            ax.text(hi,i+.12,row["outcome"],fontsize=8)
        ax.axvline(0,color="#555555",ls="--",label="No mean difference")
        ax.axvline(-config.statistics["practical_loss_difference"],color="#009E73",ls=":",
                   label="Prespecified minimum-benefit threshold")
        ax.set(yticks=range(len(primary)),
               yticklabels=[f"{r['case']} / P≥{r['minimum_clean_transmission']:g} / D−{r['first_method'][0]}" for r in primary],
               xlabel="Paired mean loss difference: D − baseline (dimensionless; negative favors D)",
               title="Prespecified comparisons · approximate family-adjusted bootstrap intervals")
        ax.set_ylim(len(primary)-.5,-.5)
        ax.margins(x=.15)
        ax.grid(axis="x",alpha=.2);ax.legend(loc="best",fontsize=8)
        save(fig,"paired_effects","Dots are paired mean loss differences, bars are basic bootstrap intervals with Bonferroni "
             "adjustment over the prespecified D-versus-baselines family. Data: paired_differences.csv. This is conditional "
             "on the frozen designs; it does not measure training or initialization variability. A zero crossing and a practical-margin crossing are different tests.")
        fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout="constrained")
        phases=("preflight","search","postflight","evaluation")
        for ax,field,label in zip(axes,("forward_work","wall_seconds"),
                                 ("RHS-equivalent energy sweeps (count)","Measured wall time (s)")):
            bottoms=np.zeros(4)
            for phase,color in zip(phases,["#999999","#0072B2","#CC79A7","#E69F00"]):
                data=[]
                for method in METHODS:
                    related=[r for r in costs if r["method"]==method and
                        (r["phase"].startswith(phase) if phase in {"preflight","search"} else r["phase"].endswith(phase))]
                    data.append(sum(r[field] for r in related))
                ax.bar(range(4),data,bottom=bottoms,label=phase,color=color);bottoms+=data
            ax.set(xticks=range(4),xticklabels=["A fixed","B clean","C Monte Carlo","D sensitivity"],ylabel=label)
            ax.tick_params(axis="x",labelrotation=15);ax.grid(axis="y",alpha=.2)
        axes[0].legend(fontsize=9)
        fig.suptitle("Phaseward · complete method costs across all declared cases/floors\n"
                     "Shared target setup and numerical convergence are charged separately in the tables")
        save(fig,"computation_costs","Stacked preflight, search, postflight and evaluation costs, aggregated without "
             "discarding unsuccessful starts. Data: costs.csv. One forward energy sweep costs one RHS-equivalent; implicit "
             "response costs three. Wall time depends on the local machine; objective evaluations, factorizations and setup are also recorded.")
        fig,axes=plt.subplots(2,3,figsize=(13,8),layout="constrained")
        for variant,color in (("clean","#0072B2"),("fixed_disorder_field","#D55E00")):
            rows=[r for r in convergence if r["study"]=="spatial_grid" and r["variant"]==variant]
            nonzero=[r for r in rows if r["max_complex_t_difference_to_finest"]>0]
            if nonzero:axes[0,0].loglog([r["spacing_nm"] for r in nonzero],
                [r["max_complex_t_difference_to_finest"] for r in nonzero],"o-",label=variant,color=color)
            rows=[r for r in convergence if r["study"]=="energy_quadrature" and r["variant"]==variant]
            nonzero=[r for r in rows if abs(r["p_transmitted_difference_to_finest"])>0]
            if nonzero:axes[0,1].loglog([r["energy_spacing_mev"] for r in nonzero],
                [abs(r["p_transmitted_difference_to_finest"]) for r in nonzero],"o-",label=variant,color=color)
        axes[0,0].set(xlabel="Spatial spacing (nm)",ylabel="max |t − t_finest| (dimensionless)",title="Spatial discretization; finest omitted")
        axes[0,1].set(xlabel="Energy spacing (meV)",ylabel="|P − P_densest| (dimensionless)",title="Energy quadrature; densest omitted")
        ks=sorted({r["level"] for r in convergence if r["study"]=="mode_truncation"})
        rms=[]
        for k in ks:
            data=np.sqrt([r["weighted_complex_t_error_squared"] for r in convergence if r["study"]=="mode_truncation" and r["level"]==k])
            axes[0,2].scatter(k+np.linspace(-.12,.12,len(data)),data,s=12,alpha=.45,color="#0072B2")
            rms.append(float(np.sqrt(np.mean(data**2))))
        axes[0,2].plot(ks,rms,"o-",color="#D55E00",label="RMS across draws")
        axes[0,2].set(xlabel="Retained modes K (count)",ylabel="Weighted complex-t error (dimensionless)",
                      title="KL truncation versus full covariance")
        modes=sorted({r["mode"] for r in convergence if r["study"]=="finite_difference_step"})
        for k in modes:
            rows=[r for r in convergence if r["study"]=="finite_difference_step" and r["mode"]==k]
            usable=[r for r in rows if r["max_complex_derivative_error"]>0]
            if usable:axes[1,0].loglog([r["step_mev_sqrt_nm"] for r in usable],
                 [r["max_complex_derivative_error"] for r in usable],"o-",label=f"mode {k+1}")
        axes[1,0].set(xlabel="Coefficient step (meV √nm)",ylabel="max |D_FD − D_implicit| ((meV √nm)⁻¹)",
                      title="Complex derivative truncation/cancellation")
        rows=[r for r in convergence if r["study"]=="sample_count"]
        n=[r["level"] for r in rows]
        axes[1,1].plot(n,[r["mean_loss"] for r in rows],"o-",color="#0072B2")
        axes[1,1].fill_between(n,[r["ci_low"] for r in rows],[r["ci_high"] for r in rows],alpha=.2,color="#0072B2")
        axes[1,1].set(xlabel="Independent diagnostic draws N (count)",ylabel="Mean raw loss (dimensionless)",
                      title="Nested sample counts; basic bootstrap interval")
        for regime in ("below","above"):
            rows=[r for r in convergence if r["study"]=="analytical_rectangle" and r.get("variant")==regime]
            if rows:axes[1,2].loglog([r["spacing_nm"] for r in rows],[r["max_complex_t_error"] for r in rows],"o-",label=regime+" barrier")
        axes[1,2].set(xlabel="Spatial spacing (nm)",ylabel="max |t_FD − t_continuum| (dimensionless)",
                      title="Independent rectangular-barrier reference")
        for ax in axes.flat:
            ax.grid(alpha=.2)
            if ax.get_legend_handles_labels()[0]:ax.legend(fontsize=7)
        fig.suptitle("Phaseward · numerical convergence diagnostics, separate from method findings\n"
                     "Configured fixed gates; independent diagnostic seeds; increasing N cannot repair discretization bias")
        save(fig,"numerical_convergence","Data: convergence.csv. Top: spatial complex-amplitude difference to the finest grid, "
             "quadrature probability difference to the densest energy grid, and paired truncation errors to full covariance. "
             "Bottom: central-difference error against implicit response, nested sample means with marginal basic-bootstrap intervals, "
             "and independent continuum barrier complex-amplitude errors. Zero reference differences are omitted from log axes, never replaced by invented positive values. "
             "These diagnostics apply to the first case's fixed gates, not all optimized devices; sample prefixes are statistically dependent.")
    _write_json(output/"figure_descriptions.json",descriptions)

