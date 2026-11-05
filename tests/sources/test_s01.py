"""T010 acceptance: the S01 adapter round trip preserves units, IDs and source timestamps on a
real Open-Meteo response (CC BY 4.0, committed fixture); malformed, empty and changed responses
fail; a disabled source fails closed; the issue time comes only from the model metadata."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.data.validate import read_mapping, validate_table
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s01 import HOSTS, MEASURES, S01

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
FORECAST = FIX / "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json"
META = FIX / "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json"
FETCHED = datetime(2026, 11, 5, 12, 55, 1, 914727, tzinfo=UTC)  # actual retrieval of FORECAST
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S01")
ADAPTER = S01("ka", [(12.97, 77.59)])


def artifact(path: Path, url: str = "https://api.open-meteo.com/v1/forecast") -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/json",
        response_status=200,
        source_url=url,
        schema_mapping_version="s01-v1",
    )


def edited(tmp_path: Path, edit) -> RawArtifact:
    body = json.loads(FORECAST.read_text("utf-8"))
    out = tmp_path / "forecast.json"
    out.write_text(json.dumps(edit(body)), encoding="utf-8")
    return artifact(out)


def parse(raw: RawArtifact):
    return ADAPTER.parse(raw, CONFIG, meta=artifact(META))


def test_roundtrip_preserves_units_ids_and_timestamps(tmp_path):
    table = parse(artifact(FORECAST))
    pq.write_table(table, tmp_path / "s01.parquet")
    back = pq.read_table(tmp_path / "s01.parquet")
    assert back.equals(table)
    validate_table(back, measures=["temperature_c", "rain_mm", "humidity_pct", "wind_ms"])
    assert read_mapping(back)["provider_to_canonical"]["wind_speed_10m"] == "wind_ms"
    assert back.num_rows == 384 and len(set(back["record_id"].to_pylist())) == 384
    first = back.slice(0, 1).to_pylist()[0]
    assert first["cell_id"] == "om_ecmwf_ifs025_13.0000N_77.5000E"
    assert first["issued_at"] == datetime(2026, 11, 5, tzinfo=UTC)
    assert first["published_at"] == datetime(2026, 11, 5, 9, 4, 15, tzinfo=UTC)
    assert first["available_at"] == FETCHED == first["fetched_at"]  # later than ready + 10 min
    assert first["valid_at"] == datetime(2026, 11, 5, tzinfo=UTC)
    source = json.loads(FORECAST.read_text("utf-8"))["hourly"]
    assert (first["temperature_c"], first["rain_mm"]) == (
        source["temperature_2m"][0],
        source["precipitation"][0],
    )


def test_hours_past_model_end_are_null_with_reason():
    table = parse(artifact(FORECAST))
    gone = table.filter(pc.equal(table["missing_reason"], "out_of_coverage"))
    assert gone.num_rows == 23  # T009: 23 trailing hours have no precipitation
    assert gone["rain_mm"].null_count == gone["humidity_pct"].null_count == 23
    assert min(gone["valid_at"].to_pylist()) > datetime(2026, 11, 20, tzinfo=UTC)


def test_out_of_range_humidity_is_rejected(tmp_path):
    def bad(body):
        body["hourly"]["relative_humidity_2m"][5] = 140
        return body

    table = parse(edited(tmp_path, bad))
    row = table.filter(pc.equal(table["missing_reason"], "quality_rejected")).to_pylist()
    assert len(row) == 1 and row[0]["humidity_pct"] is None
    assert row[0]["quality_flags"] == ["out_of_range"]


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s01.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_copy_rejected(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_bytes(FORECAST.read_bytes()[:500])
    with pytest.raises(IngestError, match="not JSON"):
        parse(artifact(broken))


def test_empty_response_rejected(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text("[]", encoding="utf-8")
    with pytest.raises(IngestError, match="empty"):
        parse(artifact(empty))


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b["hourly_units"].update(wind_speed_10m="km/h") or b,
        lambda b: b["hourly"].pop("relative_humidity_2m") and b,
        lambda b: b.update(utc_offset_seconds=19800) or b,
    ],
    ids=["unit", "missing column", "not utc"],
)
def test_changed_columns_rejected(tmp_path, change):
    with pytest.raises(IngestError):
        parse(edited(tmp_path, change))


def test_issue_time_needed_and_disabled_source_fails_closed():
    with pytest.raises(IngestError, match="issue time unknown"):
        ADAPTER.parse(artifact(FORECAST), CONFIG)
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(FORECAST), off, meta=artifact(META))
    with pytest.raises(ValueError, match="best_match"):
        S01("ka", [(12.97, 77.59)], model="best_match")


def serve(meta_bodies: list[bytes], seen: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        body = meta_bodies.pop(0) if "meta.json" in request.url.path else FORECAST.read_bytes()
        return httpx.Response(200, content=body, headers={"content-type": "application/json"})

    return handler


def context(tmp_path) -> FetchContext:
    return FetchContext(
        source_id="S01",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=6, max_bytes=1024**2),
        raw_root=tmp_path,
    )


def test_fetch_reads_metadata_around_the_forecast(tmp_path):
    seen: list[str] = []
    meta = META.read_bytes()
    transport = httpx.MockTransport(serve([meta, meta], seen))
    adapter = S01(
        "ka", [(12.97, 77.59)], fetcher=Fetcher(RawStore(tmp_path), HOSTS, transport=transport)
    )
    meta_raw, forecast = adapter.fetch(context(tmp_path))
    assert [urlsplit(u).path for u in seen] == [
        "/data/ecmwf_ifs025/static/meta.json",
        "/v1/forecast",
        "/data/ecmwf_ifs025/static/meta.json",
    ]
    query = parse_qs(urlsplit(seen[1]).query)
    assert query["models"] == ["ecmwf_ifs025"] and query["wind_speed_unit"] == ["ms"]
    assert query["timezone"] == ["GMT"] and query["precipitation_unit"] == ["mm"]
    assert adapter.parse(forecast, CONFIG, meta=meta_raw).num_rows == 384


def test_fetch_rejects_a_run_that_changes_mid_call(tmp_path):
    meta = json.loads(META.read_text("utf-8"))
    newer = dict(meta, last_run_initialisation_time=meta["last_run_initialisation_time"] + 21600)
    bodies = [json.dumps(meta).encode(), json.dumps(newer).encode()]
    transport = httpx.MockTransport(serve(bodies, []))
    adapter = S01(
        "ka", [(12.97, 77.59)], fetcher=Fetcher(RawStore(tmp_path), HOSTS, transport=transport)
    )
    with pytest.raises(IngestError, match="run changed"):
        adapter.fetch(context(tmp_path))


def test_available_at_waits_for_settle_time():
    early = FETCHED.replace(hour=9, minute=5)  # one minute after availability
    raw = artifact(FORECAST).model_copy(update={"fetched_at": early})
    first = parse(raw).slice(0, 1).to_pylist()[0]
    assert first["available_at"] == datetime(2026, 11, 5, 9, 4, 15, tzinfo=UTC) + timedelta(
        minutes=10
    )
