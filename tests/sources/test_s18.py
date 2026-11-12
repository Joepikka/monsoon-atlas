"""T022 acceptance: the S18 adapter reads a real cut of the owner's Southern Zone extract (ODbL,
OpenStreetMap contributors; committed fixture), keeps facilities and road ways inside the state
polygon with type, id, version and tags; malformed, empty and version-less input fails; fetch
never downloads (robots.txt, D34); a disabled source fails closed."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.s18 import S18, kind_of, owner_file

shapely = pytest.importorskip("shapely")  # geo lock (D35)
osmium = pytest.importorskip("osmium")

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "tests" / "fixtures" / "s18_southern_zone_bengaluru_261111.osm.pbf"
URL = "https://download.geofabrik.de/asia/india/southern-zone-261111.osm.pbf"
FETCHED = datetime(2026, 11, 12, 5, 20, 10, tzinfo=UTC)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S18")
BENGALURU = shapely.to_wkb(shapely.box(77.40, 12.80, 77.80, 13.20))


def parse(path: Path, area: bytes = BENGALURU, config=CONFIG):
    return S18("ka", area).parse(owner_file(path, URL, FETCHED), config)


def test_source_is_enabled_and_verified():
    assert CONFIG.enabled and CONFIG.verified_by == "configs/sources/s18.yaml"


def test_roundtrip_keeps_ids_versions_tags_and_geometry(tmp_path):
    table = parse(SAMPLE)
    pq.write_table(table, tmp_path / "s18.parquet")
    back = pq.read_table(tmp_path / "s18.parquet")
    assert back.equals(table)
    validate_table(back)
    assert read_mapping(back)["provider_to_canonical"]["object version"] == "osm_version"
    kinds = set(back["feature_kind"].to_pylist())
    assert {"hospital", "police", "fire_station", "clinic", "road"} <= kinds
    keys = list(zip(back["osm_type"].to_pylist(), back["osm_id"].to_pylist(), strict=True))
    assert len(keys) == len(set(keys)) and len(set(back["record_id"].to_pylist())) == len(keys)
    assert min(back["osm_version"].to_pylist()) >= 1
    for row in back.to_pylist():
        geom = shapely.from_wkb(row["geometry"])
        assert geom.is_valid and geom.geom_type in {"Point", "LineString"}
        assert (
            kind_of(json.loads(row["tags_json"]), row["osm_type"] == "way") == row["feature_kind"]
        )
        assert row["provenance"] == "inferred" and row["valid_at"] is None
        assert row["licence_id"] == "odbl-1.0-openstreetmap"
    assert not any("opening" in t for t in back["tags_json"].to_pylist() if '"shelter"' in t)


def test_polygon_clips_by_centroid():
    everything = parse(SAMPLE, shapely.to_wkb(shapely.box(70, 5, 96, 20)))
    bengaluru = parse(SAMPLE)
    outside = everything.num_rows - bengaluru.num_rows
    assert outside >= 1  # the Chennai hospital (Tamil Nadu) is dropped

    def hospitals(t):
        return pc.sum(pc.equal(t["feature_kind"], "hospital")).as_py()

    assert hospitals(everything) == hospitals(bengaluru) + 1


def test_malformed_and_empty_extracts_fail(tmp_path):
    cut = tmp_path / "truncated.osm.pbf"
    data = SAMPLE.read_bytes()
    cut.write_bytes(data[: len(data) // 2])
    with pytest.raises(IngestError):
        parse(cut)
    empty = tmp_path / "empty.osm.pbf"
    empty.write_bytes(b"")
    with pytest.raises(IngestError, match="empty"):
        parse(empty)


def test_missing_version_fails(tmp_path):
    out = tmp_path / "noversion.osm.pbf"
    with osmium.SimpleWriter(str(out)) as w:
        node = osmium.osm.mutable.Node(id=1, location=(77.6, 12.97), tags={"amenity": "police"})
        w.add_node(node)
    with pytest.raises(IngestError, match="no version"):
        parse(out)


def test_fetch_never_downloads_and_disabled_fails_closed(tmp_path):
    ctx = FetchContext(
        source_id="S18",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=1, max_bytes=1),
        raw_root=tmp_path,
    )
    with pytest.raises(SourceUnavailable, match="robots.txt"):
        S18("ka", BENGALURU).fetch(ctx)
    assert not any(tmp_path.iterdir())
    with pytest.raises(SourceUnavailable, match="disabled"):
        parse(SAMPLE, config=CONFIG.model_copy(update={"enabled": False}))
