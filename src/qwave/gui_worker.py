"""Local worker entrypoint. Reuse tested pipeline functions; never import Streamlit."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from time import perf_counter
import traceback
from typing import Any

from qwave.config import DisorderConfig, PacketConfig, ScatterConfig, SensitivityConfig
from qwave.diagnostics import cpu_environment, software_versions
from qwave.gui_config import PreviewSettings, device_arrays, preview_model, preview_request
from qwave.gui_results import json_bytes, strict_json
from qwave.provenance import sha256_file, source_identity


def validate_request(request: dict[str, Any]) -> None:
    """Revalidate both the user settings and every resolved scientific input."""
    if not isinstance(request, dict) or request.get("schema_version") != 1:
        raise ValueError("unsupported panel request schema")
    if request.get("operation") == "experiment":
        from qwave.experiment_config import ExperimentConfig
        if set(request) != {"schema_version","scope","operation","experiment","allow_research"}:
            raise ValueError("unexpected experiment request fields")
        config = ExperimentConfig.from_mapping(request["experiment"])
        if request["scope"] != "saved_research_run" or type(request["allow_research"]) is not bool:
            raise ValueError("invalid experiment scope or research consent")
        if config.resource_profile == "research" and not request["allow_research"]:
            raise ValueError("research profile requires an explicit opt-in")
    else:
        settings = PreviewSettings.from_mapping(request["preview_settings"])
        expected = preview_request(settings, request["operation"])
        if json_bytes(expected) != json_bytes(request):
            raise ValueError("resolved preview inputs differ from the declared settings")


def save_device(settings: PreviewSettings, output: Path) -> None:
    """Export sampled gate geometry only; this operation is not a transport result."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    from qwave.gui_visuals import device_figure

    output.mkdir()
    model = preview_model(settings)
    arrays = device_arrays(model)
    np.savez_compressed(output/"arrays.npz", **arrays)
    np.savetxt(output/"potential.csv", np.column_stack((arrays["x_nm"],arrays["potential_mev"],
                  arrays["gate_contributions_mev"])), delimiter=",", comments="",
               header="x_nm,V_mev,"+",".join(f"gate_{j+1}_mev" for j in range(len(settings.gate_values))))
    figure = device_figure(arrays, model.channel, settings)
    for extension in ("png","svg","pdf"):
        figure.savefig(output/f"device.{extension}", dpi=170, bbox_inches="tight")
    (output/"figure_descriptions.json").write_bytes(json_bytes({"device":
        "Sampled gate contributions and total real potential energy. No scattering or electron trajectory is computed."}))


def execute(request_file: Path) -> int:
    """Run once in a new directory, preserve partial failures, and write a manifest last."""
    envelope = strict_json(request_file.read_bytes())
    request = envelope["request"]
    validate_request(request)
    output = request_file.parent/"result"
    output.mkdir(exist_ok=False)
    started = perf_counter()
    identity = source_identity()
    status, error = "completed", None
    (output/"config.json").write_bytes(json_bytes(request))
    print(f"Starting {request['operation']} · {request['scope']} · local CPU, one BLAS thread", flush=True)
    try:
        if identity["sha256"] != envelope["runtime"]["source"]["sha256"]:
            raise RuntimeError("source changed after Run; submit a new run with the current code")
        if request["operation"] == "device":
            print("Sampling bounded gate contributions and saving geometry", flush=True)
            save_device(PreviewSettings.from_mapping(request["preview_settings"]), output/"device")
        elif request["operation"] == "wave":
            from qwave.experiments import run_scatter
            from qwave.packet_experiments import run_packet
            config = PacketConfig.from_mapping(request["packet"])
            print("Solving complex stationary amplitudes and conservation diagnostics", flush=True)
            run_scatter(ScatterConfig.from_mapping(config.scattering), output/"scattering")
            print("Integrating packet states, bounded delay alignment and lead reconstruction", flush=True)
            run_packet(config, output/"packet")
        elif request["operation"] == "disorder":
            from qwave.disorder_experiments import run_disorder, run_sensitivity
            print("Sampling full and truncated covariance; checking empirical variance and correlation", flush=True)
            run_disorder(DisorderConfig.from_mapping(request["disorder"]), output/"disorder")
            print("Differentiating complex t; checking steps and first-order errors against full solves", flush=True)
            run_sensitivity(SensitivityConfig.from_mapping(request["sensitivity"]), output/"sensitivity")
        else:
            from qwave.experiment_config import ExperimentConfig
            from qwave.experiment_runner import run_experiment
            run_experiment(ExperimentConfig.from_mapping(request["experiment"]), output/"experiment",
                           allow_research=request["allow_research"], progress=lambda s:print(str(s),flush=True))
            status = strict_json((output/"experiment"/"manifest.json").read_bytes())["status"]
        if source_identity()["sha256"] != identity["sha256"]:
            raise RuntimeError("source changed during computation; this run cannot establish reproducibility")
    except BaseException as exc:
        status = "cancelled" if isinstance(exc, KeyboardInterrupt) else "failed"
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
        (output/"failure.json").write_bytes(json_bytes({"status":status,"error":error}))
    components = {p.parent.name:strict_json(p.read_bytes()) for p in sorted(output.glob("*/manifest.json"))}
    checks = {}
    for component, manifest in components.items():
        for group in (manifest.get("metrics",{}),manifest.get("diagnostics",{})):
            for name in ("conservation_passed","sampling_checks_passed"):
                if name in group:
                    checks[component+"."+name] = group[name]
    if status == "completed" and any(value is False for value in checks.values()):
        status = "completed_with_failed_checks"
    metadata = {"manifest_version":3,"project":"Phaseward","stage":"PROMPT 6 local panel",
        "created_utc":datetime.now(timezone.utc).isoformat(),"status":status,"scope":request["scope"],
        "operation":request["operation"],"config":request,"cache_key":envelope["cache_key"],
        "source":identity,"software_versions":envelope["runtime"]["versions"],
        "environment":cpu_environment(),"worker_threads":1,"components":components,
        "elapsed_seconds":perf_counter()-started,"error":error,"component_checks":checks,
        "units":{"position":"nm","energy":"meV","time":"ps","density":"nm^-1"},
        "scope_note":"Preview runs are illustrative. Research suites preserve their prespecified design and checks. Neither is a laboratory observation.",
        "approximations":{"solver":"Same finite-difference Hamiltonian and exact discrete leads as CLI; no GUI physics solver",
            "gates":"Sampled peak normalization; ideal leads fixed. Optional u(meV)=alpha(meV/mV)*voltage(mV) is an explicit illustrative mapping, not calibration.",
            "packet":"Energy-normalized spectral state; exact discrete velocity/Jacobian. Asymptotic lead components only, no display renormalization or classical trajectory.",
            "covariance":"Phi.T W Phi=I; Var(eta)=lambda; retained KL modes are not rescaled.",
            "details":"Complete component manifests below retain equations, seeds, bounds, numerical checks and original data hashes."},
        "outputs":{p.relative_to(output).as_posix():{"sha256":sha256_file(p),"size_bytes":p.stat().st_size}
                   for p in sorted(output.rglob("*")) if p.is_file()}}
    (output/"manifest.json").write_bytes(json_bytes(metadata))
    print(f"{status}: {output}", flush=True)
    return 0 if status.startswith("completed") else 1


if __name__ == "__main__":
    raise SystemExit(execute(Path(sys.argv[1]).resolve()))
