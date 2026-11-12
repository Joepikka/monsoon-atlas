"""T005 acceptance: late revisions cannot enter past predictions; duplicate snapshots idempotent;
midnight IST converted correctly; missing != 0.

Built from one real Open-Meteo record (tests/fixtures/README.md) plus malformed copies.
"""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from atlas.data.asof import asof_join, local_midnight_utc, local_to_utc
from atlas.data.validate import (
    TS,
    SchemaError,
    dedupe_snapshots,
    envelope_schema,
    read_mapping,
    validate_table,
    with_mapping,
)

FIXTURE = Path(__file__).parent / "fixtures/s02_openmeteo_archive_bengaluru_2024-07-01_04.json"
URL = (
    "https://archive-api.open-meteo.com/v1/archive?latitude=12.97&longitude=77.59"
    "&start_date=2024-07-01&end_date=2024-07-04&daily=precipitation_sum&timezone=Asia%2FKolkata"
)
FETCHED = datetime(2026, 11, 5, 6, 9, 33, tzinfo=UTC)  # actual retrieval time of the fixture
PLACE = "in:ka:h3:8861892a6dfffff:h3v4"
RAW_SHA = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


def fixture_rows():
    """Normalize the real response. ERA5 history fetched today has no recorded release time, so
    available_at is reconstructed as valid day + 5 days (ERA5 latency) and flagged."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))["daily"]
    rows = []
    for day, rain in zip(data["time"], data["precipitation_sum"], strict=True):
        valid = local_midnight_utc(date.fromisoformat(day))
        rows.append(row(valid, rain, available=valid + timedelta(days=5), snapshot="snap-1"))
    return rows


def row(valid, rain, *, available, snapshot, missing_reason=None, flags=(), provenance=None):
    key = f"S02|{PLACE}|{valid.isoformat()}"
    return {
        "source_id": "S02",
        "state": "ka",
        "record_id": hashlib.sha256(key.encode()).hexdigest(),
        "snapshot_id": snapshot,
        "observed_at": None,
        "valid_at": valid,
        "issued_at": None,
        "available_at": available,
        "fetched_at": FETCHED,
        "published_at": None,
        "source_url": URL,
        "raw_sha256": RAW_SHA,
        "schema_version": 1,
        "mapping_version": "s02-v1",
        "provenance": provenance or ("reconstructed" if available < FETCHED else "model"),
        "quality_flags": list(flags),
        "licence_id": "cc-by-4.0-open-meteo",
        "redistribution_allowed": False,
        "place_id": PLACE,
        "boundary_version": "h3v4",
        "missing_reason": missing_reason,
        "rain_mm": rain,
    }


SCHEMA = envelope_schema().append(pa.field("rain_mm", pa.float64()))


def table(rows):
    return pa.Table.from_pylist(rows, schema=SCHEMA)


def spine(*issues):
    return pa.table(
        {"place_id": [PLACE] * len(issues), "issue_at": pa.array(list(issues), type=TS)}
    )


# --- the real fixture -----------------------------------------------------------------------


def test_real_fixture_validates():
    t = validate_table(table(fixture_rows()), measures=["rain_mm"])
    assert t.column("rain_mm").to_pylist() == [9.0, 0.1, 10.4, 3.8]


def test_empty_typed_table_validates_without_inventing_measurements():
    empty = table([])
    assert validate_table(empty, measures=["rain_mm"]).equals(empty)


def test_midnight_ist_converted_correctly():
    assert local_midnight_utc(date(2024, 7, 2)) == datetime(2024, 7, 1, 18, 30, tzinfo=UTC)
    assert local_to_utc(datetime(2024, 7, 2, 0, 0)) == datetime(2024, 7, 1, 18, 30, tzinfo=UTC)
    first = table(fixture_rows()).column("valid_at")[0].as_py()
    assert first == datetime(2024, 6, 30, 18, 30, tzinfo=UTC)  # 2024-07-01 00:00 IST
    with pytest.raises(ValueError):
        local_to_utc(datetime(2024, 7, 2, tzinfo=UTC))


# --- as-of joins ----------------------------------------------------------------------------


def test_late_revision_cannot_enter_past_prediction():
    valid = local_midnight_utc(date(2024, 7, 3))
    first = row(valid, 10.4, available=valid + timedelta(days=5), snapshot="snap-1")
    revised = row(valid, 12.0, available=valid + timedelta(days=20), snapshot="snap-2")
    obs = table([first, revised])
    before = valid + timedelta(days=7)  # issued after the first release, before the revision
    after = valid + timedelta(days=25)
    out = asof_join(spine(before, after), obs, by="place_id", values=["rain_mm"]).to_pylist()
    assert [r["rain_mm"] for r in out] == [10.4, 12.0]
    assert [r["obs_snapshot_id"] for r in out] == ["snap-1", "snap-2"]
    assert all(r["obs_available_at"] <= r["issue_at"] for r in out)


def test_latest_valid_time_known_at_issue_wins():
    obs = table(fixture_rows())
    issue = local_midnight_utc(date(2024, 7, 8)) + timedelta(hours=6)  # 4th day not yet available
    (out,) = asof_join(spine(issue), obs, by="place_id", values=["rain_mm"]).to_pylist()
    assert out["rain_mm"] == 10.4  # 2024-07-03 (IST) is the newest value available by then


def test_future_valid_rows_excluded_unless_allowed():
    issue = datetime(2024, 7, 10, tzinfo=UTC)
    forecast = row(
        issue + timedelta(days=1), 5.0, available=issue - timedelta(hours=1), snapshot="f"
    )
    past = row(issue - timedelta(days=1), 1.0, available=issue - timedelta(hours=1), snapshot="p")
    obs = table([forecast, past])
    default = asof_join(spine(issue), obs, by="place_id", values=["rain_mm"]).to_pylist()
    allowed = asof_join(
        spine(issue), obs, by="place_id", values=["rain_mm"], allow_future_valid=True
    ).to_pylist()
    assert default[0]["rain_mm"] == 1.0 and allowed[0]["rain_mm"] == 5.0


def test_duplicate_snapshots_are_idempotent():
    obs = table(fixture_rows())
    doubled = pa.concat_tables([obs, obs])
    issues = spine(datetime(2024, 7, 7, tzinfo=UTC), datetime(2024, 7, 12, tzinfo=UTC))
    assert asof_join(issues, doubled, by="place_id", values=["rain_mm"]).equals(
        asof_join(issues, obs, by="place_id", values=["rain_mm"])
    )
    assert dedupe_snapshots(doubled).num_rows == obs.num_rows
    validate_table(doubled, measures=["rain_mm"])  # exact duplicates are allowed


def test_conflicting_snapshot_content_is_rejected():
    rows = fixture_rows()
    tampered = dict(rows[0], rain_mm=99.0)
    with pytest.raises(SchemaError, match="different content"):
        validate_table(table([rows[0], tampered]), measures=["rain_mm"])


def test_missing_is_not_zero():
    valid = local_midnight_utc(date(2024, 7, 5))
    gap = row(
        valid,
        None,
        available=valid + timedelta(days=5),
        snapshot="s",
        missing_reason="provider_outage",
        flags=["missing"],
    )
    obs = validate_table(table([gap]), measures=["rain_mm"])
    issue = valid + timedelta(days=6)
    (out,) = asof_join(spine(issue), obs, by="place_id", values=["rain_mm"]).to_pylist()
    assert out["rain_mm"] is None and out["missing_reason"] == "provider_outage"
    # Nothing known yet: null with a reason, never 0.
    (early,) = asof_join(spine(valid), obs, by="place_id", values=["rain_mm"]).to_pylist()
    assert early["rain_mm"] is None and early["missing_reason"] == "not_yet_available"


# --- malformed copies of the real record -----------------------------------------------------


def _broken(**changes):
    return [dict(fixture_rows()[0], **changes)]


@pytest.mark.parametrize(
    "rows,message",
    [
        (_broken(rain_mm=None), "null without missing_reason"),
        (_broken(missing_reason="provider_outage"), "missing is not 0"),
        (_broken(quality_flags=["missing"], missing_reason="not_reported"), "missing is not 0"),
        (_broken(provenance="guessed"), "provenance"),
        (_broken(state="tn"), "state"),
        (_broken(missing_reason="unknown", rain_mm=None), "missing_reason"),
        (_broken(quality_flags=["fine"]), "quality_flags"),
        (_broken(schema_version=2), "not supported"),
        (_broken(provenance="official"), "requires provenance=reconstructed"),
    ],
)
def test_malformed_rows_rejected(rows, message):
    with pytest.raises(SchemaError, match=message):
        validate_table(table(rows), measures=["rain_mm"])


def test_missing_column_and_wrong_timestamp_type_rejected():
    good = table(fixture_rows())
    with pytest.raises(SchemaError, match="missing envelope column available_at"):
        validate_table(good.drop_columns(["available_at"]), measures=["rain_mm"])
    ist = good.set_column(
        good.schema.get_field_index("fetched_at"),
        "fetched_at",
        good["fetched_at"].cast(pa.timestamp("us", tz="Asia/Kolkata")),
    )
    with pytest.raises(SchemaError, match="fetched_at: type"):
        validate_table(ist, measures=["rain_mm"])
    with pytest.raises(SchemaError, match="missing measure column"):
        validate_table(good, measures=["temperature_c"])


def test_provider_mapping_survives_parquet(tmp_path):
    t = with_mapping(
        table(fixture_rows()),
        {"daily.precipitation_sum": "rain_mm", "daily.time": "valid_at"},
        "s02-v1",
    )
    pq.write_table(t, tmp_path / "s02.parquet")
    back = read_mapping(pq.read_table(tmp_path / "s02.parquet"))
    assert back["provider_to_canonical"]["daily.precipitation_sum"] == "rain_mm"
    assert back["mapping_version"] == "s02-v1"
