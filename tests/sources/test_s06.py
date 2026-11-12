"""T054 acceptance: the S06 adapter round trip preserves units, IDs and source timestamps on real
Open-Meteo climate responses (CC BY 4.0, committed fixtures); scenario stays null and bias
correction is recorded; malformed, empty and changed responses fail; a disabled source fails
closed."""

import hashlib
import json
from collections import Counter
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
from atlas.ingest.s06 import HOSTS, MEASURES, MODELS, S06

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures"
CORRECTED = FIX / "s06_openmeteo_climate_bengaluru_2050-01.json"  # T053 e08, bias-corrected
RAW = FIX / "s06_openmeteo_climate_raw_bengaluru_2000.json"  # T053 e07, bias correction off
FETCHED = datetime(2026, 11, 9, 6, 24, 9, 886685, tzinfo=UTC)  # retrieval of CORRECTED (e08)
CONFIG = load_state(ROOT / "configs" / "states" / "ka.yaml").source("S06")
POINT = [(12.97, 77.59)]
JAN_2050 = S06("ka", POINT, date(2050, 1, 1), date(2050, 1, 31))
YEAR_2000_RAW = S06("ka", POINT, date(2000, 1, 1), date(2000, 12, 31), bias_corrected=False)
URL = "https://climate-api.open-meteo.com/v1/climate"


def artifact(path: Path) -> RawArtifact:
    return RawArtifact(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        path=path,
        fetched_at=FETCHED,
        media_type="application/json",
        response_status=200,
        source_url=URL,
        schema_mapping_version="s06-v1",
    )


def edited(tmp_path: Path, edit) -> RawArtifact:
    out = tmp_path / CORRECTED.name
    out.write_text(json.dumps(edit(json.loads(CORRECTED.read_text("utf-8")))), encoding="utf-8")
    return artifact(out)


def parse(raw: RawArtifact, adapter: S06 = JAN_2050):
    return adapter.parse(raw, CONFIG)


def test_roundtrip_preserves_units_ids_and_timestamps(tmp_path):
    table = parse(artifact(CORRECTED))
    pq.write_table(table, tmp_path / "s06.parquet")
    back = pq.read_table(tmp_path / "s06.parquet")
    assert back.equals(table)
    validate_table(back, measures=["rain_mm", "tmax_c"])
    assert read_mapping(back)["provider_to_canonical"]["series suffix"] == "model"
    assert back.num_rows == 31 * 7 and len(set(back["record_id"].to_pylist())) == 31 * 7
    first = back.slice(0, 1).to_pylist()[0]
    assert first["cell_id"] == "om_cmip6_13.0000N_77.6000E"
    assert (first["model"], first["date_local"]) == ("CMCC_CM2_VHR4", date(2050, 1, 1))
    assert (first["scenario"], first["bias_corrected"], first["provenance"]) == (
        None,
        True,
        "model",
    )
    assert first["issued_at"] is None and first["published_at"] is None
    assert first["available_at"] == FETCHED == first["fetched_at"]
    assert first["valid_at"] == datetime(2050, 1, 2, tzinfo=UTC)  # end of the GMT day
    source = json.loads(CORRECTED.read_text("utf-8"))["daily"]
    assert (first["rain_mm"], first["tmax_c"]) == (
        source["precipitation_sum_CMCC_CM2_VHR4"][0],
        source["temperature_2m_max_CMCC_CM2_VHR4"][0],
    )


def test_missing_model_days_stay_null_never_zero():
    table = parse(artifact(CORRECTED))
    gone = table.filter(pc.equal(table["missing_reason"], "out_of_coverage"))
    assert set(gone["model"].to_pylist()) == {"EC_Earth3P_HR"}  # T053: ends 31 Dec 2049
    assert gone.num_rows == 31 and gone["rain_mm"].null_count == 31
    assert Counter(table["missing_reason"].to_pylist()) == {None: 31 * 6, "out_of_coverage": 31}


