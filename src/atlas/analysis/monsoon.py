"""T145: monsoon tracker, rainfall trend and climate-projection product (derived statistics only).

S08 licence (restricted, D129): area-averaged rainfall in mm is never exported. The product holds
indices only (percent of the 1981-2010 median or mean, percentile rank, slopes). The S08 grid is
held for 1981-2025 only, so trends cover those years and the 1901-1980 gap is stated, never filled.
Climatology is strictly 1981-2010: later and projection years never enter it. S06 results are
climate projections, keyed by model, never a forecast.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping
from datetime import date, timedelta

import numpy as np

REFERENCE = (1981, 2010)
SEASON_START = (6, 1)
PROJECTION_LABEL = "climate projection, not a forecast"
INFERRED = "inferred"
ONSET_RAIN_MM, ONSET_DAYS = 2.5, 3  # heuristic: 3 days in a row with at least 2.5 mm
LIMITS = [
    "Rain values are shown as indices (percent of the 1981-2010 normal or percentile rank), "
    "not as mm: the IMD licence does not allow publishing area-averaged rainfall (D129, H11).",
    "The IMD grid is held for 1981-2025 only; 1901-1980 is not held, so trends cover 1981-2025.",
    "Year 2025 is provisional and the tracker shows a past year; it is not a live feed.",
    "Climate projections are model results for 2021-2050 against 1981-2010, not forecasts; "
    "spread across models is not forecast confidence.",
]


def cumulative(daily: Mapping[date, float | None], year: int, upto: date) -> float | None:
    """Rain summed from 1 Jun to `upto`; None if any day in between is absent (never filled)."""
    day, end, total = date(year, *SEASON_START), upto, 0.0
    while day <= end:
        v = daily.get(day)
        if v is None:
            return None
        total += v
        day += timedelta(days=1)
    return total


def reference_sample(by_year: Mapping[int, float | None]) -> list[float]:
    """Values of the 1981-2010 years only; any other year (recent or projected) is ignored."""
    lo, hi = REFERENCE
    return [v for y, v in by_year.items() if lo <= y <= hi and v is not None]


def percentile_rank(value: float, sample: list[float]) -> float:
    """Share of the sample below the value, ties counted half, in percent."""
    below = sum(s < value for s in sample) + 0.5 * sum(s == value for s in sample)
    return 100 * below / len(sample)


def tracker(
    daily_by_year: Mapping[int, Mapping[date, float | None]], year: int, checkpoints: list[date]
) -> dict:
    """Season-to-date rain at each checkpoint vs the 1981-2010 distribution, as indices."""
    rows = []
    for cp in checkpoints:
        ref = reference_sample(
            {y: cumulative(daily_by_year[y], y, date(y, cp.month, cp.day)) for y in daily_by_year}
        )
        value = cumulative(daily_by_year[year], year, cp)
        row = {"date": cp.isoformat(), "reference_years": len(ref), "value_pct_of_median": None}
        row |= {"rank_percentile": None, "band_p10_pct_of_median": None}
        row |= {"band_p90_pct_of_median": None}
        if value is not None and ref:
            med = statistics.median(ref)
            p10, p90 = np.percentile(ref, [10, 90])
            row |= {
                "value_pct_of_median": round(100 * value / med, 1),
                "rank_percentile": round(percentile_rank(value, ref), 1),
                "band_p10_pct_of_median": round(100 * float(p10) / med, 1),
                "band_p90_pct_of_median": round(100 * float(p90) / med, 1),
            }
        rows.append(row)
    return {"year": year, "reference": f"{REFERENCE[0]}-{REFERENCE[1]}", "checkpoints": rows}


def official_onset(published: Mapping[str, date] | None = None) -> dict:
    """The onset date a source published; null with a reason when no source publishes one."""
    if published:
        source, day = min(published.items(), key=lambda kv: kv[1])
        return {"official_onset": day.isoformat(), "source": source, "reason": None}
    return {
        "official_onset": None,
        "source": None,
        "reason": "no enabled source publishes an IMD onset date (checked S01 to S44 configs)",
    }


def inferred_onset(daily: Mapping[date, float | None], year: int) -> dict:
    """Heuristic onset (first run of rainy days from 1 May to 30 Jun); always labelled inferred."""
    day, last = date(year, 5, 1), date(year, 6, 30)
    method = (
        f"first of {ONSET_DAYS} days in a row with at least {ONSET_RAIN_MM} mm, 1 May to 30 Jun "
        "(a guess that can differ from the date IMD declares)"
    )
    while day <= last:
        run = [daily.get(day + timedelta(days=i)) for i in range(ONSET_DAYS)]
        if all(v is not None and v >= ONSET_RAIN_MM for v in run):
            return {"onset": day.isoformat(), "label": INFERRED, "method": method}
        day += timedelta(days=1)
    return {"onset": None, "label": INFERRED, "method": method}


def mann_kendall(values: list[float]) -> tuple[float, float]:
    """Two-sided Mann-Kendall test: (S, p). Tie-corrected variance, continuity correction,
    normal approximation (fine for n >= 10). Assumes no serial correlation (D196 limit)."""
    from math import erf, sqrt

    x = np.asarray(values, dtype=float)
    n = len(x)
    s = float(sum(np.sign(x[j] - x[i]) for i in range(n - 1) for j in range(i + 1, n)))
    _, counts = np.unique(x, return_counts=True)
    var = (n * (n - 1) * (2 * n + 5) - sum(t * (t - 1) * (2 * t + 5) for t in counts)) / 18
    z = 0.0 if s == 0 else (s - np.sign(s)) / sqrt(var)
    p = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
    return s, float(p)


def sen_slope(years: list[int], values: list[float]) -> float:
    """Median of all pairwise slopes (robust to outlier years)."""
    slopes = [
        (values[j] - values[i]) / (years[j] - years[i])
        for i in range(len(years) - 1)
        for j in range(i + 1, len(years))
    ]
    return float(np.median(slopes))


def trend(area: str, annual: Mapping[int, float | None]) -> dict:
    """Trend of annual rain as percent of the 1981-2010 mean per decade (OLS and Sen), with a
    Mann-Kendall test (D196); years held only."""
    ref = reference_sample(annual)
    years = sorted(y for y, v in annual.items() if v is not None)
    pct = [100 * annual[y] / statistics.fmean(ref) for y in years]
    slope = float(np.polyfit(years, pct, 1)[0]) * 10
    _, p = mann_kendall(pct)
    lag1 = float(np.corrcoef(pct[:-1], pct[1:])[0, 1]) if len(pct) > 2 else None
    return {
        "area": area,
        "first_year": years[0],
        "last_year": years[-1],
        "n_years": len(years),
        "slope_pct_per_decade": round(slope, 2),
        "sen_slope_pct_per_decade": round(sen_slope(years, pct) * 10, 2),
        "mann_kendall_p": round(p, 4),
        "lag1_autocorrelation": None if lag1 is None else round(lag1, 3),
        "significance": "significant at 5% (Mann-Kendall)" if p < 0.05 else "not significant",
    }


def fdr(rows: list[dict]) -> list[dict]:
    """Benjamini-Hochberg q-values across a family of trend tests (D196). The label then uses
    q < 0.05, and a lag-1 autocorrelation above 0.2 is flagged, because it inflates MK."""
    order = sorted(range(len(rows)), key=lambda i: rows[i]["mann_kendall_p"])
    m, q, running = len(rows), [0.0] * len(rows), 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, rows[i]["mann_kendall_p"] * m / rank)
        q[i] = running
    out = []
    for row, qi in zip(rows, q, strict=True):
        qi = round(qi, 4)  # judge the value that is reported
        label = "significant (5% false discovery rate)" if qi < 0.05 else "not significant"
        if qi < 0.05 and (row["lag1_autocorrelation"] or 0) > 0.2:
            label += "; autocorrelated, so weaker than it looks"
        out.append(row | {"fdr_q": qi, "significance": label})
    return out


def projections(rows: Iterable[Mapping]) -> dict:
    """S06 change in mean annual rain (2021-2050 vs 1981-2010), keyed by point then model."""
    by_point: dict[str, dict[str, float]] = {}
    for r in rows:
        by_point.setdefault(r["point"], {})[r["model"]] = float(r["change_pct"])
    spread = {
        p: {"min": min(m.values()), "median": statistics.median(m.values()), "max": max(m.values())}
        for p, m in by_point.items()
    }
    return {
        "label": PROJECTION_LABEL,
        "baseline": "1981-2010",
        "window": "2021-2050",
        "by_point": by_point,
        "model_spread_pct": spread,
    }


def product(**parts) -> dict:
    return {"schema_version": 1, "title": "Monsoon and climate", **parts, "limits": LIMITS}
