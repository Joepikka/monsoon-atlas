"""S10 adsb.lol live aircraft (T060). Field map: configs/sources/s10.yaml; rules: D108.

Community receiver reports, not an official air-traffic feed: never use for safety. The API's
"now" is milliseconds (T059 e10); a position's time is now minus seen_pos. Positions older than
300 s at fetch are dropped, LADD and PIA aircraft are dropped, and no callsign, registration or
owner data is stored. Units: feet and knots to metres and m/s (T059 e09).
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

SOURCE_ID = "S10"
API = "https://api.adsb.lol/v2/point"
HOSTS = {"api.adsb.lol"}
MAPPING_VERSION = "s10-v1"
LICENCE_ID = "odbl-1.0-adsb-lol"
MAX_AGE_S = 300  # plan: stale positions hidden after 5 minutes
PRIVATE_FLAGS = 4 | 8  # dbFlags PIA and LADD (T059 e09)
FT_TO_M, KT_TO_MS = 0.3048, 1852 / 3600
MEASURES = pa.schema(
    [
        pa.field("aircraft_id", pa.string(), False),
        pa.field("position_at", pa.timestamp("us", tz="UTC"), False),
        pa.field("lat", pa.float64(), True),
        pa.field("lon", pa.float64(), True),
        pa.field("altitude_m", pa.float64(), True),
        pa.field("speed_ms", pa.float64(), True),
        pa.field("on_ground", pa.bool_(), False),
        pa.field("position_type", pa.string(), False),
    ]
)


def _json(raw: RawArtifact):
    try:
        return json.loads(raw.path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc


class S10:
    def __init__(
        self,
        state: str,
        point: tuple[float, float],
        radius_nm: int = 100,
        fetcher: Fetcher | None = None,
    ):
        if not 0 < radius_nm <= 250:
            raise ValueError("radius_nm must be 1 to 250 (T059 e08)")
        self.state, self.point, self.radius_nm, self.fetcher = state, point, radius_nm, fetcher

    def url(self) -> str:
        lat, lon = self.point
        return f"{API}/{lat:g}/{lon:g}/{self.radius_nm}"

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        # The caller polls at most once per region every 300 s (plan cadence).
        return [self.fetcher.fetch_bytes(ctx, self.url(), mapping_version=MAPPING_VERSION)]

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        body = _json(raw)
        if not isinstance(body, dict) or not isinstance(body.get("ac"), list):
            raise IngestError(f"{SOURCE_ID}: empty or malformed aircraft response")
        if not isinstance(body.get("now"), int):
            raise IngestError(f"{SOURCE_ID}: response has no integer 'now'")
        now = datetime.fromtimestamp(body["now"] / 1000, UTC)
        if abs(now - raw.fetched_at) > timedelta(days=1):
            raise IngestError(f"{SOURCE_ID}: 'now' is not milliseconds near the fetch time")

        cols: dict[str, list] = {k: [] for k in MEASURES.names}
        for ac in body["ac"]:
            if not isinstance(ac, dict) or not ac.get("hex") or "type" not in ac:
                raise IngestError(f"{SOURCE_ID}: aircraft item lacks hex or type")
            if (ac.get("dbFlags") or 0) & PRIVATE_FLAGS:
                continue  # D108: LADD/PIA aircraft never leave the raw store
            pos = ac if ac.get("lat") is not None else ac.get("lastPosition") or {}
            lat, lon, age = pos.get("lat"), pos.get("lon"), pos.get("seen_pos")
            if lat is None or lon is None or age is None:
                continue  # no supplied position; nothing is predicted
            if not (-90 <= lat <= 90 and -180 <= lon <= 180) or age < 0:
                raise IngestError(f"{SOURCE_ID}: position out of range for {ac['hex']}")
            if age > MAX_AGE_S:
                continue  # stale at fetch time
            alt = ac.get("alt_baro")
            if isinstance(alt, str) and alt != "ground":
                raise IngestError(f"{SOURCE_ID}: unknown alt_baro value {alt!r}")
            gs = ac.get("gs")
            cols["aircraft_id"].append(ac["hex"])
            cols["position_at"].append(now - timedelta(seconds=age))
            cols["lat"].append(float(lat))
            cols["lon"].append(float(lon))
            cols["altitude_m"].append(None if alt in (None, "ground") else alt * FT_TO_M)
            cols["speed_ms"].append(None if gs is None else gs * KT_TO_MS)
            cols["on_ground"].append(alt == "ground")
            cols["position_type"].append(ac["type"])

        n, fetched = len(cols["aircraft_id"]), raw.fetched_at
        record_ids = [
            hashlib.sha256(f"{a}|{t.isoformat()}".encode()).hexdigest()
            for a, t in zip(cols["aircraft_id"], cols["position_at"], strict=True)
        ]
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": record_ids,
            "snapshot_id": [f"{SOURCE_ID}-{raw.sha256[:12]}"] * n,
            "observed_at": cols["position_at"],
            "valid_at": cols["position_at"],
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [now] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["inferred"] * n,  # D108: receiver reports, not official, not a model
            "quality_flags": [[] for _ in range(n)],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # ODbL 1.0 with attribution (T059 e02)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": [None] * n,
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | cols, schema=schema)
        validate_table(table, measures=["lat", "lon"])
        mapping = {
            "hex": "aircraft_id",
            "now - seen_pos": "position_at",
            "alt_baro (ft)": "altitude_m",
            "gs (kt)": "speed_ms",
            "type": "position_type",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
