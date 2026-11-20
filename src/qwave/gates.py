"""Bounded, channel-confined potential-energy gates; coefficients are meV, not voltages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.interpolate import PchipInterpolator

from qwave.scattering import real_vector, uniform_grid


def real_setting(value: Any, name: str, *, positive: bool = False) -> float:
    """Require a finite real setting, excluding booleans and complex values."""
    if type(value) not in (int, float) or not np.isfinite(value) or (positive and value <= 0):
        raise ValueError(f"{name} must be a finite real number" + (" > 0" if positive else ""))
    return float(value)


def channel_indices(x_nm: ArrayLike, bounds_nm: tuple[float, float]) -> NDArray[np.int64]:
    """Select an interior channel with endpoints on physical grid nodes."""
    x, spacing = uniform_grid(x_nm)
    left, right = (real_setting(v, "channel bound") for v in bounds_nm)
    if not x[0] < left < right < x[-1]:
        raise ValueError("channel must lie strictly inside the finite scattering domain")
    endpoints = [int(np.argmin(abs(x-v))) for v in (left, right)]
    if any(abs(x[i]-v) > 1e-9*spacing for i, v in zip(endpoints, (left, right))):
        raise ValueError("channel endpoints must coincide with scattering grid nodes")
    indices = np.arange(endpoints[0], endpoints[1]+1, dtype=np.int64)
    if len(indices) < 3:
        raise ValueError("channel must contain at least three grid nodes")
    return indices


def channel_envelope(x_nm: ArrayLike, bounds_nm: tuple[float, float], taper_nm: float) -> NDArray[np.float64]:
    """Compact C1 raised-cosine envelope, or an explicit hard window at zero taper."""
    x = real_vector(x_nm, "x_nm", minimum_size=3)
    left, right = bounds_nm
    taper = real_setting(taper_nm, "taper_nm")
    if not left < right or not 0 <= taper <= (right-left)/2:
        raise ValueError("taper must lie between zero and half the channel length")
    distance = np.minimum(x-left, right-x)
    if taper == 0:
        return ((x >= left) & (x <= right)).astype(float)
    envelope = np.zeros_like(x)
    inside = distance > 0
    envelope[inside] = .5*(1-np.cos(np.pi*np.minimum(distance[inside]/taper, 1)))
    return envelope


@dataclass(frozen=True)
class GatePotential:
    """Unit shapes and bounded contributions; columns index gates."""

    names: tuple[str, ...]
    shapes: NDArray[np.float64]
    amplitudes_mev: NDArray[np.float64]
    contributions_mev: NDArray[np.float64]
    total_mev: NDArray[np.float64]
    normalization_factors: NDArray[np.float64]


def build_gates(x_nm: ArrayLike, bounds_nm: tuple[float, float], spec: Mapping[str, Any]) -> GatePotential:
    """Build Gaussian, raised-cosine, or PCHIP gates without clipping amplitudes."""
    x, _ = uniform_grid(x_nm)
    channel_indices(x, bounds_nm)
    expected = {"normalization", "taper_nm", "total_abs_bound_mev", "profiles"}
    if not isinstance(spec, Mapping) or set(spec) != expected:
        raise ValueError(f"gates requires exactly {sorted(expected)}")
    if spec["normalization"] != "sampled_peak_abs":
        raise ValueError("gate normalization must be 'sampled_peak_abs'")
    envelope = channel_envelope(x, bounds_nm, real_setting(spec["taper_nm"], "gates.taper_nm", positive=True))
    total_bound = real_setting(spec["total_abs_bound_mev"], "gates.total_abs_bound_mev", positive=True)
    profiles = spec["profiles"]
    if not isinstance(profiles, list) or not 1 <= len(profiles) <= 32:
        raise ValueError("gates.profiles must contain 1 to 32 gates")
    names, shapes, amplitudes, normalization = [], [], [], []
    for gate in profiles:
        if not isinstance(gate, Mapping) or set(gate) != {"name", "amplitude_mev", "bounds_mev", "shape"}:
            raise ValueError("each gate requires name, amplitude_mev, bounds_mev, and shape")
        name = gate["name"]
        if not isinstance(name, str) or not name.strip() or len(name) > 80 or name in names:
            raise ValueError("gate names must be nonempty, unique strings of at most 80 characters")
        limits = gate["bounds_mev"]
        if not isinstance(limits, list) or len(limits) != 2:
            raise ValueError("gate.bounds_mev must be [lower, upper]")
        low, high = (real_setting(v, "gate amplitude bound") for v in limits)
        amplitude = real_setting(gate["amplitude_mev"], "gate.amplitude_mev")
        if not low < high or not low <= amplitude <= high:
            raise ValueError(f"gate {name}: amplitude must lie within its increasing bounds")
        shape = gate["shape"]
        if not isinstance(shape, Mapping):
            raise ValueError("gate.shape must be an object")
        kind = shape.get("kind")
        if not isinstance(kind, str):
            raise ValueError("gate shape kind must be a string")
        if kind in {"gaussian", "raised_cosine"}:
            scale_name = "sigma_nm" if kind == "gaussian" else "half_width_nm"
            if set(shape) != {"kind", "center_nm", scale_name}:
                raise ValueError(f"invalid {kind} gate shape fields")
            center = real_setting(shape["center_nm"], "gate center")
            scale = real_setting(shape[scale_name], scale_name, positive=True)
            if not bounds_nm[0] < center < bounds_nm[1]:
                raise ValueError("gate centers must lie inside the channel")
            distance = (x-center)/scale
            raw = (np.exp(-.5*distance**2) if kind == "gaussian" else
                   np.where(abs(distance) < 1, .5*(1+np.cos(np.pi*np.clip(distance, -1, 1))), 0.))
        elif kind == "tabulated":
            if set(shape) != {"kind", "x_nm", "values", "interpolation"} or shape["interpolation"] != "pchip":
                raise ValueError("tabulated gate requires x_nm, values, interpolation='pchip'")
            nodes = real_vector(shape["x_nm"], "gate.x_nm", minimum_size=3)
            values = real_vector(shape["values"], "gate.values", minimum_size=3)
            if nodes.shape != values.shape or np.any(np.diff(nodes) <= 0):
                raise ValueError("gate table must have ordered nodes and matching real values")
            if nodes[0] > bounds_nm[0] or nodes[-1] < bounds_nm[1]:
                raise ValueError("gate table must cover the channel; extrapolation is disabled")
            raw = np.zeros_like(x)
            inside = (x >= bounds_nm[0]) & (x <= bounds_nm[1])
            raw[inside] = PchipInterpolator(nodes, values, extrapolate=False)(x[inside])
        else:
            raise ValueError("supported gate shapes: gaussian, raised_cosine, tabulated")
        values = raw*envelope
        peak = float(max(abs(values)))
        if not np.isfinite(peak) or peak <= np.finfo(float).tiny:
            raise ValueError("gate shape is zero or numerically unresolved on this grid")
        names.append(name)
        shapes.append(values/peak)
        amplitudes.append(amplitude)
        normalization.append(peak)
    basis = np.column_stack(shapes)
    coefficients = np.asarray(amplitudes)
    contributions = basis*coefficients
    total = np.sum(contributions, axis=1)
    if max(abs(total)) > total_bound*(1+32*np.finfo(float).eps):
        raise ValueError("summed gate potential exceeds gates.total_abs_bound_mev; it is not clipped")
    return GatePotential(tuple(names), basis, coefficients, contributions, total, np.asarray(normalization))
