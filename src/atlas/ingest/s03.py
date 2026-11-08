"""S03 Open-Meteo GloFAS river discharge (T048). Field map: configs/sources/s03.yaml.

GloFAS discharge is simulated (provenance "model"), not a gauge (T047 e04). Missing river cells
stay null, never 0; available_at is the real fetch time, so past values are a hindcast unless
they were stored at issue time.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import date, timedelta

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.asof import local_midnight_utc
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S03"
URL = "https://flood-api.open-meteo.com/v1/flood"
HOSTS = {"flood-api.open-meteo.com"}
MAPPING_VERSION = "s03-v1"
LICENCE_ID = "cc-by-4.0-open-meteo"
PRODUCT = "seamless_v4"  # named explicitly; the same values as the default (T047 e07, e11)
UNITS = {"time": "iso8601", "river_discharge": "m³/s"}
MEASURES = pa.schema(
    [
        pa.field("river_cell_id", pa.string(), False),
        pa.field("valid_date", pa.date32(), False),
        pa.field("discharge_m3s", pa.float64(), True),
        pa.field("member", pa.int64(), True),
        pa.field("product", pa.string(), False),
    ]
)


class S03:
    def __init__(
        self,
        state: str,
        points: Sequence[tuple[float, float]],
        start: date,
        end: date,
        fetcher: Fetcher | None = None,
    ):
        if not points or start > end:
            raise ValueError("need points and start <= end")
        self.state, self.points, self.start, self.end = state, list(points), start, end
        self.fetcher = fetcher

    def params(self) -> dict[str, str]:
        return {
            "latitude": ",".join(f"{lat:g}" for lat, _ in self.points),
            "longitude": ",".join(f"{lon:g}" for _, lon in self.points),
            "daily": "river_discharge",
            "models": PRODUCT,
            "timezone": "Asia/Kolkata",
            "start_date": self.start.isoformat(),
            "end_date": self.end.isoformat(),
        }

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        return [
            self.fetcher.fetch_bytes(
                ctx, URL, mapping_version=MAPPING_VERSION, params=self.params()
            )
        ]

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        try:
            body = json.loads(raw.path.read_bytes())
        except (ValueError, UnicodeDecodeError) as exc:
            raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc
        locations = body if isinstance(body, list) else [body]
        if not locations or not all(isinstance(loc, dict) for loc in locations):
            raise IngestError(f"{SOURCE_ID}: empty or malformed response")

        cols: dict[str, list] = {
            c: [] for c in ("missing_reason", "quality_flags", *MEASURES.names)
        }
        for loc in locations:
            units, days = loc.get("daily_units", {}), loc.get("daily", {})
            if units != UNITS or set(days) != set(UNITS):
                raise IngestError(f"{SOURCE_ID}: columns or units changed: {sorted(units.items())}")
            if loc.get("utc_offset_seconds") != 19800:
                raise IngestError(f"{SOURCE_ID}: days are not IST days")
            times, flows = days["time"], days["river_discharge"]
            if len(times) != len(flows):
                raise IngestError(f"{SOURCE_ID}: daily arrays differ in length")
            cell = f"glofas_{PRODUCT}_{loc['latitude']:.4f}N_{loc['longitude']:.4f}E"
            known = [
                date.fromisoformat(t) for t, v in zip(times, flows, strict=True) if v is not None
            ]
            newest = max(known, default=None)
            for t, value in zip(times, flows, strict=True):
                day = date.fromisoformat(t)
                if value is None:
                    # Missing cells stay null (T047 source check); after the newest value it is lag.
                    late = newest is not None and day > newest
                    reason, flags = (
                        ("not_yet_available" if late else "out_of_coverage"),
                        ["missing"],
                    )
                elif value < 0:
                    reason, flags, value = "quality_rejected", ["out_of_range"], None
                else:
                    reason, flags = None, []
                cols["river_cell_id"].append(cell)
                cols["valid_date"].append(day)
                cols["discharge_m3s"].append(None if value is None else float(value))
                cols["member"].append(None)  # deterministic series; members are forecast-only
                cols["product"].append(PRODUCT)
                cols["missing_reason"].append(reason)
                cols["quality_flags"].append(flags)

        n = len(cols["valid_date"])
        fetched = raw.fetched_at
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"{c}|{d}|{PRODUCT}|{raw.sha256}".encode()).hexdigest()
                for c, d in zip(cols["river_cell_id"], cols["valid_date"], strict=True)
            ],
            "snapshot_id": [f"{SOURCE_ID}-{PRODUCT}-{fetched:%Y%m%dT%H%M%SZ}-{raw.sha256[:12]}"]
            * n,
            "observed_at": [None] * n,
            # A daily value describes the whole IST day, so it is valid at the day's end.
            "valid_at": [local_midnight_utc(d + timedelta(days=1)) for d in cols["valid_date"]],
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [None] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["model"] * n,  # simulated discharge, not a gauge (T047 e04)
            "quality_flags": cols["quality_flags"],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # CC BY 4.0 with attribution (T047 e03)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": cols["missing_reason"],
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | {m: cols[m] for m in MEASURES.names}, schema=schema)
        validate_table(table, measures=["discharge_m3s"])
        mapping = {"river_discharge": "discharge_m3s", "daily.time": "valid_date"}
        return with_mapping(table, mapping, MAPPING_VERSION)
