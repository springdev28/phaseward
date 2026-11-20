"""Verify the newly derived projection identities and execute the learning notebooks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from qwave.scattering import solve_scattering
from qwave.sensitivity import transmission_gradient
from qwave.wavepackets import analyze_packet, gaussian_packet

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "derivations"


def physical_packet():
    """A fixed, resolved Gaussian-barrier case; no optimizer or held-out draw."""
    x = np.linspace(-30., 30., 241)
    energy = np.linspace(15., 65., 201)
    potential = 18.*np.exp(-.5*(x/4.)**2)
    direction = 5.*np.exp(-.5*((x-5.)/3.)**2)
    response = transmission_gradient(x, potential, energy, effective_mass_ratio=.067)
    packet = gaussian_packet(energy, central_energy_mev=40., bandwidth_mev=6.,
                             propagating_bounds_mev=(0., 4*response.baseline.hopping_mev))
    return x, energy, potential, direction, response, packet


def test_documented_projection_identity_and_probability_bound() -> None:
    """Check O2/O3 on real physical outputs with the energy measure and conjugate."""
    x, energy, potential, direction, response, packet = physical_packet()
    changed = solve_scattering(x, potential+direction, energy, effective_mass_ratio=.067)
    metrics = analyze_packet(energy, packet.amplitude, changed.t, response.baseline.t)
    base = packet.amplitude*response.baseline.t
    delta = packet.amplitude*(changed.t-response.baseline.t)
    weights = packet.weights_mev
    P0 = float(np.dot(weights, abs(base)**2))
    h = base/np.sqrt(P0)
    parallel = np.dot(weights*h.conj(), delta)
    orthogonal = delta-h*parallel
    projected = float(np.dot(weights, abs(orthogonal)**2)/metrics.p_transmitted)
    # Absolute roundoff tolerance: this is an exact identity for the sampled inner product.
    assert 1-metrics.raw_fidelity == pytest.approx(projected, abs=2e-14)
    delta_norm2 = float(np.dot(weights, abs(delta)**2))
    assert projected <= delta_norm2/metrics.p_transmitted+1e-14
    assert abs(metrics.p_transmitted-P0) <= 2*np.sqrt(P0*delta_norm2)+delta_norm2+1e-14


def test_documented_projected_taylor_coefficient() -> None:
    """The normalized-infidelity coefficient is the projected response, not raw J."""
    x, energy, potential, direction, response, packet = physical_packet()
    base = packet.amplitude*response.baseline.t
    weights = packet.weights_mev
    P0 = float(np.dot(weights, abs(base)**2))
    target = base/np.sqrt(P0)
    first_order = packet.amplitude*(response.dt_dpotential_per_mev@direction)
    coefficient = float((np.dot(weights, abs(first_order)**2)-
                         abs(np.dot(weights*target.conj(), first_order))**2)/P0)
    assert coefficient > 0
    errors = []
    for scale in (.08, .04, .02):
        result = solve_scattering(x, potential+scale*direction, energy, effective_mass_ratio=.067)
        metrics = analyze_packet(energy, packet.amplitude, result.t, response.baseline.t)
        estimate = (1-metrics.raw_fidelity)/scale**2
        errors.append(abs(estimate-coefficient))
    # O(epsilon) correction after dividing by epsilon²; measurable before cancellation.
    assert errors[0] > errors[1] > errors[2]
    assert errors[-1]/coefficient < .02  # resolution-specific small-perturbation guard


def test_global_phase_surrogate_is_not_fidelity_loss() -> None:
    """A first-order amplitude-change norm counts a pure global phase (O2)."""
    _, energy, _, _, response, packet = physical_packet()
    clean = response.baseline.t
    metrics = analyze_packet(energy, packet.amplitude, clean*np.exp(.7j), clean)
    derivative = .7j*clean  # synthetic derivative with respect to dimensionless zeta
    J = float(.01*np.dot(packet.weights_mev*abs(packet.amplitude)**2, abs(derivative)**2))
    assert J > 0
    assert metrics.raw_fidelity == pytest.approx(1., abs=2e-14)
    assert metrics.p_transmitted == pytest.approx(metrics.p_reference, abs=2e-14)


def test_learning_notebooks_execute_and_are_auditable(tmp_path: Path) -> None:
    """Real library calls, embedded figures, complete checks and hashes; no kernel."""
    output = tmp_path / "learning"
    command = [sys.executable, str(GUIDE / "run_notebooks.py"), "--output", str(output)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=150)
    assert result.returncode == 0, result.stdout+result.stderr
    check = subprocess.run([sys.executable, str(GUIDE / "check_package.py"), "--results", str(output)],
                           cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert check.returncode == 0, check.stdout+check.stderr
    counts = json.loads(check.stdout)
    assert counts["equation_anchors"] == 33
    assert counts["checked_inventory_hashes"] > 0
    manifest = json.loads((output / "manifest.json").read_text())
    assert len(manifest["results"]) == 4
    for executed in output.glob("*.executed.ipynb"):
        cells = json.loads(executed.read_text())["cells"]
        code = [cell for cell in cells if cell["cell_type"] == "code"]
        assert [cell["execution_count"] for cell in code] == list(range(1, len(code)+1))
        assert all(o["output_type"] != "error" for cell in code for o in cell["outputs"])
        assert any("image/png" in o.get("data", {}) for cell in code for o in cell["outputs"])
    before = (output / "manifest.json").read_bytes()
    duplicate = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert duplicate.returncode != 0
    assert (output / "manifest.json").read_bytes() == before


def test_failed_notebook_clears_stale_outputs_and_has_no_success_manifest(tmp_path: Path) -> None:
    """A failed cell cannot leave fabricated old outputs marked as newly executed."""
    sys.path.insert(0, str(GUIDE))
    try:
        from run_notebooks import execute_notebook
        source = tmp_path / "fail.ipynb"
        source.write_text(json.dumps({"nbformat": 4, "nbformat_minor": 5, "metadata": {}, "cells": [
            {"cell_type": "code", "id": "first", "metadata": {}, "source": ["raise ValueError('intentional check')"],
             "execution_count": 8, "outputs": []},
            {"cell_type": "code", "id": "second", "metadata": {}, "source": ["print('not reached')"],
             "execution_count": 9, "outputs": [{"output_type": "stream", "name": "stdout", "text": "stale"}]},
        ]}))
        with pytest.raises(RuntimeError, match="intentional check"):
            execute_notebook(source, tmp_path)
        executed = json.loads((tmp_path / "fail.executed.ipynb").read_text())
        assert executed["cells"][0]["outputs"][0]["output_type"] == "error"
        assert executed["cells"][1]["execution_count"] is None
        assert executed["cells"][1]["outputs"] == []
        assert not (tmp_path / "manifest.json").exists()
    finally:
        sys.path.remove(str(GUIDE))


def test_math_delimiter_checks_reject_broken_latex() -> None:
    """The structural checker detects bracket, dollar and environment mistakes."""
    sys.path.insert(0, str(GUIDE))
    try:
        from check_package import math_blocks
        for value in ("$$x^2", "$x$$", "$$x_{1$$", "$$\\begin{cases}x\\end{pmatrix}$$"):
            with pytest.raises(ValueError):
                math_blocks(value)
        assert len(math_blocks("Inline $z^*z$ and\n$$\\int_a^b f(x)\\,dx$$")) == 2
    finally:
        sys.path.remove(str(GUIDE))
