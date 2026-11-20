"""Optional localhost scientific control panel. Only this module imports Streamlit."""

from __future__ import annotations

from dataclasses import replace
import io
from pathlib import Path
from typing import Any

import numpy as np
import streamlit as st

from qwave.config import ConfigError
from qwave.gui_config import PreviewSettings, device_arrays, preview_model, preview_request
from qwave.gui_jobs import JobManager
from qwave.gui_results import ResultBundle, discover_results, json_bytes, load_bundle, strict_json

VIEWS = ("Device Builder", "Wave & Scattering Explorer", "Disorder Lab", "Optimization & Experiments")
HELP = {
    "energy":"Energy labels each stationary scattering state. The packet combines many energies coherently.",
    "bandwidth":"Standard deviation of the incoming energy probability density |A(E)|² before truncation. A is an amplitude, not a probability.",
    "sigma":"Requested standard deviation of the full disorder potential, in meV. Keeping only K modes discards variance; it is not restored.",
    "ell":"Spatial separation scale of the covariance kernel. Nearby potential values are correlated; this is not a mean free path.",
    "fidelity":"Squared normalized complex overlap with the declared target, conditional on transmission. A tiny transmitted component can still have high fidelity.",
    "transmission":"Integral of |A(E)|² |t(E)|² dE. An integral adds energy contributions with quadrature weights; it is a probability, not fidelity.",
    "derivative":"A derivative measures the local change in complex transmission per small change of a disorder-mode coefficient. Finite steps and roundoff must be checked.",
}


def _privacy_guard() -> bool:
    """Fail closed if launch flags override the repository's localhost/privacy defaults."""
    if st.get_option("browser.gatherUsageStats") or st.get_option("server.address") != "127.0.0.1":
        st.error("Start from the Phaseward folder with its .streamlit/config.toml. This panel requires telemetry off and server.address=127.0.0.1.")
        st.code("streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false")
        return False
    return True


def _draft_controls() -> PreviewSettings:
    """Persistent numerical controls; constructing these never launches a calculation."""
    with st.sidebar.expander("Import preview configuration"):
        uploaded = st.file_uploader("Exported preview JSON",type="json",key="preview_upload")
        if st.button("Apply preview configuration",disabled=uploaded is None,key="apply_preview"):
            from qwave.gui_worker import validate_request
            request = strict_json(uploaded.getvalue())
            validate_request(request)
            if request["scope"] != "illustrative_preview":
                raise ValueError("import experiment JSON in the experiments view")
            st.session_state["draft"] = PreviewSettings.from_mapping(request["preview_settings"])
            keys = ("length","energy","bandwidth","sigma","ell","nx","ne","mass","modes","kernel","seed","samples","reconstruct","time","coupling","gate_unit","gate_count")
            for key in list(st.session_state):
                if key in keys or key.startswith("gate_position_") or key.startswith("gate_meV_") or key.startswith("gate_mV_"):
                    del st.session_state[key]
            st.rerun()
    old = st.session_state.get("draft", PreviewSettings())
    with st.sidebar.expander("Preview parameters", expanded=True):
        length = st.slider("Channel length (nm)",20.,120.,float(old.length_nm),step=5.,key="length")
        energy = st.number_input("Central energy (meV)",min_value=5.,max_value=100.,value=float(old.central_energy_mev),step=1.,key="energy",help=HELP["energy"])
        bandwidth = st.number_input("Bandwidth σE (meV)",min_value=.5,max_value=15.,value=float(old.bandwidth_mev),step=.5,key="bandwidth",help=HELP["bandwidth"])
        sigma = st.number_input("Disorder σ (meV)",min_value=.1,max_value=10.,value=float(old.sigma_mev),step=.1,key="sigma",help=HELP["sigma"])
        ell = st.number_input("Correlation length ℓ (nm)",min_value=.5,max_value=30.,value=float(old.correlation_length_nm),step=.5,key="ell",help=HELP["ell"])
    with st.sidebar.expander("Resolution & reproducibility"):
        nx = st.selectbox("Spatial nodes",(81,161,321),index=(81,161,321).index(old.grid_points),key="nx")
        ne = st.selectbox("Energy nodes",(81,161,321),index=(81,161,321).index(old.energy_points),key="ne")
        mass = st.number_input("Effective mass / electron mass",.01,1.,float(old.effective_mass_ratio),.001,format="%.3f",key="mass",
                               help="0.067 is illustrative, not universal. The mass is constant in the channel and both leads.")
        k = st.number_input("Retained KL modes",1,16,old.retained_modes,key="modes",help="Covariance eigenmodes represent spatial patterns. Their retained eigenvalues set how much integrated variance survives truncation.")
        kernel = st.selectbox("Covariance kernel",("gaussian","exponential","matern32"),index=("gaussian","exponential","matern32").index(old.kernel),key="kernel")
        seed_text = st.text_input("Preview seed",str(old.seed),key="seed",help="Covariance uses this exact integer; the independent sensitivity validation uses seed + 1. These are not optimization seed partitions.")
        samples = st.number_input("Covariance samples",32,2048,old.covariance_samples,key="samples")
        reconstruct = st.checkbox("Reconstruct lead probability densities",old.reconstruct,key="reconstruct")
        time = st.number_input("Outgoing observation time (ps)",0.,3.,float(old.observation_time_ps),.1,key="time",
                               help="A snapshot of the right-going asymptotic lead component. This does not track a classical electron trajectory.")
    settings = replace(old,length_nm=length,central_energy_mev=energy,bandwidth_mev=bandwidth,sigma_mev=sigma,
        correlation_length_nm=ell,grid_points=nx,energy_points=ne,effective_mass_ratio=mass,retained_modes=int(k),
        kernel=kernel,seed=int(seed_text),covariance_samples=samples,reconstruct=reconstruct,observation_time_ps=time)
    st.session_state["draft"] = settings
    return settings


