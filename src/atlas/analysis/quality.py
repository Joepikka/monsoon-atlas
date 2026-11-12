"""T106: feed-quality measures with exact denominators.

Coverage counts present cell-days against every calendar day in the requested range times the
number of cells; a missing day is any day with fewer cells than expected (never filled); the
duplicate fraction is repeated keys over all keys; the ECDF is over every observed lag.
"""

from __future__ import annotations

import calendar
import json
from collections import Counter
from collections.abc import Hashable, Iterable, Mapping
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

from atlas.contracts import RawArtifact
from atlas.ingest.s08 import UNDEF, read_grid, state_cells


def days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def month_coverage(present: Mapping[date, int], cells: int, start: date, end: date) -> list[dict]:
    """Per year-month: expected cell-days (calendar days x cells), present cell-days, share."""
    out: dict[tuple[int, int], dict] = {}
    for d in days(start, end):
        row = out.setdefault(
            (d.year, d.month), {"year": d.year, "month": d.month, "expected": 0, "present": 0}
        )
        row["expected"] += cells
        row["present"] += min(present.get(d, 0), cells)
    for row in out.values():
        row["share"] = row["present"] / row["expected"]
    return list(out.values())


def missing_days(present: Mapping[date, int], cells: int, start: date, end: date) -> list[dict]:
    """Days with fewer reporting cells than expected, with the number missing."""
    return [
        {"date": d.isoformat(), "missing_cells": cells - present.get(d, 0), "cells": cells}
        for d in days(start, end)
        if present.get(d, 0) < cells
    ]


def duplicate_fraction(keys: Iterable[Hashable]) -> dict:
    """Repeated keys (every copy after the first) over all keys."""
    counts = Counter(keys)
    total = sum(counts.values())
    duplicates = total - len(counts)
    return {
        "total": total,
        "duplicates": duplicates,
        "fraction": duplicates / total if total else None,
    }


def ecdf(values: Iterable[float]) -> list[dict]:
    """Empirical CDF: each distinct value and the share of observations at or below it."""
    data = np.sort(np.asarray(list(values), dtype=float))
    if not len(data):
        return []
    distinct, idx = np.unique(data, return_index=True)
    upto = np.r_[idx[1:], len(data)]
    return [
        {"value": float(v), "n_at_or_below": int(k), "share": float(k / len(data)), "n": len(data)}
        for v, k in zip(distinct, upto, strict=True)
    ]


def s08_cell_days(raws: list[RawArtifact], state: str = "ka") -> tuple[dict[date, int], int]:
    """Reporting land cells per day in the state's box, and the number of cells, from S08 years."""
    present: dict[date, int] = {}
    cells = None
    for raw in raws:
        year, grid = read_grid(raw)
        rows, cols, ids = state_cells(state, grid[0] != UNDEF)
        if cells is not None and len(ids) != cells:
            raise ValueError(f"S08 {year}: {len(ids)} cells, expected {cells}")
        cells = len(ids)
        counts = (grid[:, rows, cols] != UNDEF).sum(axis=1)
        for i in range(366 if calendar.isleap(year) else 365):
            present[date(year, 1, 1) + timedelta(days=i)] = int(counts[i])
    return present, cells or 0


def ledger_duplicates(ledger: Path, url_prefix: str) -> dict:
    """Successful fetches of URLs with this prefix whose content repeats an earlier fetch of the
    same URL (unchanged re-downloads)."""
    keys = []
    for line in ledger.read_text("utf-8").splitlines():
        a = json.loads(line)["artifact"]
        if a["source_url"].startswith(url_prefix) and a["response_status"] == 200:
            keys.append((a["source_url"], a["sha256"]))
    return duplicate_fraction(keys) | {"urls": len({k[0] for k in keys})}


def caption(source: str, what: str, unit: str, start: str, end: str, coverage: str) -> str:
    return f"{source}: {what} ({unit}), {start} to {end}; coverage {coverage}."


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))
