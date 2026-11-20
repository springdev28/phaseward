"""Prespecified local experiment suites, seed partitions, and laptop presets."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import re
from typing import Any, Mapping

import numpy as np

from qwave.config import ConfigError, _strict_config
from qwave.optimization_config import OptimizeConfig, _integer, _object
from qwave.gates import real_setting
from qwave.wavepackets import DelaySearch

PRESETS = ("smoke", "benchmark", "disorder-sweep", "optimization-comparison", "convergence-study")


def merge_settings(base: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    """Deep merge mapping overrides; lists replace lists and no field is inferred."""
    result = deepcopy(base)
    for key, value in changes.items():
        if key not in result:
            raise ConfigError(f"unknown override field: {key}")
        if isinstance(value, dict) and isinstance(result[key], dict):
            result[key] = merge_settings(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def reject_seed_overlap(partitions: Mapping[str, list[int]]) -> None:
    """Reject duplicate seeds both within and across named stochastic roles."""
    seen: dict[int, str] = {}
    for name, seeds in partitions.items():
        for seed in seeds:
            _integer(seed, 0, 2**64-1, name+" seed")
            if seed in seen:
                raise ConfigError(f"seed overlap: {seed} occurs in {seen[seed]} and {name}")
            seen[seed] = name


def child_seeds(root: int, count: int) -> list[int]:
    """Materialize one explicit PCG64 seed per draw, stable under prefix extension."""
    return [int(child.generate_state(1, dtype=np.uint64)[0])
            for child in np.random.SeedSequence(root).spawn(count)]


def diagnostic_settings(optimization: dict[str, Any]) -> dict[str, Any]:
    """Disable unused search budgets for fixed-device diagnostic preparation.

    Physical parameters, packet and covariance are unchanged. Diagnostic sample
    counts come from convergence.sample_counts, not these unused ensemble fields.
    """
    result = deepcopy(optimization)
    result["optimizer"].update(starts=1, forward_work_budget=1)
    result["ensembles"].update(training_samples=2, validation_samples=2, heldout_samples=2)
    return result


@dataclass(frozen=True)
class ExperimentConfig:
    """All cases, budgets, analysis rules, and convergence axes declared before data."""

    schema_version: int
    experiment: str
    preset: str
    resource_profile: str
    optimization: dict[str, Any]
    cases: list[dict[str, Any]]
    delay: dict[str, Any]
    statistics: dict[str, Any]
    convergence: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate resolved cases, numerical studies, and the entire seed registry."""
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ConfigError("schema_version must be the integer 1")
        if self.experiment != "experiment_suite" or self.preset not in PRESETS:
            raise ConfigError("experiment_suite requires a supported preset name")
        if self.resource_profile not in {"laptop", "research"}:
            raise ConfigError("resource_profile must be laptop or research")
        base = OptimizeConfig.from_mapping(self.optimization)
        object.__setattr__(self, "optimization", base.to_dict())
        if not isinstance(self.cases, list) or not 1 <= len(self.cases) <= 8:
            raise ConfigError("cases requires 1 to 8 prespecified cases")
        names = []
        for case in self.cases:
            _object(case, "name overrides", "case")
            if not isinstance(case["name"], str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", case["name"]):
                raise ConfigError("case name must be a short lowercase identifier")
            names.append(case["name"])
            if not isinstance(case["overrides"], dict) or not set(case["overrides"]) <= {"model", "packet"}:
                raise ConfigError("case overrides may change model or packet only; search budgets/seeds stay common")
        if len(set(names)) != len(names):
            raise ConfigError("case names must be unique")
        _object(self.delay, "enabled min_ps max_ps grid_points xatol_ps", "delay")
        delay = DelaySearch(**self.delay)
        stats = _object(self.statistics,
            "bootstrap_seed bootstrap_resamples confidence_level practical_loss_difference", "statistics")
        _integer(stats["bootstrap_seed"], 0, 2**64-1, "bootstrap_seed")
        _integer(stats["bootstrap_resamples"], 1000, 50000, "bootstrap_resamples")
        if not .8 <= real_setting(stats["confidence_level"], "confidence_level") <= .99:
            raise ConfigError("confidence_level must lie in [0.8,0.99]")
        if not 0 <= real_setting(stats["practical_loss_difference"], "practical_loss_difference") < 1:
            raise ConfigError("practical_loss_difference must lie in [0,1)")
        conv = _object(self.convergence,
            "seed spatial_grid_points energy_points retained_modes mode_steps_mev_sqrt_nm sample_counts",
            "convergence")
        _integer(conv["seed"], 0, 2**64-1, "convergence.seed")
        for name, lower, upper in (("spatial_grid_points", 21, 1001), ("energy_points", 9, 1001),
                                   ("retained_modes", 1, 128), ("sample_counts", 2, 512)):
            values = conv[name]
            if not isinstance(values, list) or not 3 <= len(values) <= 6:
                raise ConfigError(f"convergence.{name} requires 3 to 6 increasing levels")
            for value in values:
                _integer(value, lower, upper, name)
            if any(b <= a for a,b in zip(values, values[1:])):
                raise ConfigError(f"convergence.{name} must increase strictly")
        steps = conv["mode_steps_mev_sqrt_nm"]
        if not isinstance(steps, list) or not 3 <= len(steps) <= 8:
            raise ConfigError("convergence mode steps requires 3 to 8 decreasing values")
        for value in steps:
            real_setting(value, "mode step", positive=True)
        if any(b >= a for a,b in zip(steps,steps[1:])):
            raise ConfigError("convergence mode steps must decrease strictly")
        cases = self.resolved_cases()
        for _, config in cases:
            s = config.model["scattering"]
            delay.validate_sampling(np.linspace(s["energy_min_mev"],s["energy_max_mev"],s["energy_points"]))
        # Numerical diagnostics apply to the first declared case only.
        first = diagnostic_settings(cases[0][1].to_dict())
        for key, target in (("spatial_grid_points","grid_points"), ("energy_points","energy_points")):
            for value in conv[key]:
                changed = deepcopy(first)
                changed["model"]["scattering"][target] = value
                candidate = OptimizeConfig.from_mapping(changed)
                s = candidate.model["scattering"]
                delay.validate_sampling(np.linspace(s["energy_min_mev"],s["energy_max_mev"],s["energy_points"]))
        for value in conv["retained_modes"]:
            changed = deepcopy(first)
            changed["model"]["disorder"]["retained_modes"] = value
            OptimizeConfig.from_mapping(changed)
        if self.resource_profile == "laptop":
            work = sum(c.optimizer["forward_work_budget"]*len(c.constraints["minimum_clean_transmission_values"])
                       for _,c in cases)
            if (work > 3000 or max(conv["sample_counts"]) > 128 or max(conv["spatial_grid_points"]) > 401
                    or max(conv["energy_points"]) > 321):
                raise ConfigError("larger suites require resource_profile=research and explicit --research")
        self.seed_registry()

    def resolved_cases(self) -> list[tuple[str, OptimizeConfig]]:
        """Resolve physical variables without changing any method-specific search budget."""
        return [(case["name"], OptimizeConfig.from_mapping(merge_settings(self.optimization, case["overrides"])))
                for case in self.cases]

    def seed_registry(self) -> dict[str, Any]:
        """Store and check roots plus every independent draw seed before a solve."""
        settings = self.optimization["ensembles"]
        roots = {"initialization": self.optimization["optimizer"]["initialization_seed"],
                 **{name: settings[name+"_seed"] for name in ("training","validation","heldout")},
                 "convergence": self.convergence["seed"], "bootstrap": self.statistics["bootstrap_seed"]}
        reject_seed_overlap({name:[seed] for name,seed in roots.items()})
        draws = {name: child_seeds(roots[name],settings[name+"_samples"]) for name in ("training","validation","heldout")}
        draws["convergence"] = child_seeds(roots["convergence"],max(self.convergence["sample_counts"]))
        reject_seed_overlap({**{name+"_root":[seed] for name,seed in roots.items()}, **draws})
        return {"roots":roots,"draw_seeds":draws,
                "derivation":"SeedSequence(root).spawn(n); child.generate_state(1,uint64)[0]; one PCG64 per draw",
                "pairing":"same seed list across methods, floors and cases; cases are not independent replications",
                "scope":"overlap is checked inside this suite; rerunning a preset reuses its declared seeds"}

    def to_dict(self) -> dict[str, Any]:
        """Deep copy of the complete prespecified design."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ExperimentConfig:
        """Reject absent, unknown or unsupported settings."""
        return _strict_config(cls, data)


def preset_config(name: str, *, research: bool = False) -> ExperimentConfig:
    """Portable built-in presets; research scaling is never selected automatically."""
    if name not in PRESETS:
        raise ConfigError(f"unknown preset {name}")
    smoke = name == "smoke" and not research
    root = 510000 + 10000*PRESETS.index(name) + (100000 if research else 0)
    profiles = [{"name":f"gate_{j+1}","amplitude_mev":u,"bounds_mev":[-25.,25.],
                 "shape":{"kind":"gaussian","center_nm":center,"sigma_nm":4.}}
                for j,(center,u) in enumerate(zip([-18.,-6.,6.,18.],[8.,15.,12.,6.]))]
    opt = {
        "schema_version":1,"experiment":"gate_optimization","unit_system":"nm_meV",
        "model":{
            "scattering":{"schema_version":1,"experiment":"stationary_scattering","unit_system":"nm_meV",
                "effective_mass_ratio":.067,"x_min_nm":-40.,"x_max_nm":40.,
                "grid_points":81 if smoke else (201 if research else 161),
                "energy_min_mev":12.,"energy_max_mev":68.,"energy_points":41 if smoke else (81 if research else 57),
                "left_lead_mev":0.,"right_lead_mev":0.,"potential":{"kind":"free","offset_mev":0.},
                "conservation_tolerance":1e-8},
            "channel":{"x_min_nm":-30.,"x_max_nm":30.},
            "gates":{"normalization":"sampled_peak_abs","taper_nm":5.,"total_abs_bound_mev":60.,"profiles":profiles},
            "disorder":{"sigma_mev":2.,"correlation_length_nm":5.,"kernel":"gaussian","boundary_taper_nm":0.,
                        "retained_modes":3 if smoke else 6}},
        "packet":{"central_energy_mev":40.,"bandwidth_mev":6.},
        "target_potential":{"kind":"free","offset_mev":0.},
        "objective":{"weighting":"incoming_probability","normalization":"nominal_variance","transmission_weight":.5},
        "constraints":{"minimum_clean_transmission_values":[.85],"minimum_clean_fidelity":.95,
                       "max_gate_gradient_mev_per_nm":5.,"feasibility_tolerance":1e-7},
        "optimizer":{"method":"SLSQP","starts":3 if research else 2,"initialization_seed":root+1,
                     "forward_work_budget":90 if smoke else (600 if research else 240),
                     "maxiter":40,"ftol":1e-7,"gate_step_mev":.01,"cache_entries":128},
        "diagnostics":{"gate_steps_mev":[.1,.01,.005,1e-7],"gradient_atol":1e-7,"gradient_rtol":.005,
                       "mode_steps_mev_sqrt_nm":[.1,.001,1e-8],"mode_derivative_atol":1e-7},
        "ensembles":{"representation":"retained_kl","training_samples":2 if smoke else (8 if research else 4),
                     "validation_samples":4 if smoke else (32 if research else 12),
                     "heldout_samples":8 if smoke else (128 if research else 32),
                     "training_seed":root+2,"validation_seed":root+3,"heldout_seed":root+4}}
    cases = [{"name":"declared_device","overrides":{}}]
    if name == "disorder-sweep":
        cases = [{"name":f"sigma_{value}","overrides":{"model":{"disorder":{"sigma_mev":float(value)}}}}
                 for value in (1,2,4)]
    if name == "optimization-comparison":
        opt["constraints"]["minimum_clean_transmission_values"] = [.85,.98]
    convergence = {
        "seed":root+5,"spatial_grid_points":[81,161,321],
        "energy_points":[41,81,161], "retained_modes":[2,4,8],
        "mode_steps_mev_sqrt_nm":[.1,.01,.001,1e-7,1e-10],
        "sample_counts":[4,8,16] if smoke else [8,16,32]}
    if name == "convergence-study" or research:
        convergence.update(spatial_grid_points=[81,161,321] if not research else [161,321,641],
                           energy_points=[41,81,161,321],retained_modes=[2,4,8,16],
                           sample_counts=[8,16,32,64] if not research else [16,32,64,128])
    return ExperimentConfig.from_mapping({
        "schema_version":1,"experiment":"experiment_suite","preset":name,
        "resource_profile":"research" if research else "laptop","optimization":opt,"cases":cases,
        "delay":{"enabled":True,"min_ps":-.15,"max_ps":.15,"grid_points":81,"xatol_ps":1e-7},
        "statistics":{"bootstrap_seed":root+6,"bootstrap_resamples":12000 if research else 4000,
                      "confidence_level":.95,"practical_loss_difference":.001},
        "convergence":convergence})

