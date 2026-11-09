"""T109: spatial residual statistics with exact denominators.

Queen contiguity: two polygons are neighbours when they share any boundary point (touch or
overlap). Weights are row-standardised; a polygon with no neighbour (an island) keeps a zero
row and is reported. Moran's I is tested with permutations under the randomisation null and a
two-sided pseudo p-value; Benjamini-Hochberg adjusts a family of p-values; the semivariogram
pools same-time pairs by centroid distance and reports every pair count.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def queen_neighbours(polygons: Sequence) -> tuple[list[list[int]], list[int]]:
    """Neighbour indices per polygon (shapely geometries) and the islands (no neighbour)."""
    nbrs = [
        [j for j, b in enumerate(polygons) if j != i and a.intersects(b)]
        for i, a in enumerate(polygons)
    ]
    return nbrs, [i for i, n in enumerate(nbrs) if not n]


def row_standardised(neighbours: list[list[int]]) -> np.ndarray:
    """Dense weights: 1/k for each of a polygon's k neighbours; island rows stay zero."""
    w = np.zeros((len(neighbours), len(neighbours)))
    for i, nb in enumerate(neighbours):
        if nb:
            w[i, nb] = 1.0 / len(nb)
    return w


def morans_i(x: np.ndarray, w: np.ndarray) -> float:
    """I = (n / S0) * sum_ij w_ij z_i z_j / sum_i z_i^2, z = x - mean(x)."""
    z = np.asarray(x, dtype=float) - np.mean(x)
    return float(len(z) / w.sum() * (z @ w @ z) / (z @ z))


def permutation_test(x: np.ndarray, w: np.ndarray, rng: np.random.Generator, n: int = 999) -> dict:
    """Moran's I against n random relabellings of x over the polygons.

    Two-sided pseudo p = (1 + #{|I_perm - E| >= |I_obs - E|}) / (n + 1), E = -1 / (N - 1):
    residual clustering and residual dispersion both count against the model.
    """
    x = np.asarray(x, dtype=float)
    observed, expected = morans_i(x, w), -1.0 / (len(x) - 1)
    perms = np.array([morans_i(rng.permutation(x), w) for _ in range(n)])
    extreme = int((np.abs(perms - expected) >= abs(observed - expected)).sum())
    return {
        "moran_i": observed,
        "expected": expected,
        "p": (1 + extreme) / (n + 1),
        "as_extreme": extreme,
        "permutations": n,
    }


def benjamini_hochberg(p: Sequence[float]) -> np.ndarray:
    """BH q-values in input order: min over k >= rank of p_(k) * m / k, capped at 1."""
    p = np.asarray(p, dtype=float)
    order = np.argsort(p, kind="stable")
    scaled = p[order] * len(p) / np.arange(1, len(p) + 1)
    q = np.empty_like(p)
    q[order] = np.minimum(np.minimum.accumulate(scaled[::-1])[::-1], 1.0)
    return q


def semivariogram(xy_km: np.ndarray, values: np.ndarray, edges: Sequence[float]) -> list[dict]:
    """gamma(h) = sum (v_i - v_j)^2 / (2 N(h)) over same-row pairs i < j with distance in
    [lo, hi). values has one row per time and one column per site; NaN values are skipped and
    counted out. N(h) is the number of pair-times used."""
    xy = np.asarray(xy_km, dtype=float)
    values = np.atleast_2d(np.asarray(values, dtype=float))
    i, j = np.triu_indices(len(xy), 1)
    dist = np.hypot(*(xy[i] - xy[j]).T)
    diff2 = (values[:, i] - values[:, j]) ** 2
    out = []
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        sel = (dist >= lo) & (dist < hi)
        d = diff2[:, sel]
        used = d[~np.isnan(d)]
        out.append(
            {
                "lo_km": float(lo),
                "hi_km": float(hi),
                "site_pairs": int(sel.sum()),
                "times": len(values),
                "pair_times": int(used.size),
                "mean_km": float(dist[sel].mean()) if sel.any() else None,
                "gamma": float(used.sum() / (2 * used.size)) if used.size else None,
            }
        )
    return out
