"""T049 acceptance: the S04 (Open-Meteo CAMS air-quality estimates) discovery record passes the
discovery contract only with cited evidence and explicit access, licence and history status."""

import json
from datetime import UTC, datetime

POLLUTANTS = ("pm2_5", "pm10", "nitrogen_dioxide")


def body(rec, eid) -> dict:
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def test_s04_discovery_contract(record):
    assert record("S04").problems() == []


def test_s04_status(record):
    d = record("S04").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert d.no_card and not d.account_required
    assert (d.earliest_date, d.latest_date) == ("2022-08-04", "2026-11-13")
    errors = [f.error for f in d.failed_fetches]
    assert "404" in errors[0] and "No data is available for this location" in errors[1]


def test_no_data_committed(record):
    assert record("S04").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S04").check_local_hashes()


def test_units_and_named_domain(record):
    rec = record("S04")
    for eid in ("e08", "e10", "e11", "e12"):
        b = body(rec, eid)
        assert b["hourly_units"] == {"time": "iso8601"} | dict.fromkeys(POLLUTANTS, "μg/m³"), eid
        assert b["utc_offset_seconds"] == 0
    assert body(rec, "e10")["hourly"] == body(rec, "e08")["hourly"]  # auto == cams_global here
    script = rec.raw("e06").read_text(encoding="utf-8")  # host is `${t}-api` for t=air-quality
    assert "default:a=`https://${i}.open-meteo.com/data/${e}/static/meta.json`" in script
    assert "meta:P(`cams_global`,`air-quality`,e)" in script


def test_issue_time_is_stable_and_valid_times_follow_it(record):
    rec = record("S04")
    before, after = body(rec, "e07"), body(rec, "e09")
    assert before == after
    issued = datetime.fromtimestamp(before["last_run_initialisation_time"], UTC)
    end = datetime.fromtimestamp(before["data_end_time"], UTC)
    assert (issued.isoformat(), end.isoformat()) == (
        "2026-11-08T12:00:00+00:00",
        "2026-11-13T13:00:00+00:00",
    )
    hourly = body(rec, "e08")["hourly"]
    for t, *values in zip(hourly["time"], *(hourly[p] for p in POLLUTANTS), strict=True):
        late = datetime.fromisoformat(t).replace(tzinfo=UTC) >= end  # data_end_time is exclusive
        assert all((v is None) == late for v in values), t


def test_history_starts_4_aug_2022_with_no_gaps_and_no_negatives(record):
    rec = record("S04")
    start = body(rec, "e11")["hourly"]
    first = next(t for t, v in zip(start["time"], start["pm2_5"], strict=True) if v is not None)
    assert first == "2022-08-04T00:00"
    hourly = body(rec, "e12")["hourly"]
    for p in POLLUTANTS:
        pairs = [(t, v) for t, v in zip(hourly["time"], hourly[p], strict=True)]
        assert all(v is not None for t, v in pairs if t >= "2022-08-04"), p
        assert min(v for _, v in pairs if v is not None) >= 0, p
    assert hourly["time"][-1] == "2026-11-08T23:00"
