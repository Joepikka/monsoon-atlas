"""T142: event-study checks (pre-trend, placebo, cluster-robust SEs) for the rain-to-price study.

S22/S23 hold no price rows (D120, D126), so nothing is estimated yet; these helpers make the method
ready. An estimate is labelled causal only when every pre-event lead's 95% CI covers 0 and the
placebo estimate's CI covers 0. Otherwise, or with no data, it is "association only" (D127).
"""

from __future__ import annotations

import textwrap
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from scipy import stats

ASSOCIATION = "association only"
CAUSAL = "causal estimate (pre-trend and placebo checks passed)"


def ols_cluster(y, X, clusters) -> tuple[np.ndarray, np.ndarray]:
    """OLS coefficients and CR1 cluster-robust covariance (G/(G-1) * (n-1)/(n-k) factor)."""
    y, X, g = np.asarray(y, float), np.asarray(X, float), np.asarray(clusters)
    n, k = X.shape
    ids = np.unique(g)
    if len(ids) < 2 or n <= k:
        raise ValueError("need at least 2 clusters and more rows than columns")
    bread = np.linalg.inv(X.T @ X)
    beta = bread @ X.T @ y
    u = y - X @ beta
    scores = [X[g == c].T @ u[g == c] for c in ids]
    meat = sum(np.outer(s, s) for s in scores)
    factor = len(ids) / (len(ids) - 1) * (n - 1) / (n - k)
    return beta, factor * bread @ meat @ bread


def ci95(beta, cov, n_clusters: int) -> np.ndarray:
    """(k, 2) array of 95% CIs with the t(G-1) critical value (few clusters)."""
    se = np.sqrt(np.diag(cov))
    t = stats.t.ppf(0.975, n_clusters - 1)
    return np.column_stack([beta - t * se, beta + t * se])


def event_design(unit, period, event_period, leads: int, lags: int):
    """Unit and period fixed effects plus event-time dummies -leads..lags (reference -1).

    `event_period[i]` is the unit's event period or None for a never-treated control. Treated
    rows outside the window are dropped (returned mask), so they never join the reference.
    Returns (X, names, keep).
    """
    unit, period = np.asarray(unit), np.asarray(period, int)
    treated = np.array([e is not None for e in event_period])
    rel = np.array(
        [p - e if e is not None else 0 for p, e in zip(period, event_period, strict=True)], int
    )
    keep = ~treated | ((rel >= -leads) & (rel <= lags))
    unit, period, rel, treated = unit[keep], period[keep], rel[keep], treated[keep]
    cols, names = [np.ones(len(unit))], ["const"]
    for u in np.unique(unit)[1:]:
        cols.append((unit == u).astype(float))
        names.append(f"unit={u}")
    for p in np.unique(period)[1:]:
        cols.append((period == p).astype(float))
        names.append(f"period={p}")
    for e in range(-leads, lags + 1):
        if e != -1:
            cols.append((treated & (rel == e)).astype(float))
            names.append(f"event_time={e}")
    return np.column_stack(cols), names, keep


def verdict(lead_cis: Sequence[Sequence[float]], placebo_ci: Sequence[float] | None) -> dict:
    """Identification checks; any failure (or no leads / no placebo) means association only."""

    def covers(ci):
        return ci[0] <= 0 <= ci[1]

    pre = len(lead_cis) > 0 and all(covers(c) for c in lead_cis)
    placebo = placebo_ci is not None and covers(placebo_ci)
    return {
        "pretrend_pass": bool(pre),
        "placebo_pass": bool(placebo),
        "label": CAUSAL if pre and placebo else ASSOCIATION,
    }


def coef_chart(path: Path, event_times, beta, ci, *, source: str, vintage: str, label: str):
    """Event-time coefficients with 95% CI bars; refuses a chart without CI, source or vintage."""
    import matplotlib.pyplot as plt

    ci = np.asarray(ci, float)
    if not source.strip() or not vintage.strip():
        raise ValueError("an event-study chart needs a source and a vintage label")
    if ci.shape != (len(beta), 2) or not np.isfinite(ci).all():
        raise ValueError("an event-study chart needs a finite 95% CI for every coefficient")
    beta = np.asarray(beta, float)
    fig, ax = plt.subplots(figsize=(6, 4))
    fig.subplots_adjust(bottom=0.22)
    ax.errorbar(event_times, beta, yerr=[beta - ci[:, 0], ci[:, 1] - beta], fmt="o", capsize=3)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("Event time (reference -1)")
    ax.set_ylabel("Coefficient (95% CI, cluster-robust)")
    ax.set_title(f"Event study: {label}", fontsize=10)
    cap = f"Source: {source}. Vintage: {vintage}."
    fig.text(0.01, 0.01, textwrap.fill(cap, 100), fontsize=6)
    fig.savefig(path, dpi=80, metadata={"Software": None})
    plt.close(fig)
    return {
        "file": Path(path).name,
        "ci": "95% cluster-robust",
        "source": source,
        "vintage": vintage,
    }
