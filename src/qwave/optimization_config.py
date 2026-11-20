"""Strict configuration for budgeted, constrained gate comparisons."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

import numpy as np
from scipy.constants import hbar, m_e

from qwave.config import ChannelConfig, ConfigError, ScatterConfig, _strict_config
from qwave.gates import real_setting
from qwave.units import MEV_TO_J, NM_TO_M
from qwave.wavepackets import gaussian_packet


def _object(value: Any, names: str, label: str) -> dict[str, Any]:
    """Reject missing/unknown nested settings."""
    if not isinstance(value, dict) or set(value) != set(names.split()):
        raise ConfigError(f"{label} requires exactly {names}")
    return value


def _integer(value: Any, low: int, high: int, name: str) -> int:
    """Validate bounded integers without accepting boolean seeds/budgets."""
    if type(value) is not int or not low <= value <= high:
        raise ConfigError(f"{name} must be an integer in [{low},{high}]")
    return value


@dataclass(frozen=True)
class OptimizeConfig:
    """All scientific choices and search/evaluation budgets are explicit."""

    schema_version: int
    experiment: str
    unit_system: str
    model: dict[str, Any]
    packet: dict[str, Any]
    target_potential: dict[str, Any]
    objective: dict[str, Any]
    constraints: dict[str, Any]
    optimizer: dict[str, Any]
    diagnostics: dict[str, Any]
    ensembles: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate the fixed model, distinct seeds, explicit constraints, and CPU limits."""
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ConfigError("schema_version must be the integer 1")
        if self.experiment != "gate_optimization" or self.unit_system != "nm_meV":
            raise ConfigError("optimization requires gate_optimization and nm_meV")
        model = ChannelConfig.from_mapping(self.model)
        object.__setattr__(self, "model", model.to_dict())
        scatter = ScatterConfig.from_mapping(model.scattering)
        target = ScatterConfig.from_mapping({**model.scattering, "potential": self.target_potential})
        object.__setattr__(self, "target_potential", target.potential)
        _object(self.packet, "central_energy_mev bandwidth_mev", "packet")
        gaussian_packet(np.linspace(scatter.energy_min_mev, scatter.energy_max_mev, scatter.energy_points),
                        **self.packet, propagating_bounds_mev=self.propagating_bounds_mev())
        objective = _object(self.objective, "weighting normalization transmission_weight", "objective")
        if objective["weighting"] not in {"incoming_probability", "uniform_energy"}:
            raise ConfigError("weighting must be incoming_probability or uniform_energy")
        if objective["normalization"] not in {"none", "nominal_variance"}:
            raise ConfigError("normalization must be none or nominal_variance")
        if not 0 < real_setting(objective["transmission_weight"], "transmission_weight") < 1:
            raise ConfigError("transmission_weight must lie strictly between zero and one")
        constraints = _object(self.constraints,
            "minimum_clean_transmission_values minimum_clean_fidelity max_gate_gradient_mev_per_nm feasibility_tolerance",
            "constraints")
        floors = constraints["minimum_clean_transmission_values"]
        if not isinstance(floors, list) or not 1 <= len(floors) <= 5:
            raise ConfigError("minimum_clean_transmission_values needs 1 to 5 increasing values")
        for value in floors:
            if not 1e-4 <= real_setting(value, "minimum transmission") <= 1:
                raise ConfigError("minimum clean transmission must lie in [1e-4,1]")
        if any(b <= a for a, b in zip(floors, floors[1:])):
            raise ConfigError("transmission floors must be strictly increasing")
        if not 0 < real_setting(constraints["minimum_clean_fidelity"], "minimum fidelity") <= 1:
            raise ConfigError("minimum clean fidelity must lie in (0,1]")
        if constraints["max_gate_gradient_mev_per_nm"] is not None:
            real_setting(constraints["max_gate_gradient_mev_per_nm"], "gate gradient bound", positive=True)
        tol = real_setting(constraints["feasibility_tolerance"], "feasibility_tolerance", positive=True)
        if tol > 1e-5:
            raise ConfigError("feasibility_tolerance must be <=1e-5 (dimensionless scaled residuals)")
        optimizer = _object(self.optimizer,
            "method starts initialization_seed forward_work_budget maxiter ftol gate_step_mev cache_entries", "optimizer")
        if optimizer["method"] != "SLSQP":
            raise ConfigError("the implemented local method is SLSQP; starts supplies the multi-start strategy")
        _integer(optimizer["starts"], 1, 8, "starts")
        _integer(optimizer["initialization_seed"], 0, 2**64-1, "initialization_seed")
        _integer(optimizer["forward_work_budget"], optimizer["starts"], 10_000, "forward_work_budget")
        _integer(optimizer["maxiter"], 1, 200, "maxiter")
        _integer(optimizer["cache_entries"], 1, 512, "cache_entries")
        if not 0 < real_setting(optimizer["ftol"], "ftol") <= .01:
            raise ConfigError("ftol must lie in (0,.01]")
        step = real_setting(optimizer["gate_step_mev"], "gate_step_mev", positive=True)
        bounds = np.array([profile["bounds_mev"] for profile in model.gates["profiles"]])
        if len(bounds) > 8 or step >= min(bounds[:,1]-bounds[:,0])/4:
            raise ConfigError("optimization supports at most 8 gates; step must be < one quarter of each bound width")
        diagnostics = _object(self.diagnostics,
            "gate_steps_mev gradient_atol gradient_rtol mode_steps_mev_sqrt_nm mode_derivative_atol", "diagnostics")
        for key in ("gate_steps_mev", "mode_steps_mev_sqrt_nm"):
            values = diagnostics[key]
            if not isinstance(values, list) or not 3 <= len(values) <= 6:
                raise ConfigError(f"{key} requires 3 to 6 positive decreasing steps")
            for value in values:
                real_setting(value, key, positive=True)
            if any(b >= a for a, b in zip(values, values[1:])):
                raise ConfigError(f"{key} must be strictly decreasing")
        if step not in diagnostics["gate_steps_mev"] or step/2 not in diagnostics["gate_steps_mev"]:
            raise ConfigError("gate diagnostics must include the selected gate step and half that step")
        if max(diagnostics["gate_steps_mev"]) >= min(bounds[:,1]-bounds[:,0])/4:
            raise ConfigError("diagnostic gate steps must be < one quarter of bound widths")
        for key in ("gradient_atol", "gradient_rtol", "mode_derivative_atol"):
            real_setting(diagnostics[key], key, positive=True)
        ensemble = _object(self.ensembles,
            "representation training_samples validation_samples heldout_samples training_seed validation_seed heldout_seed", "ensembles")
        if ensemble["representation"] != "retained_kl":
            raise ConfigError("all four methods must use the same declared retained_kl disorder model")
        for name, upper in (("training",16),("validation",128),("heldout",128)):
            _integer(ensemble[name+"_samples"], 2, upper, name+"_samples")
            _integer(ensemble[name+"_seed"], 0, 2**64-1, name+"_seed")
        seeds = [optimizer["initialization_seed"], *[ensemble[name+"_seed"] for name in ("training","validation","heldout")]]
        if len(set(seeds)) != len(seeds):
            raise ConfigError("initialization, training, validation, and held-out seeds must be distinct")
        work = 3*len(floors)*optimizer["forward_work_budget"]
        work += 4*len(floors)*(3+sum(ensemble[name+"_samples"] for name in ("training","validation","heldout")))
        work += (1+2*len(bounds)*len(diagnostics["gate_steps_mev"]))*(5+ensemble["training_samples"])
        work += len(floors)*(1+2*len(bounds)*len(diagnostics["gate_steps_mev"]))*(5+ensemble["training_samples"])
        work += 3+2*model.disorder["retained_modes"]*len(diagnostics["mode_steps_mev_sqrt_nm"])
        if work*scatter.energy_points*scatter.grid_points > 250_000_000:
            raise ConfigError("optimization comparison exceeds the 250,000,000 node-energy work budget")

    def propagating_bounds_mev(self) -> tuple[float, float]:
        """Same finite lead band, mass, and reference planes for the declared target."""
        cfg = self.model["scattering"]
        spacing = (cfg["x_max_nm"]-cfg["x_min_nm"])*NM_TO_M/(cfg["grid_points"]-1)
        hopping = hbar**2/(2*cfg["effective_mass_ratio"]*m_e*spacing**2)/MEV_TO_J
        return max(cfg["left_lead_mev"],cfg["right_lead_mev"]), min(cfg["left_lead_mev"],cfg["right_lead_mev"])+4*hopping

    def to_dict(self) -> dict[str, Any]:
        """Deep copy including every seed, limit, and target setting."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> OptimizeConfig:
        """Reject implicit defaults and unknown options."""
        return _strict_config(cls, data)
