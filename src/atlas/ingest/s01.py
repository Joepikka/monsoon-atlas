"""S01 Open-Meteo weather forecast (T010). Field map: configs/sources/s01.yaml.

The forecast response carries no run time, so each fetch reads the named model's metadata
before and after the forecast call and rejects the run if it changed in between (T009 e06 to
e10). Never use the default best-match model: it names no model, so its issue time is unknown.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S01"
API = "https://api.open-meteo.com"
HOSTS = {"api.open-meteo.com"}
MAPPING_VERSION = "s01-v1"
LICENCE_ID = "cc-by-4.0-open-meteo"
SETTLE = timedelta(minutes=10)  # Model Updates page: wait 10 minutes after availability
# provider name -> (canonical column, unit the request asks for and the response must echo)
VARIABLES = {
    "temperature_2m": ("temperature_c", "°C"),
    "precipitation": ("rain_mm", "mm"),
    "relative_humidity_2m": ("humidity_pct", "%"),
    "wind_speed_10m": ("wind_ms", "m/s"),
}
UNITS = {
    "temperature_unit": "celsius",
    "wind_speed_unit": "ms",
    "precipitation_unit": "mm",
    "timezone": "GMT",
}
TS = pa.timestamp("us", tz="UTC")
MEASURES = pa.schema(
    [
        pa.field("cell_id", pa.string(), False),
        pa.field("model", pa.string(), False),
        pa.field("temperature_c", pa.float64(), True),
        pa.field("rain_mm", pa.float64(), True),
        pa.field("humidity_pct", pa.float64(), True),
        pa.field("wind_ms", pa.float64(), True),
    ]
)


def meta_url(model: str) -> str:
    return f"{API}/data/{model}/static/meta.json"


def _json(raw: RawArtifact):
    try:
        return json.loads(raw.path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc


class S01:
    def __init__(
        self,
        state: str,
        points: Sequence[tuple[float, float]],
        model: str = "ecmwf_ifs025",
        fetcher: Fetcher | None = None,
        forecast_days: int = 16,
    ):
        if not points:
            raise ValueError("at least one (lat, lon) point")
        if model == "best_match":
            raise ValueError("best_match has no known issue time; name one model")
        self.state, self.points, self.model = state, list(points), model
        self.fetcher, self.forecast_days = fetcher, forecast_days

    def params(self) -> dict[str, str]:
        return {
            "latitude": ",".join(f"{lat:g}" for lat, _ in self.points),
            "longitude": ",".join(f"{lon:g}" for _, lon in self.points),
            "hourly": ",".join(VARIABLES),
            **UNITS,
            "forecast_days": str(self.forecast_days),
            "models": self.model,
        }

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """[metadata, forecast]; raises if the model run changed during the call."""
        before = self.fetcher.fetch_bytes(
            ctx, meta_url(self.model), mapping_version=MAPPING_VERSION
        )
        forecast = self.fetcher.fetch_bytes(
            ctx, f"{API}/v1/forecast", mapping_version=MAPPING_VERSION, params=self.params()
        )
        after = self.fetcher.fetch_bytes(ctx, meta_url(self.model), mapping_version=MAPPING_VERSION)
        run = "last_run_initialisation_time"
        if _json(before).get(run) != _json(after).get(run):
            raise IngestError(f"{SOURCE_ID}: {self.model} run changed during the fetch; retry")
        return [after, forecast]

    def parse(
        self, raw: RawArtifact, config: SourceConfig, *, meta: RawArtifact | None = None
    ) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        if meta is None:
            raise IngestError(f"{SOURCE_ID}: issue time unknown without the model metadata")
        info = _json(meta)
        try:
            issued = datetime.fromtimestamp(info["last_run_initialisation_time"], UTC)
            ready = datetime.fromtimestamp(info["last_run_availability_time"], UTC)
        except (KeyError, TypeError) as exc:
            raise IngestError(f"{SOURCE_ID}: model metadata lacks run times") from exc
        body = _json(raw)
        locations = body if isinstance(body, list) else [body]
        if not locations or not all(isinstance(loc, dict) for loc in locations):
            raise IngestError(f"{SOURCE_ID}: empty or malformed forecast response")

        cols: dict[str, list] = {k: [] for k in ("cell_id", "valid_at", *MEASURES.names)}
        for loc in locations:
            units, hourly = loc.get("hourly_units", {}), loc.get("hourly", {})
            expected = {k: unit for k, (_, unit) in VARIABLES.items()} | {"time": "iso8601"}
            if units != expected or set(hourly) != set(expected):
                raise IngestError(f"{SOURCE_ID}: columns or units changed: {sorted(units.items())}")
            if loc.get("utc_offset_seconds") != 0:
                raise IngestError(f"{SOURCE_ID}: times are not UTC")
            cell = f"om_{self.model}_{loc['latitude']:.4f}N_{loc['longitude']:.4f}E"
            n = len(hourly["time"])
            if any(len(hourly[k]) != n for k in VARIABLES):
                raise IngestError(f"{SOURCE_ID}: hourly arrays differ in length")
            cols["cell_id"] += [cell] * n
            cols["model"] += [self.model] * n
            cols["valid_at"] += [
                datetime.fromisoformat(t).replace(tzinfo=UTC) for t in hourly["time"]
            ]
            for provider, (canonical, _) in VARIABLES.items():
                cols[canonical] += [None if v is None else float(v) for v in hourly[provider]]

        n = len(cols["cell_id"])
        names = [c for c, _ in VARIABLES.values()]
        reasons, flags = [], []
        for i in range(n):
            values = [cols[c][i] for c in names]
            rain, humidity = cols["rain_mm"][i], cols["humidity_pct"][i]
            if any(v is None for v in values):
                # One missing_reason per row: an hour past the model's data end becomes all null.
                reasons.append("out_of_coverage")
                flags.append(["missing"])
            elif rain < 0 or not 0 <= humidity <= 100:
                reasons.append("quality_rejected")
                flags.append(["out_of_range"])
            else:
                reasons.append(None)
                flags.append([])
                continue
            for c in names:
                cols[c][i] = None

        fetched = raw.fetched_at
        snapshot = f"{SOURCE_ID}-{self.model}-{issued:%Y%m%dT%H%MZ}-{raw.sha256[:12]}"
        record_ids = [
            hashlib.sha256(
                f"{c}|{v.isoformat()}|{self.model}|{issued.isoformat()}".encode()
            ).hexdigest()
            for c, v in zip(cols["cell_id"], cols["valid_at"], strict=True)
        ]
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": record_ids,
            "snapshot_id": [snapshot] * n,
            "observed_at": [None] * n,
            "valid_at": cols["valid_at"],
            "issued_at": [issued] * n,
            "available_at": [max(ready + SETTLE, fetched)] * n,
            "fetched_at": [fetched] * n,
            "published_at": [ready] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["model"] * n,
            "quality_flags": flags,
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # CC BY 4.0 with attribution (T009 e04)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": reasons,
        }
        measures = {name: cols[name] for name in MEASURES.names}
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table, measures=names)
        mapping = {provider: canonical for provider, (canonical, _) in VARIABLES.items()}
        return with_mapping(table, mapping | {"hourly.time": "valid_at"}, MAPPING_VERSION)
