"""S15 OpenFreeMap basemap (T016). Field map: configs/sources/s15.yaml.

Maps load tiles in the viewer's browser; the project only records which style and tile revision
it used and the attribution that must stay on the map (T015 e05, e06). Never bulk-download tiles
(T015 e03).
"""

from __future__ import annotations

import hashlib
import json
import re

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S15"
TILES = "https://tiles.openfreemap.org"
HOSTS = {"tiles.openfreemap.org"}
MAPPING_VERSION = "s15-v1"
LICENCE_ID = "odbl-osm-openmaptiles-openfreemap"
REVISION = re.compile(
    r"^https://tiles\.openfreemap\.org/planet/(\d{8}_\d{6}_[a-z]+)/\{z\}/\{x\}/\{y\}\.pbf$"
)
MEASURES = pa.schema(
    [
        pa.field("style_url", pa.string(), False),
        pa.field("revision", pa.string(), False),
        pa.field("attribution", pa.string(), False),
    ]
)


def _json(raw: RawArtifact) -> dict:
    try:
        body = json.loads(raw.path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc
    if not isinstance(body, dict) or not body:
        raise IngestError(f"{SOURCE_ID}: empty response: {raw.source_url}")
    return body


class S15:
    def __init__(self, state: str, style: str = "liberty", fetcher: Fetcher | None = None):
        self.state, self.style_url, self.fetcher = state, f"{TILES}/styles/{style}", fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """[style, TileJSON of its vector source]. No tiles are downloaded."""
        style = self.fetcher.fetch_bytes(ctx, self.style_url, mapping_version=MAPPING_VERSION)
        source = _json(style).get("sources", {}).get("openmaptiles", {}).get("url")
        if not source:
            raise IngestError(f"{SOURCE_ID}: style has no openmaptiles source")
        return [style, self.fetcher.fetch_bytes(ctx, source, mapping_version=MAPPING_VERSION)]

    def parse(
        self, raw: RawArtifact, config: SourceConfig, *, tilejson: RawArtifact | None = None
    ) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        if tilejson is None:
            raise IngestError(f"{SOURCE_ID}: revision and attribution need the TileJSON")
        style, tj = _json(raw), _json(tilejson)
        source = style.get("sources", {}).get("openmaptiles", {})
        if source.get("type") != "vector" or source.get("url") != tilejson.source_url:
            raise IngestError(f"{SOURCE_ID}: style source does not match the TileJSON fetched")
        tiles, attribution = tj.get("tiles") or [], tj.get("attribution") or ""
        match = REVISION.match(tiles[0]) if len(tiles) == 1 else None
        if not match or "OpenStreetMap" not in attribution or "OpenMapTiles" not in attribution:
            raise IngestError(f"{SOURCE_ID}: TileJSON tiles or attribution changed")
        row = {"style_url": self.style_url, "revision": match.group(1), "attribution": attribution}
        fetched = raw.fetched_at
        key = f"{row['style_url']}|{row['revision']}|{raw.sha256}|{tilejson.sha256}"
        common = {
            "source_id": SOURCE_ID,
            "state": self.state,
            "record_id": hashlib.sha256(key.encode()).hexdigest(),
            "snapshot_id": f"{SOURCE_ID}-{row['revision']}",
            "observed_at": None,
            "valid_at": None,
            "issued_at": None,  # the revision stamp's time zone is not documented
            "available_at": fetched,
            "fetched_at": fetched,
            "published_at": None,
            "source_url": raw.source_url,
            "raw_sha256": raw.sha256,
            "schema_version": 1,
            "mapping_version": MAPPING_VERSION,
            "provenance": "official",
            "quality_flags": [],
            "licence_id": LICENCE_ID,
            "redistribution_allowed": True,  # URL, revision and attribution text only
            "place_id": None,
            "boundary_version": None,
            "missing_reason": None,
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pylist([common | row], schema=schema)
        validate_table(table)
        mapping = {
            "style URL": "style_url",
            "tiles[0] revision": "revision",
            "attribution": "attribution",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
