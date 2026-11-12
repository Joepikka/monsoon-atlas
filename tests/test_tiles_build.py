"""T185 acceptance: the testable parts of the PMTiles city-layer build (D151).

Not run, by design: Tippecanoe (Linux CI only, `tiles.yml` never dispatched), tile samples read
back from a PMTiles archive (none exists) and HTTP Range 206 plus CORS on a real host (no host
until H05/H06). Delivery therefore defaults to GeoJSON, and that default is what is tested.
"""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s19 import S19
from atlas.spatial.tiles import (
    ATTRIBUTION,
    SHARD_CAP,
    TIPPECANOE_VERSION,
    check_shard_sizes,
    clipped_buildings,
    delivery,
    plan_shards,
    require_tile_source,
    shard_collection,
    tippecanoe_args,
)

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests/fixtures"
WORKFLOW = (ROOT / ".github/workflows/tiles.yml").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def footprints():
    pytest.importorskip("shapely")
    sample = FIX / "s19_open_buildings_v3_3b3_first300.csv.gz"  # real CC BY 4.0 rows (T069 e04)
    url = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_4_gzip/3b3_buildings.csv.gz"
    raw = RawArtifact(
        sha256=hashlib.sha256(sample.read_bytes()).hexdigest(),
        path=sample,
        fetched_at=datetime(2026, 11, 9, 8, 0, tzinfo=UTC),
        media_type="application/gzip",
        response_status=200,
        source_url=url,
        schema_mapping_version="test",
    )
    state = load_state(ROOT / "configs/states/ka.yaml")
    return S19("ka", cells=("3b3",)).parse(raw, state.source("S19"), box=(73.0, 0.0, 74.0, 5.0))


def h3_place(table) -> dict:
    h3 = pytest.importorskip("h3")
    import shapely

    centre = shapely.from_wkb(table["geometry"][0].as_py()).centroid
    cell = h3.latlng_to_cell(centre.y, centre.x, 7)
    ring = [(lng, lat) for lat, lng in h3.cell_to_boundary(cell)]
    return {
        "place_id": f"h3:7:{cell}",
        "kind": "h3",
        "boundary_version": "h3-v4-res7",
        "geometry": shapely.to_wkb(shapely.Polygon(ring)),
    }


def test_clipped_tiles_keep_bounds_ids_attribution_and_confidence(footprints):
    import shapely

    place = h3_place(footprints)
    layer = clipped_buildings(footprints, place, boundary_version="h3-v4-res7")
    boundary = shapely.from_wkb(place["geometry"]).buffer(1e-9)
    ids = footprints["building_id"].to_pylist()
    got = [f["properties"]["building_id"] for f in layer["features"]]
    assert got and len(set(got)) == len(got) and set(got) <= set(ids)  # IDs preserved, unique
    assert layer["attribution"] == ATTRIBUTION["S19"]
    for f in layer["features"]:
        assert shapely.geometry.shape(f["geometry"]).within(boundary)  # bounds preserved
        assert f["properties"]["confidence"] >= 0.75
        assert f["properties"]["attribution"] == ATTRIBUTION["S19"]


def test_only_open_registered_sources_may_enter_a_tile_build():
    assert require_tile_source("S19") == ATTRIBUTION["S19"]
    for restricted in ("S08", "S30", "S12", "S20"):  # licence restricted
        with pytest.raises(SourceUnavailable, match="licence restricted"):
            require_tile_source(restricted)
    with pytest.raises(SourceUnavailable, match="blocked"):  # S26: blocked, no licence statement
        require_tile_source("S26")
    with pytest.raises(SourceUnavailable, match="no registered attribution"):
        require_tile_source("S13")  # open licence, but nothing registers a tile credit for it


