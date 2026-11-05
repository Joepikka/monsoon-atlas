"""S16 WorldPop India population (T018). Field map: configs/sources/s16.yaml.

Pixels are people counts (T017 e03). Clipping keeps native cells whose centre lies in the state
polygon from S17 ADM1; nothing is resampled, so the state total is exactly the sum of the kept
cells. Needs rasterio (geo lock), imported on use so the core install can import this module.
"""

from __future__ import annotations

import hashlib
import json
import re

import numpy as np
import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S16"
CATALOGUE = "https://hub.worldpop.org/rest/data/pop/G2_CN_POP_R25A_1km"
HOSTS = {"hub.worldpop.org", "data.worldpop.org"}
MAPPING_VERSION = "s16-v1"
LICENCE_ID = "cc-by-4.0-worldpop"
RESOLUTION_M = 1000  # nominal, as WorldPop states for 30 arc seconds (T017 e03)
STATE_ISO = {"ka": "IN-KA", "kl": "IN-KL", "dl": "IN-DL"}
FILE = re.compile(r"/(R\d{4}[A-Z])/(\d{4})/([A-Z]{3})/v\d+/1km_ua/constrained/[^/]+\.tif$")
MEASURES = pa.schema(
    [
        pa.field("raster_id", pa.string(), False),
        pa.field("reference_year", pa.int64(), False),
        pa.field("cell_id", pa.string(), False),
        pa.field("population", pa.float64(), False),
        pa.field("resolution_m", pa.int64(), False),
    ]
)


class S16:
    def __init__(self, state: str, year: int, fetcher: Fetcher | None = None):
        if state not in STATE_ISO:
            raise SourceUnavailable(f"{SOURCE_ID}: unknown state {state}")
        self.state, self.year, self.fetcher = state, year, fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """[catalogue entries, the year's GeoTIFF], following the catalogue's file link."""
        listing = self.fetcher.fetch_bytes(
            ctx, CATALOGUE, mapping_version=MAPPING_VERSION, params={"iso3": "IND"}
        )
        entries = json.loads(listing.path.read_bytes()).get("data", [])
        files = [e["files"][0] for e in entries if e.get("popyear") == str(self.year)]
        if len(files) != 1:
            raise IngestError(f"{SOURCE_ID}: no single file for {self.year}")
        return [listing, self.fetcher.fetch_bytes(ctx, files[0], mapping_version=MAPPING_VERSION)]

    def parse(
        self, raw: RawArtifact, config: SourceConfig, *, boundary: RawArtifact | None = None
    ) -> pa.Table:
        """Cells of the state; `boundary` is the S17 ADM1 GeoJSON that holds the state polygon."""
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        if boundary is None:
            raise IngestError(f"{SOURCE_ID}: clipping needs the S17 ADM1 boundary file")
        match = FILE.search(raw.source_url)
        if not match:
            raise IngestError(f"{SOURCE_ID}: unexpected file URL {raw.source_url}")
        release, year, iso3 = match.group(1), int(match.group(2)), match.group(3)
        try:
            states = json.loads(boundary.path.read_bytes())["features"]
        except (ValueError, KeyError) as exc:
            raise IngestError(f"{SOURCE_ID}: boundary is not ADM1 GeoJSON") from exc
        shapes = [
            f["geometry"]
            for f in states
            if f["properties"].get("shapeISO") == STATE_ISO[self.state]
        ]
        if len(shapes) != 1:
            raise IngestError(f"{SOURCE_ID}: expected one polygon for {STATE_ISO[self.state]}")

        import rasterio  # geo lock
        from rasterio.errors import RasterioIOError
        from rasterio.features import geometry_mask
        from rasterio.windows import from_bounds

        try:
            src = rasterio.open(raw.path)
        except RasterioIOError as exc:
            raise IngestError(f"{SOURCE_ID}: not a readable GeoTIFF") from exc
        with src:
            if src.count != 1 or src.dtypes[0] != "float32" or src.crs.to_epsg() != 4326:
                raise IngestError(f"{SOURCE_ID}: bands, type or CRS changed")
            from shapely.geometry import shape

            bounds = shape(shapes[0]).bounds
            window = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
            try:
                data = src.read(1, window=window)
            except RasterioIOError as exc:
                raise IngestError(f"{SOURCE_ID}: GeoTIFF tiles cannot be read") from exc
            transform = src.window_transform(window)
            nodata = src.nodata
        outside = geometry_mask([shapes[0]], data.shape, transform, all_touched=False)
        keep = ~outside & (data != nodata) & np.isfinite(data)
        if (data[keep] < 0).any():
            raise IngestError(f"{SOURCE_ID}: negative population counts")
        rows, cols = np.nonzero(keep)
        values = data[rows, cols].astype(np.float64)
        row0, col0 = int(window.row_off), int(window.col_off)
        cells = [f"wp1km_r{row0 + r}_c{col0 + c}" for r, c in zip(rows, cols, strict=True)]

        n, fetched = len(cells), raw.fetched_at
        raster_id = f"WP00840-{release}-{year}-{iso3}-1km"
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"{raster_id}|{c}|{raw.sha256}".encode()).hexdigest() for c in cells
            ],
            "snapshot_id": [f"{SOURCE_ID}-{raster_id}"] * n,
            "observed_at": [None] * n,
            "valid_at": [None] * n,
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [None] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["model"]
            * n,  # dasymetric estimate; years after the release are projections
            "quality_flags": [[] for _ in range(n)],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # CC BY 4.0 with citation (T017 e04)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": [None] * n,
        }
        measures = {
            "raster_id": [raster_id] * n,
            "reference_year": [year] * n,
            "cell_id": cells,
            "population": pa.array(values, pa.float64()),
            "resolution_m": [RESOLUTION_M] * n,
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table, measures=["population"])
        return with_mapping(
            table, {"pixel value": "population", "popyear": "reference_year"}, MAPPING_VERSION
        )