def _gate_controls(settings: PreviewSettings) -> PreviewSettings:
    """Edit energy coefficients or an explicitly declared illustrative voltage mapping."""
    left,right = st.columns([1,2])
    with left:
        count = st.number_input("Number of gates",1,8,len(settings.gate_values),key="gate_count")
    with right:
        unit = st.radio("Gate input",("meV","mV"),index=0 if settings.gate_input_unit=="meV" else 1,horizontal=True,key="gate_unit",
                        format_func=lambda v:"Potential energy (meV)" if v=="meV" else "Voltage with declared coupling (mV)")
    alpha = None
    if unit == "mV":
        st.info("Declare a signed mapping u = α × voltage. This is an illustrative assumption, not an electrostatic calibration.")
        alpha = st.number_input("Signed coupling α (meV/mV)",value=float(settings.coupling_mev_per_mv or 0.),step=.1,key="coupling")
    else:
        st.caption("Gate strengths are potential energies. Electrode voltage is undefined until a coupling is supplied. Bounds: each |u| ≤ 25 meV; |Σuⱼgⱼ(x)| ≤ 60 meV.")
    positions, values = [], []
    columns = st.columns(min(count,4))
    for j in range(count):
        with columns[j%len(columns)]:
            st.markdown(f"**Gate {j+1}**")
            initial_position = settings.gate_fractions[j] if j < len(settings.gate_fractions) else 0.
            positions.append(st.slider(f"Center / length · {j+1}",-.45,.45,float(initial_position),step=.01,key=f"gate_position_{j}"))
            initial_value = settings.gate_values[j] if j < len(settings.gate_values) and unit==settings.gate_input_unit else 0.
            limit = 25. if unit=="meV" else 1000.
            values.append(st.number_input(f"Strength ({unit}) · {j+1}",-limit,limit,float(initial_value),step=1.,key=f"gate_{unit}_{j}"))
    updated = replace(settings,gate_values=tuple(values),gate_fractions=tuple(positions),gate_input_unit=unit,coupling_mev_per_mv=alpha)
    st.session_state["draft"] = updated
    return updated


def _adopt(manager: JobManager, path: Path, *, cached: bool = False) -> None:
    """Keep a result's own frozen configuration separate from the current draft."""
    bundle = load_bundle(path,manager.results_root)
    st.session_state["last_"+bundle.manifest["operation"]] = bundle
    st.session_state["last_job_message"] = ("Reused exact preview cache; original timestamp and manifest retained. " if cached else "Local run finished. ")+str(path)


def _run_button(label: str, request: dict[str,Any], manager: JobManager, *, disabled: bool = False) -> None:
    """The only UI path that starts scientific computations."""
    busy = manager.active is not None and manager.active.poll()["status"] in ("running","cancelling")
    reuse = True
    if request["scope"] == "illustrative_preview":
        reuse = st.checkbox("Reuse an identical completed preview",value=True,key="reuse_"+request["operation"],
                            help="Exact configuration, seed, source and runtime must match. Uncheck to request a fresh computation in a new folder.")
    if st.button(label,type="primary",disabled=disabled or busy,key="run_"+request["operation"]):
        _, cached = manager.start(request,reuse_preview=reuse)
        if cached is not None:
            _adopt(manager,cached,cached=True)
        st.rerun()


