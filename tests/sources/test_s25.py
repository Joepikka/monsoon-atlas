"""T076 acceptance: the S25 adapter reads a real FIRMS area CSV (VIIRS NOAA-20 NRT, Karnataka box,
fetched 12 Nov 2026 with the owner's MAP_KEY; NASA open data, credit FIRMS, LANCE and ESDIS),
keeps detections inside the state polygon with UTC time, confidence, FRP and latency; drops
repeats; fails on malformed, empty and changed input; and never records the key."""

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
from atlas.ingest.base import FetchError, IngestError, SourceUnavailable
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s25 import HOST, S25, KeyPathFetcher, area_url

shapely = pytest.importorskip("shapely")

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "tests" / "fixtures" / "s25_firms_viirs_noaa20_ka_20261112.csv"
URL = (
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv/MAP_KEY/VIIRS_NOAA20_NRT/74,11.5,78.6,18.5/2"
)
FETCHED = datetime(2026, 11, 12, 7, 16, 58, tzinfo=UTC)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S25")
BOX = shapely.to_wkb(shapely.box(74.0, 11.5, 78.6, 18.5))
KEY = "0123456789abcdef0123456789abcdef"  # a made-up key for transport tests


def artifact(path: Path) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="text/csv",
        response_status=200,
        source_url=URL,
        schema_mapping_version="s25-v1",
    )


def lines() -> list[str]:
    return [line + "\n" for line in SAMPLE.read_text("utf-8").splitlines()]


def copy(tmp_path: Path, content: list[str]) -> RawArtifact:
    out = tmp_path / "area.csv"
    out.write_text("".join(content), encoding="utf-8")
    return artifact(out)


def test_source_and_schema_are_enabled():
    schema = json.loads((ROOT / "schemas/s25.json").read_text("utf-8"))
    assert CONFIG.enabled and CONFIG.verified_by == "configs/sources/s25.yaml"
    assert CONFIG.secret_env == "NASA_FIRMS_MAP_KEY" and schema["mapping_version"] == "s25-v1"


def test_roundtrip_keeps_time_confidence_frp_and_latency(tmp_path):
    table = S25().parse(artifact(SAMPLE), CONFIG, area_wkb=BOX)
    pq.write_table(table, tmp_path / "s25.parquet")
    back = pq.read_table(tmp_path / "s25.parquet")
    assert back.equals(table) and back.num_rows == 113
    validate_table(back, measures=["frp_mw"])
    assert read_mapping(back)["provider_to_canonical"]["frp (MW)"] == "frp_mw"
    assert set(back["confidence"].to_pylist()) == {"low", "nominal", "high"}
    assert set(back["sensor"].to_pylist()) == {"N20"}
    assert len(set(back["detection_id"].to_pylist())) == 113
    latency = back["latency_minutes"].to_pylist()
    assert min(latency) > 0 and max(latency) < 24 * 60
    row = back.slice(0, 1).to_pylist()[0]
    assert row["provenance"] == "model" and row["valid_at"] == row["acquired_at"]
    assert "MAP_KEY" in row["source_url"]


def test_polygon_clips_and_repeats_are_dropped(tmp_path):
    rows = lines()
    twice = S25().parse(copy(tmp_path, rows + rows[1:6]), CONFIG, area_wkb=BOX)
    assert twice.num_rows == 113
    small = shapely.to_wkb(shapely.box(74.0, 11.5, 74.1, 11.6))
    assert S25().parse(artifact(SAMPLE), CONFIG, area_wkb=small).num_rows < 113


def test_malformed_empty_and_changed_fail(tmp_path):
    rows = lines()
    with pytest.raises(IngestError, match="malformed"):
        S25().parse(copy(tmp_path, [rows[0], "1,2,3\n"]), CONFIG, area_wkb=BOX)
    with pytest.raises(IngestError, match="empty"):
        S25().parse(copy(tmp_path, []), CONFIG, area_wkb=BOX)
    with pytest.raises(IngestError, match="columns changed"):
        S25().parse(
            copy(tmp_path, [rows[0].replace("frp", "frp_mw"), *rows[1:]]), CONFIG, area_wkb=BOX
        )
    bad = rows[1].split(",")
    bad[9] = "x"
    with pytest.raises(IngestError, match="confidence"):
        S25().parse(copy(tmp_path, [rows[0], ",".join(bad)]), CONFIG, area_wkb=BOX)
    with pytest.raises(SourceUnavailable, match="disabled"):
        S25().parse(artifact(SAMPLE), CONFIG.model_copy(update={"enabled": False}), area_wkb=BOX)


def ctx(tmp_path: Path, secrets: dict) -> FetchContext:
    return FetchContext(
        source_id="S25",
        state="ka",
        run_id="t",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=2, max_bytes=1024**2),
        raw_root=tmp_path,
        secrets=secrets,
    )


def test_key_goes_only_into_the_request_path(tmp_path):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200, content=SAMPLE.read_bytes(), headers={"content-type": "text/csv"}
        )

    fetcher = KeyPathFetcher(RawStore(tmp_path), {HOST}, transport=httpx.MockTransport(handler))
    [art] = S25(fetcher=fetcher).fetch(
        ctx(tmp_path, {"NASA_FIRMS_MAP_KEY": KEY}), box=(74.0, 11.5, 78.6, 18.5), days=2
    )
    assert seen == [URL.replace("MAP_KEY", KEY)]
    assert art.source_url == URL == area_url((74.0, 11.5, 78.6, 18.5), 2)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes(), path


def test_redirects_and_missing_key_are_refused(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if "/elsewhere/" in str(request.url):
            return httpx.Response(200, content=b"x", headers={"content-type": "text/csv"})
        return httpx.Response(302, headers={"location": f"https://{HOST}/elsewhere/{KEY}/"})

    fetcher = KeyPathFetcher(RawStore(tmp_path), {HOST}, transport=httpx.MockTransport(handler))
    with pytest.raises(FetchError, match="redirect"):
        S25(fetcher=fetcher).fetch(ctx(tmp_path, {"NASA_FIRMS_MAP_KEY": KEY}), box=(74, 11, 75, 12))
    with pytest.raises(SourceUnavailable, match="H09"):
        S25(fetcher=fetcher).fetch(ctx(tmp_path, {}), box=(74, 11, 75, 12))
    with pytest.raises(ValueError, match="1 to 5"):
        area_url((74, 11, 75, 12), 6)
