"""Gaussian potential disorder with spatially normalized Karhunen–Loeve modes.

phi.T W phi = I; lambda has units meV² nm; eta has variance lambda.
deltaV = phi eta, with eta=sqrt(lambda)*z and independent standard normals z.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.linalg import eigh

from qwave.gates import channel_envelope, real_setting
from qwave.scattering import uniform_grid
from qwave.wavepackets import quadrature_weights

KERNELS = ("gaussian", "exponential", "matern32")


def covariance_matrix(x_nm: ArrayLike, *, sigma_mev: float, correlation_length_nm: float,
                      kernel: str = "gaussian", boundary_taper_nm: float = 0.) -> NDArray[np.float64]:
    """Nodal covariance in meV²; a declared taper multiplies C by b(x)b(x')."""
    x, _ = uniform_grid(x_nm)
    if len(x) > 801:
        raise ValueError("dense covariance construction is limited to 801 channel nodes")
    sigma = real_setting(sigma_mev, "sigma_mev")
    ell = real_setting(correlation_length_nm, "correlation_length_nm", positive=True)
    if sigma < 0 or kernel not in KERNELS:
        raise ValueError(f"sigma_mev must be nonnegative and kernel must be one of {KERNELS}")
    distance = abs(x[:, None]-x[None, :])/ell
    if kernel == "gaussian":
        correlation = np.exp(-.5*distance**2)
    elif kernel == "exponential":
        correlation = np.exp(-distance)
    else:
        scaled = np.sqrt(3)*distance
        correlation = (1+scaled)*np.exp(-scaled)
    envelope = channel_envelope(x, (float(x[0]), float(x[-1])), boundary_taper_nm)
    covariance = sigma**2*correlation*envelope[:, None]*envelope[None, :]
    if not np.all(np.isfinite(covariance)):
        raise ValueError("covariance is not representable in float64")
    return covariance


@dataclass(frozen=True)
class CovarianceModes:
    """Weighted decomposition; shape columns include all modes in decreasing variance order."""

    x_nm: NDArray[np.float64]
    weights_nm: NDArray[np.float64]
    covariance_mev2: NDArray[np.float64]
    eigenvalues_mev2_nm: NDArray[np.float64]
    shapes_per_sqrt_nm: NDArray[np.float64]
    retained_modes: int
    diagnostics: dict[str, Any]

    @property
    def retained_shapes(self) -> NDArray[np.float64]:
        """The K quadrature-orthonormal mode columns."""
        return self.shapes_per_sqrt_nm[:, :self.retained_modes]

    @property
    def retained_eigenvalues(self) -> NDArray[np.float64]:
        """Coefficient variances, without absorbing them into the shapes."""
        return self.eigenvalues_mev2_nm[:self.retained_modes]

    @property
    def retained_covariance(self) -> NDArray[np.float64]:
        """Covariance represented by K modes; no variance-restoring rescale."""
        return (self.retained_shapes*self.retained_eigenvalues) @ self.retained_shapes.T


def covariance_modes(x_nm: ArrayLike, covariance_mev2: ArrayLike, *, retained_modes: int) -> CovarianceModes:
    """Diagonalize sqrt(W) C sqrt(W), with explicit spatial quadrature and no jitter.

    Roundoff-scale negative eigenvalues are set to zero and reported. Materially
    indefinite matrices and unresolved retained modes are rejected. Eigenvector
    signs are chosen to make each largest-magnitude entry positive.
    """
    x, _ = uniform_grid(x_nm)
    if len(x) > 801:
        raise ValueError("dense covariance decomposition is limited to 801 channel nodes")
    raw = np.asarray(covariance_mev2)
    if np.iscomplexobj(raw) or raw.dtype.kind not in "iuf":
        raise ValueError("covariance must be real")
    covariance = np.asarray(raw, dtype=float)
    if covariance.shape != (len(x), len(x)) or not np.all(np.isfinite(covariance)):
        raise ValueError("covariance must be a finite square matrix matching the channel grid")
    if type(retained_modes) is not int or not 1 <= retained_modes <= len(x):
        raise ValueError("retained_modes must be an integer between 1 and the channel node count")
    scale = float(np.max(abs(covariance)))
    if scale <= 0 or np.max(abs(covariance-covariance.T)) > 64*np.finfo(float).eps*scale:
        raise ValueError("KL requires a nonzero symmetric covariance; use disorder scale zero for a clean solve")
    weights = quadrature_weights(x)
    root = np.sqrt(weights)
    matrix = root[:, None]*(.5*(covariance+covariance.T))*root[None, :]
    values, vectors = eigh(matrix, driver="evd", check_finite=False)
    values, vectors = values[::-1].copy(), vectors[:, ::-1].copy()
    threshold = float(64*len(x)*np.finfo(float).eps*max(abs(values)))
    if values[-1] < -threshold:
        raise ValueError("covariance is not positive semidefinite beyond eigensolver roundoff")
    raw_min = float(values[-1])
    negative_count = int(np.count_nonzero(values < 0))
    clipped_mass = float(-np.sum(values[values < 0]))
    values = np.maximum(values, 0.)
    rank = int(np.count_nonzero(values > threshold))
    if retained_modes > rank:
        raise ValueError(f"requested {retained_modes} modes but only {rank} have resolved positive eigenvalues")
    for column in range(len(x)):
        peak = int(np.argmax(abs(vectors[:, column])))
        if vectors[peak, column] < 0:
            vectors[:, column] *= -1
    shapes = vectors/root[:, None]
    trace = float(np.dot(weights, np.diag(covariance)))
    represented = (shapes*values) @ shapes.T
    diagnostics = {
        "normalization": "phi.T W phi = I; eta_k variance=lambda_k; deltaV=phi eta",
        "total_integrated_variance_mev2_nm": trace,
        "retained_integrated_variance_mev2_nm": float(sum(values[:retained_modes])),
        "retained_variance_fraction": float(sum(values[:retained_modes])/trace),
        "resolved_rank": rank, "eigenvalue_resolution_threshold_mev2_nm": threshold,
        "minimum_raw_eigenvalue_mev2_nm": raw_min, "negative_eigenvalues_clipped": negative_count,
        "clipped_negative_eigenvalue_mass_mev2_nm": clipped_mass,
        "weighted_orthogonality_error": float(np.max(abs(shapes.T @ (weights[:, None]*shapes)-np.eye(len(x))))),
        "full_covariance_relative_frobenius_error": float(np.linalg.norm(represented-covariance)/np.linalg.norm(covariance)),
        "boundary_handling": "covariance on channel nodes; potential samples are zero outside the channel",
    }
    return CovarianceModes(x.copy(), weights, covariance.copy(), values, shapes, retained_modes, diagnostics)


def seed_generator(seed: int) -> np.random.Generator:
    """Local PCG64 stream from an explicit unsigned 64-bit integer seed."""
    if type(seed) is not int or not 0 <= seed <= 2**64-1:
        raise ValueError("seed must be an integer in [0, 2**64-1]")
    return np.random.Generator(np.random.PCG64(seed))


@dataclass(frozen=True)
class DisorderSamples:
    """Paired full/K-mode samples from the same stored standard-normal draws."""

    standard_normals: NDArray[np.float64]
    coefficients_mev_sqrt_nm: NDArray[np.float64]
    full_mev: NDArray[np.float64]
    retained_mev: NDArray[np.float64]


def sample_disorder(modes: CovarianceModes, *, sample_count: int, seed: int) -> DisorderSamples:
    """Draw coefficients once and retain full samples plus their K-mode projections."""
    if type(sample_count) is not int or not 2 <= sample_count <= 20_000:
        raise ValueError("sample_count must be an integer in [2, 20000]")
    if sample_count*len(modes.x_nm) > 4_000_000:
        raise ValueError("disorder sample matrix exceeds the 4,000,000 value budget")
    z = seed_generator(seed).standard_normal((sample_count, len(modes.x_nm)))
    eta = z*np.sqrt(modes.eigenvalues_mev2_nm)
    full = eta @ modes.shapes_per_sqrt_nm.T
    retained = eta[:, :modes.retained_modes] @ modes.retained_shapes.T
    return DisorderSamples(z, eta, full, retained)


def covariance_statistics(samples_mev: ArrayLike, target_covariance_mev2: ArrayLike) -> dict[str, Any]:
    """Unbiased sample covariance, with Gaussian sampling uncertainties, not confidence bounds."""
    samples = np.asarray(samples_mev, dtype=float)
    target = np.asarray(target_covariance_mev2, dtype=float)
    if samples.ndim != 2 or len(samples) < 2 or target.shape != (samples.shape[1],)*2:
        raise ValueError("samples must be (draws,nodes) with a matching covariance")
    if not np.all(np.isfinite(samples)) or not np.all(np.isfinite(target)):
        raise ValueError("samples and target must be finite")
    empirical = np.cov(samples, rowvar=False, ddof=1)
    mean = np.mean(samples, axis=0)
    diagonal = np.diag(target)
    active = diagonal > max(float(max(diagonal)), 1e-300)*1e-14
    if not np.any(active):
        raise ValueError("empirical covariance check requires resolved nonzero target variance")
    n = len(samples)
    expected_rms = np.sqrt((np.sum(target**2)+np.trace(target)**2)/(n-1))
    summary = {
        "sample_count": n, "ddof": 1,
        "relative_frobenius_error": float(np.linalg.norm(empirical-target)/np.linalg.norm(target)),
        "frobenius_error_in_expected_sampling_rms": float(np.linalg.norm(empirical-target)/expected_rms),
        "max_abs_mean_in_standard_errors": float(max(abs(mean[active])/np.sqrt(diagonal[active]/n))),
        "max_abs_variance_error_in_standard_errors": float(max(abs(np.diag(empirical)[active]-diagonal[active])/
                                                                   (diagonal[active]*np.sqrt(2/(n-1))))),
        "mean_variance_ratio_on_active_nodes": float(np.mean(np.diag(empirical)[active]/diagonal[active])),
        "active_node_variance_floor_fraction": 1e-14,
        "uncertainty_note": "Gaussian standard errors and expected Frobenius RMS; correlated entries, not a simultaneous confidence interval",
    }
    return {"summary": summary, "mean_mev": mean, "empirical_covariance_mev2": empirical}


def lag_correlations(covariance_mev2: ArrayLike) -> NDArray[np.float64]:
    """Average node-pair correlations at each lag, excluding zero-variance nodes."""
    covariance = np.asarray(covariance_mev2, dtype=float)
    diagonal = np.diag(covariance)
    denominator = np.sqrt(np.maximum(diagonal[:, None]*diagonal[None, :], 0.))
    floor = max(float(max(diagonal)), 1e-300)*1e-14
    correlation = np.divide(covariance, denominator, out=np.full_like(covariance, np.nan), where=denominator > floor)
    result = np.full(len(covariance), np.nan)
    for lag in range(len(covariance)):
        entries = np.diag(correlation, k=lag)
        finite = entries[np.isfinite(entries)]
        if len(finite):
            result[lag] = float(np.mean(finite))
    return result