@st.fragment(run_every=1)
def _progress(manager: JobManager) -> None:
    """Poll an owned worker with real stage logs; cancellation leaves partial artifacts."""
    if manager.active is None:
        return
    try:
        state = manager.poll()
    except (ValueError,OSError) as error:
        st.session_state["last_job_message"] = f"Worker ended, but its result could not be opened: {error}. Folder: {manager.active.directory}"
        manager.active = None
        st.rerun()
    if state["status"] in ("running","cancelling"):
        with st.status(f"Local CPU · {state['status']} · {state['elapsed_seconds']:.0f} s",expanded=True):
            lines = state["log_tail"].splitlines()
            st.text("\n".join(lines[-4:]) or "Worker is starting…")
            st.caption("Progress shows completed stages, not an estimated percentage. One worker and one BLAS thread are active.")
            if st.button("Cancel current run",disabled=state["status"]=="cancelling",key="cancel_run"):
                manager.active.cancel()
                st.rerun()
        return
    if state["status"] == "completed":
        _adopt(manager,Path(state["output"]))
    else:
        st.session_state["last_job_message"] = f"Run {state['status']}. Partial files retained: {state['output']}"
        st.session_state["last_failure_log"] = state["log_tail"]
    manager.active = None
    st.rerun()


def _find(bundle: ResultBundle, name: str, group: str | None = None) -> str | None:
    matches = [p for p in bundle.files if (p == name or p.endswith('/'+name)) and (group is None or p.startswith(group+'/'))]
    return matches[0] if matches else None


def _gallery(bundle: ResultBundle, names: list[str], *, key: str) -> None:
    if not names:
        st.info("This run has no saved figure for this view. Open the data inspector to see the available artifacts.")
        return
    selected = st.selectbox("Saved figure",names,format_func=lambda n:Path(n).stem.replace('_',' ').title(),key="figure_"+key+bundle.fingerprint[:8])
    st.image(bundle.read(selected),width="stretch")
    st.caption(f"Recorded figure: {selected}. Displayed from saved bytes; no numerical calculation was rerun.")
    descriptions = [n for n in bundle.files if n.endswith("figure_descriptions.json")]
    for file in descriptions:
        if Path(file).parent == Path(selected).parent:
            with st.expander("Figure description"):
                st.json(bundle.json(file))


def _metrics(bundle: ResultBundle) -> None:
    name = _find(bundle,"metrics.json","packet")
    if name is None and bundle.manifest.get("config",{}).get("experiment") == "wave_packet":
        name = _find(bundle,"metrics.json")
    if name is None:
        return
    metrics = bundle.json(name)
    columns = st.columns(4)
    for column,label,field,help_text in zip(columns,
        ("Transmitted probability","Raw conditional fidelity","Delay-aligned fidelity","Estimated delay (ps)"),
        ("p_transmitted","raw_fidelity","aligned_fidelity","estimated_delay_ps"),
        (HELP["transmission"],HELP["fidelity"],"Fidelity after the declared bounded delay search; raw fidelity is retained.","Positive means the outgoing state lags its target. Boundary hits require caution.")):
        value = metrics.get(field)
        column.metric(label,"undefined" if value is None else f"{value:.5g}",help=help_text)
    if metrics.get("low_transmission") or metrics.get("low_reference_transmission"):
        st.warning("Low throughput: conditional fidelity alone does not establish useful transport.")
    if metrics.get("alignment_boundary_hit"):
        st.warning("The best delay reaches a search boundary. Alignment is limited by the declared interval.")
    with st.expander("Conservation, quadrature, delay and spatial-window diagnostics"):
        st.json(metrics)
    recon = metrics.get("diagnostics",{}).get("reconstruction",{})
    for label, data in recon.items():
        if isinstance(data,dict) and data.get("coarse_fine_density_l1_difference",0) > .05:
            st.warning(f"{label}: coarse/fine position-density difference exceeds the panel's 0.05 display warning. Inspect/refine the energy grid; this threshold is not a physical law.")


