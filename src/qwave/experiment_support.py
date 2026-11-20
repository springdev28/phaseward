"""Experiment I/O and evaluation shared by suites and numerical diagnostics."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess
from time import perf_counter
from typing import Any

import numpy as np
from numpy.typing import NDArray

from qwave.experiments import _write_json
from qwave.optimization import OptimizationProblem
from qwave.wavepackets import DelaySearch, analyze_packet

METRICS = ("p_transmitted","raw_fidelity","aligned_fidelity","estimated_delay_ps","loss",
           "max_conservation_error","solver_seconds")


def invocation_git_identity() -> dict[str,Any]:
    """Record the caller checkout separately; it need not own an installed wheel."""
    result: dict[str,Any]={"commit":None,"working_tree_dirty":None,"available":False,
                          "scope":"invocation directory; installed code is identified separately by source hashes"}
    try:
        commit=subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True,timeout=3)
        status=subprocess.run(["git","status","--porcelain","--untracked-files=normal"],
                              capture_output=True,text=True,timeout=3)
        result.update(commit=commit.stdout.strip() if commit.returncode==0 else None,
                      working_tree_dirty=bool(status.stdout.strip()) if status.returncode==0 else None,
                      available=status.returncode==0)
    except (OSError,subprocess.TimeoutExpired):
        pass
    return result


def create_run_directory(path: str | Path, *, overwrite: bool) -> Path:
    """Only explicitly overwrite a suite-owned directory, never a parent or a symlink."""
    output=Path(path).absolute()
    if output.is_symlink() or any(parent.is_symlink() for parent in output.parents):
        raise ValueError("experiment output must not use a symlink")
    resolved=output.resolve()
    if resolved == Path.cwd().resolve() or resolved in Path.cwd().resolve().parents:
        raise ValueError("experiment output cannot be the workspace or an ancestor")
    if output.exists():
        if not overwrite:
            raise FileExistsError(f"{output} exists; choose a new directory or explicitly use --overwrite")
        marker=output/".qwave-run.json"
        if not marker.is_file() or marker.is_symlink() or (output/".git").exists():
            raise ValueError("--overwrite only replaces directories created by qwave experiment")
        if json.loads(marker.read_text()).get("owner") != "qwave experiment_suite":
            raise ValueError("unrecognized output-directory owner")
        shutil.rmtree(output)
    output.mkdir(parents=True,exist_ok=False)
    _write_json(output/".qwave-run.json",{"owner":"qwave experiment_suite","schema_version":1})
    return output


def write_table(path: Path, rows: list[dict[str,Any]]) -> None:
    """Union columns preserve failure-only fields; nested data remain JSON, not Python repr."""
    with path.open("w",newline="",encoding="utf-8") as stream:
        fields=list(dict.fromkeys(key for row in rows for key in row))
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        writer.writerows({k:json.dumps(v,sort_keys=True,allow_nan=False) if isinstance(v,(dict,list)) else v
                          for k,v in row.items()} for row in rows)


def draw_from_seeds(problem: OptimizationProblem, seeds: list[int]) -> tuple[NDArray,NDArray,NDArray]:
    """One recorded seed produces one KL vector; identical seeds pair all methods."""
    count=len(problem.device.modes.retained_eigenvalues)
    z=np.stack([np.random.Generator(np.random.PCG64(seed)).standard_normal(count) for seed in seeds])
    eta=z*np.sqrt(problem.device.modes.retained_eigenvalues)
    return z,eta,eta@problem.device.embedded_shapes.T


def packet_metrics(problem: OptimizationProblem, t: NDArray, delay: DelaySearch) -> dict[str,Any]:
    """Evaluate raw and bounded-delay fidelity, while keeping throughput independent."""
    analysis=analyze_packet(problem.device.energy_mev,problem.packet.amplitude,t,problem.target_t,delay=delay)
    values=analysis.summary()
    values["loss"]=problem.clean_loss(values)
    return values


def evaluate_design(problem: OptimizationProblem, u: NDArray, ensembles: dict[str,tuple[list[int],NDArray]],
                    *, delay: DelaySearch, identity: dict[str,Any]) -> tuple[dict[str,Any],list[dict[str,Any]],dict[str,NDArray]]:
    """Evaluate a frozen vector. Missing or failed solves remain explicit trial records."""
    started=perf_counter()
    cache=problem.cache()
    potential=problem.potential(u)
    arrays: dict[str,NDArray]={"u_mev":u.copy(),"potential_mev":potential}
    rows=[]
    sensitivity=None
    for partition,(seeds,draws) in {"clean":([None],np.zeros((1,len(potential)))),**ensembles}.items():
        t=np.full((len(draws),len(problem.device.energy_mev)),np.nan+1j*np.nan,dtype=complex)
        r=np.full_like(t,np.nan+1j*np.nan)
        conservation=np.full(t.shape,np.nan)
        valid=np.zeros(len(draws),dtype=bool)
        for index,(seed,draw) in enumerate(zip(seeds,draws)):
            row={**identity,"partition":partition,"trial_index":index,"seed":seed}
            begin=perf_counter()
            try:
                solved,response=cache.solve(potential+draw,response=partition=="clean")
                solve_time=perf_counter()-begin
                metrics_begin=perf_counter()
                values=packet_metrics(problem,solved.t,delay)
                row.update(values,solver_seconds=solve_time,analysis_seconds=perf_counter()-metrics_begin,
                           max_conservation_error=float(np.max(abs(solved.conservation_error))),
                           max_relative_residual=float(np.max(abs(solved.relative_residual))),status="ok",error=None)
                t[index],r[index],conservation[index]=solved.t,solved.r,solved.conservation_error
                valid[index]=True
                if response is not None:
                    raw,normalized,derivative=problem.sensitivity(response)
                    sensitivity={"J":raw,"J_per_mev2":normalized}
                    arrays["dt_deta"]=derivative
            except (ValueError,FloatingPointError,np.linalg.LinAlgError) as error:
                row.update({key:None for key in METRICS})
                row.update(status="failed",error=f"{type(error).__name__}: {error}",
                           solver_seconds=perf_counter()-begin,analysis_seconds=None)
            rows.append(row)
        arrays.update({partition+"_t":t,partition+"_r":r,partition+"_conservation_error":conservation,
                       partition+"_valid":valid})
    return {"sensitivity":sensitivity,"cost":{**cache.counters(),"wall_seconds":perf_counter()-started},
            "failed_trials":sum(row["status"]!="ok" for row in rows)},rows,arrays


def descriptive_statistics(rows: list[dict[str,Any]]) -> dict[str,Any]:
    """Describe all available draws with missing counts; never silently impute fidelities."""
    summary: dict[str,Any]={"samples":len(rows),"failed_trials":sum(row["status"]!="ok" for row in rows),
        "low_transmission_count":sum(bool(row.get("low_transmission")) for row in rows),
        "delay_boundary_count":sum(bool(row.get("alignment_boundary_hit")) for row in rows)}
    for metric in METRICS:
        data=np.array([row[metric] for row in rows if row.get(metric) is not None],dtype=float)
        summary[metric]={"defined_samples":len(data),"undefined_samples":len(rows)-len(data),
            "mean":float(np.mean(data)) if len(data) else None,
            "standard_deviation":float(np.std(data,ddof=1)) if len(data)>1 else None,
            "min":float(np.min(data)) if len(data) else None,
            "median":float(np.median(data)) if len(data) else None,
            "max":float(np.max(data)) if len(data) else None}
    return summary

