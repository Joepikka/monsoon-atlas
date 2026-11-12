"""T233: durable SQL admission enforces source cadence without a runner cache."""

import sqlite3
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PERIODS = {"S01": 21600, "S09": 900}


@pytest.fixture
def database(tmp_path):
    connection = sqlite3.connect(tmp_path / "admission.sqlite")
    connection.executescript((ROOT / "worker/schema.sql").read_text("utf-8"))
    yield connection
    connection.close()


def admit(connection, source, now, *, database_bytes=0, state="ka"):
    millis = int(now.timestamp() * 1000)
    period = PERIODS.get(source, 900) * 1000
    try:
        with connection:
            connection.execute(
                "INSERT OR IGNORE INTO daily_usage(day,writes_reserved) VALUES (?,0)",
                (now.astimezone(UTC).date().isoformat(),),
            )
            connection.execute(
                "INSERT INTO feed_checks(state,source_id,period_index,admitted_ms,"
                "budget_day,database_bytes) "
                "VALUES (?,?,?,?,?,?)",
                (
                    state,
                    source,
                    millis // period,
                    millis,
                    now.astimezone(UTC).date().isoformat(),
                    database_bytes,
                ),
            )
        return True
    except sqlite3.IntegrityError as error:
        if "check_not_due" in str(error):
            return False
        raise


@pytest.mark.parametrize("hour,minute", [(0, 7), (5, 59)])
def test_24_hour_clock_never_exceeds_four_weather_and_96_alert_checks(database, hour, minute):
    start = datetime(2026, 11, 6, hour, minute, tzinfo=UTC)
    counts = Counter()
    # Every call represents a new/duplicate runner with no in-memory admission state.
    for offset in range(1440):
        now = start + timedelta(minutes=offset)
        for source in PERIODS:
            counts[source] += admit(database, source, now)
            assert not admit(database, source, now)
    assert counts == {"S01": 4, "S09": 96}


def test_late_jobs_and_clock_reversal_cannot_burst_across_utc_buckets(database):
    late = datetime(2026, 11, 6, 5, 59, tzinfo=UTC)
    assert admit(database, "S01", late)
    assert not admit(database, "S01", late + timedelta(minutes=8))
    assert not admit(database, "S01", late - timedelta(hours=1))
    assert admit(database, "S01", late + timedelta(hours=6))


def test_new_utc_day_does_not_reset_elapsed_cadence(database):
    first = datetime(2026, 11, 6, 23, 59, tzinfo=UTC)
    assert admit(database, "S09", first)
    assert not admit(database, "S09", first + timedelta(minutes=8))
    assert admit(database, "S09", first + timedelta(minutes=15))


def test_write_cap_failure_does_not_consume_a_check_slot(database):
    now = datetime(2026, 11, 6, tzinfo=UTC)
    assert admit(database, "S09", now)
    database.execute("UPDATE daily_usage SET writes_reserved=10000")
    database.commit()
    with pytest.raises(sqlite3.IntegrityError, match="write_cap"):
        admit(database, "S09", now + timedelta(minutes=15))
    assert database.execute("SELECT COUNT(*) FROM feed_checks").fetchone() == (1,)
    database.execute("UPDATE daily_usage SET writes_reserved=20")
    database.commit()
    assert admit(database, "S09", now + timedelta(minutes=15))


def test_storage_cap_failure_cannot_authorize_provider_calls(database):
    now = datetime(2026, 11, 6, tzinfo=UTC)
    with pytest.raises(sqlite3.IntegrityError, match="storage_cap"):
        admit(database, "S01", now, database_bytes=399_999_999)
    assert database.execute("SELECT COUNT(*) FROM feed_checks").fetchone() == (0,)
    assert database.execute("SELECT COUNT(*) FROM daily_usage").fetchone() == (0,)


@pytest.mark.parametrize("state,source", [("kl", "S09"), ("ka", "S23")])
def test_unknown_state_or_unverified_feed_cannot_acquire_a_slot(database, state, source):
    with pytest.raises(sqlite3.IntegrityError):
        admit(database, source, datetime(2026, 11, 6, tzinfo=UTC), state=state)
    assert database.execute("SELECT COUNT(*) FROM feed_checks").fetchone() == (0,)
