"""D189: the warning archive keeps each official S09 warning once, as issued, with the times this
project first and last saw it; model or inferred items and other sources never enter it."""

import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

from atlas.alerts.archive import archive_body, warnings_from_rows

ROOT = Path(__file__).resolve().parents[1]
CAP = json.loads((ROOT / "web/tests/fixtures/sachet-ka-point.json").read_text("utf-8"))


def row(records: list[dict], at: str, source: str = "S09") -> dict:
    envelope = {"source_id": source, "snapshot": {"records": records}}
    return {
        "source_id": source,
        "as_of": datetime.fromisoformat(at),
        "payload_gzip": gzip.compress(json.dumps(envelope).encode()),
    }


def test_each_warning_once_with_first_and_last_seen():
    later = CAP | {"fetched_at": "2026-11-05T13:20:00Z"}
    rows = [
        row([later], "2026-11-05T13:20:00+00:00"),
        row([CAP], "2026-11-05T13:05:40+00:00"),
    ]
    (w,) = warnings_from_rows(rows)
    assert w["id"] == CAP["id"] and w["warning_text"] == CAP["warning_text"]
    assert (w["first_seen"], w["last_seen"]) == (CAP["fetched_at"], "2026-11-05T13:20:00Z")
    assert w["severity"] == "Moderate" and w["expires_at"] == CAP["expires_at"]


def test_only_official_s09_alerts_enter():
    model = CAP | {"id": "m", "provenance": "model"}
    weather = CAP | {"id": "w", "kind": "weather"}
    rows = [
        row([model, weather], "2026-11-05T13:00:00+00:00"),
        row([CAP], "2026-11-05T13:00:00+00:00", "S01"),
    ]
    assert warnings_from_rows(rows) == []


def test_body_is_dated_and_says_it_is_not_an_emergency_service():
    body = archive_body([], None, datetime(2026, 11, 12, tzinfo=UTC))
    assert body["count"] == 0 and body["archive_since"] is None
    assert "Not an emergency service" in body["note"] and "112" in body["note"]