def test_raw_output_is_marked_and_keeps_its_values():
    table = parse(artifact(RAW), YEAR_2000_RAW)
    assert table.num_rows == 366 * 7 and set(table["bias_corrected"].to_pylist()) == {False}
    assert table["cell_id"][0].as_py() == "om_cmip6_12.8906N_77.5000E"  # model grid, not ERA5-Land
    mri = table.filter(pc.equal(table["model"], "MRI_AGCM3_2_S"))
    assert round(pc.sum(mri["rain_mm"]).as_py(), 1) == 587.1  # T053
    corrected_ids = set(parse(artifact(CORRECTED))["record_id"].to_pylist())
    assert not corrected_ids & set(table["record_id"].to_pylist())


def test_negative_rain_is_rejected(tmp_path):
    def bad(body):
        body["daily"]["precipitation_sum_NICAM16_8S"][3] = -0.5
        return body

    table = parse(edited(tmp_path, bad))
    row = table.filter(pc.equal(table["missing_reason"], "quality_rejected")).to_pylist()
    assert len(row) == 1 and row[0]["rain_mm"] is None and row[0]["tmax_c"] is None
    assert row[0]["quality_flags"] == ["out_of_range"]


def test_schema_file_matches_measure_columns():
    spec = json.loads((ROOT / "schemas" / "s06.json").read_text("utf-8"))
    names = {"string": "string", "double": "float64", "date32[day]": "date32", "bool": "bool"}
    assert [(f["name"], f["type"], f["nullable"]) for f in spec["fields"]] == [
        (f.name, names[str(f.type)], f.nullable) for f in MEASURES
    ]


def test_malformed_copy_rejected(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_bytes(CORRECTED.read_bytes()[:500])
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
        lambda b: b["daily_units"].update(precipitation_sum_MRI_AGCM3_2_S="inch") or b,
        lambda b: b["daily"].pop("temperature_2m_max_FGOALS_f3_H") and b,
        lambda b: b.update(utc_offset_seconds=19800) or b,
    ],
    ids=["unit", "missing column", "not gmt"],
)
def test_changed_columns_rejected(tmp_path, change):
    with pytest.raises(IngestError):
        parse(edited(tmp_path, change))


def test_response_must_match_the_requested_models():
    one = S06("ka", POINT, date(2050, 1, 1), date(2050, 1, 31), models=["MRI_AGCM3_2_S"])
    with pytest.raises(IngestError, match="columns or units changed"):
        parse(artifact(CORRECTED), one)


def test_disabled_source_fails_closed_and_bad_requests_refused():
    off = CONFIG.model_copy(update={"enabled": False})
    with pytest.raises(SourceUnavailable):
        JAN_2050.parse(artifact(CORRECTED), off)
    with pytest.raises(ValueError, match="dates"):
        S06("ka", POINT, date(2050, 12, 1), date(2051, 1, 1))
    with pytest.raises(ValueError, match="models"):
        S06("ka", POINT, date(2000, 1, 1), date(2000, 1, 2), models=["SSP585_MODEL"])


def context(tmp_path) -> FetchContext:
    return FetchContext(
        source_id="S06",
        state="ka",
        run_id="test",
        requested_at=datetime.now(UTC),
        budget=Budget(max_requests=2, max_bytes=1024**2),
        raw_root=tmp_path,
    )


@pytest.mark.parametrize("bias_corrected", [True, False])
def test_fetch_requests_units_models_and_bias_choice(tmp_path, bias_corrected):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=CORRECTED.read_bytes())

    fetcher = Fetcher(RawStore(tmp_path), HOSTS, transport=httpx.MockTransport(handler))
    adapter = S06(
        "ka",
        POINT,
        date(2050, 1, 1),
        date(2050, 1, 31),
        bias_corrected=bias_corrected,
        fetcher=fetcher,
    )
    [raw] = adapter.fetch(context(tmp_path))
    query = parse_qs(urlsplit(seen[0]).query)
    assert query["models"] == [",".join(MODELS)] and query["daily"] == [
        "precipitation_sum,temperature_2m_max"
    ]
    assert query["precipitation_unit"] == ["mm"] and query["temperature_unit"] == ["celsius"]
    assert (query["start_date"], query["end_date"]) == (["2050-01-01"], ["2050-01-31"])
    assert query.get("disable_bias_correction") == (None if bias_corrected else ["true"])
    assert raw.sha256 == hashlib.sha256(CORRECTED.read_bytes()).hexdigest()
