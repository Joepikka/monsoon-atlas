"""T104: scheduled transit positions (S30) and the historical railway layer (S21).

Every S30 position is a timetable estimate, never live GPS. A trip runs on a local service date;
its times count from noon minus 12 h of that date and may pass 24:00, so an instant is checked
against the service dates of that day and the day before. Between two consecutive scheduled
stops a vehicle is placed along the trip's shape, and only there: no shape, a stop off the
shape, a missing time or a backwards time pauses the trip (no position). S21 rows are a 2016
timetable and are returned as historical reference only: no instant, ETA or position.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from atlas.contracts import RawArtifact
from atlas.ingest import s30
from atlas.ingest.s30 import read_table

TZ = ZoneInfo("Asia/Kolkata")
EARTH_M = 6371008.8
MAX_OFF_SHAPE_M = 150.0
SCHEDULED_LABEL = "Scheduled position (timetable estimate), not live"
RAIL_LABEL = "2016 timetable (historical reference), not a current schedule or ETA"
CAVEATS = {  # T028 e05, e08: the compilers' own warnings on timing uncertainty
    "bmtc": "Unofficial timetable from the Namma BMTC app; the app's timetables are known to be "
    "inaccurate and only routes with live tracking are included.",
    "bmrcl": "Unofficial timetable from BMRCL timetable images; intermediate stop times are "
    "approximated, and a couple of minutes' difference from actual times is expected.",
}


def service_seconds(at: datetime, service_date: date) -> int:
    """Seconds of `at` after noon minus 12 h of the local service date (GTFS time origin)."""
    if at.tzinfo is None:
        raise ValueError("instant must be timezone-aware")
    origin = datetime.combine(service_date, time(12), TZ) - timedelta(hours=12)
    return math.floor((at - origin).total_seconds())


def instant(service_date: date, seconds: int) -> datetime:
    """The local instant of a GTFS time: 25:10:00 on 11 Nov is 01:10 on 12 Nov."""
    return datetime.combine(service_date, time(12), TZ) - timedelta(hours=12, seconds=-seconds)


def service_dates(at: datetime, max_days: int = 2) -> list[date]:
    """Service dates whose trips can be running at `at` (times up to max_days x 24 h)."""
    local = at.astimezone(TZ).date()
    return [local - timedelta(days=k) for k in range(max_days + 1)]


@dataclass
class Shape:
    lat: np.ndarray
    lon: np.ndarray
    along: np.ndarray  # cumulative metres


@dataclass
class Network:
    feed_id: str
    revision: str
    stops: dict[str, tuple[float, float]]
    names: dict[str, str]
    stations: list[dict]
    trip_shape: dict[str, str]
    shapes: dict[str, Shape]
    offsets: dict[tuple, list[float | None]] = field(default_factory=dict)


def _metres(lat0, lon0, lat, lon):
    k = math.radians(1) * EARTH_M
    return (np.asarray(lon) - lon0) * k * math.cos(math.radians(lat0)), (np.asarray(lat) - lat0) * k


def load_network(raw: RawArtifact) -> Network:
    """Stops, stations, trip shapes and shapes of one pinned S30 feed."""
    feed_id = s30.feed_of(raw)
    zf = s30.open_feed(raw)
    stops = read_table(zf, "stops.txt").to_pylist()
    coords = {s["stop_id"]: (float(s["stop_lat"]), float(s["stop_lon"])) for s in stops}
    stations = [
        {
            "id": s["stop_id"],
            "name": s["stop_name"],
            "lat": coords[s["stop_id"]][0],
            "lon": coords[s["stop_id"]][1],
            "kind": "metro_station" if feed_id == "bmrcl" else "bus_station",
            "feed_id": feed_id,
        }
        for s in stops
        if s.get("location_type") == "1"
    ]
    trips = read_table(zf, "trips.txt")
    trip_shape = (
        {
            t: sh
            for t, sh in zip(
                trips["trip_id"].to_pylist(), trips["shape_id"].to_pylist(), strict=True
            )
            if sh
        }
        if "shape_id" in trips.column_names
        else {}
    )
    shapes: dict[str, Shape] = {}
    if "shapes.txt" in zf.namelist():
        sh = read_table(zf, "shapes.txt")
        sh = sh.append_column("seq", pc.cast(sh["shape_pt_sequence"], pa.int64()))
        sh = sh.sort_by([("shape_id", "ascending"), ("seq", "ascending")])
        ids = sh["shape_id"].to_numpy(zero_copy_only=False)
        lat = pc.cast(sh["shape_pt_lat"], pa.float64()).to_numpy()
        lon = pc.cast(sh["shape_pt_lon"], pa.float64()).to_numpy()
        starts = np.flatnonzero(np.r_[True, ids[1:] != ids[:-1]])
        for a, b in zip(starts, np.r_[starts[1:], len(ids)], strict=True):
            la, lo = lat[a:b], lon[a:b]
            x, y = _metres(la[0], lo[0], la, lo)
            step = np.hypot(np.diff(x), np.diff(y))
            shapes[str(ids[a])] = Shape(la, lo, np.r_[0.0, np.cumsum(step)])
    commit = s30.FEEDS[feed_id][0]
    names = {s["stop_id"]: s["stop_name"] for s in stops}
    return Network(feed_id, commit, coords, names, stations, trip_shape, shapes)


def _project(shape: Shape, lat: float, lon: float, start: float) -> float | None:
    """Along-shape metres of the nearest shape point at or after `start`, or None if the stop is
    more than MAX_OFF_SHAPE_M from the shape there."""
    if len(shape.along) < 2:
        return None
    x, y = _metres(lat, lon, shape.lat, shape.lon)
    ax, ay, bx, by = x[:-1], y[:-1], x[1:], y[1:]
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    t = np.clip(np.where(seg2 > 0, -(ax * dx + ay * dy) / np.where(seg2 > 0, seg2, 1), 0), 0, 1)
    dist = np.hypot(ax + t * dx, ay + t * dy)
    along = shape.along[:-1] + t * (shape.along[1:] - shape.along[:-1])
    dist = np.where(along >= start - 1e-6, dist, np.inf)
    best = int(np.argmin(dist))
    return float(along[best]) if dist[best] <= MAX_OFF_SHAPE_M else None


def _point(shape: Shape, s: float) -> tuple[float, float]:
    i = int(np.clip(np.searchsorted(shape.along, s, side="right") - 1, 0, len(shape.along) - 2))
    span = shape.along[i + 1] - shape.along[i]
    f = 0.0 if span <= 0 else (s - shape.along[i]) / span
    return (
        float(shape.lat[i] + f * (shape.lat[i + 1] - shape.lat[i])),
        float(shape.lon[i] + f * (shape.lon[i + 1] - shape.lon[i])),
    )


def _offsets(net: Network, shape_id: str, stop_ids: tuple[str, ...]) -> list[float | None]:
    key = (shape_id, stop_ids)
    if key not in net.offsets:
        shape, start, out = net.shapes[shape_id], 0.0, []
        for stop in stop_ids:
            lat, lon = net.stops[stop]
            s = _project(shape, lat, lon, start)
            out.append(s)
            start = s if s is not None else start
        net.offsets[key] = out
    return net.offsets[key]


def _trips(table: pa.Table, now: int) -> dict[str, list[dict]]:
    """Stop rows of the trips whose scheduled span contains `now`, in stop order."""
    span = table.group_by("trip_id").aggregate(
        [
            ("arrival_sec", "min"),
            ("departure_sec", "min"),
            ("arrival_sec", "max"),
            ("departure_sec", "max"),
        ]
    )
    lo = pc.min_element_wise(span["arrival_sec_min"], span["departure_sec_min"])
    hi = pc.max_element_wise(span["arrival_sec_max"], span["departure_sec_max"])
    running = span["trip_id"].filter(pc.and_(pc.less_equal(lo, now), pc.greater_equal(hi, now)))
    table = table.filter(pc.is_in(table["trip_id"], value_set=running))
    out: dict[str, list[dict]] = {}
    cols = ["trip_id", "route_id", "stop_id", "stop_sequence", "arrival_sec", "departure_sec"]
    for row in table.select([*cols, "quality_flags"]).to_pylist():
        out.setdefault(row["trip_id"], []).append(row)
    for stops in out.values():
        stops.sort(key=lambda r: r["stop_sequence"])
    return out


def scheduled_positions(net: Network, timetables: list[pa.Table], at: datetime) -> list[dict]:
    """Scheduled positions at `at` from S30 timetables (one service date per table).

    Tables for service dates that cannot be running at `at`, or from another feed, are ignored;
    S21 (historical) tables are refused.
    """
    candidates = set(service_dates(at))
    markers = []
    for table in timetables:
        sources = set(table["source_id"].to_pylist())
        if sources & {"S21"}:
            raise ValueError("S21 is a 2016 historical reference: no positions or ETAs")
        if not table.num_rows or sources != {"S30"}:
            continue
        days = set(table["service_date"].to_pylist())
        feeds = set(table["feed_id"].to_pylist())
        if len(days) != 1 or feeds != {net.feed_id}:
            raise ValueError("one feed and one service date per timetable")
        day = days.pop()
        if day not in candidates:
            continue
        now = service_seconds(at, day)
        for trip_id, stops in _trips(table, now).items():
            marker = _locate(net, trip_id, stops, now)
            if marker is not None:
                markers.append(marker | {"service_date": day.isoformat()})
    return markers


def _locate(net: Network, trip_id: str, stops: list[dict], now: int) -> dict | None:
    times = [(r["arrival_sec"], r["departure_sec"]) for r in stops]
    known = [s for pair in times for s in pair if s is not None]
    if not known or not min(known) <= now <= max(known):
        return None  # not running on this service date: no marker
    base = {
        "feed_id": net.feed_id,
        "source_revision": net.revision,
        "trip_id": trip_id,
        "route_id": stops[0]["route_id"],
        "label": SCHEDULED_LABEL,
        "live": False,
        "provenance": "reconstructed",
        "approximate": any("imputed" in r["quality_flags"] for r in stops),
        "uncertainty": CAVEATS[net.feed_id],
        "lat": None,
        "lon": None,
        "pause_reason": None,
    }

    def paused(reason: str, i: int = 0) -> dict:
        return base | {
            "status": "paused",
            "pause_reason": reason,
            "from_stop_id": stops[i]["stop_id"],
        }

    if any(None in pair for pair in times):
        return paused("missing time")
    for i, (arr, dep) in enumerate(times):
        if arr <= now <= dep:
            lat, lon = net.stops[stops[i]["stop_id"]]
            stop = stops[i]["stop_id"]
            return base | {
                "status": "at_stop",
                "lat": lat,
                "lon": lon,
                "from_stop_id": stop,
                "to_stop_id": stop,
            }
        if i + 1 < len(times) and dep < now < times[i + 1][0]:
            nxt = times[i + 1][0]
            shape_id = net.trip_shape.get(trip_id)
            if shape_id not in net.shapes:
                return paused("missing shape", i)
            offsets = _offsets(net, shape_id, tuple(r["stop_id"] for r in stops))
            a, b = offsets[i], offsets[i + 1]
            if a is None or b is None or b < a:
                return paused("stop not on shape", i)
            lat, lon = _point(net.shapes[shape_id], a + (b - a) * (now - dep) / (nxt - dep))
            return base | {
                "status": "moving",
                "lat": lat,
                "lon": lon,
                "from_stop_id": stops[i]["stop_id"],
                "to_stop_id": stops[i + 1]["stop_id"],
                "departed_sec": dep,
                "arrives_sec": nxt,
            }
    return paused("inconsistent times")


def rail_reference(table: pa.Table) -> list[dict]:
    """S21 stops as a historical reference: clock text only, no instant, ETA or position."""
    if set(table["source_id"].to_pylist()) != {"S21"}:
        raise ValueError("rail reference mode reads S21 only")
    keep = [
        "station_id",
        "train_id",
        "stop_sequence",
        "arrival_text",
        "departure_text",
        "journey_day",
        "snapshot_id",
    ]
    return [
        r | {"label": RAIL_LABEL, "mode": "historical_reference", "timetable_year": 2016}
        for r in table.select(keep).to_pylist()
    ]


def rail_stations(table: pa.Table) -> list[dict]:
    """Railway stations of the S21 layer (2016 list) with known positions."""
    seen: dict[str, dict] = {}
    for r in table.select(["station_id", "lat", "lon"]).to_pylist():
        if r["lat"] is not None and r["station_id"] not in seen:
            seen[r["station_id"]] = {
                "id": r["station_id"],
                "lat": r["lat"],
                "lon": r["lon"],
                "kind": "railway_station",
                "label": RAIL_LABEL,
            }
    return list(seen.values())


def snapshot(
    nets: list[Network], timetables: list[pa.Table], at: datetime, rail: pa.Table | None = None
) -> dict:
    """The web layer's JSON: markers, pauses, stations, feed revisions and caveats."""
    markers = [
        m
        for net in nets
        for m in scheduled_positions(
            net, [t for t in timetables if set(t["feed_id"].to_pylist()) == {net.feed_id}], at
        )
    ]
    return {
        "as_of": at.astimezone(TZ).isoformat(),
        "label": SCHEDULED_LABEL,
        "feeds": [
            {
                "feed_id": n.feed_id,
                "source_revision": n.revision,
                "uncertainty": CAVEATS[n.feed_id],
                "service_dates": sorted(
                    {m["service_date"] for m in markers if m["feed_id"] == n.feed_id}
                ),
            }
            for n in nets
        ],
        "markers": markers,
        "stations": [s for n in nets for s in n.stations] + (rail_stations(rail) if rail else []),
        "rail": {"label": RAIL_LABEL, "mode": "historical_reference"} if rail else None,
    }
