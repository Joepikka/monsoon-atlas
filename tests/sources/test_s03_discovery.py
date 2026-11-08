"""T047 acceptance: the S03 (Open-Meteo GloFAS river discharge) discovery record passes the
discovery contract only with cited evidence and explicit access, licence and history status."""

import json


def daily(rec, eid) -> dict:
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def test_s03_discovery_contract(record):
    assert record("S03").problems() == []


def test_s03_status(record):
    d = record("S03").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert d.no_card and not d.account_required
    assert (d.earliest_date, d.latest_date) == ("1997-01-02", "2026-11-07")
    assert d.failed_fetches and "404" in d.failed_fetches[0].error


def test_no_data_committed(record):
    assert record("S03").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S03").check_local_hashes()


def test_units_and_missing_cells_stay_null(record):
    rec = record("S03")
    for eid in ("e05", "e07", "e10"):
        body = daily(rec, eid)
        assert body["daily_units"] == {"time": "iso8601", "river_discharge": "m³/s"}, eid
        assert body["utc_offset_seconds"] == 19800
    assert set(daily(rec, "e08")["daily"]["river_discharge"]) == {None}  # sea: no river cell
    assert set(daily(rec, "e09")["daily"]["river_discharge"]) == {None}  # 1984 at this cell


def test_history_starts_in_1997_with_no_gaps_and_no_negatives(record):
    days = daily(record("S03"), "e10")["daily"]
    pairs = list(zip(days["time"], days["river_discharge"], strict=True))
    values = [(t, v) for t, v in pairs if v is not None]
    assert values[0][0] == "1997-01-02" and values[-1][0] == "2026-11-07"
    assert all(v is not None for t, v in pairs if t >= "1997-01-02")
    assert min(v for _, v in values) >= 0
    july = daily(record("S03"), "e07")["daily"]["river_discharge"]
    assert (july[0], max(july)) == (37.19, 1031.76)
