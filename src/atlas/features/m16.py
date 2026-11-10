"""M16 cross-state sensor and market anomalies: the card's rule as pure functions (T214).

Target: per feed-entity and report time, `robust_z = (x - median) / (1.4826 * MAD)` against the
trailing 28 report days. The window ends the day before the report: the value itself and any later
value never enter it, so a future row cannot change an earlier flag. A value is flagged when
`abs(robust_z) > 4` or when it breaks a stated physical unit bound. A flag is a data-quality
signal, not a real-world incident: a true flood looks like an outlier too.

Handling that the card does not spell out (D157):
- A missing value (NaN) is never read as 0 and never flags. It is also left out of every window.
- A value that breaks a unit bound flags as `bound` and is left out of later windows.
- MAD of exactly 0 gives no robust z (no division by zero): the row is counted as `mad_zero`, not
  flagged and not silently "normal". Daily rain is zero-heavy, so this is common in dry spells.
- Fewer than MIN_VALID usable values in the 28-day window gives no z (`too_few_valid`).
- The card's season/hour correction is not applied: the trailing window already follows the local
  level, and daily data has no hour. Season only stratifies the report.

shortcut: input is a regular daily grid (rows = days, NaN where absent, columns = entities); an
irregular report time needs a time-based window. The feature framework's `build_features`
(duckdb, one sub-query per row) does not fit millions of cell-days, so as-of safety is tested by
mutating future rows instead.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

WINDOW_DAYS = 28
MIN_VALID = 21  # implementation choice, not on the card: a median of fewer points is unstable
THRESHOLD = 4.0
MAD_SCALE = 1.4826  # makes MAD match the standard deviation of a normal sample
MIN_LABELS = 100  # card data gate: below this, counts and intervals only, no quality claim
STRENGTH = (("4-6", 6.0), ("6-10", 10.0), ("10+", float("inf")))
SEASONS = {  # IMD seasons by calendar month
    **dict.fromkeys((1, 2), "winter"),
    **dict.fromkeys((3, 4, 5), "pre-monsoon"),
    **dict.fromkeys((6, 7, 8, 9), "monsoon"),
    **dict.fromkeys((10, 11, 12), "post-monsoon"),
}
# Row status. Only EVALUATED rows have a robust z.
EVALUATED, MISSING, TOO_FEW_VALID, MAD_ZERO, BOUND = range(5)
STATUS = ("evaluated", "missing", "too_few_valid", "mad_zero", "bound")


def _median(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(median ignoring NaN, count of non-NaN) over the last axis; NaN when nothing is valid."""
    n = (~np.isnan(a)).sum(axis=-1)
    s = np.sort(a, axis=-1)  # NaN sorts last
    lo = np.take_along_axis(s, np.maximum((n - 1) // 2, 0)[..., None], axis=-1)[..., 0]
    hi = np.take_along_axis(s, (n // 2)[..., None], axis=-1)[..., 0]
    return (lo + hi) / 2, n


def detect(
    values: np.ndarray, lower: float | None = None, upper: float | None = None
) -> dict[str, np.ndarray]:
    """Robust z and flags for a (days, entities) array; row t uses only rows before t."""
    x = np.asarray(values, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    with np.errstate(invalid="ignore"):
        bad = np.zeros(x.shape, bool)
        if lower is not None:
            bad |= x < lower
        if upper is not None:
            bad |= x > upper
    clean = np.where(bad, np.nan, x)
    pad = np.vstack([np.full((WINDOW_DAYS, x.shape[1]), np.nan), clean])
    windows = np.lib.stride_tricks.sliding_window_view(pad, WINDOW_DAYS, axis=0)[: len(x)]
    med, n = _median(windows)
    mad, _ = _median(np.abs(windows - med[..., None]))
    status = np.full(x.shape, EVALUATED, np.int8)
    status[n < MIN_VALID] = TOO_FEW_VALID
    status[(mad == 0) & (n >= MIN_VALID)] = MAD_ZERO
    status[bad] = BOUND
    status[np.isnan(x)] = MISSING
    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.where(status == EVALUATED, (x - med) / (MAD_SCALE * mad), np.nan)
    return {
        "z": z,
        "status": status,
        "flag_z": np.abs(z) > THRESHOLD,  # NaN compares False: no z, no flag
        "flag_bound": status == BOUND,
    }


def strength_bucket(z: float) -> str:
    """Strength band of a flagged |z| (above 4)."""
    a = abs(z)
    return next(name for name, top in STRENGTH if a <= top)


def label_gate(adjudicated: int) -> dict:
    """Card data gate: under 100 adjudicated flags no precision or recall claim is allowed."""
    return {
        "adjudicated_flags": adjudicated,
        "required": MIN_LABELS,
        "quality_claim_allowed": adjudicated >= MIN_LABELS,
    }


def rule_parameters() -> Mapping[str, object]:
    return {
        "window_days": WINDOW_DAYS,
        "min_valid_days": MIN_VALID,
        "threshold": THRESHOLD,
        "mad_scale": MAD_SCALE,
        "mad_zero": "no robust z; counted, not flagged",
        "missing": "never zero; never flags; left out of windows",
        "season_hour_correction": "not applied",
    }
