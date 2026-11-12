"""T052 acceptance: the S05 adapter round trip preserves units, IDs and source timestamps on a
real Open-Meteo ensemble response (CC BY 4.0, committed fixture); the member count comes from the
response; hours outside the run stay null; malformed, empty and changed responses fail; a disabled
source fails closed."""

import hashlib
import json
from collections import Counter
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
from atlas.ingest.s05 import HOSTS, MEASURES, S05

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
FORECAST = FIX / "s05_openmeteo_ecmwf_ifs025_ensemble_bengaluru_2026-11-09.json"  # T051 e08
META = FIX / "s05_openmeteo_meta_ecmwf_ifs025_ensemble_2026-11-09.json"  # T051 e07 and e09
FETCHED = datetime(2026, 11, 9, 5, 15, 12, 347719, tzinfo=UTC)  # retrieval of FORECAST (T051 e08)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S05")
ADAPTER = S05("ka", [(12.97, 77.59)])
IN_RUN = 141  # 9 Nov 00:00 to 14 Nov 20:00 UTC: before the exclusive data_end_time 21:00


def artifact(path: Path, url: str = "https://ensemble-api.open-meteo.com/v1/ensemble"):
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/json",
        response_status=200,
        source_url=url,
        schema_mapping_version="s05-v1",
    )


def edited(tmp_path: Path, edit, source: Path = FORECAST) -> RawArtifact:
    out = tmp_path / source.name
    out.write_text(json.dumps(edit(json.loads(source.read_text("utf-8")))), encoding="utf-8")
    return artifact(out)


def parse(raw: RawArtifact, meta: RawArtifact | None = None):
    return ADAPTER.parse(raw, CONFIG, meta=meta or artifact(META))


def test_roundtrip_preserves_units_ids_members_and_timestamps(tmp_path):
    table = parse(artifact(FORECAST))
    pq.write_table(table, tmp_path / "s05.parquet")
    back = pq.read_table(tmp_path / "s05.parquet")
    assert back.equals(table)
    validate_table(back, measures=["rain_mm", "temperature_c"])
    assert read_mapping(back)["provider_to_canonical"]["series suffix"] == "member_id"
    assert back.num_rows == 360 * 51 and len(set(back["record_id"].to_pylist())) == 360 * 51
    members = sorted(set(back["member_id"].to_pylist()))
    assert members == [f"{i:02d}" for i in range(51)]  # read from the response, not assumed
    first = back.slice(0, 1).to_pylist()[0]
    assert first["cell_id"] == "om_ecmwf_ifs025_ensemble_13.0000N_77.5000E"
    assert (first["model"], first["member_id"], first["provenance"]) == (
        "ecmwf_ifs025_ensemble",
        "00",
        "model",
    )
    assert first["issued_at"] == datetime(2026, 11, 8, 18, tzinfo=UTC)
    assert first["published_at"] == datetime(2026, 11, 9, 2, 43, 50, tzinfo=UTC)
    assert first["available_at"] == FETCHED == first["fetched_at"]  # later than ready + 10 min
    assert first["valid_at"] == datetime(2026, 11, 9, tzinfo=UTC)
    source = json.loads(FORECAST.read_text("utf-8"))["hourly"]
    row = table.filter(
        pc.and_(pc.equal(table["member_id"], "50"), pc.equal(table["valid_at"], first["valid_at"]))
    ).to_pylist()[0]
    assert (row["rain_mm"], row["temperature_c"]) == (
        source["precipitation_member50"][0],
        source["temperature_2m_member50"][0],
    )


