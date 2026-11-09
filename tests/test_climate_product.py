"""T145 acceptance: NDVI keeps nodata, cloud gaps and zero denominators missing and bounded in
[-1, 1] (hand-checkable arrays, not imagery: S42 is blocked, H15); the monsoon climatology uses
1981-2010 only; no official onset is invented; projections are keyed by model and never labelled
a forecast. Real S08 checks skip in CI (local-only raw). The web contract runs through vitest."""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from atlas.analysis import monsoon, vegetation

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "reports/eda/08_climate_product/climate.json"


def test_ndvi_is_bounded_and_keeps_missing_missing():
    nir = [0.5, 0.0, 0.3, -9999.0, 0.4, 0.2]
    red = [0.1, 0.0, 0.3, 0.1, 0.1, -0.1]  # ok, zero denominator, flat, nodata, cloud, negative
    cloud = [False, False, False, False, True, False]
    out = vegetation.ndvi(nir, red, cloud=cloud, nodata=-9999.0)
    assert out[0] == pytest.approx(0.4 / 0.6)
    assert out[2] == 0.0
    assert np.isnan(out[[1, 3, 4, 5]]).all()  # cloud gap and nodata are not filled
    rng = np.random.default_rng(0)
    big = vegetation.ndvi(rng.uniform(0, 1, 1000), rng.uniform(0, 1, 1000))
    assert np.nanmin(big) >= -1 and np.nanmax(big) <= 1


def test_ten_day_median_ignores_missing_and_keeps_all_missing_missing():
    days = [date(2025, 7, d) for d in (1, 5, 9, 12, 15)]
    stack = np.array([[0.2, np.nan], [0.4, np.nan], [np.nan, np.nan], [0.6, 0.5], [np.nan, 0.7]])
    out = vegetation.dekad_median(days, stack)
    assert out[2025, 7, 1][0] == pytest.approx(0.3)
    assert np.isnan(out[2025, 7, 1][1])
    assert out[2025, 7, 2].tolist() == pytest.approx([0.6, 0.6])
    assert vegetation.dekad(date(2025, 7, 31)) == (2025, 7, 3)


def test_crop_health_wording_needs_a_verified_mask_and_s42_is_unavailable():
    assert vegetation.wording(False) == "vegetation greenness"
    assert vegetation.wording(True) == "crop health"
    status = vegetation.layer_status(ROOT / "configs/sources/s42.yaml")
    assert status["status"] == "unavailable"
    assert "S42" in status["reason"]
    assert status["wording"] == "vegetation greenness"


def _season(year, mm):
    return {date(year, 6, 1) + timedelta(days=i): mm for i in range(122)}


def test_cumulative_starts_on_1_june_and_never_fills_a_gap():
    daily = {date(2020, 5, 31): 99.0} | _season(2020, 2.0)
    assert monsoon.cumulative(daily, 2020, date(2020, 6, 3)) == 6.0  # 1, 2, 3 June; not 31 May
    del daily[date(2020, 6, 2)]
    assert monsoon.cumulative(daily, 2020, date(2020, 6, 3)) is None


def test_climatology_uses_only_1981_2010_and_ranks_the_tracked_year():
    by_year = {y: float(y - 1980) for y in range(1981, 2011)} | {2011: 1e6, 2030: 1e6}
    sample = monsoon.reference_sample(by_year | {1985: None})
    assert len(sample) == 29 and max(sample) == 30.0  # forecast and recent years excluded
    assert monsoon.percentile_rank(15.5, [10.0, 15.5, 20.0, 30.0]) == 37.5
    daily = {y: _season(y, float(y - 1980)) for y in range(1981, 2011)}
    daily[2025] = _season(2025, 100.0)  # far above every reference year, yet outside the sample
    row = monsoon.tracker(daily, 2025, [date(2025, 6, 30)])["checkpoints"][0]
    assert row["reference_years"] == 30 and row["rank_percentile"] == 100.0


def test_official_onset_is_null_without_a_source_and_heuristic_is_inferred():
    none = monsoon.official_onset()
    assert none["official_onset"] is None and none["reason"]
    assert monsoon.official_onset({"S99": date(2025, 5, 24)})["official_onset"] == "2025-05-24"
    daily = {date(2025, 5, 1) + timedelta(days=i): 0.0 for i in range(61)}
    for d in (date(2025, 5, 20), date(2025, 5, 21), date(2025, 5, 22)):
        daily[d] = 3.0
    got = monsoon.inferred_onset(daily, 2025)
    assert got["onset"] == "2025-05-20" and got["label"] == "inferred"
    assert monsoon.inferred_onset({}, 2025)["onset"] is None


def test_trend_covers_the_years_held_and_projections_are_keyed_by_model():
    t = monsoon.trend("a", {y: 100.0 + (y - 1981) for y in range(1981, 2026)})
    assert (t["first_year"], t["last_year"], t["n_years"]) == (1981, 2025, 45)
    assert t["slope_pct_per_decade"] > 0
    rows = [{"point": "P", "model": m, "change_pct": c} for m, c in (("A", "-1.0"), ("B", "5.0"))]
    proj = monsoon.projections(rows)
    assert proj["by_point"]["P"] == {"A": -1.0, "B": 5.0}
    assert proj["label"] == "climate projection, not a forecast"
    assert "forecast" not in json.dumps(proj).replace("not a forecast", "")


def test_committed_product_is_derived_only_and_honest():
    p = json.loads(PRODUCT.read_text("utf-8"))
    assert p["onset"]["official_onset"] is None and p["onset"]["inferred"]["label"] == "inferred"
    assert p["ndvi"]["status"] == "unavailable" and p["tracker"]["reference"] == "1981-2010"
    assert all(t["first_year"] >= 1981 for t in p["trend"])
    assert any("1901-1980" in x for x in p["limits"])
    assert "rain_mm" not in json.dumps(p)  # indices only, no area-mean mm (S08 licence)


def test_product_reproduces_from_local_s08():
    if not all((ROOT / f"data/raw/{s}").exists() for s in ("S08", "S17")):
        pytest.skip("raw files are local only")
    sys.path.insert(0, str(ROOT / "scripts"))
    from climate_product import build

    assert build() == json.loads(PRODUCT.read_text("utf-8"))


def test_web_climate_contract(web_check):
    web_check("run", "test", "--", "src/pages/Climate.test.ts")
