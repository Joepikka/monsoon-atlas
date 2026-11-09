"""S30 BMTC and Namma Metro static GTFS (T029). Field map: configs/sources/s30.yaml; rules: D115.

Neither operator publishes GTFS; the feeds are Vonter's unofficial ODbL compilations, pinned to
one commit each. Licence is restricted (raw stays local). parse() returns the stop times of trips
whose service runs on one local service date: seconds are counted from noon minus 12 h of that
date and may pass 86,400 (never wrapped). Rows are scheduled timetable entries, never live
positions; BMRCL rows with timepoint 0 are approximate and flagged imputed.
"""

from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S30"
TZ = ZoneInfo("Asia/Kolkata")
FEEDS = {  # feed_id: (commit, commit time, url); T028 e07, e10
    "bmrcl": (
        "f402c4c69a5d314320024f84620fa83e909c4188",
        datetime(2026, 8, 17, 16, 33, 48, tzinfo=UTC),
        "https://raw.githubusercontent.com/Vonter/bmrcl-gtfs/"
        "f402c4c69a5d314320024f84620fa83e909c4188/gtfs/bmrcl.zip",
    ),
    "bmtc": (
        "ee945dc0c21b29193f88e3e1e9af218dd24ea182",
        datetime(2026, 9, 8, 3, 58, 57, tzinfo=UTC),
        "https://raw.githubusercontent.com/Vonter/bmtc-gtfs/"
        "ee945dc0c21b29193f88e3e1e9af218dd24ea182/gtfs/bmtc.zip",
    ),
}
HOSTS = {"raw.githubusercontent.com"}
REQUIRED = {
    "agency.txt": {"agency_timezone"},
    "trips.txt": {"route_id", "service_id", "trip_id"},
    "stop_times.txt": {"trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"},
}
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
TIME = r"^\d{1,3}:[0-5]\d:[0-5]\d$"
MAPPING_VERSION = "s30-v1"
LICENCE_ID = "odbl-vonter-gtfs-restricted"
MEASURES = pa.schema(
    [
        pa.field("feed_id", pa.string(), False),
        pa.field("service_date", pa.date32(), False),
        pa.field("trip_id", pa.string(), False),
        pa.field("route_id", pa.string(), False),
        pa.field("stop_id", pa.string(), False),
        pa.field("stop_sequence", pa.int64(), False),
        pa.field("arrival_sec", pa.int64(), True),
        pa.field("departure_sec", pa.int64(), True),
    ]
)


def feed_of(raw: RawArtifact) -> str:
    for feed_id, (_, _, url) in FEEDS.items():
        if raw.source_url == url:
            return feed_id
    raise IngestError(f"{SOURCE_ID}: not a pinned feed URL: {raw.source_url}")


