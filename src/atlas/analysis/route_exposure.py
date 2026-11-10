"""T165: Delhi air-quality route exposure and blocked views.

A route's exposure here is the time-weighted **ambient concentration** along the route: the sum of
concentration x seconds on each segment over the total seconds. It is never an inhaled dose (no
breathing rate, no indoor or in-vehicle factor). It is computed only when every segment's reading
has the same pollutant, unit, averaging interval and provenance kind (station observation or
gridded model, never mixed), and when the segment lies inside the window the reading represents.
That window comes from the reading's own averaging interval, which the caller passes in; nothing
is guessed, converted or interpolated. With no Delhi route (S38 blocked) and no station value (S24
blocked) the real result is "unavailable"; the rules are tested on hand-built inputs only.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from atlas.analysis.prices import load_record

ROOT = Path(__file__).resolve().parents[3]
KINDS = ("observation", "model")  # station layer, gridded model layer
AMBIENT_LABEL = (
    "Route-time-weighted ambient concentration at the readings' averaging interval; "
    "not an inhaled dose."
)


@dataclass(frozen=True)
class Basis:
    """What a layer's values mean; interval_minutes is the averaging interval (0 = instant)."""

    kind: str
    pollutant: str
    unit: str
    interval_minutes: int

    def __post_init__(self):
        if self.kind not in KINDS or self.interval_minutes < 0:
            raise ValueError(f"kind must be one of {KINDS} and the interval >= 0")


@dataclass(frozen=True)
class Reading:
    """One value; tz-aware `stamp` is the "start" or "end" (`stamp_is`) of its averaging window."""

    basis: Basis
    value: float
    stamp: datetime
    stamp_is: str

    def __post_init__(self):
        if self.stamp_is not in ("start", "end"):
            raise ValueError("stamp_is must be 'start' or 'end'")


@dataclass(frozen=True)
class Segment:
    """Time spent on one stretch of route, with the reading that covers it."""

    start: datetime
    end: datetime
    reading: Reading


def _unavailable(reason: str) -> dict:
    return {"status": "unavailable", "reason": reason}


def _outcome(source_id: str) -> str:
    return load_record(ROOT / f"configs/sources/{source_id.lower()}.yaml")["outcome"]


def _differs(a: Basis, b: Basis, fields: tuple[str, ...]) -> str | None:
    for f in fields:
        if getattr(a, f) != getattr(b, f):
            return f"{f} differs ({getattr(a, f)!r} vs {getattr(b, f)!r}); nothing is converted"
    return None


def compare_layers(station: Basis | None, model: Basis | None) -> dict:
    """A station and a gridded model layer compare only on identical pollutant, unit, averaging."""
    if station is None:
        return _unavailable(f"no station basis (S24 {_outcome('S24')}); nothing to compare with")
    if model is None:
        return _unavailable("no gridded model basis (S04 is not configured for Delhi)")
    if (station.kind, model.kind) != ("observation", "model"):
        return _unavailable("layers must stay distinct: a station observation and a gridded model")
    if why := _differs(station, model, ("pollutant", "unit", "interval_minutes")):
        return _unavailable(why)
    return {
        "status": "comparable",
        "pollutant": station.pollutant,
        "unit": station.unit,
        "interval_minutes": station.interval_minutes,
    }


def route_exposure(segments: list[Segment] | None) -> dict:
    """Time-weighted ambient concentration over `segments`, or "unavailable" with the reason."""
    if segments is None:
        return _unavailable(
            f"no Delhi route (S38 {_outcome('S38')}) and no station concentration "
            f"(S24 {_outcome('S24')}); nothing is computed"
        )
    if not segments:
        return _unavailable("the route has no segments")
    basis = segments[0].reading.basis
    for s in segments:
        r = s.reading
        if why := _differs(basis, r.basis, ("kind", "pollutant", "unit", "interval_minutes")):
            return _unavailable(why)
        if not all(t.tzinfo for t in (s.start, s.end, r.stamp)):
            return _unavailable("timestamps need a time zone")
        if s.end <= s.start:
            return _unavailable("a segment must last longer than zero seconds")
        if not (math.isfinite(r.value) and r.value >= 0):
            return _unavailable("a concentration must be finite and not negative")
    if basis.interval_minutes == 0:
        return _unavailable(
            "an instantaneous value cannot cover a time span; nothing is interpolated"
        )
    ordered = sorted(segments, key=lambda s: s.start)
    if any(a.end > b.start for a, b in zip(ordered, ordered[1:], strict=False)):
        return _unavailable("segments overlap in time")
    span = timedelta(minutes=basis.interval_minutes)
    for s in ordered:
        r = s.reading
        lo, hi = (r.stamp - span, r.stamp) if r.stamp_is == "end" else (r.stamp, r.stamp + span)
        if s.start < lo or s.end > hi:
            return _unavailable(
                f"segment {s.start.isoformat()} to {s.end.isoformat()} is outside the "
                f"{basis.interval_minutes}-minute window {lo.isoformat()} to {hi.isoformat()} "
                "that its reading represents"
            )
    seconds = [(s.end - s.start).total_seconds() for s in ordered]
    return {
        "status": "computed",
        "label": AMBIENT_LABEL,
        "kind": basis.kind,
        "pollutant": basis.pollutant,
        "unit": basis.unit,
        "interval_minutes": basis.interval_minutes,
        "segments": len(ordered),
        "duration_s": sum(seconds),
        "ambient_concentration": sum(
            s.reading.value * t for s, t in zip(ordered, seconds, strict=True)
        )
        / sum(seconds),
    }


def blocked_view(record: Mapping) -> dict:
    """UI state for a layer whose source is blocked: the record's own reason and retry condition."""
    if record["outcome"] != "blocked":
        raise ValueError(f"{record['source_id']} is not blocked")
    return {
        "state": "unavailable",
        "source_id": record["source_id"],
        "reason": f"{record['source_id']} blocked: {record['access']['status'].replace('_', ' ')}",
        "retry_condition": " ".join(record["retry_condition"].split()),
    }


def planned_coverage(config: Mapping) -> dict:
    """The planned (not actual) test period and calendar months of a model config."""
    plan = config["planned_splits"]
    day, end = date.fromisoformat(plan["collect_from"]), date.fromisoformat(plan["locked_test"][1])
    months = []
    while (day.year, day.month) <= (end.year, end.month):
        months.append(day.month)
        day = date(day.year + day.month // 12, day.month % 12 + 1, 1)
    return {"status": "planned, not started", "test_period": plan["locked_test"], "months": months}


def blocked_card(registry: Mapping, config: Mapping) -> dict:
    """Card for a blocked model: its registry reason and the planned coverage, no score."""
    if registry["status"] != "blocked":
        raise ValueError(f"{registry['model_id']} is not blocked")
    return {
        "status": "blocked",
        "model_id": registry["model_id"],
        "reason": registry["reason"],
        "coverage": planned_coverage(config),
    }
