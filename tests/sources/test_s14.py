"""T068 acceptance: the S14 adapter decodes real Terrarium tiles (public-domain sources, committed
fixtures) into tile metadata with plausible land and sea ranges; malformed, empty and changed
tiles fail; a disabled source fails closed."""

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
from atlas.ingest.s14 import BUCKET, HOSTS, MEASURES, S14

Image = pytest.importorskip("PIL.Image")  # decoding needs pillow (geo lock, D35)

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
LAND = FIX / "s14_terrarium_bengaluru_10_732_474.png"  # T067 e05
SEA = FIX / "s14_terrarium_arabian_sea_8_180_119.png"  # T067 e06
FETCHED = datetime(2026, 11, 9, 7, 50, 22, tzinfo=UTC)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S14")
ADAPTER = S14("ka", [(10, 732, 474)])


def artifact(path: Path, key: str) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="image/png",
        response_status=200,
        source_url=f"{BUCKET}/{key}",
        schema_mapping_version="s14-v1",
    )


def test_roundtrip_keeps_tile_ids_encoding_and_range(tmp_path):
    table = ADAPTER.parse(artifact(LAND, "terrarium/10/732/474.png"), CONFIG)
    pq.write_table(table, tmp_path / "s14.parquet")
    back = pq.read_table(tmp_path / "s14.parquet")
    assert back.equals(table)
    validate_table(back, measures=["min_m", "max_m"])
    assert read_mapping(back)["provider_to_canonical"]["object key"] == "tile_key"
    row = back.to_pylist()[0]
    assert (row["tile_key"], row["z"], row["x"], row["y"]) == (
        "terrarium/10/732/474.png",
        10,
        732,
        474,
    )
    assert (row["elevation_encoding"], row["crs"], row["valid_at"]) == (
        "terrarium",
        "EPSG:3857",
        None,
    )
    assert 700 < row["min_m"] < row["max_m"] < 1000  # Bengaluru plateau


def test_sea_tile_keeps_negative_bathymetry():
    row = ADAPTER.parse(artifact(SEA, "terrarium/8/180/119.png"), CONFIG).to_pylist()[0]
    assert row["min_m"] < -2000 and row["missing_reason"] is None


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s14.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64", "int64": "int64"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_and_empty_tiles_rejected(tmp_path):
    broken = tmp_path / "broken.png"
    broken.write_bytes(LAND.read_bytes()[:300])
    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    for path in (broken, empty):
        with pytest.raises(IngestError, match="PNG"):
            ADAPTER.parse(artifact(path, "terrarium/10/732/474.png"), CONFIG)


def test_changed_tiles_rejected(tmp_path):
    small = tmp_path / "small.png"
    Image.open(LAND).resize((128, 128)).save(small)
    grey = tmp_path / "grey.png"
    Image.open(LAND).convert("L").save(grey)
    high = tmp_path / "high.png"
    Image.new("RGB", (256, 256), (255, 255, 255)).save(high)  # 32767 m: outside the range
    for path, match in ((small, "256"), (grey, "RGB"), (high, "outside")):
        with pytest.raises(IngestError, match=match):
            ADAPTER.parse(artifact(path, "terrarium/10/732/474.png"), CONFIG)
    with pytest.raises(IngestError, match="URL"):
        ADAPTER.parse(artifact(LAND, "normal/10/732/474.png"), CONFIG)


def test_disabled_source_fails_closed_and_tiles_checked():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(LAND, "terrarium/10/732/474.png"), off)
    with pytest.raises(ValueError, match="invalid tile"):
        S14("ka", [(10, 1024, 0)])


def test_fetch_requests_each_tile_once(tmp_path):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        body = LAND.read_bytes() if "/10/" in request.url.path else SEA.read_bytes()
        return httpx.Response(200, content=body, headers={"content-type": "image/png"})

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S14",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=2, max_bytes=1024**2),
        raw_root=tmp_path,
    )
    raws = S14("ka", [(10, 732, 474), (8, 180, 119)], fetcher).fetch(ctx)
    assert seen == [f"{BUCKET}/terrarium/10/732/474.png", f"{BUCKET}/terrarium/8/180/119.png"]
    assert [ADAPTER.parse(r, CONFIG)["z"][0].as_py() for r in raws] == [10, 8]
