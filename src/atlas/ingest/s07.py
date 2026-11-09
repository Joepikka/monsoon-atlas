"""S07 NASA POWER daily point (T056). Field map: configs/sources/s07.yaml.

POWER values are model and satellite estimates (provenance "model"), never station observations.
-999 (header fill_value) is missing, never a value. The header names the products behind a whole
request, not each day (T055), so fetch splits a date range until each response names at most one
meteorology and one solar product; parse refuses a response that still mixes them. Rain and
temperature share the row's missing_reason; solar lags months behind them, so it has its own
solar_missing_reason (the S32 pattern) instead of nulling good rain and temperature.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S07"
API = "https://power.larc.nasa.gov/api/temporal/daily/point"
HOSTS = {"power.larc.nasa.gov"}
MAPPING_VERSION = "s07-v1"
LICENCE_ID = "cc-by-4.0-nasa-power"
PAUSE_S = 3.0  # D106: documented API calls at least 3 seconds apart
FIRST = date(1981, 1, 1)  # T055 e03: daily data from 1981/01/01
# POWER parameter -> (canonical column, unit the AG community must return)
VARIABLES = {
    "PRECTOTCORR": ("rain_mm", "mm/day"),
    "T2M": ("tmean_c", "C"),
    "ALLSKY_SFC_SW_DWN": ("solar_mj_m2", "MJ/m^2/day"),
}
MET, SOLAR = {"MERRA2", "GEOSIT"}, {"SRB", "SYN1DEG"}  # products seen in T055 e16-e27
MEASURES = pa.schema(
    [
        pa.field("cell_id", pa.string(), False),
        pa.field("date_local", pa.date32(), False),
        pa.field("met_product", pa.string(), True),
        pa.field("solar_product", pa.string(), True),
        pa.field("api_version", pa.string(), False),
        pa.field("rain_mm", pa.float64(), True),
        pa.field("tmean_c", pa.float64(), True),
        pa.field("solar_mj_m2", pa.float64(), True),
        pa.field("solar_missing_reason", pa.string(), True),
    ]
)


def _json(raw: RawArtifact):
    try:
        return json.loads(raw.path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc


def products(header: dict) -> tuple[str | None, str | None, bool]:
    """(meteorology product, solar product, mixed) from a response header."""
    sources = set(header.get("sources") or [])
    unknown = sources - MET - SOLAR
    if unknown:
        raise IngestError(f"{SOURCE_ID}: unknown POWER products {sorted(unknown)}")
    met, solar = sorted(sources & MET), sorted(sources & SOLAR)
    mixed = len(met) > 1 or len(solar) > 1
    return (met[0] if len(met) == 1 else None), (solar[0] if len(solar) == 1 else None), mixed


class S07:
    def __init__(
        self,
        state: str,
        point: tuple[float, float],
        start: date,
        end: date,
        fetcher: Fetcher | None = None,
        pause: Callable[[float], None] = time.sleep,
    ):
        if not FIRST <= start <= end:
            raise ValueError(f"dates must start on or after {FIRST} and be in order")
        self.state, self.point, self.start, self.end = state, point, start, end
        self.fetcher, self.pause = fetcher, pause

    def params(self, start: date, end: date) -> dict[str, str]:
        lat, lon = self.point
        return {
            "parameters": ",".join(VARIABLES),
            "community": "AG",  # MJ/m^2/day for shortwave (RE gives kW-hr/m^2/day, T055 e17)
            "longitude": f"{lon:g}",
            "latitude": f"{lat:g}",
            "start": f"{start:%Y%m%d}",
            "end": f"{end:%Y%m%d}",
            "format": "JSON",
            "time-standard": "UTC",
        }

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """One artifact per date range whose header names one product per family."""
        out: list[RawArtifact] = []
        pending, calls = [(self.start, self.end)], 0
        while pending:
            start, end = pending.pop(0)
            if calls:
                self.pause(PAUSE_S)
            calls += 1
            raw = self.fetcher.fetch_bytes(
                ctx, API, mapping_version=MAPPING_VERSION, params=self.params(start, end)
            )
            *_, mixed = products(_json(raw).get("header", {}))
            if not mixed:
                out.append(raw)
            elif start == end:
                raise IngestError(f"{SOURCE_ID}: {start} names two products of one family")
            else:
                mid = start + (end - start) // 2
                pending[:0] = [(start, mid), (mid + timedelta(days=1), end)]
        return out

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        body = _json(raw)
        if not isinstance(body, dict) or not body.get("properties", {}).get("parameter"):
            raise IngestError(f"{SOURCE_ID}: empty or malformed POWER response")
        header, values = body.get("header", {}), body["properties"]["parameter"]
        met, solar, mixed = products(header)
        if mixed:
            raise IngestError(f"{SOURCE_ID}: response mixes products {header['sources']}; split it")
        units = {k: v.get("units") for k, v in body.get("parameters", {}).items()}
        if units != {k: unit for k, (_, unit) in VARIABLES.items()} or set(values) != set(
            VARIABLES
        ):
            raise IngestError(f"{SOURCE_ID}: parameters or units changed: {units}")
        version = header.get("api", {}).get("version")
        if header.get("time_standard") != "UTC" or "fill_value" not in header or not version:
            raise IngestError(f"{SOURCE_ID}: header lacks UTC time standard, fill value or version")
        fill = header["fill_value"]
        keys = list(values["PRECTOTCORR"])
        if any(list(v) != keys for v in values.values()):
            raise IngestError(f"{SOURCE_ID}: parameters cover different days")
        lon, lat, *_ = body["geometry"]["coordinates"]
        cell = f"power_{lat:.4f}N_{lon:.4f}E"

        def decoded(name: str) -> list[float | None]:
            return [None if values[name][k] == fill else float(values[name][k]) for k in keys]

        rain, tmean, sun = decoded("PRECTOTCORR"), decoded("T2M"), decoded("ALLSKY_SFC_SW_DWN")
        days = [datetime.strptime(k, "%Y%m%d").date() for k in keys]
        newest_met = max(
            (d for d, r, t in zip(days, rain, tmean, strict=True) if None not in (r, t)),
            default=None,
        )
        newest_sun = max((d for d, s in zip(days, sun, strict=True) if s is not None), default=None)

        def lag_reason(day: date, newest: date | None) -> str:
            return "not_yet_available" if newest is None or day > newest else "out_of_coverage"

        reasons, flags, solar_reasons = [], [], []
        for i, day in enumerate(days):
            if rain[i] is None or tmean[i] is None:
                reason, flag = lag_reason(day, newest_met), ["missing"]
            elif rain[i] < 0:
                reason, flag = "quality_rejected", ["out_of_range"]
            else:
                reason, flag = None, []
            if reason:
                rain[i] = tmean[i] = None
            if sun[i] is None:
                solar_reasons.append(lag_reason(day, newest_sun))
            elif sun[i] < 0:
                sun[i] = None
                solar_reasons.append("quality_rejected")
            else:
                solar_reasons.append(None)
            reasons.append(reason)
            flags.append(flag)

        n, fetched = len(days), raw.fetched_at
        record_ids = [
            hashlib.sha256(f"{cell}|{d.isoformat()}|{met}|{solar}".encode()).hexdigest()
            for d in days
        ]
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": record_ids,
            "snapshot_id": [f"{SOURCE_ID}-{raw.sha256[:12]}"] * n,
            "observed_at": [None] * n,
            "valid_at": [
                datetime.combine(d + timedelta(days=1), datetime.min.time(), UTC) for d in days
            ],
            "issued_at": [None] * n,
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
            "redistribution_allowed": [True] * n,  # no use restrictions, cite POWER (T055 e29)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": reasons,
        }
        measures = {
            "cell_id": [cell] * n,
            "date_local": days,
            "met_product": [met] * n,
            "solar_product": [solar] * n,
            "api_version": [version] * n,
            "rain_mm": rain,
            "tmean_c": tmean,
            "solar_mj_m2": sun,
            "solar_missing_reason": solar_reasons,
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table, measures=["rain_mm", "tmean_c"])
        mapping = {k: c for k, (c, _) in VARIABLES.items()} | {"parameter keys": "date_local"}
        return with_mapping(table, mapping, MAPPING_VERSION)
