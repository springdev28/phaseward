"""Strict JSON configuration for Phaseward's demo, scattering, and packets."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from qwave.units import DIMENSIONLESS

if TYPE_CHECKING:
    from qwave.optimization_config import OptimizeConfig
    from qwave.experiment_config import ExperimentConfig


class ConfigError(ValueError):
    """An invalid or unsupported configuration, never a request for fallback physics."""


@dataclass(frozen=True)
class DemoConfig:
    """Resolved settings; integer limits keep the placeholder modest on a laptop."""

    schema_version: int = 1
    experiment: str = "numerical_demo"
    unit_system: str = DIMENSIONLESS
    seed: int = 1729
    grid_points: int = 257
    monte_carlo_samples: int = 1024

    def __post_init__(self) -> None:
        """Validate both programmatic construction and JSON input."""
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ConfigError("schema_version must be the integer 1")
        if self.experiment != "numerical_demo":
            raise ConfigError("DemoConfig requires experiment='numerical_demo'")
        if self.unit_system != DIMENSIONLESS:
            raise ConfigError("the demo requires unit_system='dimensionless'; no physical mapping exists")
        for name, lower, upper in (
            ("seed", 0, 2**64 - 1),
            ("grid_points", 2, 1_000_001),
            ("monte_carlo_samples", 1, 1_000_000),
        ):
            value = getattr(self, name)
            if type(value) is not int or not lower <= value <= upper:
                raise ConfigError(f"{name} must be an integer in [{lower}, {upper}]")

    def to_dict(self) -> dict[str, Any]:
        """Return all resolved settings, suitable for JSON provenance."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> DemoConfig:
        """Require every known field and reject extras rather than guessing intent."""
        expected = {field.name for field in fields(cls)}
        missing = expected - data.keys()
        unknown = data.keys() - expected
        if missing or unknown:
            raise ConfigError(f"configuration fields: missing={sorted(missing)}, unknown={sorted(unknown)}")
        return cls(**data)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys so scientific settings cannot be shadowed."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    """Reject nonstandard JSON constants such as NaN and Infinity."""
    raise ConfigError(f"non-finite JSON constant is not allowed: {value}")


def load_config(path: str | Path) -> DemoConfig | ScatterConfig | PacketConfig | DisorderConfig | SensitivityConfig | OptimizeConfig | ExperimentConfig:
    """Read and validate a complete UTF-8 JSON configuration from disk."""
    try:
        data = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ConfigError(f"cannot read configuration {path}: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError("configuration must be a JSON object")
    if data.get("experiment") == "stationary_scattering":
        return ScatterConfig.from_mapping(data)
    if data.get("experiment") == "wave_packet":
        return PacketConfig.from_mapping(data)
    if data.get("experiment") == "potential_disorder":
        return DisorderConfig.from_mapping(data)
    if data.get("experiment") == "disorder_sensitivity":
        return SensitivityConfig.from_mapping(data)
    if data.get("experiment") == "gate_optimization":
        from qwave.optimization_config import OptimizeConfig

        return OptimizeConfig.from_mapping(data)
    if data.get("experiment") == "experiment_suite":
        from qwave.experiment_config import ExperimentConfig

        return ExperimentConfig.from_mapping(data)
    return DemoConfig.from_mapping(data)


@dataclass(frozen=True)
class ScatterConfig:
    """Complete explicit physical/numerical settings; energies and potentials in meV."""

    schema_version: int
    experiment: str
    unit_system: str
    effective_mass_ratio: float
    x_min_nm: float
    x_max_nm: float
    grid_points: int
    energy_min_mev: float
    energy_max_mev: float
    energy_points: int
    left_lead_mev: float
    right_lead_mev: float
    potential: dict[str, Any]
    conservation_tolerance: float

    def __post_init__(self) -> None:
        """Reject unsupported units, unknown profiles, and invalid discrete bands."""
        from scipy.constants import hbar, m_e
        from qwave.potentials import sample_potential, validate_potential_spec
        from qwave.scattering import BAND_EDGE_FRACTION_GUARD, ScatteringError
        from qwave.units import MEV_TO_J, NM_TO_M
        import numpy as np

        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ConfigError("schema_version must be the integer 1")
        if self.experiment != "stationary_scattering" or self.unit_system != "nm_meV":
            raise ConfigError("scattering requires experiment='stationary_scattering' and unit_system='nm_meV'")
        for name in ("effective_mass_ratio", "x_min_nm", "x_max_nm", "energy_min_mev", "energy_max_mev",
                     "left_lead_mev", "right_lead_mev", "conservation_tolerance"):
            value = getattr(self, name)
            if type(value) not in (float, int) or not math.isfinite(value):
                raise ConfigError(f"{name} must be a finite real number")
        if self.effective_mass_ratio <= 0 or not 0 < self.conservation_tolerance < 1:
            raise ConfigError("effective_mass_ratio must be positive; conservation_tolerance must lie in (0,1)")
        for name, minimum, maximum in (("grid_points", 3, 100_001), ("energy_points", 2, 20_001)):
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ConfigError(f"{name} must be an integer in [{minimum}, {maximum}]")
        if self.grid_points * self.energy_points > 50_000_000:
            raise ConfigError("CLI run exceeds the 50,000,000 node-energy CPU budget; use smaller sweeps")
        if self.x_max_nm <= self.x_min_nm or self.energy_max_mev <= self.energy_min_mev:
            raise ConfigError("coordinate and energy bounds must be strictly increasing")
        spacing_m = (self.x_max_nm - self.x_min_nm) * NM_TO_M / (self.grid_points - 1)
        hopping = hbar**2 / (2 * self.effective_mass_ratio * m_e * spacing_m**2) / MEV_TO_J
        for lead in (self.left_lead_mev, self.right_lead_mev):
            fractions = [(energy - lead) / (4 * hopping) for energy in (self.energy_min_mev, self.energy_max_mev)]
            if not all(BAND_EDGE_FRACTION_GUARD < value < 1 - BAND_EDGE_FRACTION_GUARD for value in fractions):
                raise ConfigError(f"energy range must propagate in both leads, away from band edges ({lead:g}, {lead + 4*hopping:g}) meV")
        try:
            normalized = validate_potential_spec(self.potential)
            sample_potential(np.linspace(self.x_min_nm, self.x_max_nm, self.grid_points), normalized)
        except ScatteringError as error:
            raise ConfigError(str(error)) from error
        object.__setattr__(self, "potential", normalized)

    def to_dict(self) -> dict[str, Any]:
        """Return a deep, JSON-serializable copy of all resolved settings."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ScatterConfig:
        """Require all fields and reject extras, including misspelled physics options."""
        expected = {field.name for field in fields(cls)}
        missing, unknown = expected - data.keys(), data.keys() - expected
        if missing or unknown:
            raise ConfigError(f"configuration fields: missing={sorted(missing)}, unknown={sorted(unknown)}")
        return cls(**data)


