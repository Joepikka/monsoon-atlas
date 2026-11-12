"""S04 Open-Meteo CAMS air-quality estimates (T050). Field map: configs/sources/s04.yaml.

CAMS values are model forecasts, never CPCB observations (provenance "model"). The response
carries no run time, so each fetch reads the cams_global metadata before and after the call and
rejects the run if it changed in between (T049 e05 to e09). Karnataka is outside the European
domain, so the domain is always named cams_global.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.s01 import SETTLE  # same Model Updates page advice (T049 e05)

SOURCE_ID = "S04"
API = "https://air-quality-api.open-meteo.com"
HOSTS = {"air-quality-api.open-meteo.com"}
DOMAIN = "cams_global"
META_URL = f"{API}/data/{DOMAIN}/static/meta.json"
MAPPING_VERSION = "s04-v1"
LICENCE_ID = "cc-by-4.0-open-meteo"
UNIT = "μg/m³"
VARIABLES = {"pm2_5": "pm25_ugm3", "pm10": "pm10_ugm3", "nitrogen_dioxide": "no2_ugm3"}
MEASURES = pa.schema(
    [
        pa.field("cell_id", pa.string(), False),
        pa.field("product", pa.string(), False),
        *(pa.field(c, pa.float64(), True) for c in VARIABLES.values()),
    ]
)


def _json(raw: RawArtifact):
    try:
        return json.loads(raw.path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc


class S04:
    def __init__(
        self,
        state: str,
        points: Sequence[tuple[float, float]],
        fetcher: Fetcher | None = None,
        forecast_days: int = 5,
    ):
        if not points:
            raise ValueError("at least one (lat, lon) point")
        self.state, self.points = state, list(points)
        self.fetcher, self.forecast_days = fetcher, forecast_days

    def params(self) -> dict[str, str]:
        return {
            "latitude": ",".join(f"{lat:g}" for lat, _ in self.points),
            "longitude": ",".join(f"{lon:g}" for _, lon in self.points),
            "hourly": ",".join(VARIABLES),
            "timezone": "GMT",
            "forecast_days": str(self.forecast_days),
            "domains": DOMAIN,
        }

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """[metadata, forecast]; raises if the CAMS run changed during the call."""
        before = self.fetcher.fetch_bytes(ctx, META_URL, mapping_version=MAPPING_VERSION)
        forecast = self.fetcher.fetch_bytes(
            ctx, f"{API}/v1/air-quality", mapping_version=MAPPING_VERSION, params=self.params()
        )
        after = self.fetcher.fetch_bytes(ctx, META_URL, mapping_version=MAPPING_VERSION)
        run = "last_run_initialisation_time"
        if _json(before).get(run) != _json(after).get(run):
            raise IngestError(f"{SOURCE_ID}: {DOMAIN} run changed during the fetch; retry")
        return [after, forecast]

    def parse(
        self, raw: RawArtifact, config: SourceConfig, *, meta: RawArtifact | None = None
    ) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        if meta is None:
            raise IngestError(f"{SOURCE_ID}: issue time unknown without the CAMS metadata")
        info = _json(meta)
        try:
            issued = datetime.fromtimestamp(info["last_run_initialisation_time"], UTC)
            ready = datetime.fromtimestamp(info["last_run_availability_time"], UTC)
        except (KeyError, TypeError) as exc:
            raise IngestError(f"{SOURCE_ID}: CAMS metadata lacks run times") from exc
        body = _json(raw)
        locations = body if isinstance(body, list) else [body]
        if not locations or not all(isinstance(loc, dict) for loc in locations):
            raise IngestError(f"{SOURCE_ID}: empty or malformed air-quality response")

        names = list(VARIABLES.values())
        cols: dict[str, list] = {k: [] for k in ("cell_id", "valid_at", *MEASURES.names)}
        for loc in locations:
            units, hourly = loc.get("hourly_units", {}), loc.get("hourly", {})
            expected = dict.fromkeys(VARIABLES, UNIT) | {"time": "iso8601"}
            if units != expected or set(hourly) != set(expected):
                raise IngestError(f"{SOURCE_ID}: columns or units changed: {sorted(units.items())}")
            if loc.get("utc_offset_seconds") != 0:
                raise IngestError(f"{SOURCE_ID}: times are not UTC")
            n = len(hourly["time"])
            if any(len(hourly[k]) != n for k in VARIABLES):
                raise IngestError(f"{SOURCE_ID}: hourly arrays differ in length")
            cols["cell_id"] += [f"om_{DOMAIN}_{loc['latitude']:.4f}N_{loc['longitude']:.4f}E"] * n
            cols["product"] += [DOMAIN] * n
            cols["valid_at"] += [
                datetime.fromisoformat(t).replace(tzinfo=UTC) for t in hourly["time"]
            ]
            for provider, canonical in VARIABLES.items():
                cols[canonical] += [None if v is None else float(v) for v in hourly[provider]]

        n = len(cols["cell_id"])
        reasons, flags = [], []
        for i in range(n):
            values = [cols[c][i] for c in names]
            if any(v is None for v in values):
                # One missing_reason per row: hours at or after the run's data_end_time are null.
                reasons.append("out_of_coverage")
                flags.append(["missing"])
            elif min(values) < 0:
                reasons.append("quality_rejected")
                flags.append(["out_of_range"])
            else:
                reasons.append(None)
                flags.append([])
                continue
            for c in names:
                cols[c][i] = None

        fetched = raw.fetched_at
        snapshot = f"{SOURCE_ID}-{DOMAIN}-{issued:%Y%m%dT%H%MZ}-{raw.sha256[:12]}"
        record_ids = [
            hashlib.sha256(
                f"{c}|{v.isoformat()}|{DOMAIN}|{issued.isoformat()}".encode()
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
            "redistribution_allowed": [True] * n,  # CC BY 4.0 with attribution (T049 e03)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": reasons,
        }
        measures = {name: cols[name] for name in MEASURES.names}
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table, measures=names)
        return with_mapping(table, VARIABLES | {"hourly.time": "valid_at"}, MAPPING_VERSION)
