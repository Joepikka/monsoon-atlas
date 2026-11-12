"""S14 AWS Terrarium terrain (T068). Field map: configs/sources/s14.yaml.

Tiles stay on S3 for the map; this adapter fetches requested tiles on demand, decodes them with
the documented Terrarium formula (metres = R*256 + G + B/256 - 32768, T067 e03) to prove they are
valid, and writes one metadata row per tile. Negative values over the sea are bathymetry, not
missing data, so a tile's minimum below 0 is kept as reported.
"""

from __future__ import annotations

import hashlib
import io
import re
from collections.abc import Sequence

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S14"
BUCKET = "https://s3.amazonaws.com/elevation-tiles-prod"
HOSTS = {"s3.amazonaws.com"}
KEY = re.compile(r"terrarium/(\d+)/(\d+)/(\d+)\.png$")
LOWEST_M, HIGHEST_M = -11000, 8900  # documented data range (T067 e03)
MAPPING_VERSION = "s14-v1"
LICENCE_ID = "mapzen-terrain-tiles-attribution"
MEASURES = pa.schema(
    [
        pa.field("tile_key", pa.string(), False),
        pa.field("z", pa.int64(), False),
        pa.field("x", pa.int64(), False),
        pa.field("y", pa.int64(), False),
        pa.field("elevation_encoding", pa.string(), False),
        pa.field("crs", pa.string(), False),
        pa.field("min_m", pa.float64(), False),
        pa.field("max_m", pa.float64(), False),
    ]
)


def decode(png: bytes) -> list[float]:
    """Terrarium metres for every pixel of a 256 x 256 RGB tile."""
    from PIL import Image  # geo lock (D35)

    try:
        image = Image.open(io.BytesIO(png))
        image.load()
    except OSError as exc:
        raise IngestError(f"{SOURCE_ID}: not a PNG tile") from exc
    if image.size != (256, 256) or image.mode != "RGB":
        raise IngestError(
            f"{SOURCE_ID}: expected a 256 x 256 RGB tile, got {image.size} {image.mode}"
        )
    return [r * 256 + g + b / 256 - 32768 for r, g, b in image.get_flattened_data()]


class S14:
    def __init__(
        self,
        state: str,
        tiles: Sequence[tuple[int, int, int]],
        fetcher: Fetcher | None = None,
    ):
        for z, x, y in tiles:
            if not (0 <= z <= 15 and 0 <= x < 2**z and 0 <= y < 2**z):
                raise ValueError(f"invalid tile {z}/{x}/{y}")
        self.state, self.tiles, self.fetcher = state, list(tiles), fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """On demand: one artifact per requested tile."""
        return [
            self.fetcher.fetch_bytes(
                ctx, f"{BUCKET}/terrarium/{z}/{x}/{y}.png", mapping_version=MAPPING_VERSION
            )
            for z, x, y in self.tiles
        ]

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        match = KEY.search(raw.source_url)
        if not match:
            raise IngestError(f"{SOURCE_ID}: not a Terrarium tile URL: {raw.source_url}")
        z, x, y = (int(v) for v in match.groups())
        metres = decode(raw.path.read_bytes())
        low, high = min(metres), max(metres)
        if low < LOWEST_M or high > HIGHEST_M:
            raise IngestError(f"{SOURCE_ID}: decoded {low:.1f}..{high:.1f} m is outside the range")
        key = f"terrarium/{z}/{x}/{y}.png"
        row = {
            "source_id": SOURCE_ID,
            "state": self.state,
            "record_id": hashlib.sha256(f"{key}|{raw.sha256}".encode()).hexdigest(),
            "snapshot_id": f"{SOURCE_ID}-{raw.sha256[:12]}",
            "observed_at": None,
            "valid_at": None,  # static terrain, no time dimension (T067 e01)
            "issued_at": None,
            "available_at": raw.fetched_at,
            "fetched_at": raw.fetched_at,
            "published_at": None,
            "source_url": raw.source_url,
            "raw_sha256": raw.sha256,
            "schema_version": 1,
            "mapping_version": MAPPING_VERSION,
            "provenance": "model",  # gridded elevation models (SRTM, GMTED2010, ETOPO1)
            "quality_flags": [],
            "licence_id": LICENCE_ID,
            "redistribution_allowed": True,  # attribution required (T067 e02)
            "place_id": None,
            "boundary_version": None,
            "missing_reason": None,
            "tile_key": key,
            "z": z,
            "x": x,
            "y": y,
            "elevation_encoding": "terrarium",
            "crs": "EPSG:3857",
            "min_m": low,
            "max_m": high,
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pylist([row], schema=schema)
        validate_table(table, measures=["min_m", "max_m"])
        mapping = {"object key": "tile_key", "R*256+G+B/256-32768": "min_m, max_m"}
        return with_mapping(table, mapping, MAPPING_VERSION)