@dataclass(frozen=True)
class PacketConfig:
    """Explicit packet, clean-reference, bounded-alignment, and display settings."""

    schema_version: int
    experiment: str
    unit_system: str
    scattering: dict[str, Any]
    reference_potential: dict[str, Any]
    central_energy_mev: float
    bandwidth_mev: float
    bandwidth_sweep_mev: list[float]
    minimum_transmission_probability: float
    delay_alignment: dict[str, Any]
    reconstruction: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate the common physical basis and all nested settings before solving."""
        from dataclasses import replace
        import numpy as np
        from qwave.wavepackets import DelaySearch, gaussian_packet

        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ConfigError("schema_version must be the integer 1")
        if self.experiment != "wave_packet" or self.unit_system != "nm_meV_ps":
            raise ConfigError("packet requires experiment='wave_packet' and unit_system='nm_meV_ps'")
        if not isinstance(self.scattering, dict):
            raise ConfigError("packet.scattering must be a complete scattering configuration")
        scatter = ScatterConfig.from_mapping(self.scattering)
        reference = replace(scatter, potential=self.reference_potential)
        object.__setattr__(self, "scattering", scatter.to_dict())
        object.__setattr__(self, "reference_potential", reference.potential)
        if scatter.energy_points < 33 or scatter.energy_points % 2 != 1:
            raise ConfigError("packet energy_points must be odd and at least 33 for nested quadrature checks")
        for name in ("central_energy_mev", "bandwidth_mev", "minimum_transmission_probability"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ConfigError(f"packet.{name} must be a finite real number")
        if not 0 < self.minimum_transmission_probability < 1:
            raise ConfigError("minimum_transmission_probability must lie in (0,1)")
        if not isinstance(self.bandwidth_sweep_mev, list) or not 2 <= len(self.bandwidth_sweep_mev) <= 16:
            raise ConfigError("bandwidth_sweep_mev must contain 2 to 16 increasing positive bandwidths")
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in self.bandwidth_sweep_mev):
            raise ConfigError("bandwidth sweep values must be finite positive numbers")
        if any(b <= a for a, b in zip(self.bandwidth_sweep_mev, self.bandwidth_sweep_mev[1:])):
            raise ConfigError("bandwidth_sweep_mev must be strictly increasing")
        delay_fields = {field.name for field in fields(DelaySearch)}
        if not isinstance(self.delay_alignment, dict) or set(self.delay_alignment) != delay_fields:
            raise ConfigError(f"delay_alignment requires exactly {sorted(delay_fields)}")
        try:
            delay = DelaySearch(**self.delay_alignment)
            energy = np.linspace(scatter.energy_min_mev, scatter.energy_max_mev, scatter.energy_points)
            delay.validate_sampling(energy[::2])
            for bandwidth in [self.bandwidth_mev, *self.bandwidth_sweep_mev]:
                gaussian_packet(energy[::2], central_energy_mev=self.central_energy_mev,
                                bandwidth_mev=bandwidth, propagating_bounds_mev=self.propagating_bounds_mev())
        except ValueError as error:
            raise ConfigError(str(error)) from error
        if delay.enabled and scatter.energy_points*delay.grid_points*(len(self.bandwidth_sweep_mev)+2) > 50_000_000:
            raise ConfigError("packet delay scan exceeds the 50,000,000 energy-delay CPU budget")
        reconstruction_fields = {"enabled", "source_offset_nm", "observation_time_ps", "lead_extent_nm", "position_points"}
        if not isinstance(self.reconstruction, dict) or set(self.reconstruction) != reconstruction_fields:
            raise ConfigError(f"reconstruction requires exactly {sorted(reconstruction_fields)}")
        setting = self.reconstruction
        if type(setting["enabled"]) is not bool:
            raise ConfigError("reconstruction.enabled must be boolean")
        for key in ("source_offset_nm", "observation_time_ps", "lead_extent_nm"):
            if type(setting[key]) not in (float, int) or not math.isfinite(setting[key]):
                raise ConfigError(f"reconstruction.{key} must be a finite number")
        if not -setting["lead_extent_nm"] < setting["source_offset_nm"] < 0 or setting["observation_time_ps"] < 0:
            raise ConfigError("source_offset_nm must be inside the displayed left lead; observation time must be nonnegative")
        if type(setting["position_points"]) is not int or not 65 <= setting["position_points"] <= 10_001:
            raise ConfigError("reconstruction.position_points must be an integer in [65,10001]")
        if setting["enabled"] and scatter.energy_points*setting["position_points"]*3 > 15_000_000:
            raise ConfigError("lead reconstruction exceeds the 15,000,000 position-energy CPU budget")

    def propagating_bounds_mev(self) -> tuple[float, float]:
        """Return the intersection of the two discrete lead bands shared with the target."""
        from scipy.constants import hbar, m_e
        from qwave.units import MEV_TO_J, NM_TO_M

        cfg = self.scattering
        spacing = (cfg["x_max_nm"]-cfg["x_min_nm"])*NM_TO_M/(cfg["grid_points"]-1)
        hopping = hbar**2/(2*cfg["effective_mass_ratio"]*m_e*spacing**2)/MEV_TO_J
        return max(cfg["left_lead_mev"], cfg["right_lead_mev"]), min(cfg["left_lead_mev"], cfg["right_lead_mev"])+4*hopping

    def to_dict(self) -> dict[str, Any]:
        """Return all packet and device settings as a deep JSON-safe copy."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> PacketConfig:
        """Require every declared field and reject unknown physical options."""
        expected = {field.name for field in fields(cls)}
        missing, unknown = expected-data.keys(), data.keys()-expected
        if missing or unknown:
            raise ConfigError(f"configuration fields: missing={sorted(missing)}, unknown={sorted(unknown)}")
        return cls(**data)


