"""T031 acceptance: the S40 adapter round trip keeps the 369 GBA 2025 ward IDs, names, parent
corporations and version from the real T030 KML (local raw; skipped in CI); malformed, empty and
changed files fail; a disabled source fails closed."""

import json
import struct
from datetime import UTC, datetime
from functools import cache
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import validate_table
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s40 import HOSTS, S40, URL

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S40")
E04 = next(
    e
    for e in json.loads((ROOT / "tests/fixtures/s40/manifest.json").read_text("utf-8"))["evidence"]
    if e["id"] == "e04"
)


def artifact(path: Path | None = None) -> RawArtifact:
    real = RAW / E04["raw_path"]
    if path is None and not real.exists():
        pytest.skip("raw evidence is local only")
    return RawArtifact(
        sha256=E04["sha256"],
        path=path or real,
        fetched_at=E04["fetched_at"],
        media_type=E04["media_type"],
        response_status=E04["status"],
        source_url=E04["url"],
        schema_mapping_version="s40-v1",
    )


@cache
def wards():
    return S40().parse(artifact(), CONFIG)


def edited(tmp_path: Path, old: str, new: str) -> RawArtifact:
    text = artifact().path.read_text("utf-8")
    assert old in text
    out = tmp_path / "wards.kml"
    out.write_text(text.replace(old, new, 1), encoding="utf-8")
    return artifact(out)


def test_roundtrip_keeps_ids_names_parents_and_version(tmp_path):
    table = wards()
    pq.write_table(table, tmp_path / "s40.parquet")
    back = pq.read_table(tmp_path / "s40.parquet")
    assert back.equals(table)
    validate_table(back)
    assert back.num_rows == 369 and len(set(back["place_id"].to_pylist())) == 369
    assert set(back["parent_name"].to_pylist()) == {"Central", "East", "North", "South", "West"}
    assert set(back["boundary_version"].to_pylist()) == {"gba-2025-final-369"}
    first = back.slice(0, 1).to_pylist()[0]
    assert (first["place_id"], first["name"], first["parent_id"]) == (
        "gba2025-c1-w24",
        "Agaram",
        "gba2025-c1",
    )
    assert first["redistribution_allowed"] and first["source_url"] == URL


def test_geometry_is_wkb_in_bengaluru():
    blob = wards()["geometry"][0].as_py()
    assert struct.unpack_from("<BII", blob)[:2] == (1, 6)
    lon, lat = struct.unpack_from("<dd", blob, 22)
    assert 77.3 < lon < 77.9 and 12.7 < lat < 13.3


def test_malformed_empty_and_changed_rejected(tmp_path):
    broken = tmp_path / "broken.kml"
    broken.write_bytes(artifact().path.read_bytes()[:2000])
    empty = tmp_path / "empty.kml"
    empty.write_text(
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document/></kml>', encoding="utf-8"
    )
    with pytest.raises(IngestError, match="not KML"):
        S40().parse(artifact(broken), CONFIG)
    with pytest.raises(IngestError, match="no placemarks"):
        S40().parse(artifact(empty), CONFIG)
    with pytest.raises(IngestError, match="fields changed"):
        S40().parse(
            edited(tmp_path, '<SimpleData name="ward_name">', '<SimpleData name="ward_label">'),
            CONFIG,
        )


def test_disabled_source_fails_closed():
    with pytest.raises(SourceUnavailable):
        S40().parse(artifact(), CONFIG.model_copy(update={"enabled": False}))
    with pytest.raises(SourceUnavailable):
        S40("kl")


def test_fetch_uses_the_published_resource(tmp_path):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200, content=b"<kml/>", headers={"content-type": "application/vnd.google-earth.kml+xml"}
        )

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S40",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=1, max_bytes=1024),
        raw_root=tmp_path,
    )
    S40(fetcher=fetcher).fetch(ctx)
    assert seen == [URL] == [E04["url"]]
