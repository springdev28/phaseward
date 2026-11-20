"""Paired resampling statistics; inference is conditional on frozen designs."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray


def paired_bootstrap(first: ArrayLike, second: ArrayLike, *, seed: int, resamples: int,
                     confidence: float = .95, family_size: int = 1) -> tuple[dict[str,Any],NDArray]:
    """Basic bootstrap CIs for mean(second-first), preserving disorder-draw pairs.

    Common indices resample paired differences, never independently resampling
    the two methods. A Bonferroni-adjusted interval is also reported for the
    prespecified family. These are approximate finite-sample intervals, not a
    coverage guarantee. Missing pairs are counted explicitly. Relative effect
    divides by the absolute first-method mean; zero denominators stay undefined.
    """
    a,b = np.asarray(first,dtype=float),np.asarray(second,dtype=float)
    if a.ndim != 1 or b.shape != a.shape or np.any(np.isinf(a)) or np.any(np.isinf(b)):
        raise ValueError("paired data must be matching vectors without infinities")
    if type(resamples) is not int or resamples < 2 or not 0 < confidence < 1:
        raise ValueError("invalid bootstrap settings")
    if type(family_size) is not int or family_size < 1:
        raise ValueError("family_size must be positive")
    finite = np.isfinite(a)&np.isfinite(b)
    a,b = a[finite],b[finite]
    result: dict[str,Any] = {"samples_total":len(finite),"paired_samples":len(a),
        "excluded_pairs":int(sum(~finite)),"confidence_level":confidence,"family_size":family_size,
        "resamples":resamples,"bootstrap_seed":seed,"difference_convention":"second minus first",
        "method":"paired basic bootstrap; linear empirical quantiles; Bonferroni primary family",
        "absolute_difference":None,"relative_difference":None,"relative_percent":None,
        "paired_standardized_effect_dz":None,"first_mean":None,"second_mean":None,
        "ci_low":None,"ci_high":None,"family_ci_low":None,"family_ci_high":None,
        "interval_crosses_zero":None,"family_interval_crosses_zero":None,
        "degenerate_empirical_distribution":None,"tail_resamples_expected":resamples*(1-confidence)/(2*family_size)}
    if len(a) < 2:
        result["status"]="insufficient_paired_values"
        return result,np.empty(0)
    delta=b-a
    estimate=float(np.mean(delta))
    # Bounded batching retains the exact same sequence and caps temporary RAM.
    rng=np.random.Generator(np.random.PCG64(seed))
    bootstrap=np.empty(resamples)
    for start in range(0,resamples,256):
        end=min(resamples,start+256)
        indices=rng.integers(0,len(delta),size=(end-start,len(delta)))
        bootstrap[start:end]=np.mean(delta[indices],axis=1)
    def interval(alpha: float) -> tuple[float,float]:
        low,high=np.quantile(bootstrap,[alpha/2,1-alpha/2],method="linear")
        return float(2*estimate-high),float(2*estimate-low)
    low,high=interval(1-confidence)
    flo,fhi=interval((1-confidence)/family_size)
    first_mean,second_mean=float(np.mean(a)),float(np.mean(b))
    sd=float(np.std(delta,ddof=1))
    relative=estimate/abs(first_mean) if first_mean != 0 else None
    result.update(status="ok",absolute_difference=estimate,first_mean=first_mean,second_mean=second_mean,
        relative_difference=relative,relative_percent=None if relative is None else 100*relative,
        paired_standardized_effect_dz=estimate/sd if sd>0 else None,
        ci_low=low,ci_high=high,family_ci_low=flo,family_ci_high=fhi,
        interval_crosses_zero=bool(low<=0<=high),family_interval_crosses_zero=bool(flo<=0<=fhi),
        degenerate_empirical_distribution=bool(sd==0),
        relative_effect_note="undefined at zero baseline; unstable when the baseline mean is close to zero")
    return result,bootstrap


def hypothesis_outcome(interval: dict[str,Any], *, practical_difference: float,
                       eligible: bool) -> str:
    """Classify the prespecified reduction of loss, without choosing the criterion after data."""
    if (not eligible or interval["status"] != "ok" or interval["excluded_pairs"] > 0
            or interval["degenerate_empirical_distribution"] or interval["tail_resamples_expected"] < 10):
        return "unresolved"
    low,high=interval["family_ci_low"],interval["family_ci_high"]
    if high < -practical_difference:
        return "supports"
    if low > -practical_difference:
        # Includes an interval excluding a meaningful benefit, not only harm.
        return "contradicts"
    return "unresolved"

