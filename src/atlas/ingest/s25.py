"""S25 NASA FIRMS active fires (T076). Field map: configs/sources/s25.yaml.

The area API takes the owner's MAP_KEY (H09, `NASA_FIRMS_MAP_KEY`) as a path segment:
/api/area/csv/MAP_KEY/SOURCE/W,S,E,N/DAYS. Recorded URLs keep the literal segment `MAP_KEY`;
`KeyPathFetcher` substitutes the key only into the outgoing request, so the key never reaches the
raw ledger, artifacts, manifests or logs written by this project. A hotspot is a satellite thermal
anomaly, never a confirmed (structure) fire. Rows are deduplicated on satellite, acquisition time
and position, and each carries its detection latency (fetch time minus acquisition time).
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import UTC, datetime

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import FetchError, IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S25"
HOST = "firms.modaps.eosdis.nasa.gov"
BASE = f"https://{HOST}/api"
KEY_SEGMENT = "MAP_KEY"
PRODUCT = "VIIRS_NOAA20_NRT"
MAPPING_VERSION = "s25-v1"
LICENCE_ID = "nasa-firms-open"
COLUMNS = [
    "latitude",
    "longitude",
    "bright_ti4",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_ti5",
    "frp",
    "daynight",
]
CONFIDENCE = {"l": "low", "n": "nominal", "h": "high"}
MEASURES = pa.schema(
    [
        pa.field("detection_id", pa.string(), False),
        pa.field("acquired_at", pa.timestamp("us", tz="UTC"), False),
        pa.field("lat", pa.float64(), False),
        pa.field("lon", pa.float64(), False),
        pa.field("confidence", pa.string(), False),
        pa.field("frp_mw", pa.float64(), True),
        pa.field("sensor", pa.string(), False),
        pa.field("latency_minutes", pa.float64(), False),
    ]
)
Box = tuple[float, float, float, float]  # west, south, east, north


class KeyPathFetcher(Fetcher):
    """Puts the secret into the `/MAP_KEY/` path segment of the request only."""

    def _request(self, ctx, public_url, secrets, headers):
        secrets = dict(secrets)
        key = secrets.pop(KEY_SEGMENT, None)
        segment = f"/{KEY_SEGMENT}/"
        if key is None or segment not in public_url:
            return super()._request(ctx, public_url, secrets, headers)
        real = public_url.replace(segment, f"/{key}/", 1)
        status, body, resp_headers, final = super()._request(ctx, real, secrets, headers)
        if final != real:  # a redirect target could carry the key; refuse rather than record it
            raise FetchError(f"{ctx.source_id}: unexpected redirect from the FIRMS API")
        return status, body, resp_headers, public_url


def area_url(box: Box, days: int, product: str = PRODUCT) -> str:
    if not 1 <= days <= 5:
        raise ValueError("FIRMS area requests cover 1 to 5 days")
    w, s, e, n = box
    return f"{BASE}/area/csv/{KEY_SEGMENT}/{product}/{w:g},{s:g},{e:g},{n:g}/{days}"


class S25:
    def __init__(self, state: str = "ka", fetcher: Fetcher | None = None):
        self.state, self.fetcher = state, fetcher

    def fetch(self, ctx: FetchContext, *, box: Box, days: int = 1) -> list[RawArtifact]:
        if self.fetcher is None:
            raise SourceUnavailable(f"{SOURCE_ID}: no fetcher configured")
        if "NASA_FIRMS_MAP_KEY" not in ctx.secrets:
            raise SourceUnavailable(f"{SOURCE_ID}: NASA_FIRMS_MAP_KEY is not configured (H09)")
        art = self.fetcher.fetch_bytes(
            ctx,
            area_url(box, days),
            mapping_version=MAPPING_VERSION,
            secret_params={KEY_SEGMENT: "NASA_FIRMS_MAP_KEY"},
        )
        return [art]

    def parse(self, raw: RawArtifact, config: SourceConfig, *, area_wkb: bytes) -> pa.Table:
        """Detections whose position lies in the state polygon, one row per detection."""
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        import shapely

        area = shapely.from_wkb(area_wkb)
        shapely.prepare(area)
        try:
            text = raw.path.read_text("utf-8")
        except (OSError, UnicodeError) as exc:
            raise IngestError(f"{SOURCE_ID}: unreadable response {raw.source_url}") from exc
        if not text.strip():
            raise IngestError(f"{SOURCE_ID}: empty response {raw.source_url}")
        reader = csv.reader(io.StringIO(text))
        if next(reader) != COLUMNS:
            raise IngestError(f"{SOURCE_ID}: columns changed in {raw.source_url}")
        rows, seen = [], set()
        for rec in reader:
            if len(rec) != len(COLUMNS):
                raise IngestError(f"{SOURCE_ID}: malformed row in {raw.source_url}")
            r = dict(zip(COLUMNS, rec, strict=True))
            try:
                lat, lon = float(r["latitude"]), float(r["longitude"])
                acquired = datetime.strptime(
                    f"{r['acq_date']} {int(r['acq_time']):04d}", "%Y-%m-%d %H%M"
                ).replace(tzinfo=UTC)
                frp = float(r["frp"]) if r["frp"] else None
            except ValueError as exc:
                raise IngestError(f"{SOURCE_ID}: bad value in {raw.source_url}: {exc}") from exc
            if r["confidence"] not in CONFIDENCE:
                raise IngestError(f"{SOURCE_ID}: unknown confidence {r['confidence']!r}")
            if not area.contains(shapely.Point(lon, lat)):
                continue
            key = f"{r['satellite']}|{acquired:%Y-%m-%dT%H:%M}|{lat:.5f}|{lon:.5f}"
            if key in seen:
                continue  # the same detection repeated across requests or rows
            seen.add(key)
            rows.append(
                {
                    "id": hashlib.sha256(key.encode()).hexdigest(),
                    "acquired": acquired,
                    "lat": lat,
                    "lon": lon,
                    "confidence": CONFIDENCE[r["confidence"]],
                    "frp": frp,
                    "sensor": r["satellite"],
                    "latency": (raw.fetched_at - acquired).total_seconds() / 60,
                }
            )
        return self._table(raw, rows)

    def _table(self, raw: RawArtifact, rows: list[dict]) -> pa.Table:
        n, fetched = len(rows), raw.fetched_at
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [r["id"] for r in rows],
            "snapshot_id": [f"{SOURCE_ID}-{raw.sha256[:12]}"] * n,
            "observed_at": [r["acquired"] for r in rows],
            "valid_at": [r["acquired"] for r in rows],
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [None] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["model"] * n,  # detected by an algorithm from satellite radiances
            "quality_flags": [[] for _ in range(n)],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # NASA open data; credit FIRMS, LANCE, ESDIS
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": [None if r["frp"] is not None else "not_reported" for r in rows],
        }
        measures = {
            "detection_id": [r["id"] for r in rows],
            "acquired_at": [r["acquired"] for r in rows],
            "lat": [r["lat"] for r in rows],
            "lon": [r["lon"] for r in rows],
            "confidence": [r["confidence"] for r in rows],
            "frp_mw": [r["frp"] for r in rows],
            "sensor": [r["sensor"] for r in rows],
            "latency_minutes": [r["latency"] for r in rows],
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table, measures=["frp_mw"])
        mapping = {
            "satellite + acq_date + acq_time + latitude + longitude": "detection_id",
            "acq_date + acq_time (UTC)": "acquired_at",
            "latitude": "lat",
            "longitude": "lon",
            "confidence (l/n/h)": "confidence",
            "frp (MW)": "frp_mw",
            "satellite": "sensor",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