def test_hours_outside_the_run_are_null_and_negatives_rejected():
    table = parse(artifact(FORECAST))
    reasons = Counter(table["missing_reason"].to_pylist())
    assert reasons == {
        None: IN_RUN * 51 - 6,
        "out_of_coverage": (360 - IN_RUN) * 51,
        "quality_rejected": 6,
    }
    stale = table.filter(pc.equal(table["missing_reason"], "out_of_coverage"))
    assert min(stale["valid_at"].to_pylist()) == datetime(2026, 11, 14, 21, tzinfo=UTC)
    assert all(f == ["missing", "stale"] for f in stale["quality_flags"].to_pylist())
    assert stale["issued_at"].null_count == stale.num_rows  # another run: issue time unknown
    assert table["issued_at"].null_count == stale.num_rows
    bad = table.filter(pc.equal(table["missing_reason"], "quality_rejected")).to_pylist()
    assert sorted({r["member_id"] for r in bad}) == ["16", "37"]
    assert all(r["rain_mm"] is None and r["quality_flags"] == ["out_of_range"] for r in bad)


def test_hours_before_the_run_are_not_given_its_issue_time(tmp_path):
    def later_run(meta):  # pretend the 06:00 run of 9 Nov is the latest
        return dict(meta, last_run_initialisation_time=meta["last_run_initialisation_time"] + 43200)

    table = parse(artifact(FORECAST), meta=edited(tmp_path, later_run, META))
    early = table.filter(pc.less(table["valid_at"], datetime(2026, 11, 9, 6, tzinfo=UTC)))
    assert early.num_rows == 6 * 51 and early["rain_mm"].null_count == 6 * 51
    assert set(early["missing_reason"].to_pylist()) == {"out_of_coverage"}
    assert early["issued_at"].null_count == early.num_rows


def test_member_count_follows_the_response(tmp_path):
    def fewer(body):
        for key in [k for k in body["hourly"] if k.endswith(("member49", "member50"))]:
            body["hourly"].pop(key)
            body["hourly_units"].pop(key)
        return body

    table = parse(edited(tmp_path, fewer))
    assert len(set(table["member_id"].to_pylist())) == 49


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s05.json").read_text("utf-8"))
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
        lambda b: b["hourly_units"].update(precipitation_member07="inch") or b,
        lambda b: b["hourly"].pop("temperature_2m_member12") and b,
        lambda b: b["hourly"].update(wind_speed_10m=b["hourly"]["precipitation"]) or b,
        lambda b: b.update(utc_offset_seconds=19800) or b,
    ],
    ids=["unit", "member missing for one variable", "new column", "not utc"],
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
        source_id="S05",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=6, max_bytes=4 * 1024**2),
        raw_root=tmp_path,
    )


def adapter(tmp_path, bodies: list[bytes], seen: list[str]) -> S05:
    transport = httpx.MockTransport(serve(bodies, seen))
    return S05("ka", [(12.97, 77.59)], Fetcher(RawStore(tmp_path), HOSTS, transport=transport))


def test_fetch_reads_metadata_around_the_forecast(tmp_path):
    seen: list[str] = []
    meta = META.read_bytes()
    meta_raw, forecast = adapter(tmp_path, [meta, meta], seen).fetch(context(tmp_path))
    assert [urlsplit(u).path for u in seen] == [
        "/data/ecmwf_ifs025_ensemble/static/meta.json",
        "/v1/ensemble",
        "/data/ecmwf_ifs025_ensemble/static/meta.json",
    ]
    query = parse_qs(urlsplit(seen[1]).query)
    assert query["models"] == ["ecmwf_ifs025_ensemble"] and query["timezone"] == ["GMT"]
    assert query["precipitation_unit"] == ["mm"] and query["temperature_unit"] == ["celsius"]
    assert ADAPTER.parse(forecast, CONFIG, meta=meta_raw).num_rows == 360 * 51


def test_fetch_rejects_a_run_that_changes_mid_call(tmp_path):
    meta = json.loads(META.read_text("utf-8"))
    newer = dict(meta, last_run_initialisation_time=meta["last_run_initialisation_time"] + 21600)
    bodies = [json.dumps(meta).encode(), json.dumps(newer).encode()]
    with pytest.raises(IngestError, match="run changed"):
        adapter(tmp_path, bodies, []).fetch(context(tmp_path))
