"""T282: spatial lags read month t-1 only, region folds never share districts, Moran's I on a
tiny grid with known answers, the effective sample size, and the committed summary, gate and
report agree. The notebook rerun needs the local M21 dataset and S08/S17 raw files."""

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest

from atlas.analysis.spatial import morans_i, row_standardised
from atlas.models import spatial_ml as sm
from atlas.models.m05 import rows_in
from atlas.models.splits import spatial_blocks

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/eda/15_ka_spatial_ml"
SUMMARY = json.loads((OUT / "summary.json").read_text("utf-8"))
GATE = json.loads((ROOT / "models/gates/m21.json").read_text("utf-8"))
REPORT = (ROOT / "reports/models/m21-tune.md").read_text("utf-8")
LOCAL = sm.DATASET.exists() and (ROOT / "data/raw/S08").exists()
PLACES = ["a", "b", "c"]
CHAIN = [[1], [0, 2], [1]]  # a - b - c


def synthetic() -> pa.Table:
    """Three districts, monthly rows 1982-01 to 1990-12; every column consistent with one
    anomaly series per district (lags and SPI describe month t-1)."""
    rng = np.random.default_rng(3)
    months = [date(y, m, 1) for y in range(1981, 1991) for m in range(1, 13)]
    z = {p: rng.standard_normal(len(months)) for p in PLACES}
    rows = []
    for p in PLACES:
        for i, t in enumerate(months[12:], start=12):
            rows.append(
                {
                    "place_id": p,
                    "target_month": t,
                    "month_of_year": t.month,
                    "target_anom": float(z[p][i]),
                    "anom_lag1": float(z[p][i - 1]),
                    "spi1_lag1": float(z[p][i - 1]),
                    "spi3_lag1": float(z[p][i - 3 : i].mean()),
                }
            )
    return pa.Table.from_pylist(rows)


