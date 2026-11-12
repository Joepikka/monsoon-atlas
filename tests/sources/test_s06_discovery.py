"""T053 acceptance: the S06 (Open-Meteo climate projections) discovery record passes the
discovery contract only with cited evidence and explicit access, licence and history status;
scenario and bias adjustment are recorded from the evidence."""

import html
import json
import re

MODELS = (
    "CMCC_CM2_VHR4",
    "FGOALS_f3_H",
    "HiRAM_SIT_HR",
    "MRI_AGCM3_2_S",
    "EC_Earth3P_HR",
    "MPI_ESM1_2_XR",
    "NICAM16_8S",
)


def body(rec, eid) -> dict:
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def test_s06_discovery_contract(record):
    assert record("S06").problems() == []


def test_s06_status(record):
    d = record("S06").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert d.no_card and not d.account_required
    assert (d.earliest_date, d.latest_date) == ("1950-01-01", "2050-12-31")
    assert "Invalid date" in d.failed_fetches[0].error
    scenario = next(f for f in d.field_map if f.canonical == "scenario")
    assert scenario.upstream is None and scenario.unit_status == "absent"


def test_no_data_committed(record):
    assert record("S06").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S06").check_local_hashes()


def test_docs_state_scenario_bias_and_licence(record):
    rec = record("S06")
    docs = text(rec, "e04")
    assert "as close to RCP8.5 as possible within CMIP6" in docs
    assert "disable_bias_correction" in docs and "linear bias correction" in docs
    assert "should not be mistaken for actual measurements" in docs
    assert "This API call is equivalent to 1844.5 calls" in docs
    assert "relaxed the license" in text(rec, "e09")


def test_units_models_and_history(record):
    rec = record("S06")
    full = body(rec, "e06")
    expected = {"time": "iso8601"}
    for m in MODELS:
        expected |= {f"precipitation_sum_{m}": "mm", f"temperature_2m_max_{m}": "°C"}
    assert full["daily_units"] == expected and full["utc_offset_seconds"] == 0
    days = full["daily"]
    assert (days["time"][0], days["time"][-1]) == ("1950-01-01", "2050-01-01")
    for m in MODELS:
        values = days[f"precipitation_sum_{m}"]
        last = None if m == "EC_Earth3P_HR" else values[-1]
        assert values[-1] is last and all(v is not None for v in values[:-1]), m
        assert min(values[:-1]) >= 0, m
    december = body(rec, "e11")["daily"]
    assert december["time"][-1] == "2050-12-31"
    for m in MODELS:
        filled = sum(v is not None for v in december[f"temperature_2m_max_{m}"])
        assert filled == (0 if m == "EC_Earth3P_HR" else 31), m


def test_bias_correction_changes_values_and_cell(record):
    rec = record("S06")
    corrected, raw = body(rec, "e06"), body(rec, "e07")
    assert (corrected["latitude"], corrected["longitude"]) == (13.0, 77.600006)
    assert (raw["latitude"], raw["longitude"]) == (12.890625, 77.5)
    days = corrected["daily"]
    year = slice(days["time"].index("2000-01-01"), days["time"].index("2000-12-31") + 1)
    rain = "precipitation_sum_MRI_AGCM3_2_S"
    assert round(sum(days[rain][year]), 1) == 708.4
    assert round(sum(raw["daily"][rain]), 1) == 587.1