def open_feed(raw: RawArtifact) -> zipfile.ZipFile:
    try:
        zf = zipfile.ZipFile(raw.path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise IngestError(f"{SOURCE_ID}: not a GTFS zip: {raw.source_url}") from exc
    for name, cols in REQUIRED.items():
        if name not in zf.namelist():
            raise IngestError(f"{SOURCE_ID}: {name} missing")
        header = zf.open(name).readline().decode("utf-8-sig").strip().split(",")
        if not cols <= set(header):
            raise IngestError(f"{SOURCE_ID}: {name} columns changed: {sorted(cols - set(header))}")
    if not {"calendar.txt", "calendar_dates.txt"} & set(zf.namelist()):
        raise IngestError(f"{SOURCE_ID}: no calendar.txt or calendar_dates.txt")
    return zf


def rows(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    if name not in zf.namelist():
        return []
    return list(csv.DictReader(io.TextIOWrapper(zf.open(name), "utf-8-sig")))


def read_table(zf: zipfile.ZipFile, name: str) -> pa.Table:
    """One GTFS file as all-string columns (T104 reads stops and shapes with this)."""
    with zf.open(name) as f:
        head = f.readline().decode("utf-8-sig").strip().split(",")
    with zf.open(name) as f:
        return pacsv.read_csv(
            f,
            read_options=pacsv.ReadOptions(column_names=head, skip_rows=1),
            convert_options=pacsv.ConvertOptions(column_types=dict.fromkeys(head, pa.string())),
        )


def _day(text: str) -> date:
    return datetime.strptime(text, "%Y%m%d").date()


def active_services(zf: zipfile.ZipFile, service_date: date) -> set[str]:
    """service_ids running on a local date: calendar days and range, then calendar_dates
    additions (1) and removals (2)."""
    weekday = WEEKDAYS[service_date.weekday()]
    try:
        active = {
            r["service_id"]
            for r in rows(zf, "calendar.txt")
            if _day(r["start_date"]) <= service_date <= _day(r["end_date"]) and r[weekday] == "1"
        }
        for r in rows(zf, "calendar_dates.txt"):
            if _day(r["date"]) == service_date:
                if r["exception_type"] == "1":
                    active.add(r["service_id"])
                elif r["exception_type"] == "2":
                    active.discard(r["service_id"])
                else:
                    raise IngestError(f"{SOURCE_ID}: exception_type {r['exception_type']!r}")
    except (KeyError, ValueError) as exc:
        raise IngestError(f"{SOURCE_ID}: malformed calendar") from exc
    return active


def seconds(times: pa.ChunkedArray | pa.Array) -> pa.Array:
    """GTFS H:MM:SS to seconds after noon minus 12 h; 25:10:00 is 90,600. Blank is null."""
    text = pc.utf8_trim_whitespace(times)
    blank = pc.equal(text, "")
    ok = pc.or_(blank, pc.match_substring_regex(text, TIME))
    if not pc.all(ok).as_py():
        bad = pc.filter(text, pc.invert(ok)).to_pylist()[:3]
        raise IngestError(f"{SOURCE_ID}: time is not H:MM:SS: {bad}")
    parts = pc.split_pattern(pc.if_else(blank, pa.scalar(None, pa.string()), text), ":")
    h, m, s = (pc.cast(pc.list_element(parts, i), pa.int64()) for i in range(3))
    return pc.add(pc.add(pc.multiply(h, 3600), pc.multiply(m, 60)), s)


class S30:
    def __init__(self, state: str, fetcher: Fetcher | None = None):
        self.state, self.fetcher = state, fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """[bmrcl, bmtc] at the pinned commits, streamed to disk (BMTC is 44 MB)."""
        return [
            self.fetcher.fetch_large(ctx, url, mapping_version=MAPPING_VERSION)
            for _, _, url in FEEDS.values()
        ]

    def parse(
        self, raw: RawArtifact, config: SourceConfig, *, service_date: date | None = None
    ) -> pa.Table:
        """Stop times running on `service_date` (default: the local fetch date)."""
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        feed_id = feed_of(raw)
        commit, commit_at, _ = FEEDS[feed_id]
        zf = open_feed(raw)
        zones = {r["agency_timezone"] for r in rows(zf, "agency.txt")}
        if zones != {"Asia/Kolkata"}:
            raise IngestError(f"{SOURCE_ID}: agency_timezone {sorted(zones)}")
        day = service_date or raw.fetched_at.astimezone(TZ).date()
        active = active_services(zf, day)

        # Whole-file checks first: a malformed feed fails whatever the service date.
        all_trips = read_table(zf, "trips.txt")
        st = read_table(zf, "stop_times.txt")
        if not pc.all(
            pc.is_in(st["trip_id"], value_set=all_trips["trip_id"].combine_chunks())
        ).as_py():
            raise IngestError(f"{SOURCE_ID}: stop_times refer to unknown trips")
        try:
            st = st.append_column("seq", pc.cast(st["stop_sequence"], pa.int64()))
        except pa.ArrowInvalid as exc:
            raise IngestError(f"{SOURCE_ID}: stop_sequence is not an integer") from exc
        st = st.append_column("arr", seconds(st["arrival_time"]))
        st = st.append_column("dep", seconds(st["departure_time"]))
        st = st.sort_by([("trip_id", "ascending"), ("seq", "ascending")])
        ids, sq = st["trip_id"].to_pylist(), st["seq"].to_pylist()
        for i in range(1, len(sq)):
            if ids[i] == ids[i - 1] and sq[i] == sq[i - 1]:
                raise IngestError(f"{SOURCE_ID}: stop_sequence repeated in trip {ids[i]}")

        running = pc.is_in(all_trips["service_id"], pa.array(sorted(active), pa.string()))
        trips = all_trips.filter(running)
        st = st.filter(pc.is_in(st["trip_id"], value_set=trips["trip_id"].combine_chunks()))
        trip_ids, seqs = st["trip_id"].to_pylist(), st["seq"].to_pylist()
        arrival, departure = st["arr"], st["dep"]
        route = pc.take(
            trips["route_id"],
            pc.index_in(st["trip_id"], value_set=trips["trip_id"].combine_chunks()),
        )

        n = st.num_rows
        missing = pc.or_(pc.is_null(arrival), pc.is_null(departure))
        reasons = pc.if_else(missing, "not_reported", pa.scalar(None, pa.string()))
        approx = np.zeros(n, dtype=bool)
        if "timepoint" in st.column_names:  # BMRCL: 0 = time approximated by the compiler
            approx = pc.equal(st["timepoint"], "0").to_numpy(zero_copy_only=False)
        offsets = np.concatenate([[0], np.cumsum(approx)]).astype(np.int32)
        flags = pa.ListArray.from_arrays(
            pa.array(offsets), pa.array(["imputed"] * int(approx.sum()), pa.string())
        )
        record_ids = [
            hashlib.sha256(f"{commit}|{day}|{t}|{s}".encode()).hexdigest()
            for t, s in zip(trip_ids, seqs, strict=True)
        ]
        fetched = raw.fetched_at
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": record_ids,
            "snapshot_id": [f"{SOURCE_ID}-{feed_id}-{commit[:12]}-{day:%Y%m%d}"] * n,
            "observed_at": [None] * n,
            "valid_at": [None] * n,  # D115: scheduled entries; the instant is date + seconds
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [commit_at] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["reconstructed"] * n,  # unofficial compilation (D115)
            "quality_flags": flags,
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [False] * n,  # restricted (T028)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": reasons,
        }
        cols = {
            "feed_id": [feed_id] * n,
            "service_date": [day] * n,
            "trip_id": st["trip_id"],
            "route_id": route,
            "stop_id": st["stop_id"],
            "stop_sequence": st["seq"],
            "arrival_sec": arrival,
            "departure_sec": departure,
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | cols, schema=schema)
        validate_table(table)
        mapping = {
            "calendar.txt + calendar_dates.txt": "service_date",
            "stop_times.trip_id": "trip_id",
            "trips.route_id": "route_id",
            "stop_times.stop_id": "stop_id",
            "stop_times.stop_sequence": "stop_sequence",
            "stop_times.arrival_time": "arrival_sec",
            "stop_times.departure_time": "departure_sec",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
