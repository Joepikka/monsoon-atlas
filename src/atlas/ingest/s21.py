"""S21 Datameet railway schedules (T074). Field map: configs/sources/s21.yaml; rules: D111.

A 2016 community timetable (CC0), pinned to one commit: rows are a historical reference, never
current schedules or ETAs. Stops at stations in the configured state are kept; the stop sequence
is the file order within each train (not published), and trains whose stop ids do not rise in
that order are flagged imputed. "None" times become null.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S21"
COMMIT = "e0c538a1e41ae5eace454d2818902e1065608e16"  # 8 Aug 2016 (T073 e04)
COMMIT_AT = datetime(2016, 8, 8, 7, 20, tzinfo=UTC)
BASE = f"https://raw.githubusercontent.com/datameet/railways/{COMMIT}"
HOSTS = {"raw.githubusercontent.com"}
STOP_KEYS = {
    "arrival",
    "day",
    "departure",
    "id",
    "station_code",
    "station_name",
    "train_name",
    "train_number",
}
MAPPING_VERSION = "s21-v1"
LICENCE_ID = "cc0-datameet-railways"
MEASURES = pa.schema(
    [
        pa.field("station_id", pa.string(), False),
        pa.field("train_id", pa.string(), False),
        pa.field("stop_sequence", pa.int64(), False),
        pa.field("arrival_text", pa.string(), True),
        pa.field("departure_text", pa.string(), True),
        pa.field("journey_day", pa.int64(), True),
        pa.field("lat", pa.float64(), True),
        pa.field("lon", pa.float64(), True),
    ]
)


def _json(raw: RawArtifact):
    try:
        return json.loads(raw.path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc


def _clock(value) -> str | None:
    if value == "None":
        return None
    if not isinstance(value, str) or len(value) != 8 or value[2] != ":" or value[5] != ":":
        raise IngestError(f"{SOURCE_ID}: time is not HH:MM:SS: {value!r}")
    return value


class S21:
    def __init__(self, state: str, state_name: str, fetcher: Fetcher | None = None):
        self.state, self.state_name, self.fetcher = state, state_name, fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """[stations, schedules] at the pinned commit; schedules (82 MB) is streamed to disk."""
        stations = self.fetcher.fetch_bytes(
            ctx, f"{BASE}/stations.json", mapping_version=MAPPING_VERSION
        )
        schedules = self.fetcher.fetch_large(
            ctx, f"{BASE}/schedules.json", mapping_version=MAPPING_VERSION
        )
        return [stations, schedules]

    def parse(
        self, raw: RawArtifact, config: SourceConfig, *, stations: RawArtifact | None = None
    ) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        if stations is None:
            raise IngestError(f"{SOURCE_ID}: station positions needed to place stops")
        if COMMIT not in raw.source_url or COMMIT not in stations.source_url:
            raise IngestError(f"{SOURCE_ID}: files must come from the pinned commit {COMMIT}")
        places = {}
        try:
            for f in _json(stations)["features"]:
                p, geom = f["properties"], f["geometry"]
                lon, lat = geom["coordinates"] if geom else (None, None)
                places[p["code"]] = (p.get("state"), lat, lon)
        except (KeyError, TypeError, ValueError) as exc:
            raise IngestError(f"{SOURCE_ID}: malformed stations file") from exc
        stops = _json(raw)
        if not isinstance(stops, list) or not stops:
            raise IngestError(f"{SOURCE_ID}: empty or malformed schedules file")
        trains: dict[str, list[dict]] = defaultdict(list)
        for stop in stops:
            if not isinstance(stop, dict) or set(stop) != STOP_KEYS:
                raise IngestError(f"{SOURCE_ID}: schedule columns changed")
            trains[stop["train_number"]].append(stop)

        cols: dict[str, list] = {f.name: [] for f in MEASURES}
        flags = []
        for train, rows in trains.items():
            ordered = all(a["id"] < b["id"] for a, b in zip(rows, rows[1:], strict=False))
            for seq, stop in enumerate(rows, start=1):
                code = stop["station_code"]
                if code not in places:
                    raise IngestError(f"{SOURCE_ID}: stop at unknown station {code}")
                state, lat, lon = places[code]
                if state != self.state_name:
                    continue
                day = stop["day"]
                if day is not None and (not isinstance(day, int) or day < 1):
                    raise IngestError(f"{SOURCE_ID}: journey day out of range: {day!r}")
                cols["station_id"].append(code)
                cols["train_id"].append(train)
                cols["stop_sequence"].append(seq)
                cols["arrival_text"].append(_clock(stop["arrival"]))
                cols["departure_text"].append(_clock(stop["departure"]))
                cols["journey_day"].append(day)
                cols["lat"].append(lat)
                cols["lon"].append(lon)
                flags.append([] if ordered else ["imputed"])

        n, fetched = len(cols["station_id"]), raw.fetched_at
        record_ids = [
            hashlib.sha256(f"{COMMIT}|{t}|{s}|{c}".encode()).hexdigest()
            for t, s, c in zip(
                cols["train_id"], cols["stop_sequence"], cols["station_id"], strict=True
            )
        ]
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": record_ids,
            "snapshot_id": [f"{SOURCE_ID}-{COMMIT[:12]}"] * n,
            "observed_at": [None] * n,
            "valid_at": [None] * n,  # D111: a 2016 timetable, no dated validity
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [COMMIT_AT] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["reconstructed"] * n,  # historical community timetable (D111)
            "quality_flags": flags,
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # CC0 (T073 e02)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": [None] * n,
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | cols, schema=schema)
        validate_table(table)
        mapping = {
            "station_code": "station_id",
            "train_number": "train_id",
            "file order within train": "stop_sequence",
            "arrival": "arrival_text",
            "departure": "departure_text",
            "day": "journey_day",
            "stations geometry.coordinates": "lon, lat",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
