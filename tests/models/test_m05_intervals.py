"""T262 (child of T103): M05 interval recalibration fixed by D97 before any test use."""

import json
import re
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest

pytest.importorskip("sklearn")

from atlas.models import m05  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "models/registry/M05/v1.intervals.json"


def synthetic(seed=1, shift=None):
    rng = np.random.default_rng(seed)
    months = [date(y, m, 1) for y in range(1981, 2025) for m in range(1, 13)][6:]
    rows = []
    for place in ("a", "b"):
        for month in months:
            x = rng.normal(size=3)
            target = 0.6 * x[1] + rng.normal(scale=1.5 if month.month in m05.MONSOON else 0.5)
            if shift and shift[0] <= month <= shift[1]:
                target += 5.0
            rows.append(
                {
                    "place_id": place,
                    "target_month": month,
                    "month_of_year": month.month,
                    "spi1_lag1": x[0],
                    "spi3_lag1": x[1],
                    "spi6_lag1": x[2],
                    "rain_lag1_mm": abs(x[0]) * 50,
                    m05.TARGET: target,
                }
            )
    return pa.Table.from_pylist(rows)


def forecasts(table):
    res = m05.rolling_residuals(table, 1.0)
    # Same row order as the function: one five-year window per origin.
    windows = [m05.rows_in(table, o, date(o.year + 4, 12, 31)) for o in m05.ORIGINS]
    y = np.concatenate([np.asarray(w[m05.TARGET].to_pylist()) for w in windows])
    return res, y - res["ridge"]


def test_residuals_are_out_of_sample_and_stop_before_the_test():
    res, base = forecasts(synthetic())
    assert res["year"].min() == 2000 and res["year"].max() == 2019
    assert len(res["year"]) == 2 * 12 * 20
    years = res["year"]
    # Targets inside the purge and the predicted window cannot move that window's forecasts.
    _, later = forecasts(synthetic(shift=(date(2014, 10, 1), date(2024, 12, 1))))
    assert np.allclose(base[years >= 2015], later[years >= 2015])
    _, earlier = forecasts(synthetic(shift=(date(1990, 1, 1), date(2014, 9, 1))))
    assert not np.allclose(base[years >= 2015], earlier[years >= 2015])


def test_seasonal_rules_calibrate_each_season_apart():
    rng = np.random.default_rng(0)
    cal_month = np.tile(np.arange(1, 13), 100)
    resid = rng.normal(scale=np.where(np.isin(cal_month, list(m05.MONSOON)), 2.0, 0.5))
    month = np.array([7, 1])
    lower, upper = m05._offsets(resid, cal_month, month, seasonal=True)
    assert upper[0] - lower[0] > 3 * (upper[1] - lower[1])
    lower, upper = m05._offsets(resid, cal_month, month, seasonal=False)
    assert lower[0] == lower[1] and upper[0] == upper[1]


def test_rules_are_ranked_by_distance_from_80_percent_on_pre_test_years():
    rng = np.random.default_rng(3)
    year = np.repeat(np.arange(2000, 2020), 360)
    res = {
        "year": year,
        "month": np.tile(np.arange(1, 13), 600),
        "ridge": rng.normal(size=len(year)),
    }
    table = m05.choose_rule(res)
    assert {(r["window_years"], r["seasonal"]) for r in table} == set(m05.RULES)
    distance = [abs(r["coverage"] - 0.8) for r in table]
    assert distance == sorted(distance)
    assert abs(table[0]["coverage"] - 0.8) < 0.02


def test_committed_record_follows_d97():
    record = json.loads(RECORD.read_text("utf-8"))
    best = record["selection"][0]
    assert record["rule"] == {"window_years": best["window_years"], "seasonal": best["seasonal"]}
    distance = [(abs(r["coverage"] - 0.8), r["width"]) for r in record["selection"]]
    assert distance == sorted(distance) and len(distance) == 6
    assert record["selection_years"] == "2010/2019"
    assert record["calibration_years"] == f"{2020 - best['window_years']}/2019"
    coverage = record["test"]["coverage"]
    assert record["publishable"] == (0.75 <= coverage <= 0.85)
    release = json.loads((ROOT / "models/registry/M05/v1.json").read_text("utf-8"))
    assert record["dataset_sha256"] == release["dataset_sha256"]
    report = (ROOT / "reports/models/m05-intervals.md").read_text("utf-8")
    assert f"Test coverage {coverage:.3f}" in report and "second use of the test years" in report
    for number in re.findall(r"\d+\.\d{3}", report):
        assert any(f"{v:.3f}" == number for v in _numbers(record)), number


def _numbers(value):
    if isinstance(value, dict):
        return [n for v in value.values() for n in _numbers(v)]
    if isinstance(value, list):
        return [n for v in value for n in _numbers(v)]
    return [value] if isinstance(value, float) else []
