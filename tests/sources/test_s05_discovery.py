"""T051 acceptance: the S05 (Open-Meteo ensemble) discovery record passes the discovery contract
only with cited evidence and explicit access, licence and history status; member counts are read
from real responses, not hardcoded."""

import json
from datetime import UTC, datetime


def body(rec, eid) -> dict:
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def series(hourly: dict, variable: str) -> list[str]:
    return [k for k in hourly if k == variable or k.startswith(f"{variable}_member")]


def test_s05_discovery_contract(record):
    assert record("S05").problems() == []


def test_s05_status(record):
    d = record("S05").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "partial",
        "pass",
    )
    assert d.no_card and not d.account_required
    assert (d.earliest_date, d.latest_date) == ("2026-11-04", "2026-11-23")
    assert "out of allowed range from 2026-08-08" in d.failed_fetches[0].error


def test_no_data_committed(record):
    assert record("S05").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S05").check_local_hashes()


def test_member_counts_are_discovered_per_product(record):
    rec = record("S05")
    counts = {}
    for eid in ("e08", "e10", "e11", "e12"):
        b = body(rec, eid)
        rain, temp = series(b["hourly"], "precipitation"), series(b["hourly"], "temperature_2m")
        assert len(rain) == len(temp) and set(b["hourly"]) == {"time", *rain, *temp}, eid
        assert set(b["hourly_units"].values()) == {"iso8601", "mm", "°C"}, eid
        assert b["utc_offset_seconds"] == 0
        counts[eid] = len(rain)
    assert counts == {"e08": 51, "e10": 31, "e11": 40, "e12": 21}
    assert series(body(rec, "e08")["hourly"], "precipitation")[-1] == "precipitation_member50"


def test_run_time_covers_hours_before_data_end_only(record):
    rec = record("S05")
    meta = body(rec, "e07")
    assert meta == body(rec, "e09")
    stamp = {k: datetime.fromtimestamp(meta[k], UTC).isoformat() for k in meta if "time" in k}
    assert stamp["last_run_initialisation_time"] == "2026-11-08T18:00:00+00:00"
    assert stamp["data_end_time"] == "2026-11-14T21:00:00+00:00"
    hourly = body(rec, "e08")["hourly"]
    filled = [t for i, t in enumerate(hourly["time"]) if hourly["precipitation"][i] is not None]
    assert filled[-1] == "2026-11-23T12:00"  # 8 Nov 12:00 + 15 days: past this run's end


def test_negative_rain_exists_and_history_is_short(record):
    rec = record("S05")
    hourly = body(rec, "e08")["hourly"]
    negative = sorted(
        k for k in series(hourly, "precipitation") for v in hourly[k] if v is not None and v < 0
    )
    assert negative == ["precipitation_member16"] * 3 + ["precipitation_member37"] * 3
    early = body(rec, "e13")["hourly"]
    assert all(v is None for k, vs in early.items() if k != "time" for v in vs)
    past = body(rec, "e14")["hourly"]
    first = min(
        i for k in series(past, "precipitation") for i, v in enumerate(past[k]) if v is not None
    )
    assert past["time"][first] == "2026-11-04T22:00"
    assert all(v is not None for k in series(past, "precipitation") for v in past[k][first:])