def _exports(bundle: ResultBundle) -> None:
    """Export actual recorded config and data, never the unrelated current slider draft."""
    with st.expander("Export & inspect this result"):
        st.caption(str(bundle.root))
        columns = st.columns(2)
        config_name = _find(bundle,"config.json")
        columns[0].download_button("Result configuration",bundle.read(config_name) if config_name else json_bytes(bundle.manifest["config"]),
                                   file_name="phaseward-config.json",mime="application/json",key="cfg_"+bundle.fingerprint)
        columns[1].download_button("Self-contained manifest",bundle.read("manifest.json"),file_name="manifest.json",mime="application/json",key="manifest_"+bundle.fingerprint)
        st.caption("The complete bundle includes every original file and hash. Data-only and plot-only ZIPs are subsets of that inventory.")
        if st.button("Prepare data, plots & complete ZIP",key="zip_"+bundle.fingerprint):
            st.session_state["exports_"+bundle.fingerprint] = {category:bundle.archive(category) for category in ("data","plots","all")}
        archives = st.session_state.get("exports_"+bundle.fingerprint,{})
        for col,(category,data) in zip(st.columns(3),archives.items()):
            col.download_button({"data":"Underlying data","plots":"Plots (PNG / SVG / PDF)","all":"Complete run"}[category],data,
                                file_name=f"phaseward-{category}.zip",mime="application/zip",key="download_"+category+bundle.fingerprint)
        chosen = st.selectbox("Data inspector",["Select an artifact",*[n for n in bundle.files if Path(n).suffix in (".json",".csv",".md")]],key="inspect_"+bundle.fingerprint)
        if chosen != "Select an artifact":
            raw = bundle.read(chosen)
            if chosen.endswith(".json"):
                st.json(strict_json(raw),expanded=False)
            elif chosen.endswith(".csv"):
                import pandas as pd
                st.dataframe(pd.read_csv(io.BytesIO(raw)),hide_index=True,width="stretch")
            else:
                st.code(raw.decode(),language=None)


def _saved_device(bundle: ResultBundle) -> None:
    names = [n for n in bundle.files if Path(n).stem in ("device","gates") and n.endswith('.png')]
    if names:
        _gallery(bundle,names,key="device")
        return
    # Suites save every initial gate array, even though their standard figures focus on comparisons.
    name = _find(bundle,"arrays.npz")
    if name:
        arrays = bundle.arrays(name)
        choices = [n for n in arrays if n.endswith("gate_contributions_mev")]
        if choices:
            selected = st.selectbox("Saved initial device",choices,key="saved_device_"+bundle.fingerprint)
            prefix = selected.removesuffix("gate_contributions_mev")
            x = arrays[prefix+"x_nm"]
            contributions = arrays[selected]
            from qwave.gui_visuals import device_figure
            channel_x = arrays[prefix+"channel_x_nm"]
            # Sum recorded gate contributions only; no field solve or gate resampling.
            fig = device_figure({"x_nm":x,"gate_contributions_mev":contributions,"potential_mev":contributions.sum(axis=1)},
                                {"x_min_nm":channel_x[0],"x_max_nm":channel_x[-1]})
            st.pyplot(fig,width="stretch")
            st.caption("Recorded initial gate contributions. Frozen optimized amplitudes and constraints are in Optimization & Experiments.")
            return
    st.info("This result does not contain a saved gate decomposition.")


def _saved_amplitudes(bundle: ResultBundle) -> None:
    """Display stored complex scattering arrays; do not call the scattering solver."""
    name = _find(bundle,"arrays.npz")
    if name is None:
        return
    arrays = bundle.arrays(name)
    candidates = [n for n in arrays if n.endswith("_evaluation_clean_t") and n[:-1]+"r" in arrays]
    if not candidates:
        st.info("No saved packet/scattering figure in this result. Raw artifact exports remain available.")
        return
    selected = st.selectbox("Frozen clean design",candidates,key="amplitude_"+bundle.fingerprint)
    energy_names = [n for n in arrays if n.endswith("_energy_mev") and selected.startswith(n.removesuffix("_energy_mev"))]
    energy = arrays[max(energy_names,key=len)]
    t,r = arrays[selected],arrays[selected[:-1]+"r"]
    # Suite evaluation stores a one-row clean ensemble, unlike scalar-spectrum runs.
    if t.shape == (1,len(energy)) and r.shape == t.shape:
        t,r = t[0],r[0]
    if t.shape != energy.shape or r.shape != energy.shape:
        raise ValueError("unsupported saved clean-spectrum dimensions; inspect the raw arrays")
    if not np.isfinite(t).all() or not np.isfinite(r).all():
        st.warning("This saved clean solve is invalid. Its failed trial and raw arrays remain available in the data inspector.")
        return
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from qwave.scattering import transmission_phase
    fig = Figure(figsize=(10,3.4),layout="constrained")
    FigureCanvasAgg(fig)
    probabilities,phase = fig.subplots(1,2)
    probabilities.plot(energy,abs(t)**2,label="T(E)")
    probabilities.plot(energy,abs(r)**2,label="R(E)")
    probabilities.set(xlabel="Energy (meV)",ylabel="Probability")
    probabilities.legend()
    phase.plot(energy,transmission_phase(t))
    phase.set(xlabel="Energy (meV)",ylabel="Unwrapped arg[t] (rad)")
    st.pyplot(fig,width="stretch")
    st.caption("Unit-flux amplitudes; phase is referenced to the saved left/right grid endpoints and retains free propagation. No position-density reconstruction is stored in this suite. Packet metrics are in the saved trial table.")


