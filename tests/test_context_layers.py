"""T105 acceptance: context layers are shown only when their source contract allows it; FIRMS
hotspots can never become confirmed (structure) fires; RERA rows keep no personal fields; building
footprints are clipped to one place boundary of the expected version; crime is district-year
totals of registered cases with an under-reporting note and no map join (D114)."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pytest

from atlas.config import load_state
from atlas.contracts import RawArtifact
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.s19 import S19
from atlas.ingest.s44 import FILES, S44
from atlas.spatial.context import (
    MIN_CONFIDENCE,
    buildings_in_place,
    crime_totals,
    fire_kind,
    layer_status,
    require,
    rera_public,
)

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests/fixtures"
STATE = load_state(ROOT / "configs/states/ka.yaml")


def artifact(path: Path, url: str, media: str) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=datetime(2026, 11, 9, 8, 0, tzinfo=UTC),
        media_type=media,
        response_status=200,
        source_url=url,
        schema_mapping_version="test",
    )


def status():
    return {s["layer"]: s for s in layer_status()}


def test_unavailable_layers_are_disabled_with_reason_and_evidence():
    layers = status()
    assert {k: v["available"] for k, v in layers.items()} == {
        "fire": False,
        "rera": False,
        "buildings": True,
        "crime": True,
    }
    assert "MAP_KEY" in layers["fire"]["reason"] and "H09" in layers["fire"]["reason"]
    assert "K-RERA" in layers["rera"]["reason"]
    for layer in layers.values():
        assert (ROOT / layer["evidence"]).exists() and layer["landing_url"].startswith("https://")
        assert (layer["reason"] is None) == layer["available"]


def test_no_firms_hotspot_becomes_a_confirmed_structure_fire():
    assert "not a confirmed fire" in status()["fire"]["note"]
    assert fire_kind("thermal_anomaly") == "thermal_anomaly"
    for category in ("fire", "confirmed_fire", "structure_fire"):
        with pytest.raises(ValueError, match="thermal_anomaly"):
            fire_kind(category)
    with pytest.raises(SourceUnavailable, match="fire layer unavailable"):
        require("fire")


def test_rera_keeps_only_public_project_fields():
    row = {
        "project_id": "PRM/KA/RERA/1251/309/PR/171024/000001",
        "project_name": "example",
        "promoter_name": "a person",
        "promoter_phone": "0",
        "promoter_email": "x",
        "address": "y",
    }
    assert set(rera_public(row)) == {"project_id", "project_name"}
    with pytest.raises(SourceUnavailable):
        require("rera")


@pytest.fixture(scope="module")
def footprints():
    pytest.importorskip("shapely")
    sample = FIX / "s19_open_buildings_v3_3b3_first300.csv.gz"  # real CC BY 4.0 rows (T069 e04)
    url = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_4_gzip/3b3_buildings.csv.gz"
    return S19("ka", cells=("3b3",)).parse(
        artifact(sample, url, "application/gzip"), STATE.source("S19"), box=(73.0, 0.0, 74.0, 5.0)
    )


def h3_place(table: pa.Table) -> dict:
    """The real H3 resolution-7 analysis cell around the first fixture footprint."""
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


def test_buildings_are_clipped_to_a_versioned_boundary(footprints):
    import shapely

    place = h3_place(footprints)
    features = buildings_in_place(footprints, place, boundary_version="h3-v4-res7")
    boundary = shapely.from_wkb(place["geometry"])
    assert features
    for f in features:
        assert f["properties"]["confidence"] >= MIN_CONFIDENCE
        assert f["properties"]["boundary_version"] == "h3-v4-res7"
        assert shapely.geometry.shape(f["geometry"]).within(boundary.buffer(1e-9))
    assert len(features) <= footprints.num_rows
    with pytest.raises(ValueError, match="boundary version"):
        buildings_in_place(footprints, place, boundary_version="h3-v3-res7")
    with pytest.raises(ValueError, match="place kind"):
        buildings_in_place(footprints, place | {"kind": "pincode"}, boundary_version="h3-v4-res7")
    other = footprints.set_column(
        footprints.schema.get_field_index("boundary_version"),
        "boundary_version",
        pa.array(["gba2025"] * footprints.num_rows),
    )
    with pytest.raises(ValueError, match="other boundary versions"):
        buildings_in_place(other, place, boundary_version="h3-v4-res7")


def test_crime_is_district_year_registered_totals_with_a_note():
    totals = FIX / "s44_opencity_ksp_totals_2023.csv"  # real public-domain table (T087 e05)
    table = S44("ka").parse(
        artifact(totals, FILES[2023], "text/csv"), STATE.source("S44"), year=2023
    )
    rows = crime_totals(table)
    assert rows and {r["year"] for r in rows} == {2023}
    assert all(r["measure"] == "registered cases" and r["map_join"] is None for r in rows)
    assert all("under-reporting" in r["note"] for r in rows)
    assert len(rows) == len({r["district_id"] for r in rows})
    heads = S44("ka").parse(
        artifact(FIX / "s44_opencity_ksp_district_ipc_2024.csv", FILES[2024], "text/csv"),
        STATE.source("S44"),
        year=2024,
    )
    assert crime_totals(heads) == []  # no published Total: heads are never summed


def test_web_context_controls(web_check):
    web_check("test", "--", "src/map/ContextLayers.test.ts")


def test_web_fixture_matches_the_source_contracts():
    import json

    fixture = json.loads((ROOT / "web/tests/fixtures/context-layers.json").read_text("utf-8"))
    assert fixture == layer_status()
