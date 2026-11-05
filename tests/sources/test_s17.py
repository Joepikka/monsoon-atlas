"""T020 acceptance: the S17 adapter round trip keeps IDs, names, parent state and version on the
real T019 files (local raw; skipped in CI); malformed, empty and changed files fail; a disabled
source fails closed."""

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
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s17 import HOSTS, S17

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S17")
EVIDENCE = {
    e["id"]: e
    for e in json.loads((ROOT / "tests/fixtures/s17/manifest.json").read_text("utf-8"))["evidence"]
}


def artifact(eid: str, path: Path | None = None) -> RawArtifact:
    e = EVIDENCE[eid]
    real = RAW / e["raw_path"]
    if path is None and not real.exists():
        pytest.skip("raw evidence is local only")
    return RawArtifact(
        sha256=e["sha256"],
        path=path or real,
        fetched_at=e["fetched_at"],
        media_type=e["media_type"],
        response_status=e["status"],
        source_url=e["url"],
        schema_mapping_version="s17-v1",
    )


@cache
def karnataka():
    return S17("ka").parse(artifact("e06"), CONFIG, adm1=artifact("e05"))


def test_roundtrip_keeps_ids_names_parent_and_version(tmp_path):
    table = karnataka()
    pq.write_table(table, tmp_path / "s17.parquet")
    back = pq.read_table(tmp_path / "s17.parquet")
    assert back.equals(table)
    validate_table(back)
    assert read_mapping(back)["provider_to_canonical"]["shapeID"] == "source_place_id"
    assert back.num_rows == 30  # T019: Vijayanagara is not in this release
    names = set(back["name"].to_pylist())
    assert {"Bangalore", "Mysore", "Dakshina Kannada", "Bellary"} <= names
    assert "Vijayanagara" not in names
    assert set(back["boundary_version"].to_pylist()) == {"geoboundaries-IND-ADM2-9469f09"}
    assert len(set(back["place_id"].to_pylist())) == 30
    assert len(set(back["parent_id"].to_pylist())) == 1
    assert set(back["admin_level"].to_pylist()) == {"ADM2"}


def test_geometry_is_wkb_multipolygon_in_karnataka():
    blob = karnataka()["geometry"][0].as_py()
    order, kind, parts = struct.unpack_from("<BII", blob)
    assert (order, kind) == (1, 6) and parts >= 1
    _, ptype, rings, points = struct.unpack_from("<BIII", blob, 9)
    lon, lat = struct.unpack_from("<dd", blob, 22)
    assert ptype == 3 and rings >= 1 and points >= 4
    assert 74 < lon < 78.7 and 11.5 < lat < 18.5


def small_copy(tmp_path: Path, edit) -> RawArtifact:
    body = json.loads(artifact("e06").path.read_text("utf-8"))
    out = tmp_path / "adm2.json"
    out.write_text(json.dumps(edit(body)), encoding="utf-8")
    return artifact("e06", out)


def test_malformed_empty_and_changed_rejected(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_bytes(artifact("e06").path.read_bytes()[:1000])
    adm1 = artifact("e05")
    with pytest.raises(IngestError, match="not JSON"):
        S17("ka").parse(artifact("e06", broken), CONFIG, adm1=adm1)
    with pytest.raises(IngestError, match="no features"):
        S17("ka").parse(small_copy(tmp_path, lambda b: b | {"features": []}), CONFIG, adm1=adm1)

    def rename(body):
        body["features"][0]["properties"]["shapeLabel"] = body["features"][0]["properties"].pop(
            "shapeName"
        )
        return body

    with pytest.raises(IngestError, match="properties changed"):
        S17("ka").parse(small_copy(tmp_path, rename), CONFIG, adm1=adm1)


def test_disabled_and_missing_adm1_fail_closed():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        S17("ka").parse(artifact("e06"), off, adm1=artifact("e05"))
    with pytest.raises(IngestError, match="ADM1"):
        S17("ka").parse(artifact("e06"), CONFIG)


def test_fetch_follows_published_links(tmp_path):
    meta2, meta1 = artifact("e03").path.read_bytes(), artifact("e04").path.read_bytes()
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        seen.append(url)
        body = (
            meta2
            if url.endswith("/ADM2/")
            else meta1
            if url.endswith("/ADM1/")
            else b'{"features": []}'
        )
        return httpx.Response(200, content=body, headers={"content-type": "application/json"})

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S17",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=6, max_bytes=1024**2),
        raw_root=tmp_path,
    )
    S17("ka", fetcher).fetch(ctx)
    assert seen[1].endswith("/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2.geojson")
    assert seen[3].endswith("/ADM1/geoBoundaries-IND-ADM1_simplified.geojson")
