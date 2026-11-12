"""T106 acceptance: the Karnataka feed-quality helpers use exact denominators, and the notebook
re-run from a fresh process reproduces the committed outputs byte for byte, with source dates
and no data after the frozen fetches. S08 raw files are local only (IMD), so the notebook run
skips in CI; the helper checks always run."""

import csv
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

from atlas.analysis.quality import days, duplicate_fraction, ecdf, missing_days, month_coverage

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/eda/01_ka_quality"
S08_RAW = (
    next((p for p in (ROOT / "data/raw/S08").glob("*/*.bin")), None)
    if (ROOT / "data/raw/S08").exists()
    else None
)


def test_coverage_counts_every_calendar_day_times_cells():
    present = {d: 3 for d in days(date(2024, 2, 1), date(2024, 3, 31))}
    present[date(2024, 2, 29)] = 1
    del present[date(2024, 3, 2)]
    rows = month_coverage(present, 3, date(2024, 2, 1), date(2024, 3, 31))
    assert [(r["month"], r["expected"], r["present"]) for r in rows] == [(2, 87, 85), (3, 93, 90)]
    assert missing_days(present, 3, date(2024, 2, 1), date(2024, 3, 31)) == [
        {"date": "2024-02-29", "missing_cells": 2, "cells": 3},
        {"date": "2024-03-02", "missing_cells": 3, "cells": 3},
    ]


def test_duplicates_and_ecdf_have_exact_denominators():
    assert duplicate_fraction(["a", "b", "a", "a"]) == {
        "total": 4,
        "duplicates": 2,
        "fraction": 0.5,
    }
    assert duplicate_fraction([]) == {"total": 0, "duplicates": 0, "fraction": None}
    rows = ecdf([3.0, 1.0, 3.0, 2.0])
    assert [(r["value"], r["n_at_or_below"], r["share"]) for r in rows] == [
        (1.0, 1, 0.25),
        (2.0, 2, 0.5),
        (3.0, 4, 1.0),
    ]
    assert {r["n"] for r in rows} == {4} and ecdf([]) == []


@pytest.mark.skipif(S08_RAW is None, reason="S08 raw files are local only (IMD)")
def test_notebook_reproduces_from_a_clean_process(tmp_path):
    nb = json.loads((ROOT / "notebooks/01_ka_quality.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    env = os.environ | {"ATLAS_EDA_OUT": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)
    names = sorted(p.name for p in OUT.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    for name in names:
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), name

    summary = json.loads((OUT / "summary.json").read_text("utf-8"))
    s08 = summary["s08"]
    assert s08["expected_cell_days"] == s08["cells"] * s08["days"] == 540 * 16436
    assert s08["days"] == len(days(date(1981, 1, 1), date(2025, 12, 31)))
    assert s08["row_duplicates"]["total"] == s08["present_cell_days"]
    assert date.fromisoformat(s08["data_end"]) < datetime.fromisoformat(s08["first_fetch"]).date()
    with open(OUT / "s08_coverage.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    feb = next(r for r in rows if (r["year"], r["month"]) == ("2024", "2"))
    assert int(feb["expected"]) == 29 * 540 and len(rows) == 45 * 12
    s10 = summary["s10"]
    with open(OUT / "s10_position_age_ecdf.csv", encoding="utf-8") as f:
        lag = list(csv.DictReader(f))
    assert {int(r["n"]) for r in lag} == {s10["with_position"]} and float(lag[-1]["share"]) == 1.0
    assert all(0 <= float(r["value"]) <= 300 for r in lag)  # no position from after the fetch
    assert summary["s01"]["available"] > summary["s01"]["initialised"]
    assert any("S22/S23" in limit for limit in summary["limits"])
