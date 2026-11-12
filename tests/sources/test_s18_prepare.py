"""D175: S18 facilities for the Nearby tab come from real adapter rows, keep only hospitals,
police and fire stations within 25 km of a place, link to the OSM object and never include
shelters; the web fixture is exactly what the Python export produces."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from atlas.config import load_state
from atlas.ingest.s18 import S18, owner_file
from atlas.ingest.s18_prepare import KINDS, MAX_KM, facilities, km

shapely = pytest.importorskip("shapely")
pytest.importorskip("osmium")

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "tests" / "fixtures" / "s18_southern_zone_bengaluru_261111.osm.pbf"
WEB = ROOT / "web" / "tests" / "fixtures" / "s18-facilities-bengaluru.json"
PLACE = json.loads((ROOT / "web/tests/fixtures/bangalore-place.json").read_text("utf-8"))
URL = "https://download.geofabrik.de/asia/india/southern-zone-261111.osm.pbf"
FETCHED = datetime(2026, 11, 12, 5, 20, 10, tzinfo=UTC)


def rows():
    config = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S18")
    area = shapely.to_wkb(shapely.box(77.40, 12.80, 77.80, 13.20))
    return S18("ka", area).parse(owner_file(SAMPLE, URL, FETCHED), config)


def test_web_fixture_is_the_python_export():
    assert json.loads(WEB.read_text("utf-8")) == facilities(rows(), [PLACE])


def test_only_named_kinds_within_range_with_osm_links():
    table = rows()
    out = facilities(table, [PLACE])
    assert {f["kind"] for f in out} == set(KINDS)
    assert "shelter" in table["feature_kind"].to_pylist()  # present in the input, left out
    for f in out:
        assert km(PLACE["longitude"], PLACE["latitude"], f["longitude"], f["latitude"]) <= MAX_KM
        kind, osm_id = f["facility_id"].split(":")[1:]
        assert f["source_url"] == f"https://www.openstreetmap.org/{kind}/{osm_id}"
        assert f["verification_status"] == "source_checked" and f["source_id"] == "S18"
        assert f["fetched_at"] == "2026-11-12T05:20:10Z" and f["name"]
    far = {"place_id": "x", "longitude": 80.25, "latitude": 13.05}  # Chennai
    assert facilities(table, [far]) == []  # the Chennai hospital was clipped by the polygon
