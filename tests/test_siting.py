"""T286: hospital siting by greedy maximal coverage on a tiny grid with known answers, the
baselines it must beat, and the committed summary's consistency."""

import json
from pathlib import Path

import numpy as np
import pytest

from atlas.analysis.siting import covered, greedy, most_populous, worst_districts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/eda/16_ka_hospital_siting"
LOCAL = all((ROOT / "data/raw" / s).exists() for s in ("S16", "S17", "S18"))


def grid():
    """Gap cells on a line at 0.1 degree (about 11 km) steps along the equator: a 20 km radius
    from cell i reaches i-1, i, i+1. People: two dense neighbours at 0-1, one big lone cell at 5,
    a cluster of three at 8-10."""
    people = np.array([50, 50, 0, 0, 0, 90, 0, 0, 40, 40, 40], dtype=float)
    lonlat = np.column_stack([np.arange(11) * 0.1, np.zeros(11)])
    return lonlat, people


def test_reach_is_great_circle_and_keeps_zero_distance_pairs():
    pytest.importorskip("scipy")  # geo/ml lock; core-only CI has no scipy
    from atlas.analysis.siting import reach

    lonlat, _ = grid()
    m = reach(lonlat, lonlat, 20.0).toarray()
    assert np.all(np.diag(m) == 1)  # a candidate covers its own cell
    assert m[0, 1] == 1 and m[0, 2] == 0 and m.sum() == 11 + 2 * 10


def test_greedy_picks_known_answer_and_marginal_gains():
    pytest.importorskip("scipy")
    from atlas.analysis.siting import reach

    lonlat, people = grid()
    m = reach(lonlat, lonlat, 20.0)
    picks, gains = greedy(m, people, 3)
    # cell 9 covers 8-10 (120); then 0 or 1 covers 100 and 4, 5 or 6 covers 90 (ties go low)
    assert picks == [9, 0, 4] and gains == [120.0, 100.0, 90.0]
    assert covered(m, picks, people) == people.sum()
    # stops once nothing is left to cover
    assert greedy(m, people, 10)[0] == [9, 0, 4]


def test_greedy_beats_every_baseline_on_the_grid():
    pytest.importorskip("scipy")
    from atlas.analysis.siting import random_sites, reach

    lonlat, people = grid()
    m = reach(lonlat, lonlat, 20.0)
    rows = np.arange(11)
    district = np.array(["A"] * 4 + ["B"] * 3 + ["C"] * 4)
    share = {"A": 1.0, "B": 0.9, "C": 0.8}
    for k in (1, 2, 3):
        g = covered(m, greedy(m, people, k)[0], people)
        top = most_populous(rows, people, k)
        assert top[0] == 5  # the single biggest cell
        worst = worst_districts(rows, people, district, share, k)
        assert worst[:2] == [0, 5][:k]  # A's biggest (first on the tie), then B's
        assert g >= covered(m, top, people) and g >= covered(m, worst, people)
        assert all(g >= covered(m, r, people) for r in random_sites(11, k, 50, 0))


def test_baselines_skip_non_candidates_and_empty_districts():
    people = np.array([10.0, 99.0, 5.0])
    gap_rows = np.array([0, -1, 1])  # cell 1 is outside every district: not a candidate
    assert most_populous(gap_rows, people, 5) == [0, 1]
    district = np.array(["A", "", "B"])
    assert worst_districts(gap_rows, people, district, {"A": 0.0, "B": 0.5}, 2) == [1]


def test_committed_summary_is_consistent():
    s = json.loads((OUT / "summary.json").read_text("utf-8"))
    h = s["headline"]
    assert set(s["inputs"]) == {"S16", "S17", "S18"} and s["hospitals"] == 3581
    assert len(s["sites"]) == 10 and all(x["district"] for x in s["sites"])
    gains = [x["people_newly_within_10km"] for x in s["sites"]]
    assert gains == sorted(gains, reverse=True)
    assert abs(sum(gains) - h["greedy_newly_within_10km"]) <= len(gains)  # rounding only
    assert all(
        round(x["lon"], 2) == x["lon"] and round(x["lat"], 2) == x["lat"] for x in s["sites"]
    )
    assert h["mean_km_after"] < h["mean_km_before"]
    for name, b in s["baselines"].items():
        best = b.get("newly_within_10km", b.get("newly_within_10km_max"))
        assert h["greedy_newly_within_10km"] >= best, name
    for row in s["sensitivity"]:
        g = row["greedy_newly_within"]
        assert g <= row["people_beyond_before"]
        assert all(g >= v for k, v in row.items() if k.endswith("_newly_within")), row
    ks = [r["greedy_newly_within"] for r in s["sensitivity"] if r["threshold_km"] == 10.0]
    assert ks == sorted(ks)  # more sites never cover fewer people
    assert len(s["osm_completeness_check"]["runs"]) == 5 and len(s["limits"]) == 6


@pytest.mark.skipif(not LOCAL, reason="S16, S17 and S18 raw files are local only")
def test_notebook_reproduces_from_a_clean_process(tmp_path):
    import os
    import subprocess
    import sys

    nb = json.loads((ROOT / "notebooks/16_ka_hospital_siting.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    env = os.environ | {"ATLAS_EDA_OUT": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)
    names = sorted(p.name for p in OUT.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    for name in names:
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), name
