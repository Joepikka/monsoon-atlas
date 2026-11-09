"""S12 CelesTrak orbit elements (T064). Field map: configs/sources/s12.yaml; rules: D109.

OMM JSON, not TLE: TLE cannot carry the 6-digit catalog numbers in use since July 2026, so
tle_line1/tle_line2 stay null. CelesTrak asks machine clients to download once per 2-hour update
and to stop on any non-200 response, so fetch refuses a Fetcher that retries. Element sets older
than 7 days are flagged stale (hidden on the map). Rows are the published elements; positions
propagated from them are a separate, inferred product.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S12"
API = "https://celestrak.org/NORAD/elements/gp.php"
HOSTS = {"celestrak.org"}
MAPPING_VERSION = "s12-v1"
LICENCE_ID = "celestrak-no-licence-published"
MAX_AGE = timedelta(days=7)
GROUP = re.compile(r"^[a-z0-9-]+$", re.IGNORECASE)
# OMM key -> (column, arrow type); all are required in every object (T063 e08)
OMM = {
    "NORAD_CAT_ID": ("norad_id", pa.int64()),
    "OBJECT_NAME": ("name", pa.string()),
    "OBJECT_ID": ("object_id", pa.string()),
    "EPOCH": ("epoch_at", pa.timestamp("us", tz="UTC")),
    "MEAN_MOTION": ("mean_motion_rev_day", pa.float64()),
    "ECCENTRICITY": ("eccentricity", pa.float64()),
    "INCLINATION": ("inclination_deg", pa.float64()),
    "RA_OF_ASC_NODE": ("raan_deg", pa.float64()),
    "ARG_OF_PERICENTER": ("arg_pericenter_deg", pa.float64()),
    "MEAN_ANOMALY": ("mean_anomaly_deg", pa.float64()),
    "BSTAR": ("bstar", pa.float64()),
    "MEAN_MOTION_DOT": ("mean_motion_dot", pa.float64()),
    "MEAN_MOTION_DDOT": ("mean_motion_ddot", pa.float64()),
    "ELEMENT_SET_NO": ("element_set_no", pa.int64()),
    "REV_AT_EPOCH": ("rev_at_epoch", pa.int64()),
    "CLASSIFICATION_TYPE": ("classification", pa.string()),
    "EPHEMERIS_TYPE": ("ephemeris_type", pa.int64()),
}
MEASURES = pa.schema(
    [
        pa.field("norad_id", pa.int64(), False),
        pa.field("epoch_at", pa.timestamp("us", tz="UTC"), False),
        pa.field("tle_line1", pa.string(), True),
        pa.field("tle_line2", pa.string(), True),
        pa.field("name", pa.string(), False),
        *(
            pa.field(col, typ, False)
            for key, (col, typ) in OMM.items()
            if col not in ("norad_id", "epoch_at", "name")
        ),
    ]
)


def _json(raw: RawArtifact):
    try:
        return json.loads(raw.path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc


class S12:
    def __init__(self, state: str, group: str = "stations", fetcher: Fetcher | None = None):
        if not GROUP.match(group):
            raise ValueError("group must be a CelesTrak GROUP name such as stations")
        self.state, self.group, self.fetcher = state, group, fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        if self.fetcher is None or self.fetcher.retry_delays:
            raise ValueError("CelesTrak forbids retries: use Fetcher(..., retry_delays=()) (D109)")
        # The caller fetches each group at most once per 2-hour update (T063 e05).
        params = {"GROUP": self.group, "FORMAT": "json"}
        return [self.fetcher.fetch_bytes(ctx, API, mapping_version=MAPPING_VERSION, params=params)]

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        body = _json(raw)
        if not isinstance(body, list) or not body or not all(isinstance(o, dict) for o in body):
            raise IngestError(f"{SOURCE_ID}: empty or malformed OMM response")
        cols: dict[str, list] = {f.name: [] for f in MEASURES}
        flags = []
        for obj in body:
            missing = set(OMM) - set(obj)
            if missing:
                raise IngestError(f"{SOURCE_ID}: OMM object lacks {sorted(missing)}")
            epoch = datetime.fromisoformat(obj["EPOCH"]).replace(tzinfo=UTC)
            ecc, inc, mm = obj["ECCENTRICITY"], obj["INCLINATION"], obj["MEAN_MOTION"]
            if not (0 <= ecc < 1 and 0 <= inc <= 180 and mm > 0):
                raise IngestError(f"{SOURCE_ID}: elements out of range for {obj['NORAD_CAT_ID']}")
            for key, (col, _) in OMM.items():
                cols[col].append(epoch if key == "EPOCH" else obj[key])
            cols["tle_line1"].append(None)  # D109: TLE cannot carry 6-digit catalog numbers
            cols["tle_line2"].append(None)
            flags.append(["stale"] if raw.fetched_at - epoch > MAX_AGE else [])

        n, fetched = len(body), raw.fetched_at
        record_ids = [
            hashlib.sha256(f"{i}|{e.isoformat()}|{s}".encode()).hexdigest()
            for i, e, s in zip(
                cols["norad_id"], cols["epoch_at"], cols["element_set_no"], strict=True
            )
        ]
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": record_ids,
            "snapshot_id": [f"{SOURCE_ID}-{self.group}-{raw.sha256[:12]}"] * n,
            "observed_at": [None] * n,
            "valid_at": cols["epoch_at"],
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [None] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["official"] * n,  # 18 SDS element sets as published
            "quality_flags": flags,
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [False] * n,  # D109: no licence published
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": [None] * n,
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | cols, schema=schema)
        validate_table(table)
        return with_mapping(table, {k: c for k, (c, _) in OMM.items()}, MAPPING_VERSION)
