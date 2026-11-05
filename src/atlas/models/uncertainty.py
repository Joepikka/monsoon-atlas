"""Paired block bootstrap, validation-only intervals and thresholds (T034, plan section 11).

Shared protocol: 1000 resamples with seed 42, resampling whole blocks (events, months or
catchments) so correlated rows move together. The same seed always gives the same interval.
Calibration and thresholds use validation rows only, never test rows.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

RESAMPLES, SEED = 1000, 42


@dataclass(frozen=True)
class Improvement:
    mean: float
    lower95: float
    upper95: float
    n_rows: int
    n_blocks: int


def paired_block_bootstrap(
    baseline_loss: Sequence[float],
    candidate_loss: Sequence[float],
    blocks: Sequence[str],
    *,
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> Improvement:
    """Mean improvement (baseline loss minus candidate loss, positive = candidate better)."""
    base = np.asarray(baseline_loss, dtype=float)
    cand = np.asarray(candidate_loss, dtype=float)
    if not (len(base) == len(cand) == len(blocks)) or len(base) == 0:
        raise ValueError("losses and blocks must be non-empty and the same length")
    if not (np.isfinite(base).all() and np.isfinite(cand).all()):
        raise ValueError("missing or infinite loss: never replaced by 0")
    names = sorted(set(blocks))
    index = {b: i for i, b in enumerate(names)}
    codes = np.array([index[b] for b in blocks])
    diff_sum = np.bincount(codes, weights=base - cand, minlength=len(names))
    count = np.bincount(codes, minlength=len(names))
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(names), size=(resamples, len(names)))
    stats = diff_sum[draws].sum(axis=1) / count[draws].sum(axis=1)
    lo, hi = np.quantile(stats, [0.025, 0.975])
    return Improvement(float((base - cand).mean()), float(lo), float(hi), len(base), len(names))


def conformal_interval(
    validation_residuals: Sequence[float], coverage: float = 0.8
) -> tuple[float, float]:
    """Residual quantiles from validation rows (split conformal); add them to a point forecast."""
    r = np.asarray(validation_residuals, dtype=float)
    if len(r) < 20 or not np.isfinite(r).all():
        raise ValueError("need at least 20 finite validation residuals")
    tail = (1 - coverage) / 2
    lo, hi = np.quantile(r, [tail, 1 - tail])
    return float(lo), float(hi)


def coverage(y: Sequence[float], lower: Sequence[float], upper: Sequence[float]) -> float:
    y, lower, upper = (np.asarray(a, dtype=float) for a in (y, lower, upper))
    return float(((y >= lower) & (y <= upper)).mean())


def select_threshold(y_val: Sequence[int], p_val: Sequence[float], max_alert_rate: float) -> float:
    """Highest-recall threshold on validation rows whose alert rate stays within the cap."""
    y, p = np.asarray(y_val), np.asarray(p_val, dtype=float)
    if len(set(y.tolist())) < 2:
        raise ValueError("validation rows need both classes")
    best, best_recall = 1.0, -1.0
    for t in np.unique(p)[::-1]:
        alerts = p >= t
        if alerts.mean() > max_alert_rate:
            break
        recall = (alerts & (y == 1)).sum() / (y == 1).sum()
        if recall > best_recall:
            best, best_recall = float(t), recall
    return best
