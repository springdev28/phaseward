"""Explicit preview settings and adapters to the tested, GUI-independent API.

No eigendecomposition, scattering or random sampling happens in these adapters.
Gate voltage conversion is an optional *declared assumption*, never calibration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import math
from typing import Any, Mapping

import numpy as np

from qwave.config import ChannelConfig, ConfigError, DisorderConfig, PacketConfig, SensitivityConfig
from qwave.gates import build_gates


@dataclass(frozen=True)
class PreviewSettings:
    """Illustrative settings; bandwidth is the probability-density standard deviation."""

    length_nm: float = 60.
    central_energy_mev: float = 40.
    bandwidth_mev: float = 6.
    effective_mass_ratio: float = .067
    grid_points: int = 161
    energy_points: int = 161
    gate_fractions: tuple[float, ...] = (-.3, -.1, .1, .3)
    gate_values: tuple[float, ...] = (8., 15., 12., 6.)
    gate_input_unit: str = "meV"
    coupling_mev_per_mv: float | None = None
    sigma_mev: float = 2.
    correlation_length_nm: float = 5.
    kernel: str = "gaussian"
    retained_modes: int = 4
    seed: int = 600001
    covariance_samples: int = 256
    observation_time_ps: float = .9
    reconstruct: bool = True

    def __post_init__(self) -> None:
        """Reject unsafe dimensions, nonfinite values, and implicit voltage mappings."""
        for name in ("length_nm", "central_energy_mev", "bandwidth_mev", "effective_mass_ratio",
                     "sigma_mev", "correlation_length_nm"):
            value = getattr(self, name)
            if type(value) not in (float, int) or not math.isfinite(value) or value <= 0:
                raise ConfigError(f"{name} must be finite and positive")
        if not 20 <= self.length_nm <= 120 or self.grid_points not in (81, 161, 321):
            raise ConfigError("preview length is 20–120 nm; spatial grids are 81, 161 or 321")
        if self.energy_points not in (81, 161, 321):
            raise ConfigError("preview energy grids are 81, 161 or 321")
        if not 1 <= len(self.gate_values) <= 8 or len(self.gate_values) != len(self.gate_fractions):
            raise ConfigError("one to eight gates require matching positions and values")
        if any(type(v) not in (float, int) or not math.isfinite(v) for v in (*self.gate_values, *self.gate_fractions)):
            raise ConfigError("gate positions and values must be finite")
        if any(abs(v) > .45 for v in self.gate_fractions):
            raise ConfigError("gate centers must lie within ±0.45 channel lengths")
        if self.gate_input_unit not in ("meV", "mV"):
            raise ConfigError("gate_input_unit must be meV or mV")
        if self.gate_input_unit == "mV":
            alpha = self.coupling_mev_per_mv
            if type(alpha) not in (float, int) or not math.isfinite(alpha) or alpha == 0:
                raise ConfigError("voltage entry requires a finite nonzero signed coupling in meV/mV")
        elif self.coupling_mev_per_mv is not None:
            raise ConfigError("energy entry must not imply a voltage calibration")
        if type(self.seed) is not int or not 0 <= self.seed <= 2**64-2:
            raise ConfigError("preview seed must be an integer in [0,2**64-2]; seed+1 validates sensitivity")
        if type(self.covariance_samples) is not int or not 32 <= self.covariance_samples <= 2048:
            raise ConfigError("preview covariance sample count must be 32–2048")
        if type(self.retained_modes) is not int or not 1 <= self.retained_modes <= 16:
            raise ConfigError("preview retained modes must be 1–16")
        if type(self.reconstruct) is not bool or not math.isfinite(self.observation_time_ps) or self.observation_time_ps < 0:
            raise ConfigError("invalid reconstruction settings")

    @property
    def amplitudes_mev(self) -> tuple[float, ...]:
        """Potential energies, optionally from an explicitly supplied signed mapping."""
        scale = self.coupling_mev_per_mv if self.gate_input_unit == "mV" else 1.
        return tuple(float(v * scale) for v in self.gate_values)

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe complete settings; serialize the voltage assumption when supplied."""
        result = asdict(self)
        result["gate_values"] = list(self.gate_values)
        result["gate_fractions"] = list(self.gate_fractions)
        return result

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> PreviewSettings:
        """Require all fields, rejecting silently ignored controls."""
        if not isinstance(data, Mapping) or set(data) != {f.name for f in fields(cls)}:
            raise ConfigError("preview settings require exactly the exported fields")
        return cls(**{**data, "gate_values": tuple(data["gate_values"]), "gate_fractions": tuple(data["gate_fractions"])})


