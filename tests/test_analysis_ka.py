"""T041 acceptance: BMTC coverage counts each person once (covered + uncovered = total, per cell and
overall), measures catchments along the walking network rather than straight lines, excludes
motorways and foot=no ways, and the notebook re-run from a fresh process reproduces the committed
outputs byte for byte. The raw files are local only, so the notebook run skips in CI."""

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from atlas.analysis.coverage import (
    RADIUS_M,
    Edge,
    catchment,
    cell_coverage,
    metres,
    trips_per_hour,
    walk_edges,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/eda/04_bmtc_coverage"
RAW = ROOT / "data/raw"
LOCAL = all((RAW / s).exists() for s in ("S16", "S17", "S18", "S30"))
STEP = 0.001  # degrees of longitude on the equator line below, about 111 m


def line(n: int) -> list[Edge]:
    """A straight street of n segments along the equator."""
    pts = [(round(i * STEP, 7), 0.0) for i in range(n + 1)]
    return walk_edges([('{"highway": "residential"}', pts)])


def test_catchment_follows_the_network_and_caps_at_the_radius():
    edges = line(10)
    seg = edges[0].length_m
    covered = catchment(edges, {edges[0].u: 0.0})
    assert sum(covered) == pytest.approx(RADIUS_M)
    assert covered[:4] == pytest.approx([seg] * 4) and covered[-1] == 0
    # snap distance counts toward the radius
    assert sum(catchment(edges, {edges[0].u: 200.0})) == pytest.approx(RADIUS_M - 200)
    assert sum(catchment(edges, {edges[0].u: 600.0})) == 0


def test_overlapping_catchments_never_double_count():
    edges = line(4)  # about 445 m long, fully inside one 500 m catchment from either end
    both = catchment(edges, {edges[0].u: 0.0, edges[-1].v: 0.0})
    one = catchment(edges, {edges[0].u: 0.0})
    assert sum(both) == pytest.approx(sum(e.length_m for e in edges)) == pytest.approx(sum(one))
    rows = cell_coverage({"c1": 1000.0}, ["c1"] * len(edges), edges, both)
    assert rows[0]["covered_population"] == pytest.approx(1000.0)


def test_disconnected_street_is_not_reached_by_straight_line_distance():
    near = line(2)
    across = walk_edges([('{"highway": "residential"}', [(0.0, 0.0005), (STEP, 0.0005)])])
    covered = catchment(near + across, {near[0].u: 0.0})
    assert covered[-1] == 0  # 55 m away in a straight line, but no path joins it


def test_population_is_conserved_per_cell_and_overall():
    edges = line(10)
    covered = catchment(edges, {edges[0].u: 0.0})
    cells = ["a"] * 5 + ["b"] * 5
    pop = {"a": 300.0, "b": 700.0, "empty": 50.0}
    rows = {r["cell_id"]: r for r in cell_coverage(pop, cells, edges, covered)}
    assert sum(r["population"] for r in rows.values()) == sum(pop.values())
    for r in rows.values():
        assert 0 <= r["covered_population"] <= r["population"]
        assert 0 <= r["covered_fraction"] <= 1
    assert rows["empty"]["walk_m"] == 0 and rows["empty"]["covered_population"] == 0
    assert rows["a"]["covered_fraction"] > rows["b"]["covered_fraction"]


def test_motorways_and_foot_no_ways_are_not_walkable():
    pts = [(0.0, 0.0), (STEP, 0.0)]
    ways = [
        ('{"highway": "motorway"}', pts),
        ('{"highway": "primary", "foot": "no"}', pts),
        ('{"highway": "footway"}', pts),
    ]
    edges = walk_edges(ways)
    assert len(edges) == 1 and edges[0].length_m == pytest.approx(metres(0, 0, STEP, 0))


def test_trips_per_hour_keeps_service_hours_past_midnight():
    hours = trips_per_hour([5 * 3600, 5 * 3600 + 59, 8 * 3600, 24 * 3600 + 10])
    assert (hours[5], hours[8], hours[24], hours[0]) == (2, 1, 1, 0)
    assert sum(hours.values()) == 4


def test_committed_outputs_conserve_population():
    summary = json.loads((OUT / "summary.json").read_text("utf-8"))
    with open(OUT / "cell_coverage.csv", encoding="utf-8") as f:
        cells = list(csv.DictReader(f))
    total = sum(float(c["population"]) for c in cells)
    covered = sum(float(c["covered_population"]) for c in cells)
    p = summary["population"]
    assert abs(total - p["total"]) <= len(cells) * 0.05 + 1
    assert abs(covered - p["covered"]) <= len(cells) * 0.05 + 1
    assert p["covered"] + p["uncovered"] == p["total"]
    assert all(float(c["covered_population"]) <= float(c["population"]) + 0.05 for c in cells)
    assert summary["radius_m"] == 500 and len(summary["limits"]) >= 4
    assert any("Scheduled supply only" in limit for limit in summary["limits"])


@pytest.mark.skipif(not LOCAL, reason="S16, S17, S18 and S30 raw files are local only")
def test_notebook_reproduces_from_a_clean_process(tmp_path):
    nb = json.loads((ROOT / "notebooks/04_bmtc_coverage.ipynb").read_text("utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    env = os.environ | {"ATLAS_EDA_OUT": str(tmp_path), "MPLBACKEND": "Agg"}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)
    names = sorted(p.name for p in OUT.iterdir())
    assert names == sorted(p.name for p in tmp_path.iterdir())
    for name in names:
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), name
