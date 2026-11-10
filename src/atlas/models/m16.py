"""T215: M16 rule counts on the held S08 daily grids, and the no-model fit.

The robust-z rule has no fitted parameter, so there are no weights, scores or predictions: this
module only counts the flags the rule raises. S08 is licence restricted (D129), so the committed
table holds counts by state, year, season and strength band; no rainfall value, cell or date.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from atlas.features import m16
from atlas.features.m05 import year_artifacts
from atlas.features.m16 import data_gate
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.s08 import BOXES, UNDEF, read_grid, state_cells
from atlas.models import blocked

ROOT = Path(__file__).resolve().parents[3]
COUNTS = "reports/models/m16-flag-counts.json"
YEARS = range(1981, 2026)
RAIN_LOWER_MM = 0.0  # configs/models/m16.yaml unit_bounds; S08 reports mm "from 0 upward"
SEASON_NAMES = ("winter", "pre-monsoon", "monsoon", "post-monsoon")
BANDS = [name for name, _ in m16.STRENGTH]
LICENCE = "S08 is restricted (D129): counts only, no rainfall value, cell or date is published"


def s08_flag_counts(raw_root: Path, states=("ka", "kl"), years=YEARS) -> dict:
    """Run the rule on every held S08 year, in order; each year's first windows use the previous
    year's last 28 days. The first held year starts with no history (no earlier day is invented)."""
    years = list(years)
    if years != list(range(years[0], years[-1] + 1)):
        raise ValueError("years must be consecutive: the 28-day window needs the previous day")
    raws = year_artifacts(raw_root, range(years[0], years[-1] + 1))
    if not all(r.path.exists() for r in raws):
        raise SourceUnavailable(f"S08 year files listed in {raw_root} are not on disk")
    cells, tails, flags, coverage = {}, {}, {}, []
    for raw in raws:
        year, grid = read_grid(raw)
        land = grid[0] != UNDEF
        days = grid.shape[0]
        month = np.array([(date(year, 1, 1) + timedelta(d)).month for d in range(days)])
        season = np.array([SEASON_NAMES.index(m16.SEASONS[m]) for m in month])
        for state in states:
            if state not in cells:
                rows, cols, ids = state_cells(state, land)
                cells[state] = (rows, cols, land)
                tails[state] = np.full((m16.WINDOW_DAYS, len(ids)), np.nan)
            rows, cols, first_land = cells[state]
            if not (land == first_land).all():
                raise IngestError(f"S08 {year}: land mask differs from the first year")
            x = grid[:, rows, cols].astype(np.float64)
            x[x == UNDEF] = np.nan  # a missing day, never 0 (D40)
            both = np.vstack([tails[state], x])
            out = m16.detect(both, lower=RAIN_LOWER_MM)
            z, status = out["z"][m16.WINDOW_DAYS :], out["status"][m16.WINDOW_DAYS :]
            tails[state] = both[-m16.WINDOW_DAYS :]
            day, cell = np.nonzero(out["flag_z"][m16.WINDOW_DAYS :])
            band = np.digitize(np.abs(z[day, cell]), [t for _, t in m16.STRENGTH[:-1]], right=True)
            code = np.bincount(
                season[day] * len(BANDS) + band, minlength=len(SEASON_NAMES) * len(BANDS)
            )
            for i, n in enumerate(code):
                if n:
                    flags[(state, year, SEASON_NAMES[i // len(BANDS)], BANDS[i % len(BANDS)])] = (
                        int(n)
                    )
            by_status = np.bincount(status.ravel(), minlength=len(m16.STATUS))
            coverage.append(
                [state, year, *by_status.tolist(), int((z[day, cell] > 0).sum()), len(day)]
            )
    totals = {}
    for state in states:
        mine = [c for c in coverage if c[0] == state]
        evaluated = sum(c[2 + m16.EVALUATED] for c in mine)
        cell_days = sum(sum(c[2:7]) for c in mine)
        n_flags = sum(c[-1] for c in mine)
        totals[state] = {
            "cells": int(cells[state][0].size),
            "cell_days": cell_days,
            "evaluated": evaluated,
            "flags_z": n_flags,
            "flags_high": sum(c[-2] for c in mine),
            "flags_low": n_flags - sum(c[-2] for c in mine),
            "flags_bound": sum(c[2 + m16.BOUND] for c in mine),
            "flags_per_entity_week": round(7 * n_flags / cell_days, 5),
            "flags_per_evaluated_entity_week": round(7 * n_flags / evaluated, 5),
        }
    return {
        "source": "S08",
        "licence": LICENCE,
        "rule": dict(m16.rule_parameters()),
        "unit_bound": {"rain_mm_lower": RAIN_LOWER_MM, "upper": None},
        "years": [years[0], years[-1]],
        "states": {s: {"cell_box": list(BOXES[s])} for s in states},
        "box_note": "the ka and kl cell boxes overlap in 11.5-12.75N, 74.75-77.5E: shared cells "
        "are counted in both states",
        "flag_columns": ["state", "year", "season", "strength_band", "flags"],
        "flags": [[*k, v] for k, v in sorted(flags.items())],
        "coverage_columns": ["state", "year", *m16.STATUS, "flags_high", "flags_z"],
        "coverage": coverage,
        "totals": totals,
        "precision": "not measured: 0 of 100 flags adjudicated",
    }


def write_counts(counts: dict) -> Path:
    path = ROOT / COUNTS
    path.write_text(json.dumps(counts, indent=1) + "\n", encoding="utf-8", newline="\n")
    return path


def no_model_manifest(folder: Path) -> Path:
    """What a fit leaves behind: the rule, and the proof that nothing was fitted or scored."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "m16_no_model.json"
    record = {
        "model_id": "M16",
        "status": "research_only",
        "rule": dict(m16.rule_parameters()),
        "challengers": {"isolation_forest": "not run: 0 adjudicated labels"},
        "label_gate": m16.label_gate(0),
        "weights": None,
        "scores": None,
        "prediction_rows": 0,
    }
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def fit(train, tune, folder: Path) -> Path:
    """Nothing is learned: train and tune are not read, so no test row can affect the result."""
    return no_model_manifest(folder)


def predict(model, rows):
    raise SourceUnavailable("M16 is research-only: no flag is published as a prediction or alert")


def status_record() -> dict:
    """The registry file (T216): bound to the gate's bytes, never a release; every score null."""
    gate = data_gate()
    record = blocked.status_record(gate, "all")
    return {**record, "status": "research_only", "label_gate": gate["label_gate"]}


def write_status() -> tuple[Path, Path]:
    """Write the gate and the registry status, in that order (the status hashes the gate)."""
    gate_file = blocked.write_gate(data_gate())
    path = ROOT / "models" / "registry" / "m16.json"
    path.write_text(json.dumps(status_record(), indent=2) + "\n", encoding="utf-8", newline="\n")
    return gate_file, path