def _experiment_results(bundle: ResultBundle) -> None:
    summary_file = _find(bundle,"summary.json")
    if summary_file:
        summary = bundle.json(summary_file)
        runs = summary.get("runs",[])
        if runs:
            rows = []
            for run in runs:
                candidate = run.get("reported_candidate") or {}
                rows.append({"case":run.get("case"),"method":run.get("method"),"feasible":candidate.get("feasible",False),
                    "objective (method-specific)":candidate.get("objective"),
                    "clean P":candidate.get("p_transmitted"),"clean raw F":candidate.get("raw_fidelity"),
                    "minimum scaled residual":candidate.get("minimum_scaled_residual"),
                    "search work":run.get("cost",{}).get("forward_work"),"status":run.get("status")})
            st.dataframe(rows,hide_index=True,width="stretch")
            st.caption("Objectives differ between methods and are not directly comparable. Use common held-out metrics and paired effect intervals for comparisons; nonnegative constraint residuals indicate feasibility.")
            selected = st.selectbox("Frozen candidate details",range(len(runs)),format_func=lambda i:runs[i].get("run_id",str(i)),key="run_detail_"+bundle.fingerprint)
            with st.expander("Objective, constraints, feasibility, costs and held-out metrics"):
                st.json(runs[selected],expanded=False)
        if summary.get("checks"):
            st.write("Recorded checks",summary["checks"])
    names = [n for n in bundle.files if n.endswith('.png') and any(word in n for word in ("distribution","paired","cost","convergence","pareto","tradeoff"))]
    _gallery(bundle,names,key="experiments")
    report_file = _find(bundle,"report.md")
    if report_file:
        with st.expander("Automated scientific report"):
            st.text(bundle.read(report_file).decode())
    trials = _find(bundle,"trials.csv")
    if trials:
        with st.expander("All trial-level results — including failed and held-out trials"):
            import pandas as pd
            st.dataframe(pd.read_csv(io.BytesIO(bundle.read(trials))),hide_index=True,width="stretch")
    st.caption("Comparisons are conditional on this model and frozen design. Replaying the same seeds is not independent replication. Convergence diagnostics are separate from physical findings.")