@dataclass(frozen=True)
class ChannelConfig:
    """Shared gated channel and covariance settings, in nm and meV."""

    scattering: dict[str, Any]
    channel: dict[str, Any]
    gates: dict[str, Any]
    disorder: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate channel support, bounded gates, covariance family, and CPU dimensions."""
        import numpy as np
        from qwave.disorder import KERNELS
        from qwave.gates import build_gates, channel_envelope, channel_indices, real_setting

        if not isinstance(self.scattering, dict):
            raise ConfigError("model.scattering must be a complete scattering configuration")
        scatter = ScatterConfig.from_mapping(self.scattering)
        object.__setattr__(self, "scattering", scatter.to_dict())
        if not isinstance(self.channel, dict) or set(self.channel) != {"x_min_nm", "x_max_nm"}:
            raise ConfigError("model.channel requires exactly x_min_nm and x_max_nm")
        if not isinstance(self.disorder, dict) or set(self.disorder) != {
            "sigma_mev", "correlation_length_nm", "kernel", "boundary_taper_nm", "retained_modes"
        }:
            raise ConfigError("model.disorder requires sigma_mev, correlation_length_nm, kernel, boundary_taper_nm, retained_modes")
        try:
            bounds = (real_setting(self.channel["x_min_nm"], "channel.x_min_nm"),
                      real_setting(self.channel["x_max_nm"], "channel.x_max_nm"))
            x = np.linspace(scatter.x_min_nm, scatter.x_max_nm, scatter.grid_points)
            indices = channel_indices(x, bounds)
            if len(indices) > 801:
                raise ValueError("channel covariance is limited to 801 nodes for local dense decomposition")
            build_gates(x, bounds, self.gates)
            for name in ("sigma_mev", "correlation_length_nm"):
                real_setting(self.disorder[name], f"disorder.{name}", positive=True)
            channel_envelope(x[indices], bounds, self.disorder["boundary_taper_nm"])
            if self.disorder["kernel"] not in KERNELS:
                raise ValueError(f"disorder.kernel must be one of {KERNELS}")
            count = self.disorder["retained_modes"]
            if type(count) is not int or not 1 <= count <= min(32, len(indices)):
                raise ValueError("retained_modes must be an integer from 1 to min(32, channel node count)")
        except ValueError as error:
            raise ConfigError(str(error)) from error

    def to_dict(self) -> dict[str, Any]:
        """Deep copy of the model shared by disorder and sensitivity commands."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ChannelConfig:
        """Reject incomplete or unknown model settings."""
        return _strict_config(cls, data)


