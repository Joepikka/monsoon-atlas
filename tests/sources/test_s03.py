"""T048 acceptance: the S03 adapter round trip preserves units, IDs and source timestamps on real
Open-Meteo GloFAS responses (CC BY 4.0, committed fixtures); malformed, empty and changed
responses fail; a disabled source fails closed; missing river cells stay null, never zero."""

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
from atlas.ingest.s03 import HOSTS, MEASURES, S03

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
JULY = FIX / "s03_openmeteo_glofas_cauvery_2024-07.json"  # T047 e11
SEA = FIX / "s03_openmeteo_glofas_sea_2024-07-01_07.json"  # T047 e08
FETCHED = datetime(2026, 11, 8, 18, 45, 54, 630967, tzinfo=UTC)  # actual retrieval of JULY
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S03")
ADAPTER = S03("ka", [(12.42, 76.69)], date(2024, 7, 1), date(2024, 7, 31))


def artifact(path: Path) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/json",
        response_status=200,
        source_url="https://flood-api.open-meteo.com/v1/flood",
        schema_mapping_version="s03-v1",
    )


def edited(tmp_path: Path, edit) -> RawArtifact:
    out = tmp_path / "glofas.json"
    out.write_text(json.dumps(edit(json.loads(JULY.read_text("utf-8")))), encoding="utf-8")
    return artifact(out)


def test_fixtures_are_the_recorded_evidence():
    manifest = json.loads((FIX / "s03" / "manifest.json").read_text("utf-8"))
    sha = {e["id"]: e["sha256"] for e in manifest["evidence"]}
    assert hashlib.sha256(JULY.read_bytes()).hexdigest() == sha["e11"]
    assert hashlib.sha256(SEA.read_bytes()).hexdigest() == sha["e08"]


def test_roundtrip_preserves_units_ids_and_timestamps(tmp_path):
    table = ADAPTER.parse(artifact(JULY), CONFIG)
    pq.write_table(table, tmp_path / "s03.parquet")
    back = pq.read_table(tmp_path / "s03.parquet")
    assert back.equals(table)
    validate_table(back, measures=["discharge_m3s"])
    assert read_mapping(back)["provider_to_canonical"]["river_discharge"] == "discharge_m3s"
    assert back.num_rows == 31 and len(set(back["record_id"].to_pylist())) == 31
    first = back.slice(0, 1).to_pylist()[0]
    assert (first["river_cell_id"], first["valid_date"], first["product"]) == (
        "glofas_seamless_v4_12.4250N_76.6750E",
        date(2024, 7, 1),
        "seamless_v4",
    )
    assert first["discharge_m3s"] == 37.19 and first["member"] is None  # T047 e11
    assert first["valid_at"] == datetime(2024, 7, 1, 18, 30, tzinfo=UTC)  # end of the IST day
    assert first["available_at"] == first["fetched_at"] == FETCHED
    assert first["provenance"] == "model" and first["issued_at"] is None
    assert max(back["discharge_m3s"].to_pylist()) == 1031.76


def test_missing_river_cell_stays_null_not_zero():
    table = S03("ka", [(13.0, 73.5)], date(2024, 7, 1), date(2024, 7, 7)).parse(
        artifact(SEA), CONFIG
    )
    assert table.num_rows == 7 and table["discharge_m3s"].null_count == 7
    assert set(table["missing_reason"].to_pylist()) == {"out_of_coverage"}


def test_days_after_the_newest_value_are_not_yet_available(tmp_path):
    def tail_missing(body):
        body["daily"]["river_discharge"][-3:] = [None, None, None]
        return body

    table = ADAPTER.parse(edited(tmp_path, tail_missing), CONFIG)
    lag = table.filter(pc.equal(table["missing_reason"], "not_yet_available"))
    assert [d.isoformat() for d in lag["valid_date"].to_pylist()] == [
        "2024-07-29",
        "2024-07-30",
        "2024-07-31",
    ]


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s03.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64", "date32[day]": "date32", "int64": "int64"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_and_empty_rejected(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_bytes(JULY.read_bytes()[:120])
    with pytest.raises(IngestError, match="not JSON"):
        ADAPTER.parse(artifact(broken), CONFIG)
    empty = tmp_path / "empty.json"
    empty.write_text("[]", encoding="utf-8")
    with pytest.raises(IngestError, match="empty"):
        ADAPTER.parse(artifact(empty), CONFIG)


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b["daily_units"].update(river_discharge="ft³/s") or b,
        lambda b: b["daily"].pop("river_discharge") and b,
        lambda b: b.update(utc_offset_seconds=0) or b,
    ],
    ids=["unit", "missing column", "not ist"],
)
def test_changed_columns_rejected(tmp_path, change):
    with pytest.raises(IngestError):
        ADAPTER.parse(edited(tmp_path, change), CONFIG)


def test_negative_discharge_rejected(tmp_path):
    def negative(body):
        body["daily"]["river_discharge"][0] = -1.0
        return body

    table = ADAPTER.parse(edited(tmp_path, negative), CONFIG)
    bad = table.filter(pc.equal(table["missing_reason"], "quality_rejected")).to_pylist()
    assert len(bad) == 1 and bad[0]["quality_flags"] == ["out_of_range"]
    assert bad[0]["discharge_m3s"] is None


def test_disabled_source_fails_closed():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        ADAPTER.parse(artifact(JULY), off)


def test_fetch_names_the_model_and_ist_days(tmp_path):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(
            200, content=JULY.read_bytes(), headers={"content-type": "application/json"}
        )

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    ctx = FetchContext(
        source_id="S03",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=2, max_bytes=1024**2),
        raw_root=tmp_path,
    )
    adapter = S03("ka", [(12.42, 76.69)], date(2024, 7, 1), date(2024, 7, 31), fetcher)
    (raw,) = adapter.fetch(ctx)
    query = parse_qs(urlsplit(seen[0]).query)
    assert query["models"] == ["seamless_v4"] and query["timezone"] == ["Asia/Kolkata"]
    assert query["daily"] == ["river_discharge"] and query["start_date"] == ["2024-07-01"]
    assert adapter.parse(raw, CONFIG).num_rows == 31
