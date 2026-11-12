"""D191: the public bus-access page bundles only derived T041 shares, exactly as the committed
report computes them; no stop, route, trip or time from the restricted S30 feed is included."""

import json
from pathlib import Path

from atlas.analysis.coverage import WEB, web_cells

ROOT = Path(__file__).resolve().parents[1]


def test_bundle_is_the_committed_report():
    assert json.loads(WEB.read_text("utf-8")) == json.loads(json.dumps(web_cells()))


def test_derived_only_no_timetable_fields():
    data = json.loads(WEB.read_text("utf-8"))
    assert set(data) == {
        "schema_version",
        "district",
        "service_date",
        "radius_m",
        "cell_deg",
        "population",
        "limits",
        "credit",
        "cells",
    }
    assert all(len(c) == 4 and 0 <= c[3] <= 1 for c in data["cells"])  # lon, lat, pop, share
    text = WEB.read_text("utf-8").lower()
    for word in ("stop_id", "route_id", "trip_id", "departure", "arrival"):
        assert word not in text, word
    assert "no stops, routes or timetables" in data["credit"]
    assert data["population"]["covered_share"] == 0.6534
