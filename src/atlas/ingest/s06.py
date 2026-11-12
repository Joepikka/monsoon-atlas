"""S06 Open-Meteo climate projections (T054). Field map: configs/sources/s06.yaml.

Daily CMIP6 HighResMIP model climate for 1950-2050, never a forecast or a record of any day
(T053 e04). One row per cell, GMT day and model. The API has no scenario parameter and names no
SSP ("as close to RCP8.5 as possible", e04), so `scenario` is always null. Each row records
whether the default ERA5-Land bias correction was applied.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S06"
API = "https://climate-api.open-meteo.com/v1/climate"
HOSTS = {"climate-api.open-meteo.com"}
MAPPING_VERSION = "s06-v1"
LICENCE_ID = "cc-by-4.0-open-meteo-cmip6"
MODELS = (
    "CMCC_CM2_VHR4",
    "FGOALS_f3_H",
    "HiRAM_SIT_HR",
    "MRI_AGCM3_2_S",
    "EC_Earth3P_HR",
    "MPI_ESM1_2_XR",
    "NICAM16_8S",
)
# provider variable -> (canonical column, unit the request asks for and the response must echo)
VARIABLES = {"precipitation_sum": ("rain_mm", "mm"), "temperature_2m_max": ("tmax_c", "°C")}
FIRST, LAST = date(1950, 1, 1), date(2050, 12, 31)  # T053: 2051 gets HTTP 400
MEASURES = pa.schema(
    [
        pa.field("cell_id", pa.string(), False),
        pa.field("date_local", pa.date32(), False),
        pa.field("model", pa.string(), False),
        pa.field("scenario", pa.string(), True),
        pa.field("bias_corrected", pa.bool_(), False),
        pa.field("rain_mm", pa.float64(), True),
        pa.field("tmax_c", pa.float64(), True),
    ]
)


def _json(raw: RawArtifact):
    try:
        return json.loads(raw.path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc


class S06:
    def __init__(
        self,
        state: str,
        points: Sequence[tuple[float, float]],
        start: date,
        end: date,
        models: Sequence[str] = MODELS,
        bias_corrected: bool = True,
        fetcher: Fetcher | None = None,
    ):
        if not points:
            raise ValueError("at least one (lat, lon) point")
        if not FIRST <= start <= end <= LAST:
            raise ValueError(f"dates must lie within {FIRST} to {LAST}")
        if not models or set(models) - set(MODELS):
            raise ValueError(f"models must be among {MODELS}")
        self.state, self.points, self.start, self.end = state, list(points), start, end
        self.models, self.bias_corrected, self.fetcher = list(models), bias_corrected, fetcher

    def params(self) -> dict[str, str]:
        params = {
            "latitude": ",".join(f"{lat:g}" for lat, _ in self.points),
            "longitude": ",".join(f"{lon:g}" for _, lon in self.points),
            "daily": ",".join(VARIABLES),
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
            "start_date": self.start.isoformat(),
            "end_date": self.end.isoformat(),
            "models": ",".join(self.models),
        }
        if not self.bias_corrected:
            params["disable_bias_correction"] = "true"
        return params

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        # shortcut: one request per call; long ranges count as many provider calls (T053 e04),
        # so callers split 1950-2050 pulls into chunks within the daily quota.
        return [
            self.fetcher.fetch_bytes(
                ctx, API, mapping_version=MAPPING_VERSION, params=self.params()
            )
        ]

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        body = _json(raw)
        locations = body if isinstance(body, list) else [body]
        if not locations or not all(isinstance(loc, dict) for loc in locations):
            raise IngestError(f"{SOURCE_ID}: empty or malformed climate response")

        cols: dict[str, list] = {k: [] for k in MEASURES.names}
        reasons, flags = [], []
        for loc in locations:
            units, daily = loc.get("daily_units", {}), loc.get("daily", {})
            expected = {"time": "iso8601"} | {
                f"{v}_{m}": unit for m in self.models for v, (_, unit) in VARIABLES.items()
            }
            if units != expected or set(daily) != set(expected):
                raise IngestError(f"{SOURCE_ID}: columns or units changed: {sorted(units)}")
            if loc.get("utc_offset_seconds") != 0:
                raise IngestError(f"{SOURCE_ID}: days are not GMT days")
            days = [date.fromisoformat(t) for t in daily["time"]]
            if any(len(v) != len(days) for v in daily.values()):
                raise IngestError(f"{SOURCE_ID}: daily arrays differ in length")
            cell = f"om_cmip6_{loc['latitude']:.4f}N_{loc['longitude']:.4f}E"
            for model in self.models:
                rain = daily[f"precipitation_sum_{model}"]
                tmax = daily[f"temperature_2m_max_{model}"]
                for i, day in enumerate(days):
                    r = None if rain[i] is None else float(rain[i])
                    t = None if tmax[i] is None else float(tmax[i])
                    if r is None or t is None:
                        # One reason per row: a model with no value that day (EC_Earth3P_HR, 2050).
                        reason, flag = "out_of_coverage", ["missing"]
                    elif r < 0:
                        reason, flag = "quality_rejected", ["out_of_range"]
                    else:
                        reason, flag = None, []
                    if reason:
                        r = t = None
                    cols["cell_id"].append(cell)
                    cols["date_local"].append(day)
                    cols["model"].append(model)
                    cols["scenario"].append(None)  # no scenario in the API (T053)
                    cols["bias_corrected"].append(self.bias_corrected)
                    cols["rain_mm"].append(r)
                    cols["tmax_c"].append(t)
                    reasons.append(reason)
                    flags.append(flag)

        n = len(cols["cell_id"])
        fetched = raw.fetched_at
        bias = "corrected" if self.bias_corrected else "raw"
        record_ids = [
            hashlib.sha256(f"{c}|{d.isoformat()}|{m}|{bias}".encode()).hexdigest()
            for c, d, m in zip(cols["cell_id"], cols["date_local"], cols["model"], strict=True)
        ]
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": record_ids,
            "snapshot_id": [f"{SOURCE_ID}-{bias}-{raw.sha256[:12]}"] * n,
            "observed_at": [None] * n,
            "valid_at": [
                datetime.combine(d + timedelta(days=1), time(), UTC) for d in cols["date_local"]
            ],
            "issued_at": [None] * n,  # a projection has no issue time
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [None] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["model"] * n,
            "quality_flags": flags,
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # CC BY 4.0 with attribution (T053 e03, e09)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": reasons,
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | cols, schema=schema)
        validate_table(table, measures=["rain_mm", "tmax_c"])
        mapping = {
            "precipitation_sum_<model>": "rain_mm",
            "temperature_2m_max_<model>": "tmax_c",
            "series suffix": "model",
            "daily.time": "date_local",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
