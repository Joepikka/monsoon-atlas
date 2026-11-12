"""T183: deterministic daily state brief from official alerts and current records (D149).

Official S09 alerts go through `supersede()`, are deduplicated by sender, alert ID and revision
(the sent time), and dropped once expired. Cancelled and superseded alerts never appear. Every
line carries its own source link and timestamps. Official, model and inferred lines stay in
separate sections, and no model output is ever written as an official line. The brief stores
nothing about the people who read it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

import pyarrow as pa

from atlas.ingest.s09 import supersede

IST = timezone(timedelta(hours=5, minutes=30))
SECTIONS = ("official", "model", "inferred")
JOB_START_UTC_HOUR = 1  # the daily job starts at 01:00 UTC, which is 06:30 IST
ON_TIME_GRACE = timedelta(minutes=30)  # D149: a run finished by 07:00 IST still counts as on time
SEVERITY = {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3}


@dataclass(frozen=True)
class CurrentRecord:
    """A non-alert line, such as a current official forecast value or a model estimate."""

    provenance: str
    text: str
    source_url: str
    as_of: datetime
    expires_at: datetime | None = None


@dataclass(frozen=True)
class Line:
    provenance: str
    text: str
    source_url: str
    as_of: datetime
    expires_at: datetime | None = None


@dataclass(frozen=True)
class Brief:
    state: str
    run_date: date
    completed_at: datetime
    published_label: str
    lines: tuple[Line, ...]


def ist(moment: datetime) -> str:
    return moment.astimezone(IST).strftime("%Y-%m-%d %H:%M IST")


def _aware(moment: datetime | None, name: str) -> None:
    if moment is not None and moment.tzinfo is None:
        raise ValueError(f"{name} needs a timezone")


def alert_lines(table: pa.Table, as_of: datetime) -> list[Line]:
    """Active official alerts: superseded, cancelled, duplicate and expired ones are removed."""
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for row in supersede(table).to_pylist():
        if row["source_id"] != "S09" or row["provenance"] != "official":
            continue
        if not row["redistribution_allowed"]:
            continue
        key = (row["sender"], row["alert_id"])
        if key not in latest or row["sent_at"] > latest[key]["sent_at"]:
            latest[key] = row  # a later revision of the same alert wins
    active = [
        r
        for r in latest.values()
        if r["sent_at"] <= as_of and (r["expires_at"] is None or r["expires_at"] > as_of)
    ]
    active.sort(
        key=lambda r: (SEVERITY.get(r["severity"], 9), -r["sent_at"].timestamp(), r["alert_id"])
    )
    lines = []
    for r in active:
        start = r["effective_at"] or r["sent_at"]
        until = f"until {ist(r['expires_at'])}" if r["expires_at"] else "no end time given"
        text = f"{r['event']} ({r['severity']}) for {r['area_text']}, from {ist(start)}, {until}."
        text += f" Issued by {r['sender']} at {ist(r['sent_at'])}."
        if r["instruction"]:
            text += f" Issuer's instruction: {r['instruction']}"
        lines.append(Line("official", text, r["source_url"], r["sent_at"], r["expires_at"]))
    return lines


def build_brief(
    state: str,
    run_date: date,
    completed_at: datetime,
    alerts: pa.Table | None,
    current: Sequence[CurrentRecord] = (),
) -> Brief:
    """Build the brief for the 01:00 UTC job of `run_date`, which must have completed."""
    _aware(completed_at, "completed_at")
    start = datetime(run_date.year, run_date.month, run_date.day, JOB_START_UTC_HOUR, tzinfo=UTC)
    if completed_at < start:
        raise ValueError("the 01:00 UTC job has not completed for this date")
    lines = alert_lines(alerts, completed_at) if alerts is not None else []
    for record in sorted(current, key=lambda r: (r.text, r.source_url)):
        if record.provenance not in SECTIONS:
            raise ValueError(f"unknown provenance {record.provenance!r}")
        if not record.source_url.startswith("https://"):
            raise ValueError("every line needs an https source link")
        _aware(record.as_of, "as_of")
        _aware(record.expires_at, "expires_at")
        if record.expires_at is None or record.expires_at > completed_at:
            lines.append(Line(**vars(record)))  # an expired forecast is never shown as current
    lines.sort(key=lambda x: SECTIONS.index(x.provenance))  # stable: alerts keep their order
    on_time = completed_at <= start + ON_TIME_GRACE
    label = "06:30 IST" if on_time else f"{ist(completed_at)} (later than the scheduled 06:30 IST)"
    return Brief(state, run_date, completed_at, label, tuple(lines))
