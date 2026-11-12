"""S05 Open-Meteo ensemble (T052). Field map: configs/sources/s05.yaml.

One row per grid cell, hour and member. The member count is read from each response, never
assumed (T051: IFS 0.25 has 51 series, other products differ). The response carries no run time
and can mix runs: hours before the run's initialisation or at/after its data_end_time belong to
another run (T051 e07 to e09), so they are kept as null rows, never given this run's issue time.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.s01 import SETTLE  # same Model Updates page advice (T051 e05)

SOURCE_ID = "S05"
API = "https://ensemble-api.open-meteo.com"
HOSTS = {"ensemble-api.open-meteo.com"}
MODEL = "ecmwf_ifs025_ensemble"  # the only product whose metadata URL T051 verified
META_URL = f"{API}/data/{MODEL}/static/meta.json"
MAPPING_VERSION = "s05-v1"
LICENCE_ID = "cc-by-4.0-open-meteo"
# provider variable -> (canonical column, unit the request asks for and the response must echo)
VARIABLES = {"precipitation": ("rain_mm", "mm"), "temperature_2m": ("temperature_c", "°C")}
UNITS = {"temperature_unit": "celsius", "precipitation_unit": "mm", "timezone": "GMT"}
MEMBER = re.compile(r"^(?P<var>[a-z0-9_]+?)(?:_member(?P<n>\d{2}))?$")
MEASURES = pa.schema(
    [
        pa.field("cell_id", pa.string(), False),
        pa.field("member_id", pa.string(), False),
        pa.field("model", pa.string(), False),
        pa.field("rain_mm", pa.float64(), True),
        pa.field("temperature_c", pa.float64(), True),
    ]
)


def _json(raw: RawArtifact):
    try:
        return json.loads(raw.path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc


def _members(hourly: dict, units: dict) -> list[str]:
    """Member IDs ("00" for the unsuffixed series); every variable must have the same set."""
    found: dict[str, set[str]] = {v: set() for v in VARIABLES}
    for key in hourly:
        if key == "time":
            continue
        m = MEMBER.match(key)
        if not m or m["var"] not in VARIABLES or units.get(key) != VARIABLES[m["var"]][1]:
            raise IngestError(f"{SOURCE_ID}: columns or units changed: {key}={units.get(key)}")
        found[m["var"]].add(m["n"] or "00")
    sets = list(found.values())
    if not sets[0] or any(s != sets[0] for s in sets) or units.get("time") != "iso8601":
        raise IngestError(f"{SOURCE_ID}: member series differ between variables or are missing")
    return sorted(sets[0])


class S05:
    def __init__(
        self,
        state: str,
        points: Sequence[tuple[float, float]],
        fetcher: Fetcher | None = None,
        forecast_days: int = 15,
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
            **UNITS,
            "forecast_days": str(self.forecast_days),
            "models": MODEL,
        }

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """[metadata, forecast]; raises if the model run changed during the call."""
        before = self.fetcher.fetch_bytes(ctx, META_URL, mapping_version=MAPPING_VERSION)
        forecast = self.fetcher.fetch_bytes(
            ctx, f"{API}/v1/ensemble", mapping_version=MAPPING_VERSION, params=self.params()
        )
        after = self.fetcher.fetch_bytes(ctx, META_URL, mapping_version=MAPPING_VERSION)
        run = "last_run_initialisation_time"
        if _json(before).get(run) != _json(after).get(run):
            raise IngestError(f"{SOURCE_ID}: {MODEL} run changed during the fetch; retry")
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
            end = datetime.fromtimestamp(info["data_end_time"], UTC)  # exclusive
        except (KeyError, TypeError) as exc:
            raise IngestError(f"{SOURCE_ID}: model metadata lacks run times") from exc
        body = _json(raw)
        locations = body if isinstance(body, list) else [body]
        if not locations or not all(isinstance(loc, dict) for loc in locations):
            raise IngestError(f"{SOURCE_ID}: empty or malformed ensemble response")

        cols: dict[str, list] = {k: [] for k in ("valid_at", "issued_at", *MEASURES.names)}
        reasons, flags = [], []
        for loc in locations:
            hourly, units = loc.get("hourly", {}), loc.get("hourly_units", {})
            if "time" not in hourly:
                raise IngestError(f"{SOURCE_ID}: no hourly times")
            members = _members(hourly, units)
            if loc.get("utc_offset_seconds") != 0:
                raise IngestError(f"{SOURCE_ID}: times are not UTC")
            times = [datetime.fromisoformat(t).replace(tzinfo=UTC) for t in hourly["time"]]
            if any(len(v) != len(times) for v in hourly.values()):
                raise IngestError(f"{SOURCE_ID}: hourly arrays differ in length")
            cell = f"om_{MODEL}_{loc['latitude']:.4f}N_{loc['longitude']:.4f}E"
            for member in members:
                suffix = "" if member == "00" else f"_member{member}"
                rain = hourly[f"precipitation{suffix}"]
                temp = hourly[f"temperature_2m{suffix}"]
                for i, valid in enumerate(times):
                    r = None if rain[i] is None else float(rain[i])
                    t = None if temp[i] is None else float(temp[i])
                    in_run = issued <= valid < end
                    if not in_run:
                        # Another run's hour (T051): keep the row, never this run's issue time.
                        reason, flag = "out_of_coverage", ["missing", "stale"]
                    elif r is None or t is None:
                        reason, flag = "out_of_coverage", ["missing"]
                    elif r < 0:
                        reason, flag = "quality_rejected", ["out_of_range"]
                    else:
                        reason, flag = None, []
                    if reason:
                        r = t = None
                    cols["valid_at"].append(valid)
                    cols["issued_at"].append(issued if in_run else None)
                    cols["cell_id"].append(cell)
                    cols["member_id"].append(member)
                    cols["model"].append(MODEL)
                    cols["rain_mm"].append(r)
                    cols["temperature_c"].append(t)
                    reasons.append(reason)
                    flags.append(flag)

        n = len(cols["cell_id"])
        fetched = raw.fetched_at
        snapshot = f"{SOURCE_ID}-{MODEL}-{issued:%Y%m%dT%H%MZ}-{raw.sha256[:12]}"
        record_ids = [
            hashlib.sha256(
                f"{c}|{v.isoformat()}|{MODEL}|{issued.isoformat()}|{m}".encode()
            ).hexdigest()
            for c, v, m in zip(cols["cell_id"], cols["valid_at"], cols["member_id"], strict=True)
        ]
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": record_ids,
            "snapshot_id": [snapshot] * n,
            "observed_at": [None] * n,
            "valid_at": cols["valid_at"],
            "issued_at": cols["issued_at"],
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
            "redistribution_allowed": [True] * n,  # CC BY 4.0 with attribution (T051 e03)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": reasons,
        }
        measures = {name: cols[name] for name in MEASURES.names}
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table, measures=["rain_mm", "temperature_c"])
        mapping = {
            "precipitation[_memberNN]": "rain_mm",
            "temperature_2m[_memberNN]": "temperature_c",
            "series suffix": "member_id",
            "hourly.time": "valid_at",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