def _saved_disorder(bundle: ResultBundle) -> None:
    """Plot stored suite covariance, modes and frozen evaluation draws without sampling."""
    name = _find(bundle,"arrays.npz")
    if name is None:
        st.info("No saved disorder arrays in this run.")
        return
    arrays = bundle.arrays(name)
    choices = [n for n in arrays if n.endswith("_covariance_mev2") and not n.endswith("_kl_covariance_mev2")]
    if not choices:
        st.info("This run has no stored disorder covariance decomposition.")
        return
    selected = st.selectbox("Saved covariance case",choices,key="covariance_case_"+bundle.fingerprint)
    prefix = selected.removesuffix("covariance_mev2")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig = Figure(figsize=(10,6.4),layout="constrained")
    FigureCanvasAgg(fig)
    covariance,modes,eigenvalues,samples = fig.subplots(2,2).ravel()
    x = arrays[prefix+"channel_x_nm"]
    mesh = covariance.imshow(arrays[selected],origin="lower",extent=(x[0],x[-1],x[0],x[-1]),aspect="auto")
    fig.colorbar(mesh,ax=covariance,label="Covariance (meV²)")
    covariance.set(xlabel="Position (nm)",ylabel="Position (nm)",title="Recorded target covariance")
    phi = arrays[prefix+"all_phi_per_sqrt_nm"]
    k = arrays[prefix+"retained_phi_per_sqrt_nm"].shape[1]
    for j in range(min(k,4)):
        modes.plot(x,phi[:,j],label=f"Mode {j+1}")
    modes.set(xlabel="Position (nm)",ylabel="Shape φ (nm⁻¹ᐟ²)",title="Spatially normalized modes")
    modes.legend(fontsize=8)
    lam = arrays[prefix+"eigenvalues_mev2_nm"]
    indices = np.arange(1,len(lam)+1)
    eigenvalues.semilogy(indices[lam>0],lam[lam>0])
    eigenvalues.axvline(k,linestyle="--",color="#087E8B",label=f"Retained K={k}")
    eigenvalues.set(xlabel="Mode index",ylabel="λ (meV² nm)",title="Saved covariance eigenvalues")
    eigenvalues.legend(fontsize=8)
    draw_key = prefix+"heldout_potential_mev"
    if draw_key in arrays:
        for i,row in enumerate(arrays[draw_key][:5]):
            samples.plot(arrays[prefix+"x_nm"],row,label=f"Draw {i}")
    samples.set(xlabel="Position (nm)",ylabel="Disorder potential (meV)",title="First saved held-out K-mode draws")
    st.pyplot(fig,width="stretch")
    st.caption("Only saved arrays are displayed. Draws are fixed evaluation data, not new samples. Var(η)=λ; no discarded variance is restored.")
    derivatives = [n for n in arrays if n.startswith(prefix) and n.endswith("_evaluation_dt_deta")]
    if derivatives:
        key = st.selectbox("Frozen-design complex sensitivity",derivatives,key="saved_derivative_"+bundle.fingerprint)
        energy = arrays[prefix+"energy_mev"]
        fig = Figure(figsize=(9,3.5),layout="constrained")
        FigureCanvasAgg(fig)
        axis = fig.subplots()
        mesh = axis.pcolormesh(energy,np.arange(1,arrays[key].shape[1]+1),abs(arrays[key]).T,shading="nearest")
        fig.colorbar(mesh,ax=axis,label="|∂t/∂η| (meV⁻¹ nm⁻¹ᐟ²)")
        axis.set(xlabel="Energy (meV)",ylabel="Mode index",title="Magnitude of the saved complex derivative")
        st.pyplot(fig,width="stretch")


def _render_result(bundle: ResultBundle, view: str, current_request: dict | None = None) -> None:
    """Render only recorded data, with status and provenance visible before metrics."""
    st.divider()
    scope = bundle.manifest.get("scope", "saved_pipeline_run")
    st.markdown(f"**Recorded result · {scope.replace('_',' ')}**")
    st.caption(f"{bundle.manifest.get('created_utc','UTC time not recorded')} · {bundle.status}")
    if bundle.status not in ("completed","legacy_completed_check_metrics"):
        st.warning(f"Recorded status: {bundle.status}. Inspect failed checks or partial data before interpreting this run.")
    if current_request is not None and json_bytes(current_request) != json_bytes(bundle.manifest.get("config",{})):
        st.warning("Settings changed since this result. The figures and metrics below still use the recorded configuration; press Run to calculate the new draft.")
    if view == VIEWS[0]:
        _saved_device(bundle)
    elif view == VIEWS[1]:
        _metrics(bundle)
        names = [n for n in bundle.files if n.endswith('.png') and any(word in Path(n).stem for word in ("scattering","packet"))]
        if names:
            names.sort(key=lambda n:("position" not in n,n))
            _gallery(bundle,names,key="wave")
        else:
            _saved_amplitudes(bundle)
        st.caption("|Ψ(x,t)|² is probability density (1/nm), not a path. Lead reconstructions use the discrete group velocity/Jacobian and are not renormalized to the visible window.")
    elif view == VIEWS[2]:
        names = [n for n in bundle.files if n.endswith('.png') and any(word in Path(n).stem for word in ("sample","covariance","sensitivity","derivative","linearization","step"))]
        if names:
            _gallery(bundle,names,key="disorder")
        else:
            _saved_disorder(bundle)
        for group in ("disorder","sensitivity"):
            name = _find(bundle,"metrics.json",group)
            if name:
                with st.expander(group.title()+" diagnostics: variance, steps and errors"):
                    st.json(bundle.json(name),expanded=False)
    else:
        _experiment_results(bundle)
    _exports(bundle)


