"""T009 acceptance: the S01 (Open-Meteo weather forecast) discovery record passes the discovery
contract only with cited evidence and explicit access, licence and history status."""

import json
from datetime import UTC, datetime


def load(rec, eid):
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def test_s01_discovery_contract(record):
    assert record("S01").problems() == []


def test_s01_status(record):
    d = record("S01").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "partial",
        "pass",
    )
    assert d.no_card and not d.account_required
    assert d.provider_quota.status == "published"


def test_no_data_committed(record):
    assert record("S01").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S01").check_local_hashes()


def test_sample_values_and_units(record):
    sample = load(record("S01"), "e08")
    assert sample["hourly_units"] == {
        "time": "iso8601",
        "temperature_2m": "°C",
        "precipitation": "mm",
        "relative_humidity_2m": "%",
        "wind_speed_10m": "m/s",
    }
    hourly = sample["hourly"]
    rain = [v for v in hourly["precipitation"] if v is not None]
    humidity = [v for v in hourly["relative_humidity_2m"] if v is not None]
    assert rain and min(rain) >= 0
    assert humidity and 0 <= min(humidity) and max(humidity) <= 100
    assert (sample["latitude"], sample["longitude"]) == (13.0, 77.5)  # snapped to the 0.25 grid


def test_issue_time_comes_only_from_model_metadata(record):
    rec = record("S01")
    for eid in ("e08", "e10"):
        assert not {"model", "run", "init", "issued"} & set(load(rec, eid)), eid
    meta = load(rec, "e09")
    init = datetime.fromtimestamp(meta["last_run_initialisation_time"], UTC)
    ready = datetime.fromtimestamp(meta["last_run_availability_time"], UTC)
    assert init == datetime(2026, 11, 5, tzinfo=UTC) and init < ready
    script = rec.raw("e07").read_text(encoding="utf-8")
    assert "open-meteo.com/data/${e}/static/meta.json" in script


def test_terms_limits_and_licence(record):
    rec = record("S01")
    terms = rec.raw("e03").read_text(encoding="utf-8")
    assert "Less than 10'000 API calls per day, 5'000 per hour and 600 per minute" in terms
    assert "non-commercial purposes" in terms
    assert "Attribution 4.0 International (CC BY 4.0)" in rec.raw("e04").read_text("utf-8")
    assert rec.raw("e02").read_text("utf-8").split() == ["User-agent:", "*", "Disallow:", "/"]
