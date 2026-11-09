"""S13 NASA GIBS satellite imagery (T066). Field map: configs/sources/s13.yaml.

One row per imagery day chosen for the map: the layer, its date, the tile template, bounds and
CRS. The date is never assumed: fetch reads the WMTS capabilities, then probes the state's tile
for the newest listed dates until one is not blank (T065: the default date is all black before
the afternoon pass). White cloud is imagery, not a missing feed. Tiles stay with GIBS; only this
metadata row is stored.
"""

from __future__ import annotations

import hashlib
import io
import math
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime, time, timedelta

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S13"
ROOT = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
CAPABILITIES = f"{ROOT}/1.0.0/WMTSCapabilities.xml"
HOSTS = {"gibs.earthdata.nasa.gov"}
LAYER = "VIIRS_NOAA20_CorrectedReflectance_TrueColor"  # Suomi NPP stopped (T065 e05)
MATRIX_SET, ZOOM = "GoogleMapsCompatible_Level9", 6
MAX_PROBES = 3
BLACK = 8  # grey level at or below which a pixel counts as no imagery
MAPPING_VERSION = "s13-v1"
LICENCE_ID = "nasa-open-data"
NS = {"w": "http://www.opengis.net/wmts/1.0", "ows": "http://www.opengis.net/ows/1.1"}
MEASURES = pa.schema(
    [
        pa.field("layer_id", pa.string(), False),
        pa.field("imagery_date", pa.date32(), False),
        pa.field("tile_template", pa.string(), False),
        pa.field("bounds", pa.string(), False),
        pa.field("crs", pa.string(), False),
    ]
)


def tile_index(lat: float, lon: float, zoom: int = ZOOM) -> tuple[int, int]:
    """(row, col) of the Web Mercator tile containing a point."""
    n = 2**zoom
    col = int((lon + 180) / 360 * n)
    lat_r = math.radians(lat)
    row = int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n)
    return row, col


def _layer(raw: RawArtifact):
    try:
        root = ET.fromstring(raw.path.read_bytes())
    except ET.ParseError as exc:
        raise IngestError(f"{SOURCE_ID}: capabilities are not XML: {raw.source_url}") from exc
    for lay in root.findall(".//w:Contents/w:Layer", NS):
        if getattr(lay.find("ows:Identifier", NS), "text", None) == LAYER:
            return lay
    raise IngestError(f"{SOURCE_ID}: layer {LAYER} not in the capabilities")


def listed_dates(layer, newest: int) -> list[date]:
    """The newest `newest` dates in the layer's daily Time ranges, newest first."""
    dim = layer.find("w:Dimension", NS)
    if dim is None or getattr(dim.find("ows:Identifier", NS), "text", None) != "Time":
        raise IngestError(f"{SOURCE_ID}: {LAYER} has no Time dimension")
    out: list[date] = []
    for value in reversed([v.text for v in dim.findall("w:Value", NS)]):
        start, end, period = value.split("/")
        if period != "P1D":
            raise IngestError(f"{SOURCE_ID}: unexpected period {period}")
        day, first = date.fromisoformat(end), date.fromisoformat(start)
        while day >= first and len(out) < newest:
            out.append(day)
            day -= timedelta(days=1)
        if len(out) == newest:
            break
    return out


def is_blank(raw: RawArtifact) -> bool:
    from PIL import Image  # geo lock (D35)

    hist = Image.open(io.BytesIO(raw.path.read_bytes())).convert("L").histogram()
    return sum(hist[: BLACK + 1]) == sum(hist)


class S13:
    def __init__(self, state: str, point: tuple[float, float], fetcher: Fetcher | None = None):
        self.state, self.point, self.fetcher = state, point, fetcher

    def tile_url(self, layer, day: date) -> str:
        row, col = tile_index(*self.point)
        template = layer.find("w:ResourceURL", NS).get("template")
        values = {"Time": day.isoformat(), "TileMatrixSet": MATRIX_SET, "TileMatrix": ZOOM}
        return template.format(**values, TileRow=row, TileCol=col)

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """[capabilities, tile of the newest non-blank listed date over the state]."""
        caps = self.fetcher.fetch_bytes(ctx, CAPABILITIES, mapping_version=MAPPING_VERSION)
        layer = _layer(caps)
        for day in listed_dates(layer, MAX_PROBES):
            tile = self.fetcher.fetch_bytes(
                ctx, self.tile_url(layer, day), mapping_version=MAPPING_VERSION
            )
            if not is_blank(tile):
                return [caps, tile]
        raise IngestError(f"{SOURCE_ID}: the newest {MAX_PROBES} listed dates are all blank")

    def parse(
        self, raw: RawArtifact, config: SourceConfig, *, tile: RawArtifact | None = None
    ) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        if tile is None:
            raise IngestError(f"{SOURCE_ID}: imagery date unknown without the probed tile")
        layer = _layer(raw)
        listed = listed_dates(layer, 10_000)
        day = next((d for d in listed if self.tile_url(layer, d) == tile.source_url), None)
        if day is None:
            raise IngestError(f"{SOURCE_ID}: probed tile is not a listed date of {LAYER}")
        if is_blank(tile):
            raise IngestError(f"{SOURCE_ID}: {day} is blank over the state; not imagery")
        box = layer.find("ows:WGS84BoundingBox", NS)
        bounds = " ".join(box.find(f"ows:{c}Corner", NS).text for c in ("Lower", "Upper"))
        fetched = raw.fetched_at
        row = {
            "source_id": SOURCE_ID,
            "state": self.state,
            "record_id": hashlib.sha256(f"{LAYER}|{day.isoformat()}".encode()).hexdigest(),
            "snapshot_id": f"{SOURCE_ID}-{day.isoformat()}-{raw.sha256[:12]}",
            "observed_at": None,
            "valid_at": datetime.combine(day + timedelta(days=1), time(), UTC),
            "issued_at": None,
            "available_at": max(fetched, tile.fetched_at),
            "fetched_at": fetched,
            "published_at": None,
            "source_url": tile.source_url,
            "raw_sha256": tile.sha256,
            "schema_version": 1,
            "mapping_version": MAPPING_VERSION,
            "provenance": "official",
            "quality_flags": [],
            "licence_id": LICENCE_ID,
            "redistribution_allowed": True,  # NASA open data; tiles stay with GIBS (T065 e05)
            "place_id": None,
            "boundary_version": None,
            "missing_reason": None,
            "layer_id": LAYER,
            "imagery_date": day,
            "tile_template": layer.find("w:ResourceURL", NS).get("template"),
            "bounds": bounds,
            "crs": "EPSG:3857",
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pylist([row], schema=schema)
        validate_table(table)
        mapping = {
            "Layer/ows:Identifier": "layer_id",
            "Dimension Time (probed)": "imagery_date",
            "ResourceURL@template": "tile_template",
            "WGS84BoundingBox": "bounds",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