def _experiment_controls(settings: PreviewSettings, manager: JobManager) -> dict | None:
    """Presets stay unchanged unless explicitly starting a separate custom design."""
    from qwave.experiment_config import ExperimentConfig, PRESETS, preset_config
    st.info("Saved research runs use the declared suite configuration below. Preview sliders apply only when you explicitly select a custom preview-device suite.")
    preset = st.selectbox("Experiment preset",PRESETS,key="preset")
    research = st.checkbox("Use the slower research profile",key="research",help="Opt-in only. More starts, disorder draws and finer grids can occupy the laptop CPU substantially longer.")
    uploaded = st.file_uploader("Or import a prespecified experiment JSON",type="json",key="experiment_upload",help="Local file only. The strict library validator rejects unknown fields and overlapping seed partitions.")
    config = ExperimentConfig.from_mapping(strict_json(uploaded.getvalue())) if uploaded else preset_config(preset,research=research)
    custom = st.checkbox("Use preview device in a new custom suite",disabled=uploaded is not None,key="custom_suite")
    if custom and uploaded is None:
        root = int(st.text_input("New suite seed root (six separate roles)","610001",key="suite_seed"))
        if not 0 <= root <= 2**64-6:
            raise ValueError("suite seed root must be in [0,2**64-6]")
        data = config.to_dict()
        data["optimization"]["model"] = preview_model(settings).to_dict()
        data["optimization"]["packet"] = {"central_energy_mev":settings.central_energy_mev,"bandwidth_mev":settings.bandwidth_mev}
        data["optimization"]["optimizer"]["initialization_seed"] = root
        for i,role in enumerate(("training","validation","heldout"),1):
            data["optimization"]["ensembles"][role+"_seed"] = root+i
        data["convergence"]["seed"], data["statistics"]["bootstrap_seed"] = root+4, root+5
        config = ExperimentConfig.from_mapping(data)
        st.caption("This is a new user-defined design. Preset case overrides and convergence levels remain explicit in the resolved configuration. Do not tune the final distribution after viewing held-out results.")
    if config.resource_profile == "research" and not research:
        st.warning("This imported configuration requests the research profile. Check the explicit research opt-in to enable Run.")
    opt = config.optimization
    s = opt["model"]["scattering"]
    st.caption(f"CPU cost: {len(config.cases)} case(s); {s['grid_points']} spatial × {s['energy_points']} energy nodes; {opt['optimizer']['starts']} starts; search cap {opt['optimizer']['forward_work_budget']} work units per method/floor. Preflight, postflight and evaluation cost extra. Covariance decomposition grows roughly cubically with channel nodes.")
    st.write("Disorder samples per method",{r:opt["ensembles"][r+"_samples"] for r in ("training","validation","heldout")})
    with st.expander("Review exact design, constraints, budgets and seed partitions"):
        st.json(config.to_dict(),expanded=False)
        st.json(config.seed_registry(),expanded=False)
    st.download_button("Export active experiment configuration",json_bytes(config.to_dict()),file_name="experiment.json",mime="application/json")
    request = {"schema_version":1,"scope":"saved_research_run","operation":"experiment","experiment":config.to_dict(),"allow_research":research}
    _run_button("Run experiment suite",request,manager,disabled=config.resource_profile=="research" and not research)
    return request


