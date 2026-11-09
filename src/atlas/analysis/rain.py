"""T107: annual gauge/grid rainfall comparison with exact denominators.

Gauge = S29 KSNDMC published district totals (annual only, D113); grid = S08 IMD 0.25 degree
analysis (itself interpolated from gauges: a reconstruction), area-weighted to S17 districts. The
S29-to-S17 district names come only from the committed crosswalk CSV; nothing is matched by
guessing, imputed or filled. Bias is grid minus gauge.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path


def load_crosswalk(path: Path) -> dict[str, str]:
    """S29 district name -> S17 district name, one row per S29 name."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out = {r["s29_name"]: r["s17_name"] for r in rows}
    if len(out) != len(rows):
        raise ValueError(f"{path}: repeated s29_name")
    return out


def annual_grid_totals(monthly: Iterable[Mapping]) -> dict[tuple[str, int], float | None]:
    """(S17 name, year) -> sum of 12 monthly means; None if any month is absent or null."""
    months: dict[tuple[str, int], dict[int, float | None]] = defaultdict(dict)
    for r in monthly:
        months[r["name"], r["month"].year][r["month"].month] = r["rain_mm"]
    return {
        k: sum(m.values()) if len(m) == 12 and None not in m.values() else None
        for k, m in months.items()
    }


def compare(
    gauge: Iterable[Mapping],
    grid: Mapping[tuple[str, int], float | None],
    crosswalk: Mapping[str, str],
    exclude: Mapping[tuple[str, int], str],
) -> list[dict]:
    """One row per gauge district-year: compared, 'excluded: reason' or missing (never filled)."""
    out = []
    for r in gauge:
        name, year, g = r["area_id"], r["year"], r["rain_mm"]
        row = {"district": name, "year": year, "gauge_mm": g, "grid_mm": None, "bias_mm": None}
        row |= {"ratio": None, "status": "missing"}
        if (name, year) in exclude:
            row["status"] = f"excluded: {exclude[name, year]}"
        elif name not in crosswalk:
            raise KeyError(f"{name} is neither in the crosswalk nor excluded")
        else:
            s = grid.get((crosswalk[name], year))
            if g is not None and s is not None:
                row |= {"grid_mm": s, "bias_mm": s - g, "ratio": s / g if g else None}
                row["status"] = "compared"
        out.append(row)
    return out


def station_coverage(stations: Iterable[Mapping]) -> list[dict]:
    """Per district (first part of the 'DISTRICT / Taluk / station' path): stations and values."""
    total, with_value = Counter(), Counter()
    for r in stations:
        d = r["area_id"].split(" / ")[0]
        total[d] += 1
        with_value[d] += r["rain_mm"] is not None
    return [
        {
            "district": d,
            "stations": total[d],
            "with_value": with_value[d],
            "share": with_value[d] / total[d],
        }
        for d in sorted(total)
    ]
