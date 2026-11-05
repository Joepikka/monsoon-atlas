"""S17 geoBoundaries administrative boundaries (T020). Field map: configs/sources/s17.yaml.

ADM2 features carry no parent, so each district is placed in a state by testing an interior
point against the ADM1 polygons (T019 e05, e06). Counts come from the file, never the metadata
(the file has 735 districts, the metadata says 736).
"""

from __future__ import annotations

import hashlib
import json
import re
import struct

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S17"
API = "https://www.geoboundaries.org/api/current/gbOpen/IND"
HOSTS = {"www.geoboundaries.org", "github.com", "media.githubusercontent.com"}
MAPPING_VERSION = "s17-v1"
LICENCE_ID = "odbl-1.0-geoboundaries-pathways"
STATE_ISO = {"ka": "IN-KA", "kl": "IN-KL", "dl": "IN-DL"}
PROPERTIES = {"shapeName", "shapeISO", "shapeID", "shapeGroup", "shapeType"}
MEASURES = pa.schema(
    [
        pa.field("source_place_id", pa.string(), False),
        pa.field("name", pa.string(), False),
        pa.field("admin_level", pa.string(), False),
        pa.field("parent_id", pa.string(), True),
        pa.field("valid_from", pa.date32(), True),
        pa.field("valid_to", pa.date32(), True),
        pa.field("geometry", pa.binary(), False),
    ]
)

Ring = list[list[float]]


def polygons(geometry: dict) -> list[list[Ring]]:
    kind, coords = geometry.get("type"), geometry.get("coordinates")
    if kind == "Polygon":
        return [coords]
    if kind == "MultiPolygon":
        return coords
    raise IngestError(f"{SOURCE_ID}: unsupported geometry {kind}")


def wkb(parts: list[list[Ring]]) -> bytes:
    """Little-endian WKB MultiPolygon, rings in GeoJSON order (exterior, then holes)."""
    out = struct.pack("<BII", 1, 6, len(parts))
    for rings in parts:
        out += struct.pack("<BII", 1, 3, len(rings))
        for ring in rings:
            out += struct.pack("<I", len(ring))
            out += b"".join(struct.pack("<dd", v[0], v[1]) for v in ring)
    return out


def _edges(ring: Ring):
    return zip(ring, ring[1:] + ring[:1], strict=True)


def _inside(x: float, y: float, ring: Ring) -> bool:
    hit = False
    for a, b in _edges(ring):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            hit = not hit
    return hit


def contains(parts: list[list[Ring]], x: float, y: float) -> bool:
    return any(_inside(x, y, p[0]) and not any(_inside(x, y, h) for h in p[1:]) for p in parts)


def interior_point(parts: list[list[Ring]]) -> tuple[float, float]:
    """A point inside the largest exterior ring: the middle of its first span on the mid line."""
    ring = max((p[0] for p in parts), key=len)
    ys = [v[1] for v in ring]
    y = (min(ys) + max(ys)) / 2
    xs = sorted(
        (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
        for a, b in _edges(ring)
        if (a[1] > y) != (b[1] > y)
    )
    return ((xs[0] + xs[1]) / 2, y) if len(xs) >= 2 else (ring[0][0], ring[0][1])


def _features(raw: RawArtifact, level: str) -> list[dict]:
    try:
        body = json.loads(raw.path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise IngestError(f"{SOURCE_ID}: not JSON: {raw.source_url}") from exc
    features = body.get("features") if isinstance(body, dict) else None
    if not features:
        raise IngestError(f"{SOURCE_ID}: no features in {raw.source_url}")
    for f in features:
        props = f.get("properties") or {}
        if set(props) != PROPERTIES or props["shapeType"] != level:
            raise IngestError(f"{SOURCE_ID}: properties changed: {sorted(props)}")
    return features


def release(raw: RawArtifact) -> str:
    match = re.search(r"/raw/([0-9a-f]{7,40})/releaseData/", raw.source_url)
    if not match:
        raise IngestError(f"{SOURCE_ID}: no release commit in {raw.source_url}")
    return match.group(1)


class S17:
    def __init__(self, state: str, fetcher: Fetcher | None = None):
        if state not in STATE_ISO:
            raise SourceUnavailable(f"{SOURCE_ID}: unknown state {state}")
        self.state, self.fetcher = state, fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """[ADM2 GeoJSON, ADM1 simplified GeoJSON], from the links the API publishes."""
        out = []
        for level, key in (("ADM2", "gjDownloadURL"), ("ADM1", "simplifiedGeometryGeoJSON")):
            meta = self.fetcher.fetch_bytes(ctx, f"{API}/{level}/", mapping_version=MAPPING_VERSION)
            url = json.loads(meta.path.read_bytes()).get(key)
            if not url:
                raise IngestError(f"{SOURCE_ID}: {level} metadata has no {key}")
            out.append(self.fetcher.fetch_bytes(ctx, url, mapping_version=MAPPING_VERSION))
        return out

    def parse(
        self, raw: RawArtifact, config: SourceConfig, *, adm1: RawArtifact | None = None
    ) -> pa.Table:
        """ADM2 districts of this state, with the state's ADM1 shapeID as parent."""
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        if adm1 is None:
            raise IngestError(f"{SOURCE_ID}: districts need the ADM1 file to find their state")
        iso = STATE_ISO[self.state]
        states = [f for f in _features(adm1, "ADM1") if f["properties"]["shapeISO"] == iso]
        if len(states) != 1:
            raise IngestError(f"{SOURCE_ID}: expected one ADM1 polygon for {iso}")
        state_parts = polygons(states[0]["geometry"])
        xs = [v[0] for p in state_parts for v in p[0]]
        ys = [v[1] for p in state_parts for v in p[0]]
        version = f"geoboundaries-IND-ADM2-{release(raw)}"
        parent = f"gb-IND-ADM1-{states[0]['properties']['shapeID']}"

        rows = []
        for f in _features(raw, "ADM2"):
            parts = polygons(f["geometry"])
            if any(r[0] != r[-1] or len(r) < 4 for p in parts for r in p):
                raise IngestError(
                    f"{SOURCE_ID}: open or short ring in {f['properties']['shapeID']}"
                )
            x, y = interior_point(parts)
            in_box = min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys)
            if not in_box or not contains(state_parts, x, y):
                continue
            props = f["properties"]
            rows.append(
                {
                    "place_id": f"gb-IND-ADM2-{props['shapeID']}",
                    "source_place_id": props["shapeID"],
                    "name": props["shapeName"],
                    "admin_level": props["shapeType"],
                    "parent_id": parent,
                    "valid_from": None,  # only a represented year (2021) is published
                    "valid_to": None,
                    "geometry": wkb(parts),
                }
            )
        if not rows:
            raise IngestError(f"{SOURCE_ID}: no districts found in {iso}")
        fetched, n = raw.fetched_at, len(rows)
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"{r['place_id']}|{raw.sha256}".encode()).hexdigest() for r in rows
            ],
            "snapshot_id": [version] * n,
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
            "provenance": ["official"] * n,
            "quality_flags": [[] for _ in rows],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # ODbL 1.0 with attribution and share-alike
            "place_id": [r["place_id"] for r in rows],
            "boundary_version": [version] * n,
            "missing_reason": [None] * n,
        }
        measures = {m.name: [r[m.name] for r in rows] for m in MEASURES}
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table)
        mapping = {
            "shapeID": "source_place_id",
            "shapeName": "name",
            "shapeType": "admin_level",
            "geometry": "geometry",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