def preview_model(settings: PreviewSettings) -> ChannelConfig:
    """Build Gaussian gates within a fixed ideal-lead buffer; no transport solve."""
    length = settings.length_nm
    scattering = dict(schema_version=1, experiment="stationary_scattering", unit_system="nm_meV",
        effective_mass_ratio=settings.effective_mass_ratio, x_min_nm=-2*length/3, x_max_nm=2*length/3,
        grid_points=settings.grid_points, energy_min_mev=max(.2, settings.central_energy_mev-4.5*settings.bandwidth_mev),
        energy_max_mev=settings.central_energy_mev+4.5*settings.bandwidth_mev, energy_points=settings.energy_points,
        left_lead_mev=0., right_lead_mev=0., potential={"kind":"free", "offset_mev":0.}, conservation_tolerance=1e-8)
    return ChannelConfig(scattering=scattering, channel={"x_min_nm":-length/2, "x_max_nm":length/2},
        gates={"normalization":"sampled_peak_abs", "taper_nm":length/12, "total_abs_bound_mev":60.,
               "profiles":[{"name":f"gate_{j+1}", "amplitude_mev":u, "bounds_mev":[-25.,25.],
                            "shape":{"kind":"gaussian", "center_nm":p*length, "sigma_nm":length/15}}
                           for j,(p,u) in enumerate(zip(settings.gate_fractions, settings.amplitudes_mev))]},
        disorder={"sigma_mev":settings.sigma_mev, "correlation_length_nm":settings.correlation_length_nm,
                  "kernel":settings.kernel, "boundary_taper_nm":0., "retained_modes":settings.retained_modes})


def device_arrays(model: ChannelConfig) -> dict[str, np.ndarray]:
    """Cheap deterministic gate sampling for the live builder; no eigensolver."""
    s = model.scattering
    x = np.linspace(s["x_min_nm"], s["x_max_nm"], s["grid_points"])
    gate = build_gates(x, (model.channel["x_min_nm"], model.channel["x_max_nm"]), model.gates)
    return {"x_nm":x, "gate_contributions_mev":gate.contributions_mev, "potential_mev":gate.total_mev}


def preview_request(settings: PreviewSettings, operation: str) -> dict[str, Any]:
    """Resolve every scientific input before Run; the worker uses these exact inputs."""
    model = preview_model(settings)
    request: dict[str, Any] = {"schema_version":1, "scope":"illustrative_preview", "operation":operation,
                               "preview_settings":settings.to_dict(), "model":model.to_dict()}
    if operation == "wave":
        arrays = device_arrays(model)
        scatter = {**model.scattering, "potential":{"kind":"tabulated", "x_nm":arrays["x_nm"].tolist(),
                   "values_mev":arrays["potential_mev"].tolist(), "interpolation":"pchip"}}
        cfg = PacketConfig(schema_version=1, experiment="wave_packet", unit_system="nm_meV_ps",
            scattering=scatter, reference_potential={"kind":"free","offset_mev":0.},
            central_energy_mev=settings.central_energy_mev, bandwidth_mev=settings.bandwidth_mev,
            bandwidth_sweep_mev=[settings.bandwidth_mev, 1.5*settings.bandwidth_mev],
            minimum_transmission_probability=1e-8,
            delay_alignment={"enabled":True,"min_ps":-.1,"max_ps":.1,"grid_points":81,"xatol_ps":1e-7},
            reconstruction={"enabled":settings.reconstruct,"source_offset_nm":-200.,
                            "observation_time_ps":settings.observation_time_ps,"lead_extent_nm":600.,"position_points":1201})
        request["packet"] = cfg.to_dict()
    elif operation == "disorder":
        request["disorder"] = DisorderConfig(1,"potential_disorder","nm_meV",model.to_dict(),
                                              settings.covariance_samples,settings.seed).to_dict()
        request["sensitivity"] = SensitivityConfig(1,"disorder_sensitivity","nm_meV",model.to_dict(),
            [.1,.01,.001,1e-7],.001,[0.,.1,1.],4,settings.seed+1).to_dict()
    elif operation != "device":
        raise ConfigError("preview operation must be device, wave or disorder")
    return request
