"""Lightweight display of declared device geometry; no new physical calculations."""

from __future__ import annotations

from typing import Any
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np

from qwave.gui_config import PreviewSettings

COLORS = ("#087E8B", "#7755A2", "#D07A30", "#497DB8", "#B35872", "#629246", "#9A693F", "#2F7284")


def device_figure(arrays: dict[str, np.ndarray], channel: dict[str, Any],
                  settings: PreviewSettings | None = None) -> Figure:
    """Plot energy contributions with positions and lead boundaries, never trajectories."""
    figure = Figure(figsize=(9,3.6), layout="constrained")
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    x = arrays["x_nm"]
    contributions = arrays["gate_contributions_mev"]
    for j in range(contributions.shape[1]):
        axis.plot(x, contributions[:,j], color=COLORS[j%len(COLORS)], lw=1.3, alpha=.85, label=f"Gate {j+1}")
    axis.plot(x, arrays["potential_mev"], color="#152B42", lw=2.6, label="Total V(x)")
    axis.axvspan(x[0],channel["x_min_nm"],color="#DCE5EF",alpha=.6)
    axis.axvspan(channel["x_max_nm"],x[-1],color="#DCE5EF",alpha=.6)
    if settings is not None:
        for j, fraction in enumerate(settings.gate_fractions):
            axis.axvline(fraction*settings.length_nm,color=COLORS[j],ls=":",alpha=.25)
    axis.set(xlabel="Position x (nm)",ylabel="Potential energy (meV)",title="Gate contributions and device potential")
    axis.legend(ncols=5,frameon=False,loc="upper left",fontsize=8)
    axis.grid(alpha=.12)
    return figure
