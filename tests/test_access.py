"""D195: hospital access maths on cases with known answers: exact nearest site on the sphere,
people-weighted statistics, Gini 0 for equal distances and near 1 when one person is far."""

import numpy as np
import pytest

from atlas.analysis.access import (
    by_district,
    km_between,
    lorenz,
    nearest_km,
    summarise,
    weighted_gini,
    weighted_quantile,
)


def test_nearest_site_is_exact_great_circle():
    pytest.importorskip("scipy")  # geo/ml lock; core-only CI has no scipy
    sites = np.array([[77.0, 13.0], [76.0, 12.0]])
    cells = np.array([[77.1, 13.0], [76.0, 12.2]])
    km = nearest_km(cells, sites)
    assert km[0] == pytest.approx(km_between(77.1, 13.0, 77.0, 13.0), rel=1e-6)
    assert km[1] == pytest.approx(km_between(76.0, 12.2, 76.0, 12.0), rel=1e-6)
    assert 10.8 < km[0] < 10.9  # 0.1 degree of longitude at 13 N


def test_people_weighted_statistics():
    km = np.array([1.0, 20.0])
    people = np.array([900.0, 100.0])
    s = summarise(km, people)
    assert s["mean_km"] == pytest.approx(2.9)
    assert s["median_km"] == 1.0 and s["share_beyond_10km"] == pytest.approx(0.1)
    assert weighted_quantile(km, people, 0.95) == 20.0


def test_gini_and_lorenz_bounds():
    equal = np.full(5, 3.0)
    assert weighted_gini(equal, np.ones(5)) == pytest.approx(0.0, abs=1e-12)
    skewed = np.array([0.0] * 99 + [100.0])
    assert weighted_gini(skewed, np.ones(100)) > 0.95
    curve = lorenz(np.array([1.0, 2.0, 3.0]), np.ones(3), points=3)
    assert curve[0] == [0.0, 0.0] and curve[-1] == [1.0, 1.0] and curve[1][1] < 0.5


def test_districts_are_ranked_farthest_first_and_unassigned_cells_are_left_out():
    km = np.array([1.0, 2.0, 30.0, 5.0])
    people = np.ones(4)
    rows = by_district(km, people, ["A", "A", "B", None])
    assert [r["district"] for r in rows] == ["B", "A"] and rows[1]["people"] == 2


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/eda/11_ka_hospital_access"
LOCAL = all((ROOT / "data/raw" / s).exists() for s in ("S16", "S17", "S18"))


def test_committed_summary_is_consistent():
    import json

    s = json.loads((OUT / "summary.json").read_text("utf-8"))
    assert s["hospitals"] == 3581 and 0 < s["statewide"]["gini"] < 1
    assert s["statewide"]["share_beyond_10km"] <= s["statewide"]["share_beyond_5km"]
    assert len(s["limits"]) == 4 and s["lorenz"][0] == [0.0, 0.0] and s["lorenz"][-1] == [1.0, 1.0]


@pytest.mark.skipif(not LOCAL, reason="S16, S17 and S18 raw files are local only")
def test_notebook_reproduces_from_a_clean_process(tmp_path):
    import json
    import os
    import subprocess
    import sys

    nb = json.loads((ROOT / "notebooks/11_ka_hospital_access.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    env = os.environ | {"ATLAS_EDA_OUT": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)
    names = sorted(p.name for p in OUT.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    for name in names:
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), name
