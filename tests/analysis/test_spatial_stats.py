"""T109 acceptance: the spatial helpers match hand-computed values with exact denominators, and
the notebook re-run from a fresh process reproduces the committed outputs byte for byte, with
source dates, a training-only variogram and no future-data feature. S08 raw files and the saved
M05 fit are local only (IMD), so the notebook run skips in CI; the helper checks always run."""

import csv
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pytest
import shapely
from scipy.stats import false_discovery_control

from atlas.analysis.spatial import (
    benjamini_hochberg,
    morans_i,
    permutation_test,
    queen_neighbours,
    row_standardised,
    semivariogram,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/eda/10_spatial_statistics"
LOCAL = (ROOT / "data/raw/S08").exists() and (ROOT / "data/models/m05/m05_fit.json").exists()
CHAIN = [shapely.box(i, 0, i + 1, 1) for i in range(4)]  # A-B-C-D in a row


def test_queen_contiguity_counts_corners_and_reports_islands():
    grid = [shapely.box(x, y, x + 1, y + 1) for y in (0, 1) for x in (0, 1)]
    nbrs, islands = queen_neighbours([*grid, shapely.box(5, 5, 6, 6)])
    assert nbrs == [[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2], []] and islands == [4]
    w = row_standardised(nbrs)
    assert np.allclose(w.sum(axis=1), [1, 1, 1, 1, 0]) and np.allclose(w[0, 1:4], 1 / 3)


def test_morans_i_matches_hand_values_on_a_chain():
    w = row_standardised(queen_neighbours(CHAIN)[0])
    # z = (-1.5, -0.5, 0.5, 1.5): z'Wz = 2, z'z = 5, n / S0 = 1, so I = 0.4.
    assert morans_i(np.array([1.0, 2, 3, 4]), w) == pytest.approx(0.4)
    assert morans_i(np.array([1.0, -1, 1, -1]), w) == pytest.approx(-1.0)


def test_permutation_p_is_two_sided_bounded_and_seeded():
    line = [shapely.box(i, 0, i + 1, 1) for i in range(20)]
    w = row_standardised(queen_neighbours(line)[0])
    x = np.arange(20.0)
    first = permutation_test(x, w, np.random.default_rng(7))
    assert first == permutation_test(x, w, np.random.default_rng(7))
    assert first["expected"] == pytest.approx(-1 / 19) and first["permutations"] == 999
    assert first["p"] == (1 + first["as_extreme"]) / 1000 and first["p"] <= 0.01
    chain = row_standardised(queen_neighbours(CHAIN)[0])
    small = permutation_test(np.array([1.0, -1, 1, -1]), chain, np.random.default_rng(0))
    assert small["moran_i"] == pytest.approx(-1.0) and 0 < small["p"] <= 1


def test_benjamini_hochberg_matches_hand_values_and_scipy():
    p = [0.01, 0.04, 0.03, 0.005]
    assert np.allclose(benjamini_hochberg(p), [0.02, 0.04, 0.04, 0.02])
    assert np.allclose(benjamini_hochberg([0.9, 0.95]), [0.95, 0.95])
    many = np.random.default_rng(1).uniform(size=60) ** 3
    assert np.allclose(benjamini_hochberg(many), false_discovery_control(many))


def test_semivariogram_counts_pairs_and_skips_missing_values():
    xy = np.array([[0.0, 0], [1, 0], [3, 0]])
    values = np.array([[0.0, 1, 3], [0, np.nan, 1]])
    rows = semivariogram(xy, values, [0, 1.5, 2.5, 4])
    assert [(r["site_pairs"], r["times"], r["pair_times"]) for r in rows] == [
        (1, 2, 1),
        (1, 2, 1),
        (1, 2, 2),
    ]
    assert [r["gamma"] for r in rows] == [0.5, 2.0, 2.5]
    empty = semivariogram(xy, values, [10, 20])[0]
    assert empty["site_pairs"] == 0 and empty["gamma"] is None


@pytest.mark.skipif(not LOCAL, reason="S08 raw files and the M05 fit are local only (IMD)")
def test_notebook_reproduces_from_a_clean_process(tmp_path):
    nb = json.loads((ROOT / "notebooks/10_spatial_statistics.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    env = os.environ | {"ATLAS_EDA_OUT": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)
    names = sorted(p.name for p in OUT.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    for name in names:
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), name

    summary = json.loads((OUT / "summary.json").read_text("utf-8"))
    model, weights, moran, vario = (summary[k] for k in ("model", "weights", "moran", "variogram"))
    assert model["features_known_before_target"] is True
    assert date.fromisoformat(model["train_cutoff"].split("/")[1]) < date(2020, 1, 1)
    assert weights["districts"] == 30 and weights["islands"] == []
    assert moran["district_months_expected"] == moran["months"] * 30 == 1800
    assert moran["district_months"] == moran["months_tested"] * 30
    assert moran["significant_bh"] <= moran["significant_raw_p05"] <= moran["months_tested"]
    with open(OUT / "moran_by_month.csv", encoding="utf-8") as f:
        months = list(csv.DictReader(f))
    assert len(months) == moran["months_tested"] and months[0]["month"] == "2020-01"
    assert all(int(r["permutations"]) == 999 and 0 < float(r["p"]) <= 1 for r in months)
    assert all(float(r["p"]) == (1 + int(r["as_extreme"])) / 1000 for r in months)
    assert sum(r["significant_q05"] == "True" for r in months) == moran["significant_bh"]

    assert vario["years"] == list(range(2000, 2020)) and max(vario["years"]) < 2020
    assert vario["district_months_expected"] == vario["months"] * 30 == 240 * 30
    assert vario["site_pairs"] == 30 * 29 // 2
    with open(OUT / "variogram_training.csv", encoding="utf-8") as f:
        bins = list(csv.DictReader(f))
    assert sum(int(b["site_pairs"]) for b in bins) == vario["site_pairs"]
    assert sum(int(b["pair_times"]) for b in bins) == vario["pair_months"]
    assert all(int(b["pair_times"]) <= int(b["site_pairs"]) * int(b["times"]) for b in bins)

    inputs = summary["inputs"]
    manifest = json.loads((ROOT / "tests/fixtures/s17/manifest.json").read_text("utf-8"))
    e06 = next(e for e in manifest["evidence"] if e["id"] == "e06")
    assert inputs["s17_sha256"] == e06["sha256"]
    assert datetime.fromisoformat(inputs["s17_fetch"]) == datetime.fromisoformat(e06["fetched_at"])
    assert inputs["s08_files"] == 44 and inputs["s08_years"] == [1981, 2024]
    assert datetime.fromisoformat(inputs["s08_first_fetch"]).date() > date(2024, 12, 31)
    assert any("M04" in limit for limit in summary["limits"])
