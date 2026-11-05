"""S02 Open-Meteo historical weather / ERA5 (T012). Field map: configs/sources/s02.yaml.

ERA5 is a reanalysis (provenance "model"), published about 5 to 6 days after the day it
describes (T011 e04, e05). available_at is the real fetch time; backtests apply the lag.
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

SOURCE_ID = "S02"
URL = "https://archive-api.open-meteo.com/v1/archive"
HOSTS = {"archive-api.open-meteo.com"}
MAPPING_VERSION = "s02-v1"
LICENCE_ID = "cc-by-4.0-open-meteo"
PRODUCT = "era5"
VARIABLES = {  # provider name -> (canonical column, unit the response must echo)
    "precipitation_sum": ("rain_mm", "mm"),
    "temperature_2m_max": ("tmax_c", "°C"),
    "temperature_2m_min": ("tmin_c", "°C"),
}
MEASURES = pa.schema(
    [
        pa.field("cell_id", pa.string(), False),
        pa.field("date_local", pa.date32(), False),
        pa.field("product", pa.string(), False),
        pa.field("rain_mm", pa.float64(), True),
        pa.field("tmax_c", pa.float64(), True),
        pa.field("tmin_c", pa.float64(), True),
    ]
)


class S02:
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
            "daily": ",".join(VARIABLES),
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
            "timezone": "Asia/Kolkata",
            "models": PRODUCT,
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

        expected = {k: unit for k, (_, unit) in VARIABLES.items()} | {"time": "iso8601"}
        rows = []
        for loc in locations:
            units, days = loc.get("daily_units", {}), loc.get("daily", {})
            if units != expected or set(days) != set(expected):
                raise IngestError(f"{SOURCE_ID}: columns or units changed: {sorted(units.items())}")
            if loc.get("utc_offset_seconds") != 19800:
                raise IngestError(f"{SOURCE_ID}: days are not IST days")
            if any(len(days[k]) != len(days["time"]) for k in VARIABLES):
                raise IngestError(f"{SOURCE_ID}: daily arrays differ in length")
            cell = f"om_{PRODUCT}_{loc['latitude']:.4f}N_{loc['longitude']:.4f}E"
            values = [[days[k][i] for k in VARIABLES] for i in range(len(days["time"]))]
            complete = [
                date.fromisoformat(t)
                for t, v in zip(days["time"], values, strict=True)
                if None not in v
            ]
            newest = max(complete, default=date.min)
            for t, v in zip(days["time"], values, strict=True):
                day = date.fromisoformat(t)
                rows.append((cell, day, v, newest))

        n = len(rows)
        cols: dict[str, list] = {
            c: [] for c in ("missing_reason", "quality_flags", *MEASURES.names)
        }
        for cell, day, v, newest in rows:
            cols["cell_id"].append(cell)
            cols["date_local"].append(day)
            cols["product"].append(PRODUCT)
            rain, tmax, tmin = v
            if None in v:
                # One missing_reason per row; after the newest complete day it is the release lag.
                reason, flag, v = (
                    ("not_yet_available" if day > newest else "out_of_coverage"),
                    ["missing"],
                    [None] * 3,
                )
            elif rain < 0 or tmin > tmax:
                reason, flag, v = "quality_rejected", ["out_of_range"], [None] * 3
            else:
                reason, flag = None, []
            for name, x in zip(("rain_mm", "tmax_c", "tmin_c"), v, strict=True):
                cols[name].append(None if x is None else float(x))
            cols["missing_reason"].append(reason)
            cols["quality_flags"].append(flag)

        fetched = raw.fetched_at
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"{c}|{d}|{PRODUCT}|{raw.sha256}".encode()).hexdigest()
                for c, d in zip(cols["cell_id"], cols["date_local"], strict=True)
            ],
            "snapshot_id": [f"{SOURCE_ID}-{PRODUCT}-{fetched:%Y%m%dT%H%M%SZ}-{raw.sha256[:12]}"]
            * n,
            "observed_at": [None] * n,
            # A daily value describes the whole IST day, so it is valid at the day's end.
            "valid_at": [local_midnight_utc(d + timedelta(days=1)) for d in cols["date_local"]],
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [None] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["model"] * n,  # reanalysis, not observations (T011 source check)
            "quality_flags": cols["quality_flags"],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # CC BY 4.0 with attribution (T011 e03)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": cols["missing_reason"],
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | {m: cols[m] for m in MEASURES.names}, schema=schema)
        validate_table(table, measures=["rain_mm", "tmax_c", "tmin_c"])
        mapping = {provider: canonical for provider, (canonical, _) in VARIABLES.items()}
        return with_mapping(table, mapping | {"daily.time": "date_local"}, MAPPING_VERSION)
