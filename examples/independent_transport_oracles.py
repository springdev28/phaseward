"""Small independent audit references; deliberately do not import qwave.

These are verification algorithms, not alternative production solvers. The
transfer recurrence is restricted to well-conditioned, modest test devices;
it must never replace the stable banded solver for opaque barriers.
Public units: nm, meV, electron-mass ratios; amplitudes use unit flux and
reference planes at the first and last nodes. Constants are converted here.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.constants import electron_volt, hbar, m_e


def kinetic_coefficient(mass_ratio: float) -> float:
    """Return hbar²/(2m*) in meV nm², independently of production unit helpers."""
    return hbar**2 / (2 * mass_ratio * m_e) / (electron_volt * 1e-3 * 1e-18)


def recurrence_scattering(x: NDArray, potential: NDArray, energies: NDArray, *,
                          mass_ratio: float, left: float = 0., right: float = 0.
                          ) -> tuple[NDArray, NDArray, NDArray]:
    """Match independent second-order recurrences to incoming/reflected leads.

    M maps [psi_0, psi_-1] to [psi_N, psi_(N-1)]. Solving the resulting
    two-by-two boundary system yields wave amplitudes; sqrt(sin(qR)/sin(qL))
    converts transmission to flux normalization. Reject condition >1e8.
    """
    hopping = kinetic_coefficient(mass_ratio) / (x[1] - x[0])**2
    transmissions, reflections, conditions = [], [], []
    for energy in energies:
        cosines = 1 - (energy - np.array([left, right])) / (2 * hopping)
        if np.any(abs(cosines) >= 1):
            raise ValueError("reference requires two open discrete lead channels")
        ql, qr = np.arccos(cosines)
        recurrence = np.eye(2, dtype=complex)
        for value in potential:
            recurrence = np.array([[2 + (value - energy) / hopping, -1], [1, 0]]) @ recurrence
        incident = np.array([1, np.exp(-1j * ql)])
        reflected = np.array([1, np.exp(1j * ql)])
        outgoing = np.array([np.exp(1j * qr), 1])
        matrix = np.column_stack((recurrence @ reflected, -outgoing))
        condition = np.linalg.cond(matrix)
        if not np.isfinite(condition) or condition > 1e8:
            raise ValueError("transfer reference is ill-conditioned; not a production fallback")
        reflection, transmission = np.linalg.solve(matrix, -recurrence @ incident)
        transmissions.append(transmission * np.sqrt(np.sin(qr) / np.sin(ql)))
        reflections.append(reflection)
        conditions.append(condition)
    return np.array(transmissions), np.array(reflections), np.array(conditions)


def rectangular_matching(energies: NDArray, *, height: float, width: float,
                         plane_distance: float, mass_ratio: float
                         ) -> tuple[NDArray, NDArray]:
    """Continuum 4x4 continuity/derivative matching, including E=barrier height.

    Inside use a*cos(q*x)+b*sin(q*x)/q, with sin(q*x)/q -> x at q=0.
    Equal zero-potential leads surround a centered barrier. Symmetric padding
    moves both amplitudes to planes separated by plane_distance (nm).
    """
    coefficient = kinetic_coefficient(mass_ratio)
    transmissions, reflections = [], []
    for energy in energies:
        k = np.sqrt(energy / coefficient)
        q = np.sqrt(complex(energy - height) / coefficient)
        cosine = np.cos(q * width)
        sine_over_q = width if abs(q) < 1e-14 else np.sin(q * width) / q
        matrix = np.array([
            [1, -1, 0, 0], [-1j * k, 0, -1, 0],
            [0, cosine, sine_over_q, -1],
            [0, -q*q*sine_over_q, cosine, -1j*k],
        ], dtype=complex)
        reflection, _, _, transmission = np.linalg.solve(matrix, [-1, -1j*k, 0, 0])
        padding_phase = np.exp(1j*k*(plane_distance-width))
        transmissions.append(transmission*padding_phase)
        reflections.append(reflection*padding_phase)
    return np.array(transmissions), np.array(reflections)


def impurity_amplitudes(energies: NDArray, *, height: float, spacing: float,
                       count: int, site: int, mass_ratio: float
                       ) -> tuple[NDArray, NDArray, NDArray]:
    """Exact discrete single-site t, r and dt/dU; U has units meV.

    With Q=2*tau*sin(q), t=e^(iq(N-1))*Q/(Q+iU). This identity follows by
    matching the wave and recurrence at the one impurity, not by matrix inversion.
    """
    hopping = kinetic_coefficient(mass_ratio)/spacing**2
    q = np.arccos(1-energies/(2*hopping))
    current_scale = 2*hopping*np.sin(q)
    denominator = current_scale+1j*height
    phase = np.exp(1j*q*(count-1))
    t = phase*current_scale/denominator
    r = np.exp(2j*q*site)*(-1j*height)/denominator
    derivative = -1j*phase*current_scale/denominator**2
    return t, r, derivative


def exponential_packet_exact(width: float, attenuation: float, phase_difference: float
                             ) -> tuple[float, float, float, float]:
    """Uniform energy density on width, exponential amplitude and linear phase.

    t(E)=exp[-a*(E-Emin)+i*b*(E-Emin)], reference exp[i*c*(E-Emin)].
    Returns P, raw F, delay-aligned F, lag (ps); a and b-c are in 1/meV.
    This is a synthetic spectral identity, not a scattering-device result.
    """
    probability = -np.expm1(-2*attenuation*width)/(2*attenuation*width)
    exponent = attenuation-1j*phase_difference
    overlap = -np.expm1(-exponent*width)/(exponent*width)
    aligned_overlap = -np.expm1(-attenuation*width)/(attenuation*width)
    hbar_mev_ps = hbar/(electron_volt*1e-3*1e-12)
    return (float(probability), float(abs(overlap)**2/probability),
            float(aligned_overlap**2/probability), float(hbar_mev_ps*phase_difference))
