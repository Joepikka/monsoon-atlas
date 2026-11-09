"""T050 acceptance: the S04 adapter round trip preserves units, IDs and source timestamps on a
real Open-Meteo CAMS response (CC BY 4.0, committed fixture); malformed, empty and changed
responses fail; a disabled source fails closed; the issue time comes only from the metadata."""

import hashlib
import json
from datetime import UTC, datetime
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
from atlas.ingest.s04 import HOSTS, MEASURES, S04

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
FORECAST = FIX / "s04_openmeteo_cams_global_bengaluru_2026-11-09.json"  # T049 e08
META = FIX / "s04_openmeteo_meta_cams_global_2026-11-09.json"  # T049 e07 and e09
FETCHED = datetime(2026, 11, 9, 4, 53, 24, 537610, tzinfo=UTC)  # actual retrieval of FORECAST
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S04")
ADAPTER = S04("ka", [(12.97, 77.59)])
POLLUTANTS = ["pm25_ugm3", "pm10_ugm3", "no2_ugm3"]


def artifact(path: Path, url: str = "https://air-quality-api.open-meteo.com/v1/air-quality"):
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/json",
        response_status=200,
        source_url=url,
        schema_mapping_version="s04-v1",
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
    pq.write_table(table, tmp_path / "s04.parquet")
    back = pq.read_table(tmp_path / "s04.parquet")
    assert back.equals(table)
    validate_table(back, measures=POLLUTANTS)
    assert read_mapping(back)["provider_to_canonical"]["pm2_5"] == "pm25_ugm3"
    assert back.num_rows == 120 and len(set(back["record_id"].to_pylist())) == 120
    first = back.slice(0, 1).to_pylist()[0]
    assert first["cell_id"] == "om_cams_global_13.0000N_77.6000E"
    assert (first["product"], first["provenance"]) == ("cams_global", "model")
    assert first["issued_at"] == datetime(2026, 11, 8, 12, tzinfo=UTC)
    assert first["published_at"] == datetime(2026, 11, 8, 21, 48, 32, tzinfo=UTC)
    assert first["available_at"] == FETCHED == first["fetched_at"]  # later than ready + 10 min
    assert first["valid_at"] == datetime(2026, 11, 9, tzinfo=UTC)
    source = json.loads(FORECAST.read_text("utf-8"))["hourly"]
    assert (first["pm25_ugm3"], first["pm10_ugm3"], first["no2_ugm3"]) == (
        source["pm2_5"][0],
        source["pm10"][0],
        source["nitrogen_dioxide"][0],
    )


def test_hours_past_data_end_are_null_with_reason():
    table = parse(artifact(FORECAST))
    gone = table.filter(pc.equal(table["missing_reason"], "out_of_coverage"))
    assert gone.num_rows == 11  # T049: data_end_time 13 Nov 13:00 UTC is exclusive
    assert all(gone[c].null_count == 11 for c in POLLUTANTS)
    assert min(gone["valid_at"].to_pylist()) == datetime(2026, 11, 13, 13, tzinfo=UTC)


def test_negative_pollutant_is_rejected(tmp_path):
    def bad(body):
        body["hourly"]["nitrogen_dioxide"][5] = -0.1
        return body

    table = parse(edited(tmp_path, bad))
    row = table.filter(pc.equal(table["missing_reason"], "quality_rejected")).to_pylist()
    assert len(row) == 1 and row[0]["no2_ugm3"] is None and row[0]["pm25_ugm3"] is None
    assert row[0]["quality_flags"] == ["out_of_range"]


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s04.json").read_text("utf-8"))
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
        lambda b: b["hourly_units"].update(pm2_5="ppb") or b,
        lambda b: b["hourly"].pop("nitrogen_dioxide") and b,
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


def serve(meta_bodies: list[bytes], seen: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        body = meta_bodies.pop(0) if "meta.json" in request.url.path else FORECAST.read_bytes()
        return httpx.Response(200, content=body, headers={"content-type": "application/json"})

    return handler


def context(tmp_path) -> FetchContext:
    return FetchContext(
        source_id="S04",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=6, max_bytes=1024**2),
        raw_root=tmp_path,
    )


def adapter(tmp_path, bodies: list[bytes], seen: list[str]) -> S04:
    transport = httpx.MockTransport(serve(bodies, seen))
    return S04("ka", [(12.97, 77.59)], Fetcher(RawStore(tmp_path), HOSTS, transport=transport))


def test_fetch_reads_metadata_around_the_forecast(tmp_path):
    seen: list[str] = []
    meta = META.read_bytes()
    meta_raw, forecast = adapter(tmp_path, [meta, meta], seen).fetch(context(tmp_path))
    assert [urlsplit(u).path for u in seen] == [
        "/data/cams_global/static/meta.json",
        "/v1/air-quality",
        "/data/cams_global/static/meta.json",
    ]
    query = parse_qs(urlsplit(seen[1]).query)
    assert query["domains"] == ["cams_global"] and query["timezone"] == ["GMT"]
    assert query["hourly"] == ["pm2_5,pm10,nitrogen_dioxide"]
    assert ADAPTER.parse(forecast, CONFIG, meta=meta_raw).num_rows == 120


def test_fetch_rejects_a_run_that_changes_mid_call(tmp_path):
    meta = json.loads(META.read_text("utf-8"))
    newer = dict(meta, last_run_initialisation_time=meta["last_run_initialisation_time"] + 43200)
    bodies = [json.dumps(meta).encode(), json.dumps(newer).encode()]
    with pytest.raises(IngestError, match="run changed"):
        adapter(tmp_path, bodies, []).fetch(context(tmp_path))