def main(workspace: Path) -> None:
    """Render the four views and wire explicit actions to local workers."""
    st.set_page_config(page_title="Phaseward · local quantum transport",page_icon="∿",layout="wide",initial_sidebar_state="expanded")
    if not _privacy_guard():
        return
    st.markdown("""<style>
      .block-container {padding-top:2rem; max-width:1240px; padding-bottom:3rem;}
      h1 {letter-spacing:-.04em; font-weight:750;} h2,h3 {letter-spacing:-.02em;}
      [data-testid='stMetricValue'] {font-size:1.65rem;}
      [data-testid='stSidebar'] {border-right:1px solid #dce4ed;}
      .eyebrow {color:#087e8b;font-size:.76rem;letter-spacing:.16em;font-weight:700;}
      </style>""",unsafe_allow_html=True)
    st.sidebar.markdown("## ∿ Phaseward")
    st.sidebar.caption("LOCAL QUANTUM TRANSPORT")
    view = st.sidebar.radio("Workspace",VIEWS,key="view",label_visibility="collapsed")
    mode = st.sidebar.radio("Data source",("Illustrative previews","Open saved results"),key="data_source")
    results_root = workspace/"results"
    if "job_manager" not in st.session_state:
        st.session_state["job_manager"] = JobManager(results_root)
    manager = st.session_state["job_manager"]
    st.markdown('<div class="eyebrow">PHASEWARD / SCIENTIFIC CONTROL PANEL</div>',unsafe_allow_html=True)
    st.title(view)
    st.caption("Local CPU · idealized coherent 1D model · no accounts or external APIs")
    _progress(manager)
    if st.session_state.get("last_job_message"):
        st.caption(st.session_state["last_job_message"])
    if st.session_state.get("last_failure_log"):
        with st.expander("Last failed or cancelled worker log"):
            st.code(st.session_state["last_failure_log"],language=None)
    try:
        if mode == "Open saved results":
            choices = discover_results(results_root)
            if not choices:
                st.info("No manifests found in results/. Run a preview or a CLI experiment first.")
                return
            selected = st.sidebar.selectbox("Result folder",choices,format_func=lambda p:str(p.relative_to(results_root)),key="saved_folder")
            if st.sidebar.button("Open result",type="primary",key="open_result"):
                st.session_state["opened_result"] = load_bundle(selected,results_root)
            bundle = st.session_state.get("opened_result")
            st.info("Read-only saved results. Opening a bundle verifies its hashes and displays its recorded data; it does not launch a calculation.")
            if bundle:
                if bundle.root != selected:
                    st.caption("The selected folder is not open yet. Below is the previously opened result.")
                _render_result(bundle,view)
            return
        settings = _draft_controls()
        st.markdown("**Illustrative preview settings**" if view != VIEWS[3] else "**Prespecified experiments**")
        if view == VIEWS[0]:
            st.write("Build a finite gated channel between uniform ideal leads. The live drawing samples your potential; it does not solve transport.")
            settings = _gate_controls(settings)
            model = preview_model(settings)
            from qwave.gui_visuals import device_figure
            fig = device_figure(device_arrays(model),model.channel,settings)
            st.pyplot(fig,width="stretch")
            st.dataframe([{"Gate":j+1,"Center (nm)":p*settings.length_nm,"Energy (meV)":u,
                           "Voltage (mV)":settings.gate_values[j] if settings.gate_input_unit=="mV" else None}
                          for j,(p,u) in enumerate(zip(settings.gate_fractions,settings.amplitudes_mev))],hide_index=True,width="stretch")
            request = preview_request(settings,"device")
            _run_button("Save device preview",request,manager)
            operation = "device"
        elif view == VIEWS[1]:
            st.write("Inspect complex scattering and a normalized energy packet. The target is the clean free channel with the same leads and phase planes.")
            st.caption("Transmission is unconditional; fidelity is conditional on the transmitted state. Global phase cancels from fidelity. Delay alignment is bounded to [−0.1, +0.1] ps.")
            request = preview_request(settings,"wave")
            st.caption(f"CPU work: {settings.grid_points} × {settings.energy_points} stationary grids, a reference solve, and up to {3*1201*settings.energy_points:,} position–energy terms. Resolution changes take effect only on Run.")
            _run_button("Run wave & scattering",request,manager)
            operation = "wave"
        elif view == VIEWS[2]:
            st.write("Explore spatially correlated disorder, retained covariance modes and the derivative of complex transmission.")
            st.caption("ΦᵀWΦ = I; ηₖ = √λₖ zₖ; Var(ηₖ) = λₖ. Eigenvalue scaling is in η, not in Φ. Full and retained covariance samples are paired.")
            st.markdown("Complex sensitivity",help=HELP["derivative"])
            request = preview_request(settings,"disorder")
            st.caption(f"CPU work: dense covariance decomposition, {settings.covariance_samples} draws, {settings.retained_modes} modes, four derivative steps and full-solve checks at three disorder scales. Larger grids and sample sets cost more CPU/memory.")
            _run_button("Run disorder & sensitivity",request,manager)
            operation = "disorder"
        else:
            request = _experiment_controls(settings,manager)
            operation = "experiment"
        if view != VIEWS[3]:
            with st.expander("Active configuration & physical conventions"):
                st.download_button("Export active configuration",json_bytes(request),file_name="phaseward-preview.json",mime="application/json")
                st.json(request,expanded=False)
                st.caption("Finite energy window and grid are recorded explicitly. Semi-infinite discrete leads, constant effective mass, real potentials and unit-flux amplitudes. A preview is not a convergence-certified research result.")
        bundle = st.session_state.get("last_"+operation)
        if bundle:
            _render_result(bundle,view,request)
        else:
            st.info("No result for this view yet. Adjust the settings, then use Run or open an existing result.")
    except (ValueError,TypeError,KeyError,OSError) as error:
        st.error(f"Configuration or result could not be used: {error}")
        st.caption("No replacement physics or inferred parameters were substituted. Correct the settings or select an intact results folder.")
    st.sidebar.divider()
    st.sidebar.caption(f"CPU only • localhost:{st.get_option('server.port')}\n\nThe CLI remains the reproducible research pipeline. Stop the local server with Ctrl+C in Terminal.")
