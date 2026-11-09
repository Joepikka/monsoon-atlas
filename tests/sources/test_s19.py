"""T070 acceptance: the S19 adapter round trip keeps IDs, areas and confidence on real Open
Buildings v3 rows (first 300 rows of cell 3b3, CC BY 4.0, committed fixture); rows outside the
box and duplicate Plus Codes are dropped; malformed, empty and changed shards fail; a disabled
source fails closed; fetch resolves shard URLs from the index and streams them to disk."""

import gzip
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s19 import HOSTS, INDEX, MEASURES, S19

shapely = pytest.importorskip("shapely")  # geo lock (D35)

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "tests" / "fixtures" / "s19_open_buildings_v3_3b3_first300.csv.gz"  # T069 e04
URL = "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_4_gzip/3b3_buildings.csv.gz"
FETCHED = datetime(2026, 11, 9, 7, 54, 32, tzinfo=UTC)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S19")
ADAPTER = S19("ka", cells=("3b3",))
ALL = (73.0, 0.0, 74.0, 5.0)  # covers every fixture row


def artifact(path: Path) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/gzip",
        response_status=200,
        source_url=URL,
        schema_mapping_version="s19-v1",
    )


def lines() -> list[str]:
    return gzip.open(SAMPLE, "rt", encoding="utf-8", newline="").read().splitlines(keepends=True)


def shard(tmp_path: Path, content: list[str]) -> RawArtifact:
    out = tmp_path / "shard.csv.gz"
    with gzip.open(out, "wt", encoding="utf-8", newline="") as f:
        f.writelines(content)
    return artifact(out)


def test_roundtrip_keeps_ids_geometry_area_and_confidence(tmp_path):
    table = ADAPTER.parse(artifact(SAMPLE), CONFIG, box=ALL)
    pq.write_table(table, tmp_path / "s19.parquet")
    back = pq.read_table(tmp_path / "s19.parquet")
    assert back.equals(table)
    validate_table(back, measures=["area_m2", "confidence"])
    assert read_mapping(back)["provider_to_canonical"]["area_in_meters"] == "area_m2"
    assert back.num_rows == 300 and len(set(back["record_id"].to_pylist())) == 300
    first = back.slice(0, 1).to_pylist()[0]
    assert (first["building_id"], first["plus_code"]) == ("6JPM5GG3+97RM", "6JPM5GG3+97RM")
    assert (first["area_m2"], first["confidence"], first["source_release"]) == (
        166.5919,
        0.8909,
        "open-buildings-v3",
    )
    assert shapely.from_wkb(first["geometry"]).geom_type == "Polygon"
    assert first["provenance"] == "model" and first["valid_at"] is None
    assert sum(c >= 0.75 for c in back["confidence"].to_pylist()) == 193  # display default


def test_box_clips_and_duplicates_are_dropped(tmp_path):
    rows = lines()
    table = ADAPTER.parse(shard(tmp_path, rows + rows[1:6]), CONFIG, box=ALL)
    assert table.num_rows == 300  # five repeated Plus Codes dropped
    north = ADAPTER.parse(artifact(SAMPLE), CONFIG, box=(73.0, 4.0, 74.0, 5.0))
    assert 0 < north.num_rows < 300
    assert ADAPTER.parse(artifact(SAMPLE), CONFIG, box=(77.0, 12.0, 78.0, 13.0)).num_rows == 0


def test_batches_are_bounded():
    batches = list(ADAPTER.parse_batches(artifact(SAMPLE), CONFIG, box=ALL, batch_rows=128))
    assert [b.num_rows for b in batches] == [128, 128, 44]


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s19.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64", "binary": "wkb"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_and_empty_shards_rejected(tmp_path):
    broken = tmp_path / "broken.csv.gz"
    broken.write_bytes(SAMPLE.read_bytes()[:400])
    with pytest.raises(IngestError, match="unreadable"):
        ADAPTER.parse(artifact(broken), CONFIG, box=ALL)
    with pytest.raises(IngestError, match="columns"):
        ADAPTER.parse(shard(tmp_path, []), CONFIG, box=ALL)


@pytest.mark.parametrize(
    "change",
    [
        lambda rows: [rows[0].replace("full_plus_code", "plus_code"), *rows[1:]],
        lambda rows: [rows[0], rows[1].replace(",0.8909,", ",1.4,"), *rows[2:]],
        lambda rows: [rows[0], rows[1].replace(",166.5919,", ",-1,"), *rows[2:]],
        lambda rows: [rows[0], rows[1].replace("POLYGON((", "POLYGON(("), "1,2\n"],
    ],
    ids=["renamed column", "confidence", "area", "short row"],
)
def test_changed_shards_rejected(tmp_path, change):
    with pytest.raises(IngestError):
        ADAPTER.parse(shard(tmp_path, change(lines())), CONFIG, box=ALL)


def test_disabled_source_fails_closed():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(SAMPLE), off, box=ALL)


def test_fetch_resolves_urls_from_the_index_and_streams(tmp_path):
    index = {"features": [{"properties": {"tile_id": "3b3", "tile_url": URL, "size_mb": 3.9}}]}
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if str(request.url) == INDEX:
            return httpx.Response(200, json=index)
        return httpx.Response(200, content=SAMPLE.read_bytes())

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S19",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=3, max_bytes=1024**2),
        raw_root=tmp_path,
    )
    _, raw = S19("ka", cells=("3b3",), fetcher=fetcher).fetch(ctx)
    assert seen == [INDEX, URL] and raw.sha256 == hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
    with pytest.raises(IngestError, match="not in the index"):
        S19("ka", cells=("3bb",), fetcher=fetcher).fetch(ctx)