def _strict_config(cls: Any, data: Mapping[str, Any]) -> Any:
    """Load a complete dataclass configuration with no implicit physics defaults."""
    expected = {field.name for field in fields(cls)}
    if not isinstance(data, Mapping) or set(data) != expected:
        raise ConfigError(f"{cls.__name__} requires exactly {sorted(expected)}")
    return cls(**data)


def _stage3_header(schema: int, experiment: str, units: str, expected: str) -> None:
    """Validate the explicit stage-3 experiment and units tag."""
    if type(schema) is not int or schema != 1 or experiment != expected or units != "nm_meV":
        raise ConfigError(f"requires schema_version=1, experiment='{expected}', unit_system='nm_meV'")


@dataclass(frozen=True)
class DisorderConfig:
    """Full/KL covariance validation with one recorded sampling seed."""

    schema_version: int
    experiment: str
    unit_system: str
    model: dict[str, Any]
    sample_count: int
    seed: int

    def __post_init__(self) -> None:
        """Validate sampling size, seed, and the common model."""
        import numpy as np
        from qwave.disorder import seed_generator
        from qwave.gates import channel_indices

        _stage3_header(self.schema_version, self.experiment, self.unit_system, "potential_disorder")
        model = ChannelConfig.from_mapping(self.model)
        object.__setattr__(self, "model", model.to_dict())
        if type(self.sample_count) is not int or not 32 <= self.sample_count <= 20_000:
            raise ConfigError("sample_count must be an integer in [32,20000]")
        try:
            seed_generator(self.seed)
            scatter = model.scattering
            x = np.linspace(scatter["x_min_nm"], scatter["x_max_nm"], scatter["grid_points"])
            n = len(channel_indices(x, (model.channel["x_min_nm"], model.channel["x_max_nm"])))
            if self.sample_count*n > 4_000_000:
                raise ValueError("disorder sampling exceeds the 4,000,000 value CPU/memory budget")
        except ValueError as error:
            raise ConfigError(str(error)) from error

    def to_dict(self) -> dict[str, Any]:
        """Complete resolved configuration for result provenance."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> DisorderConfig:
        """Require every field and reject extras."""
        return _strict_config(cls, data)


@dataclass(frozen=True)
class SensitivityConfig:
    """Complex derivative step study and paired first-order validation."""

    schema_version: int
    experiment: str
    unit_system: str
    model: dict[str, Any]
    steps_mev_sqrt_nm: list[float]
    selected_step_mev_sqrt_nm: float
    disorder_scales: list[float]
    validation_samples: int
    validation_seed: int

    def __post_init__(self) -> None:
        """Keep finite differences, chosen baseline, and validation draws explicit."""
        from qwave.disorder import seed_generator
        from qwave.gates import real_setting

        _stage3_header(self.schema_version, self.experiment, self.unit_system, "disorder_sensitivity")
        model = ChannelConfig.from_mapping(self.model)
        object.__setattr__(self, "model", model.to_dict())
        try:
            if not isinstance(self.steps_mev_sqrt_nm, list) or not 3 <= len(self.steps_mev_sqrt_nm) <= 20:
                raise ValueError("steps_mev_sqrt_nm requires 3 to 20 decreasing positive steps")
            steps = [real_setting(v, "derivative step", positive=True) for v in self.steps_mev_sqrt_nm]
            if any(b >= a for a, b in zip(steps, steps[1:])):
                raise ValueError("steps_mev_sqrt_nm must be strictly decreasing")
            chosen = real_setting(self.selected_step_mev_sqrt_nm, "selected_step_mev_sqrt_nm", positive=True)
            if chosen not in steps:
                raise ValueError("selected_step_mev_sqrt_nm must be one of the explicitly studied steps")
            if not isinstance(self.disorder_scales, list) or not 3 <= len(self.disorder_scales) <= 12:
                raise ValueError("disorder_scales requires 3 to 12 increasing nonnegative scales starting at zero")
            scales = [real_setting(v, "disorder scale") for v in self.disorder_scales]
            if scales[0] != 0 or any(b <= a for a, b in zip(scales, scales[1:])):
                raise ValueError("disorder_scales must start at zero and increase strictly")
            if type(self.validation_samples) is not int or not 2 <= self.validation_samples <= 128:
                raise ValueError("validation_samples must be an integer in [2,128]")
            seed_generator(self.validation_seed)
            scatter = model.scattering
            if scatter["energy_points"] < 3:
                raise ValueError("sensitivity validation requires at least three energy points")
            solves = 2*len(steps)*model.disorder["retained_modes"]+2*len(scales)*self.validation_samples+3
            if solves*scatter["grid_points"]*scatter["energy_points"] > 50_000_000:
                raise ValueError("sensitivity exceeds the 50,000,000 node-energy CPU budget")
        except ValueError as error:
            raise ConfigError(str(error)) from error

    def to_dict(self) -> dict[str, Any]:
        """Complete settings, including the seed and the chosen finite-difference step."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> SensitivityConfig:
        """Require all fields without default numerical or scientific substitutions."""
        return _strict_config(cls, data)
