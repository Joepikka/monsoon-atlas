"""T011 acceptance: the S02 (Open-Meteo historical weather / ERA5) discovery record passes the
discovery contract only with cited evidence and explicit access, licence and history status."""

import json
from datetime import date


def daily(rec, eid) -> dict:
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def test_s02_discovery_contract(record):
    assert record("S02").problems() == []


def test_s02_status(record):
    d = record("S02").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert d.no_card and not d.account_required
    assert (d.earliest_date, d.latest_date) == ("1940-01-02", "2026-10-30")


def test_no_data_committed(record):
    assert record("S02").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S02").check_local_hashes()


def test_release_lag_in_recent_sample(record):
    body = daily(record("S02"), "e05")
    days = body["daily"]
    filled = [
        date.fromisoformat(t)
        for t, v in zip(days["time"], days["precipitation_sum"], strict=True)
        if v is not None
    ]
    assert max(filled) == date(2026, 10, 30)  # fetched 2026-11-05: 6 days behind
    assert days["precipitation_sum"][-5:] == [None] * 5


def test_units_and_ist_days(record):
    rec = record("S02")
    for eid in ("e05", "e06", "e07"):
        body = daily(rec, eid)
        assert body["daily_units"] == {
            "time": "iso8601",
            "precipitation_sum": "mm",
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
        }, eid
        assert body["utc_offset_seconds"] == 19800 and (body["latitude"], body["longitude"]) == (
            13.0,
            77.5,
        )
    first = daily(rec, "e06")["daily"]
    assert first["time"][0] == "1940-01-01" and first["precipitation_sum"][0] is None
    july = daily(rec, "e07")["daily"]["precipitation_sum"]
    assert len(july) == 31 and min(july) >= 0 and round(sum(july), 1) == 264.2


def test_docs_state_coverage_and_delay(record):
    page = record("S02").raw("e04").read_text(encoding="utf-8")
    text = " ".join(page.split())
    assert "1940 to present" in text and "Daily with 5 days delay" in text