def test_shards_stay_under_twenty_mebibytes_and_keep_every_id_once():
    assert SHARD_CAP == 20 * 1024 * 1024
    mib = 1024 * 1024
    sizes = [(f"b{i}", 6 * mib) for i in range(7)]
    shards = plan_shards(sizes)
    assert [len(s) for s in shards] == [3, 3, 1]  # 3 x 6 MiB fits in 19 MiB, a fourth does not
    assert [k for s in shards for k in s] == [k for k, _ in sizes]
    with pytest.raises(ValueError, match="exceeds a shard"):
        plan_shards([("huge", SHARD_CAP)])
    assert plan_shards([]) == []


def test_collection_is_sharded_without_losing_or_repeating_a_feature():
    feats = [
        {
            "type": "Feature",
            "geometry": None,
            "properties": {"building_id": f"id{i}", "pad": "x" * 50},
        }
        for i in range(40)
    ]
    collection = {"type": "FeatureCollection", "attribution": "credit", "features": feats}
    parts = shard_collection(collection, cap=1500, reserve=300)
    assert len(parts) > 1
    seen = [f["properties"]["building_id"] for p in parts for f in p["features"]]
    assert seen == [f"id{i}" for i in range(40)]
    for p in parts:
        assert p["attribution"] == "credit"
        assert len(json.dumps(p["features"], separators=(",", ":"))) <= 1200 + 40


def test_built_archives_at_or_over_the_cap_fail(tmp_path):
    small, big = tmp_path / "a.pmtiles", tmp_path / "b.pmtiles"
    small.write_bytes(b"x" * 99)
    big.write_bytes(b"x" * 100)
    check_shard_sizes([small], cap=100)
    with pytest.raises(ValueError, match="b.pmtiles"):
        check_shard_sizes([small, big], cap=100)


def test_delivery_defaults_to_geojson_until_a_probe_saw_206_and_cors():
    site = "https://monsoon-atlas.example"
    assert delivery(None, None, site) == "geojson"  # no host, nothing probed (H05/H06)
    assert delivery(200, "*", site) == "geojson"  # Range ignored
    assert delivery(206, None, site) == "geojson"  # no CORS
    assert delivery(206, "https://other.example", site) == "geojson"
    assert delivery(206, "*", site) == "pmtiles"
    assert delivery(206, site, site) == "pmtiles"


def test_tippecanoe_arguments_name_the_layer_credit_and_id_field(tmp_path):
    args = tippecanoe_args(tmp_path / "in.geojson", tmp_path / "o.pmtiles", "buildings", "c", 14)
    assert args[:2] == ["tippecanoe", "-f"] and args[args.index("-l") + 1] == "buildings"
    assert args[args.index("--attribution") + 1] == "c"
    assert args[args.index("--use-attribute-for-id") + 1] == "building_id"


def test_workflow_is_manual_read_only_pinned_and_fails_closed_without_a_verified_commit():
    assert TIPPECANOE_VERSION == "2.79.0" and "2.79.0" in WORKFLOW
    assert re.search(r"(?m)^on:\s*\n\s+workflow_dispatch:", WORKFLOW)
    assert not re.search(r"(?m)^\s+(push|schedule|pull_request)\s*:", WORKFLOW)
    assert re.search(r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$", WORKFLOW)
    assert re.search(r"tippecanoe_commit:\s*\n(\s+.*\n)*?\s+required: true", WORKFLOW)
    guard = WORKFLOW.index("[0-9a-f]{40}")
    assert guard < WORKFLOW.index("repository: felt/tippecanoe")  # refused before any checkout
    assert "exit 1" in WORKFLOW[guard : guard + 400]
    for line in re.findall(r"uses:\s*(\S+)", WORKFLOW):
        assert re.search(r"@[0-9a-f]{40}$", line), line


def test_not_run_items_are_stated_not_passed():
    pytest.skip(
        "not run: Tippecanoe archive samples (none built), Range 206 and CORS on a no-card host "
        "(no host until H05/H06); retry when tiles.yml has produced an archive and a host exists"
    )
