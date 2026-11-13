"""T285: district segmentation on synthetic data with known answers, the committed summary, and a
clean-process reproduction of notebook 14."""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("sklearn")  # ml lock; core-only CI has no scikit-learn

from atlas.analysis.segments import (  # noqa: E402
    bootstrap_ari,
    choose_k,
    drop_collinear,
    kmeans,
    name_segments,
    robust_scale,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/eda/14_ka_district_segments"


def blobs(n_per=10, centres=((0, 0), (8, 8), (0, 8)), noise=0.3, seed=1):
    rng = np.random.default_rng(seed)
    x = np.vstack([rng.normal(c, noise, (n_per, 2)) for c in centres])
    return x, np.repeat(np.arange(len(centres)), n_per)


def test_known_three_blobs_give_k3_and_stable_segments():
    from sklearn.metrics import adjusted_rand_score

    x, truth = blobs()
    k, table = choose_k(x)
    assert k == 3 and [t["k"] for t in table] == [2, 3, 4, 5, 6]
    labels = kmeans(x, k).labels_
    assert adjusted_rand_score(truth, labels) == pytest.approx(1.0)
    assert np.median(bootstrap_ari(x, k, labels, runs=30)) > 0.9


def test_pure_noise_is_not_stable():
    x = np.random.default_rng(3).normal(size=(30, 4))
    labels = kmeans(x, 3).labels_
    assert np.median(bootstrap_ari(x, 3, labels, runs=40)) < 0.6


def test_a_tiny_segment_is_never_chosen():
    rng = np.random.default_rng(1)
    pair = rng.normal((30, 0), 0.3, (2, 2))  # two far districts always form a 2-district segment
    x = np.vstack([blobs(10, ((0, 0), (8, 8)))[0], pair])
    with pytest.raises(ValueError):
        choose_k(x)


def test_collinear_feature_is_dropped_and_scaling_is_robust():
    a = np.random.default_rng(0).normal(size=40)
    x = np.column_stack([a, a * 2 + 1, np.random.default_rng(1).normal(size=40)])
    kept, dropped = drop_collinear(x, ["a", "b", "c"])
    assert kept == [0, 2] and dropped[0]["dropped"] == "b" and dropped[0]["kept"] == "a"
    s = robust_scale(np.array([[1.0], [2.0], [3.0], [4.0], [1000.0]]))
    assert s[2, 0] == 0.0 and s[0, 0] == pytest.approx(-1.0)  # median 3, IQR 2


def test_segment_names_come_from_the_centroid():
    raw = np.array([[500.0, 5.0]] * 6 + [[2000.0, 5.0]] * 2)
    scaled = robust_scale(raw)
    labels = np.array([0] * 6 + [1] * 2)
    segs = name_segments(raw, scaled, labels, kept=[0, 4])  # sw_rain_level, hospital_km
    assert segs[0]["name"].startswith("close to the state middle") and segs[1]["name"] == "wet"
    assert segs[1]["centroid"]["sw_rain_level"] == pytest.approx(2000.0)


def test_committed_summary_is_consistent():
    s = json.loads((OUT / "summary.json").read_text("utf-8"))
    assert s["n_districts"] == 30 and 2 <= s["k"] <= 6
    best = max(
        (t for t in s["silhouette_by_k"] if t["smallest_segment"] >= 3),
        key=lambda t: (t["silhouette"], -t["k"]),
    )
    assert best["k"] == s["k"] and best["silhouette"] == s["silhouette"]
    stable = s["bootstrap"]["median_ari"] >= s["bootstrap"]["bar"] == 0.6
    assert s["publish_decision"] == ("descriptive typology" if stable else "exploratory")
    assert sum(g["districts"] for g in s["segments"]) == 30 and len(s["segments"]) == s["k"]
    rows = (OUT / "segments.csv").read_text("utf-8").splitlines()
    assert len(rows) == 31 and rows[0] == "district,segment,segment_name"
    text = json.dumps(s)
    assert "imd_mm" not in text and len(s["limits"]) == 4


def test_notebook_reproduces_from_a_clean_process(tmp_path):
    nb = json.loads((ROOT / "notebooks/14_ka_district_segments.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    env = os.environ | {"ATLAS_EDA_OUT": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)
    names = sorted(p.name for p in OUT.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    for name in names:
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), name
