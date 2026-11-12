"""S18 Geofabrik OSM extracts (T022). Field map: configs/sources/s18.yaml.

Geofabrik's robots.txt disallows scripted *.osm.pbf downloads (D34), so fetch stays closed: the
owner downloads the Southern Zone extract in a browser into data/raw/S18 and `owner_file` turns
that file into a RawArtifact (D174). parse_batches streams the PBF with pyosmium, keeps the
facility and road features the map needs whose centroid lies in the state polygon, and yields
bounded tables, so the whole zone never sits in memory. OSM is volunteer-mapped, so rows are
"inferred", never "official", and no shelter opening status is ever derived from OSM tags.
ODbL 1.0: credit OpenStreetMap contributors; derived databases stay ODbL.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable

SOURCE_ID = "S18"
MAPPING_VERSION = "s18-v1"
LICENCE_ID = "odbl-1.0-openstreetmap"
PAGE = "https://download.geofabrik.de/asia/india/southern-zone.html"
ROBOTS = (
    f"{SOURCE_ID}: robots.txt disallows scripted extract downloads (D34); the owner downloads "
    f"the extract in a browser from {PAGE} into data/raw/S18 and owner_file reads it (D174)"
)
# (key, value) -> feature_kind. Shelters keep only what OSM says exists; never opening status.
FACILITIES = {
    ("amenity", "hospital"): "hospital",
    ("amenity", "clinic"): "clinic",
    ("amenity", "police"): "police",
    ("amenity", "fire_station"): "fire_station",
    ("amenity", "shelter"): "shelter",
    ("emergency", "assembly_point"): "assembly_point",
    ("highway", "bus_stop"): "bus_stop",
}
ROADS = frozenset(
    "motorway trunk primary secondary tertiary unclassified residential service living_street "
    "pedestrian footway path steps track motorway_link trunk_link primary_link secondary_link "
    "tertiary_link".split()
)
MEASURES = pa.schema(
    [
        pa.field("osm_type", pa.string(), False),
        pa.field("osm_id", pa.int64(), False),
        pa.field("osm_version", pa.int64(), False),
        pa.field("feature_kind", pa.string(), False),
        pa.field("tags_json", pa.string(), False),
        pa.field("geometry", pa.binary(), False),
    ]
)


def owner_file(path: Path, url: str, fetched_at: datetime) -> RawArtifact:
    """A browser-downloaded extract as a RawArtifact (hashed in 1 MB chunks)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return RawArtifact(
        sha256=h.hexdigest(),
        path=path,
        fetched_at=fetched_at,
        media_type="application/x-protobuf",
        response_status=200,
        source_url=url,
        schema_mapping_version=MAPPING_VERSION,
    )


def kind_of(tags: dict[str, str], is_way: bool) -> str | None:
    for (k, v), kind in FACILITIES.items():
        if tags.get(k) == v:
            return kind
    if is_way and tags.get("highway") in ROADS:
        return "road"
    return None


class S18:
    def __init__(self, state: str, area_wkb: bytes):
        """area_wkb: the state polygon (WGS84 WKB, from S17); rows are kept by centroid."""
        self.state, self.area_wkb = state, area_wkb
        self.skipped_invalid = 0

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        raise SourceUnavailable(ROBOTS)

    def parse_batches(
        self, raw: RawArtifact, config: SourceConfig, *, batch_rows: int = 200_000
    ) -> Iterator[pa.Table]:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        import osmium
        import shapely  # geo lock (D35)

        area = shapely.from_wkb(self.area_wkb)
        shapely.prepare(area)
        minx, miny, maxx, maxy = area.bounds
        seen: set[tuple[str, int]] = set()
        rows: list[dict] = []
        self.skipped_invalid = 0
        if not Path(raw.path).stat().st_size:
            raise IngestError(f"{SOURCE_ID}: empty extract {raw.source_url}")
        try:
            processor = (
                osmium.FileProcessor(str(raw.path))
                .with_locations()
                .with_filter(osmium.filter.KeyFilter("amenity", "highway", "emergency"))
            )
            for o in processor:
                if o.is_relation():
                    continue  # facility multipolygons are rare; roads are ways
                kind = kind_of(dict(o.tags), o.is_way())
                if kind is None:
                    continue
                key = ("node" if o.is_node() else "way", o.id)
                if key in seen:
                    raise IngestError(f"{SOURCE_ID}: duplicate {key} in {raw.source_url}")
                if not o.version:
                    raise IngestError(f"{SOURCE_ID}: {key} has no version (metadata changed)")
                geom = self._geometry(o, osmium, shapely)
                if geom is None:
                    self.skipped_invalid += 1
                    continue
                c = shapely.centroid(geom)
                if not (minx <= c.x <= maxx and miny <= c.y <= maxy and area.contains(c)):
                    continue
                seen.add(key)
                rows.append(
                    {
                        "type": key[0],
                        "id": o.id,
                        "version": o.version,
                        "kind": kind,
                        "tags": json.dumps(dict(o.tags), ensure_ascii=False, sort_keys=True),
                        "wkb": shapely.to_wkb(geom),
                    }
                )
                if len(rows) >= batch_rows:
                    yield self._table(raw, rows)
                    rows = []
        except (RuntimeError, OSError) as exc:  # libosmium reports bad PBF data as RuntimeError
            raise IngestError(f"{SOURCE_ID}: unreadable extract {raw.source_url}: {exc}") from exc
        if rows or not seen:
            yield self._table(raw, rows)

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        """All rows as one table (for small inputs; use parse_batches for a state)."""
        return pa.concat_tables(list(self.parse_batches(raw, config)))

    @staticmethod
    def _geometry(o, osmium, shapely):
        try:
            if o.is_node():
                if not o.location.valid():
                    return None
                return shapely.Point(o.location.lon, o.location.lat)
            pts = [(n.lon, n.lat) for n in o.nodes]
        except osmium.InvalidLocationError:
            return None  # a referenced node is outside the extract
        if len(pts) < 2:
            return None
        geom = shapely.LineString(pts)
        return geom if geom.is_valid else None

    def _table(self, raw: RawArtifact, rows: list[dict]) -> pa.Table:
        n, fetched = len(rows), raw.fetched_at
        snapshot = f"{SOURCE_ID}-{raw.sha256[:12]}"
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"osm|{r['type']}|{r['id']}|{r['version']}".encode()).hexdigest()
                for r in rows
            ],
            "snapshot_id": [snapshot] * n,
            "observed_at": [None] * n,
            "valid_at": [None] * n,  # an extract is a map state, not a dated observation
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [None] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["inferred"] * n,  # volunteer-mapped, not official, not a model (D174)
            "quality_flags": [[] for _ in range(n)],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # ODbL 1.0 with attribution and share-alike
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": [None] * n,
        }
        measures = {
            "osm_type": [r["type"] for r in rows],
            "osm_id": [r["id"] for r in rows],
            "osm_version": [r["version"] for r in rows],
            "feature_kind": [r["kind"] for r in rows],
            "tags_json": [r["tags"] for r in rows],
            "geometry": [r["wkb"] for r in rows],
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table)
        mapping = {
            "object type": "osm_type",
            "object id": "osm_id",
            "object version": "osm_version",
            "amenity/emergency/highway tag": "feature_kind",
            "tags": "tags_json",
            "node location / way node locations": "geometry (WKB)",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
