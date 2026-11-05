"""T012 acceptance: the S02 adapter round trip preserves units, IDs and source timestamps on real
Open-Meteo ERA5 responses (CC BY 4.0, committed fixtures); malformed, empty and changed responses
fail; a disabled source fails closed; release-lag days are null with a reason, not zero."""

import hashlib
import json
from datetime import UTC, date, datetime
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
from atlas.ingest.s02 import HOSTS, MEASURES, S02

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
RECENT = FIX / "s02_openmeteo_era5_bengaluru_2026-10-20_11-04.json"
EARLY = FIX / "s02_openmeteo_era5_bengaluru_1940-01-01_07.json"
FETCHED = datetime(2026, 11, 5, 13, 1, 7, 707756, tzinfo=UTC)  # actual retrieval of RECENT
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S02")
ADAPTER = S02("ka", [(12.97, 77.59)], date(2026, 10, 20), date(2026, 11, 4))


def artifact(path: Path) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/json",
        response_status=200,
        source_url="https://archive-api.open-meteo.com/v1/archive",
        schema_mapping_version="s02-v1",
    )


def edited(tmp_path: Path, edit) -> RawArtifact:
    out = tmp_path / "era5.json"
    out.write_text(json.dumps(edit(json.loads(RECENT.read_text("utf-8")))), encoding="utf-8")
    return artifact(out)


def test_roundtrip_preserves_units_ids_and_timestamps(tmp_path):
    table = ADAPTER.parse(artifact(RECENT), CONFIG)
    pq.write_table(table, tmp_path / "s02.parquet")
    back = pq.read_table(tmp_path / "s02.parquet")
    assert back.equals(table)
    validate_table(back, measures=["rain_mm", "tmax_c", "tmin_c"])
    assert read_mapping(back)["provider_to_canonical"]["precipitation_sum"] == "rain_mm"
    assert back.num_rows == 16 and len(set(back["record_id"].to_pylist())) == 16
    first = back.slice(0, 1).to_pylist()[0]
    assert (first["cell_id"], first["date_local"], first["product"]) == (
        "om_era5_13.0000N_77.5000E",
        date(2026, 10, 20),
        "era5",
    )
    assert (first["rain_mm"], first["tmax_c"], first["tmin_c"]) == (0.3, 28.9, 21.0)  # T011 e05
    assert first["valid_at"] == datetime(2026, 10, 20, 18, 30, tzinfo=UTC)  # end of the IST day
    assert first["available_at"] == first["fetched_at"] == FETCHED
    assert first["provenance"] == "model" and first["issued_at"] is None


def test_release_lag_days_are_not_yet_available():
    table = ADAPTER.parse(artifact(RECENT), CONFIG)
    lag = table.filter(pc.equal(table["missing_reason"], "not_yet_available"))
    assert [d.isoformat() for d in lag["date_local"].to_pylist()] == [
        "2026-10-31",
        "2026-11-01",
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
    ]
    assert lag["rain_mm"].null_count == 5


def test_partial_first_day_is_out_of_coverage():
    table = S02("ka", [(12.97, 77.59)], date(1940, 1, 1), date(1940, 1, 7)).parse(
        artifact(EARLY), CONFIG
    )
    first = table.slice(0, 1).to_pylist()[0]
    assert first["missing_reason"] == "out_of_coverage" and first["tmax_c"] is None
    assert table.filter(pc.is_null(table["missing_reason"])).num_rows == 6


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s02.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64", "date32[day]": "date32"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_and_empty_rejected(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_bytes(RECENT.read_bytes()[:200])
    with pytest.raises(IngestError, match="not JSON"):
        ADAPTER.parse(artifact(broken), CONFIG)
    empty = tmp_path / "empty.json"
    empty.write_text("[]", encoding="utf-8")
    with pytest.raises(IngestError, match="empty"):
        ADAPTER.parse(artifact(empty), CONFIG)


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b["daily_units"].update(precipitation_sum="inch") or b,
        lambda b: b["daily"].pop("temperature_2m_min") and b,
        lambda b: b.update(utc_offset_seconds=0) or b,
    ],
    ids=["unit", "missing column", "not ist"],
)
def test_changed_columns_rejected(tmp_path, change):
    with pytest.raises(IngestError):
        ADAPTER.parse(edited(tmp_path, change), CONFIG)


def test_impossible_values_rejected(tmp_path):
    def swap(body):
        body["daily"]["temperature_2m_min"][0] = 40.0  # above that day's maximum
        return body

    table = ADAPTER.parse(edited(tmp_path, swap), CONFIG)
    bad = table.filter(pc.equal(table["missing_reason"], "quality_rejected")).to_pylist()
    assert len(bad) == 1 and bad[0]["quality_flags"] == ["out_of_range"]


def test_disabled_source_fails_closed():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(RECENT), off)


def test_fetch_requests_era5_with_units(tmp_path):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200, content=RECENT.read_bytes(), headers={"content-type": "application/json"}
        )

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S02",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=2, max_bytes=1024**2),
        raw_root=tmp_path,
    )
    adapter = S02("ka", [(12.97, 77.59)], date(2026, 10, 20), date(2026, 11, 4), fetcher)
    (raw,) = adapter.fetch(ctx)
    query = parse_qs(urlsplit(seen[0]).query)
    assert query["models"] == ["era5"] and query["timezone"] == ["Asia/Kolkata"]
    assert query["start_date"] == ["2026-10-20"] and query["precipitation_unit"] == ["mm"]
    assert adapter.parse(raw, CONFIG).num_rows == 16
