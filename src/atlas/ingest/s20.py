"""S20 USGS earthquakes (T072). Field map: configs/sources/s20.yaml; rules: D110.

Live rows come from the real-time GeoJSON feed (the docs ask automated applications to use it);
history comes from the FDSN query with an explicit start time, because without one the service
searches only the last 30 days (T071 e05). Rows are keyed by event id and versioned by `updated`.
`review_status` automatic means a preliminary magnitude. Only earthquakes inside the box are kept.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S20"
FEED = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
QUERY = "https://earthquake.usgs.gov/fdsnws/event/1/query"
HOSTS = {"earthquake.usgs.gov"}
STATUSES = {"automatic", "reviewed", "deleted"}
MAPPING_VERSION = "s20-v1"
LICENCE_ID = "usgs-licence-unconfirmed"
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
Box = tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
MEASURES = pa.schema(
    [
        pa.field("event_id", pa.string(), False),
        pa.field("origin_at", pa.timestamp("us", tz="UTC"), False),
        pa.field("lat", pa.float64(), False),
        pa.field("lon", pa.float64(), False),
        pa.field("depth_km", pa.float64(), True),
        pa.field("magnitude", pa.float64(), True),
        pa.field("mag_type", pa.string(), True),
        pa.field("review_status", pa.string(), False),
        pa.field("updated_at", pa.timestamp("us", tz="UTC"), False),
    ]
)


def _ms(value) -> datetime:
    if not isinstance(value, int):
        raise IngestError(f"{SOURCE_ID}: time is not epoch milliseconds: {value!r}")
    return EPOCH + timedelta(milliseconds=value)


class S20:
    def __init__(
        self, state: str, box: Box, starttime: str | None = None, fetcher: Fetcher | None = None
    ):
        self.state, self.box, self.starttime, self.fetcher = state, box, starttime, fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """The past-day feed, or the catalogue from `starttime` (at most 1,000 newest events)."""
        if self.starttime is None:
            return [self.fetcher.fetch_bytes(ctx, FEED, mapping_version=MAPPING_VERSION)]
        min_lon, min_lat, max_lon, max_lat = self.box
        params = {
            "format": "geojson",
            "orderby": "time",
            "limit": "1000",  # time-ordered queries of 1,000 or fewer have no range limit (e01)
            "starttime": self.starttime,
            "minlatitude": f"{min_lat:g}",
            "maxlatitude": f"{max_lat:g}",
            "minlongitude": f"{min_lon:g}",
            "maxlongitude": f"{max_lon:g}",
        }
        return [
            self.fetcher.fetch_bytes(ctx, QUERY, mapping_version=MAPPING_VERSION, params=params)
        ]

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        try:
            body = json.loads(raw.path.read_bytes())
        except (ValueError, UnicodeDecodeError) as exc:
            raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc
        if not isinstance(body, dict) or body.get("type") != "FeatureCollection":
            raise IngestError(f"{SOURCE_ID}: empty or malformed GeoJSON response")
        features = body.get("features")
        if not isinstance(features, list):
            raise IngestError(f"{SOURCE_ID}: response has no features list")
        min_lon, min_lat, max_lon, max_lat = self.box
        cols: dict[str, list] = {f.name: [] for f in MEASURES}
        for f in features:
            try:
                props, (lon, lat, depth) = f["properties"], f["geometry"]["coordinates"]
                event_id, status, kind = f["id"], props["status"], props["type"]
                origin, updated = _ms(props["time"]), _ms(props["updated"])
                mag, mag_type = props["mag"], props["magType"]
            except (KeyError, TypeError, ValueError) as exc:
                raise IngestError(f"{SOURCE_ID}: feature lacks documented fields") from exc
            if status not in STATUSES:
                raise IngestError(f"{SOURCE_ID}: unknown status {status!r}")
            if kind != "earthquake" or status == "deleted":
                continue  # D110: quarry blasts, explosions and deleted events are not shown
            if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
                continue
            cols["event_id"].append(event_id)
            cols["origin_at"].append(origin)
            cols["lat"].append(float(lat))
            cols["lon"].append(float(lon))
            cols["depth_km"].append(None if depth is None else float(depth))
            cols["magnitude"].append(None if mag is None else float(mag))
            cols["mag_type"].append(mag_type)
            cols["review_status"].append(status)
            cols["updated_at"].append(updated)

        n, fetched = len(cols["event_id"]), raw.fetched_at
        reasons = ["not_reported" if m is None else None for m in cols["magnitude"]]
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"{e}|{u.isoformat()}".encode()).hexdigest()
                for e, u in zip(cols["event_id"], cols["updated_at"], strict=True)
            ],
            "snapshot_id": [f"{SOURCE_ID}-{raw.sha256[:12]}"] * n,
            "observed_at": cols["origin_at"],
            "valid_at": cols["origin_at"],
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": cols["updated_at"],
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["official"] * n,  # USGS ComCat; automatic = preliminary
            "quality_flags": [["missing"] if r else [] for r in reasons],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [False] * n,  # D110: licence not yet recorded
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": reasons,
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | cols, schema=schema)
        validate_table(table, measures=["magnitude"])
        mapping = {
            "id": "event_id",
            "properties.time": "origin_at",
            "geometry.coordinates": "lon, lat, depth_km",
            "properties.mag": "magnitude",
            "properties.magType": "mag_type",
            "properties.status": "review_status",
            "properties.updated": "updated_at",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
