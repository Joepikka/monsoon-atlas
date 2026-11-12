"""S19 Google Open Buildings v3 (T070). Field map: configs/sources/s19.yaml.

Polygons come as one gzipped CSV per S2 level-4 cell; Karnataka's cell 3bb is 4.8 GB (T069 e02),
so fetch resolves the cell's URL from the published index and streams the file to disk
(Fetcher.fetch_large). parse_batches reads it row by row, keeps buildings whose centroid lies in
the requested box, drops duplicate Plus Codes and yields bounded tables, so the whole state never
sits in memory. Geometry only: no owners, residents or building use exist or are added. CC BY 4.0
branch of the dual licence.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections.abc import Iterator

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S19"
RELEASE = "open-buildings-v3"
INDEX = "https://openbuildings-public-dot-gweb-research.uw.r.appspot.com/public/tiles.geojson"
HOSTS = {"openbuildings-public-dot-gweb-research.uw.r.appspot.com", "storage.googleapis.com"}
COLUMNS = ["latitude", "longitude", "area_in_meters", "confidence", "geometry", "full_plus_code"]
MIN_CONFIDENCE, DISPLAY_CONFIDENCE = 0.65, 0.75  # documented range start; map default (T069)
MAPPING_VERSION = "s19-v1"
LICENCE_ID = "cc-by-4.0-google-open-buildings"
MEASURES = pa.schema(
    [
        pa.field("building_id", pa.string(), False),
        pa.field("source_release", pa.string(), False),
        pa.field("geometry", pa.binary(), False),
        pa.field("area_m2", pa.float64(), True),
        pa.field("confidence", pa.float64(), True),
        pa.field("plus_code", pa.string(), False),
    ]
)
Box = tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat


class S19:
    def __init__(
        self, state: str, cells: tuple[str, ...] = ("3bb",), fetcher: Fetcher | None = None
    ):
        self.state, self.cells, self.fetcher = state, cells, fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """[index, one streamed shard per cell]; shard URLs come only from the published index."""
        index = self.fetcher.fetch_bytes(ctx, INDEX, mapping_version=MAPPING_VERSION)
        try:
            urls = {
                f["properties"]["tile_id"]: f["properties"]["tile_url"]
                for f in json.loads(index.path.read_bytes())["features"]
            }
        except (ValueError, KeyError, TypeError) as exc:
            raise IngestError(f"{SOURCE_ID}: malformed tile index") from exc
        missing = [c for c in self.cells if c not in urls]
        if missing:
            raise IngestError(f"{SOURCE_ID}: cells not in the index: {missing}")
        shards = [
            self.fetcher.fetch_large(ctx, urls[c], mapping_version=MAPPING_VERSION)
            for c in self.cells
        ]
        return [index, *shards]

    def parse_batches(
        self, raw: RawArtifact, config: SourceConfig, *, box: Box, batch_rows: int = 200_000
    ) -> Iterator[pa.Table]:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        import shapely  # geo lock (D35)

        csv.field_size_limit(2**31 - 1)
        min_lon, min_lat, max_lon, max_lat = box
        seen: set[str] = set()
        rows: list[dict] = []
        try:
            with gzip.open(raw.path, "rt", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                if next(reader, None) != COLUMNS:
                    raise IngestError(f"{SOURCE_ID}: columns changed in {raw.source_url}")
                for record in reader:
                    if len(record) != len(COLUMNS):
                        raise IngestError(f"{SOURCE_ID}: malformed row in {raw.source_url}")
                    lat, lon, area, conf, wkt, code = record
                    lat, lon = float(lat), float(lon)
                    if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
                        continue
                    if code in seen:
                        continue  # duplicate within the release
                    conf, area = float(conf), float(area)
                    if not MIN_CONFIDENCE <= conf <= 1 or area <= 0:
                        raise IngestError(
                            f"{SOURCE_ID}: confidence or area out of range for {code}"
                        )
                    seen.add(code)
                    rows.append({"code": code, "wkt": wkt, "area": area, "conf": conf})
                    if len(rows) >= batch_rows:
                        yield self._table(raw, rows, shapely)
                        rows = []
        except (OSError, EOFError, ValueError, csv.Error) as exc:
            raise IngestError(f"{SOURCE_ID}: unreadable shard {raw.source_url}: {exc}") from exc
        if rows or not seen:
            yield self._table(raw, rows, shapely)

    def parse(self, raw: RawArtifact, config: SourceConfig, *, box: Box) -> pa.Table:
        """All rows in the box as one table (for small inputs; use parse_batches for a state)."""
        return pa.concat_tables(list(self.parse_batches(raw, config, box=box)))

    def _table(self, raw: RawArtifact, rows: list[dict], shapely) -> pa.Table:
        try:
            geoms = shapely.from_wkt([r["wkt"] for r in rows])
        except Exception as exc:  # shapely raises GEOSException subclasses
            raise IngestError(f"{SOURCE_ID}: invalid WKT in {raw.source_url}") from exc
        n, fetched = len(rows), raw.fetched_at
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"{RELEASE}|{r['code']}".encode()).hexdigest() for r in rows
            ],
            "snapshot_id": [f"{SOURCE_ID}-{RELEASE}-{raw.sha256[:12]}"] * n,
            "observed_at": [None] * n,
            "valid_at": [None] * n,  # one static release; rows carry no image dates (T069)
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [None] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["model"] * n,  # detected by a model from imagery
            "quality_flags": [[] for _ in range(n)],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # CC BY 4.0 branch, credit Google Research
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": [None] * n,
        }
        measures = {
            "building_id": [r["code"] for r in rows],
            "source_release": [RELEASE] * n,
            "geometry": list(shapely.to_wkb(geoms)) if n else [],
            "area_m2": [r["area"] for r in rows],
            "confidence": [r["conf"] for r in rows],
            "plus_code": [r["code"] for r in rows],
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table, measures=["area_m2", "confidence"])
        mapping = {
            "full_plus_code": "building_id, plus_code",
            "geometry (WKT)": "geometry (WKB)",
            "area_in_meters": "area_m2",
            "confidence": "confidence",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
