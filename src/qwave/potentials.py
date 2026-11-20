"""Real potential-energy profiles in meV sampled on a uniform nm grid."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.interpolate import PchipInterpolator

from qwave.scattering import ScatteringError, real_vector, uniform_grid

POTENTIAL_FIELDS: dict[str, set[str]] = {
    "free": {"kind", "offset_mev"},
    "rectangular": {"kind", "offset_mev", "height_mev", "center_nm", "width_nm"},
    "gaussian": {"kind", "offset_mev", "height_mev", "center_nm", "sigma_nm"},
    "double_barrier": {"kind", "offset_mev", "height_mev", "center_nm", "width_nm", "separation_nm"},
    "tabulated": {"kind", "x_nm", "values_mev", "interpolation"},
}


def validate_potential_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a complete profile specification; no executable text is accepted."""
    if not isinstance(spec, Mapping) or not isinstance(spec.get("kind"), str):
        raise ScatteringError("potential must be an object with a string kind")
    kind = spec["kind"]
    if kind not in POTENTIAL_FIELDS or set(spec) != POTENTIAL_FIELDS[kind]:
        raise ScatteringError(f"invalid fields for potential kind {kind!r}; allowed profiles: {sorted(POTENTIAL_FIELDS)}")
    normalized: dict[str, Any] = {"kind": kind}
    if kind == "tabulated":
        x = real_vector(spec["x_nm"], "potential.x_nm", minimum_size=3)
        values = real_vector(spec["values_mev"], "potential.values_mev", minimum_size=3)
        if len(x) != len(values) or not np.all(np.diff(x) > 0):
            raise ScatteringError("tabulated coordinates must be increasing and match values_mev")
        if spec["interpolation"] != "pchip":
            raise ScatteringError("tabulated potential requires explicit interpolation='pchip'")
        normalized.update(x_nm=x.tolist(), values_mev=values.tolist(), interpolation="pchip")
    else:
        for key in POTENTIAL_FIELDS[kind] - {"kind"}:
            value = spec[key]
            if type(value) not in (float, int) or not np.isfinite(value):
                raise ScatteringError(f"potential.{key} must be a finite real number")
            if key in {"width_nm", "sigma_nm", "separation_nm"} and value <= 0:
                raise ScatteringError(f"potential.{key} must be positive")
            normalized[key] = float(value)
        if kind == "double_barrier" and normalized["separation_nm"] < normalized["width_nm"]:
            raise ScatteringError("double-barrier center separation must be at least the width")
    return normalized


def sample_callable(x_nm: ArrayLike, potential: Callable[[NDArray[np.float64]], ArrayLike]) -> NDArray[np.float64]:
    """Sample a user-defined real V(x_nm) -> meV, one value per coordinate."""
    x, _ = uniform_grid(x_nm)
    values = real_vector(potential(x.copy()), "callable potential_mev", minimum_size=3)
    if values.shape != x.shape:
        raise ScatteringError("user-defined potential must return one value per grid node")
    return values


def sample_potential(x_nm: ArrayLike, spec: Mapping[str, Any]) -> NDArray[np.float64]:
    """Sample a profile; rectangular edges use cell-averaged heights.

    Overlap with [x_i-a/2,x_i+a/2] avoids adding a whole cell when an interface
    lies on a node. Smooth Gaussian/PCHIP profiles are point sampled. Separately
    specified uniform leads take over outside the finite region.
    """
    x, spacing = uniform_grid(x_nm)
    settings = validate_potential_spec(spec)
    kind = settings["kind"]
    if kind == "tabulated":
        if settings["x_nm"][0] > x[0] or settings["x_nm"][-1] < x[-1]:
            raise ScatteringError("tabulated potential must cover the entire device; extrapolation is disabled")
        return np.asarray(PchipInterpolator(settings["x_nm"], settings["values_mev"], extrapolate=False)(x))
    values = np.full_like(x, settings["offset_mev"])
    if kind == "free":
        return values
    if kind == "gaussian":
        return values + settings["height_mev"] * np.exp(-0.5 * ((x - settings["center_nm"]) / settings["sigma_nm"]) ** 2)
    centers = [settings["center_nm"]]
    if kind == "double_barrier":
        centers = [settings["center_nm"] + sign * settings["separation_nm"] / 2 for sign in (-1, 1)]
    for center in centers:
        left, right = center - settings["width_nm"] / 2, center + settings["width_nm"] / 2
        if left <= x[0] or right >= x[-1]:
            raise ScatteringError("rectangular barriers must lie strictly inside the finite region")
        overlap = np.maximum(0, np.minimum(x + spacing / 2, right) - np.maximum(x - spacing / 2, left))
        values += settings["height_mev"] * overlap / spacing
    return values