def bump(rows: pa.Table, month: date, delta: float) -> pa.Table:
    """Change every value that describes `month`: its target and the next row's t-1 columns."""
    nxt = date(month.year + month.month // 12, month.month % 12 + 1, 1)
    out = []
    for r in rows.to_pylist():
        if r["target_month"] == month:
            r["target_anom"] += delta
        if r["target_month"] == nxt:
            r["anom_lag1"] += delta
            r["spi1_lag1"] += delta
            r["spi3_lag1"] += delta
        out.append(r)
    return pa.Table.from_pylist(out)


def lags_at(rows: pa.Table, month: date) -> list:
    lagged = sm.spatial_lags(rows, PLACES, CHAIN, sm.M21_SPATIAL)
    at = rows_in(lagged, month, month)
    return [at[f].to_pylist() for f in sm.M21_SPATIAL]


def test_spatial_lag_uses_only_month_t_minus_1():
    rows, t = synthetic(), date(1986, 6, 1)
    base = lags_at(rows, t)
    assert lags_at(bump(rows, t, 9.0), t) == base  # month t itself is never seen
    assert lags_at(bump(rows, date(1986, 7, 1), 9.0), t) == base
    moved = lags_at(bump(rows, date(1986, 5, 1), 9.0), t)  # month t-1 is
    assert all(m != pytest.approx(b) for m, b in zip(moved, base, strict=True))
    assert lags_at(bump(rows, date(1986, 4, 1), 9.0), t)[0] == base[0]  # anomaly lag is t-1 only


def test_neighbour_mean_known_answer_and_gaps():
    grid = np.array([[1.0, 2.0, 4.0], [np.nan, 5.0, np.nan]])
    out = sm.neighbour_mean(grid, CHAIN)
    assert out[0].tolist() == [2.0, 2.5, 2.0]
    assert np.isnan(out[1, 1]) and out[1, 0] == 5.0 and out[1, 2] == 5.0  # no zero fill


def test_moran_known_answers_on_a_tiny_grid():
    path = [[1], [0, 2], [1, 3], [2]]  # four districts in a line
    w = row_standardised(path)
    assert morans_i(np.array([1.0, -1.0, 1.0, -1.0]), w) == pytest.approx(-1.0)
    assert morans_i(np.array([1.0, 1.0, -1.0, -1.0]), w) == pytest.approx(0.5)
    rows = pa.Table.from_pylist(
        [
            {"place_id": p, "target_month": m, "x": x}
            for m, xs in ((date(2015, 1, 1), (1, -1, 1, -1)), (date(2015, 2, 1), (1, 1, -1)))
            for p, x in zip("pqrs", xs, strict=False)
        ]
    )
    out = sm.moran_by_month(rows["x"].to_pylist(), rows, list("pqrs"), path)
    assert out[0]["moran_i"] == pytest.approx(-1.0) and out[0]["districts"] == 4
    assert "p" not in out[1] and out[1]["districts"] == 3  # incomplete month is not tested


def test_effective_size_known_answers():
    months = [date(2015, m, 1) for m in range(1, 7) for _ in range(5)]
    rows = pa.Table.from_pylist([{"target_month": m} for m in months])
    shared = np.repeat(np.arange(6.0), 5)  # every district equal within a month
    e = sm.effective_size(shared, rows, list("abcde"))
    assert e["icc"] == pytest.approx(1.0) and e["n_eff_per_month"] == pytest.approx(1.0)


def test_region_folds_never_share_districts():
    rows = pa.Table.from_pylist(
        [
            {"place_id": p, "target_month": date(y, m, 1)}
            for p in PLACES
            for y in range(1982, 2015)
            for m in range(1, 13 if y < 2014 else 12)
        ]
    )
    region_of = {"a": "R1", "b": "R2", "c": "R3"}
    place, months = (
        np.array(rows["place_id"].to_pylist()),
        np.array(rows["target_month"].to_pylist()),
    )
    for scheme in ("region", "region_temporal"):
        for fit_mask, score_mask in sm.cv_folds(rows, region_of, scheme):
            assert not set(place[fit_mask]) & set(place[score_mask]), scheme
            if scheme == "region_temporal":
                assert months[fit_mask].max() < months[score_mask].min()
    random = sm.cv_folds(rows, region_of, "random")
    assert all(set(place[a]) & set(place[b]) for a, b in random)  # the leaky scheme shares


def test_committed_regions_are_contiguous_and_disjoint():
    pytest.importorskip("sklearn")
    pytest.importorskip("shapely")
    rows = sm.nn.NEIGHBOURS.read_text("utf-8").splitlines()[1:]
    places = sorted(r.split(",")[0] for r in rows)
    nbrs = sm.neighbours(places)
    region_of = sm.regions(places, nbrs, sm.centroids(places))
    folds = spatial_blocks(region_of, sm.REGIONS)
    assert len(folds) == sm.REGIONS and all(len(f) == 1 for f in folds)
    for r in set(region_of.values()):
        assert sm.connected([i for i, p in enumerate(places) if region_of[p] == r], nbrs)
    members = SUMMARY["regions"]["members"]
    assert sum(len(v) for v in members.values()) == 30
    assert sorted(len(v) for v in members.values()) == sorted(
        list(region_of.values()).count(r) for r in set(region_of.values())
    )


def test_summary_gate_and_report_agree():
    s, t = SUMMARY, SUMMARY["tune"]
    assert s["task"] == "T282" and s["inputs"]["m21_dataset_sha256"] == GATE["dataset_sha256"]
    assert t["models"]["base"]["mae"] == pytest.approx(GATE["tune"]["models"]["lightgbm"]["mae"])
    assert t["lag_helps"] == (t["lags_over_base"]["lower95"] > 0)
    assert t["rows"] == GATE["rows"]["tune"] == 897 and t["months"] == 36
    assert GATE["candidate"]["model"] == "lightgbm" and GATE["test_opened"] is True
    mo = s["moran"]
    assert len(mo["by_month"]) == 36 == mo["before"]["months"]
    assert mo["before"]["months_tested"] == sum("before_i" in r for r in mo["by_month"])
    assert mo["before"]["months_tested"] == mo["after"]["months_tested"]
    cv = s["cv"]["schemes"]
    assert set(cv) == set(sm.SCHEMES) and cv["region_temporal"]["overstatement"]["base"] == 0
    assert cv["region"]["folds"] == sm.REGIONS and cv["region_temporal"]["folds"] == 10 * sm.REGIONS
    c = s["m05_challenger"]
    assert c["last_month"] <= "2019-12" and c["status"] == "research-only"
    assert c["rows"] == 30 * c["months"]
    assert "rain_mm" not in json.dumps(s)
    sp = GATE["tune"]["spatial"]
    assert sp["task"] == "T282" and sp["tune"] == t and set(sp["mlflow_run_ids"]) == {"m21", "m05"}
    assert REPORT.count(sm.HEADER) == 1
    assert f"The spatial lag {'helps' if t['lag_helps'] else 'does not help'} on tune" in REPORT
    assert sm.fit._ci(t["lags_over_base"]) in REPORT


@pytest.mark.skipif(not LOCAL, reason="needs the local M21 dataset and S08/S17 raw files")
def test_notebook_reproduces_from_a_clean_process(tmp_path):
    nb = json.loads((ROOT / "notebooks/15_ka_spatial_ml.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    env = os.environ | {"ATLAS_EDA_OUT": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)
    names = sorted(p.name for p in OUT.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    for name in names:
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), name
