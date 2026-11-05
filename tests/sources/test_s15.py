"""T016 acceptance: the S15 adapter round trip keeps the style URL, tile revision and attribution
from the real T015 style and TileJSON (local raw files; skipped in CI); malformed, empty and
changed responses fail; a disabled source fails closed; no tile is downloaded."""

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
from atlas.ingest.s15 import HOSTS, MEASURES, S15

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S15")
EVIDENCE = {
    e["id"]: e
    for e in json.loads((ROOT / "tests/fixtures/s15/manifest.json").read_text("utf-8"))["evidence"]
}


def artifact(eid: str, path: Path | None = None) -> RawArtifact:
    e = EVIDENCE[eid]
    real = RAW / e["raw_path"]
    if path is None and not real.exists():
        pytest.skip("raw evidence is local only (not redistributed)")
    return RawArtifact(
        sha256=e["sha256"],
        path=path or real,
        fetched_at=e["fetched_at"],
        media_type=e["media_type"],
        response_status=e["status"],
        source_url=e["url"],
        schema_mapping_version="s15-v1",
    )


def edited(tmp_path: Path, eid: str, edit) -> RawArtifact:
    out = tmp_path / f"{eid}.json"
    out.write_text(
        json.dumps(edit(json.loads(artifact(eid).path.read_text("utf-8")))), encoding="utf-8"
    )
    return artifact(eid, out)


def test_roundtrip_keeps_revision_and_attribution(tmp_path):
    table = S15("ka").parse(artifact("e05"), CONFIG, tilejson=artifact("e06"))
    pq.write_table(table, tmp_path / "s15.parquet")
    back = pq.read_table(tmp_path / "s15.parquet")
    assert back.equals(table)
    validate_table(back)
    assert read_mapping(back)["mapping_version"] == "s15-v1"
    row = back.to_pylist()[0]
    assert row["style_url"] == "https://tiles.openfreemap.org/styles/liberty"
    assert (
        row["revision"] == "20261101_080013_pt" and row["snapshot_id"] == "S15-20261101_080013_pt"
    )
    assert "OpenStreetMap" in row["attribution"] and "OpenMapTiles" in row["attribution"]
    assert row["fetched_at"] == datetime.fromisoformat(EVIDENCE["e05"]["fetched_at"])


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s15.json").read_text("utf-8"))
    assert [(f["name"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, f.nullable) for f in MEASURES
    ]


def test_malformed_empty_and_changed_rejected(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_bytes(artifact("e06").path.read_bytes()[:100])
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")
    style = artifact("e05")
    with pytest.raises(IngestError, match="not JSON"):
        S15("ka").parse(style, CONFIG, tilejson=artifact("e06", broken))
    with pytest.raises(IngestError, match="empty"):
        S15("ka").parse(style, CONFIG, tilejson=artifact("e06", empty))
    no_credit = edited(tmp_path, "e06", lambda tj: tj | {"attribution": "OpenFreeMap"})
    with pytest.raises(IngestError, match="attribution"):
        S15("ka").parse(style, CONFIG, tilejson=no_credit)
    other = edited(
        tmp_path, "e05", lambda s: s | {"sources": {"openmaptiles": {"type": "raster", "url": "x"}}}
    )
    with pytest.raises(IngestError, match="does not match"):
        S15("ka").parse(other, CONFIG, tilejson=artifact("e06"))


def test_disabled_and_missing_tilejson_fail_closed():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        S15("ka").parse(artifact("e05"), off, tilejson=artifact("e06"))
    with pytest.raises(IngestError, match="TileJSON"):
        S15("ka").parse(artifact("e05"), CONFIG)


def test_fetch_reads_style_and_tilejson_only(tmp_path):
    bodies = {
        "/styles/liberty": artifact("e05").path.read_bytes(),
        "/planet": artifact("e06").path.read_bytes(),
    }
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(
            200, content=bodies[request.url.path], headers={"content-type": "application/json"}
        )

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S15",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=3, max_bytes=1024**2),
        raw_root=tmp_path,
    )
    style, tilejson = S15("ka", fetcher=fetcher).fetch(ctx)
    assert seen == ["/styles/liberty", "/planet"]
    assert S15("ka").parse(style, CONFIG, tilejson=tilejson).num_rows == 1
