"""S40 ward polygons: GBA Wards Delimitation 2025 (T031). Field map: configs/sources/s40.yaml.

Only the public-domain GBA 2025 final 369-ward KML is parsed (T030 e03, e04). The older BBMP
maps have no licence and stay local research files. A ward's ID is its corporation and ward
number; its parent is the corporation.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher
from atlas.ingest.s17 import wkb

SOURCE_ID = "S40"
URL = (  # T030 e04, the final 369-ward resource
    "https://data.opencity.in/dataset/863209cb-4ced-4f51-b5c5-156939c50922/resource/"
    "dbe57ae6-a72f-426e-917b-e55b3b22a87b/download/1c5bbd4e-006c-4130-b278-fd6680fef91b.kml"
)
HOSTS = {"data.opencity.in"}
MAPPING_VERSION = "s40-v1"
LICENCE_ID = "public-domain-gba-2025-opencity"
VERSION = "gba-2025-final-369"
KML = {"k": "http://www.opengis.net/kml/2.2"}
REQUIRED = ("corporation_id", "Corporation", "ward_id", "ward_name")
MEASURES = pa.schema(
    [
        pa.field("name", pa.string(), False),
        pa.field("level", pa.string(), False),
        pa.field("parent_id", pa.string(), False),
        pa.field("parent_name", pa.string(), False),
        pa.field("valid_from", pa.date32(), True),
        pa.field("geometry", pa.binary(), False),
    ]
)


def _ring(text: str | None) -> list[list[float]]:
    points = [[float(v) for v in p.split(",")[:2]] for p in (text or "").split()]
    if len(points) < 4 or points[0] != points[-1]:
        raise IngestError(f"{SOURCE_ID}: open or short ring")
    return points


class S40:
    def __init__(self, state: str = "ka", fetcher: Fetcher | None = None):
        if state != "ka":
            raise SourceUnavailable(f"{SOURCE_ID}: GBA wards exist only for Karnataka")
        self.state, self.fetcher = state, fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        return [self.fetcher.fetch_bytes(ctx, URL, mapping_version=MAPPING_VERSION)]

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        try:
            root = ET.fromstring(raw.path.read_bytes())
        except ET.ParseError as exc:
            raise IngestError(f"{SOURCE_ID}: not KML") from exc
        marks = root.findall(".//k:Placemark", KML)
        if not marks:
            raise IngestError(f"{SOURCE_ID}: no placemarks")
        rows, seen = [], set()
        for mark in marks:
            data = {
                d.get("name"): (d.text or "").strip()
                for d in mark.iter(f"{{{KML['k']}}}SimpleData")
            }
            if any(not data.get(k) for k in REQUIRED):
                raise IngestError(f"{SOURCE_ID}: fields changed: {sorted(data)}")
            key = (data["corporation_id"], data["ward_id"])
            if key in seen:
                raise IngestError(f"{SOURCE_ID}: duplicate ward {key}")
            seen.add(key)
            parts = []
            for poly in mark.iter(f"{{{KML['k']}}}Polygon"):
                outer = poly.find("k:outerBoundaryIs/k:LinearRing/k:coordinates", KML)
                inner = poly.findall("k:innerBoundaryIs/k:LinearRing/k:coordinates", KML)
                parts.append(
                    [
                        _ring(outer.text if outer is not None else None),
                        *(_ring(i.text) for i in inner),
                    ]
                )
            if not parts:
                raise IngestError(f"{SOURCE_ID}: ward {key} has no polygon")
            rows.append(
                {
                    "place_id": f"gba2025-c{key[0]}-w{key[1]}",
                    "name": data["ward_name"],
                    "level": "ward",
                    "parent_id": f"gba2025-c{key[0]}",
                    "parent_name": data["Corporation"],
                    "valid_from": None,  # the resource gives no start date (T030)
                    "geometry": wkb(parts),
                }
            )
        n, fetched = len(rows), raw.fetched_at
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"{r['place_id']}|{raw.sha256}".encode()).hexdigest() for r in rows
            ],
            "snapshot_id": [VERSION] * n,
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
            "redistribution_allowed": [True] * n,  # public domain (T030 e02, e03)
            "place_id": [r["place_id"] for r in rows],
            "boundary_version": [VERSION] * n,
            "missing_reason": [None] * n,
        }
        measures = {m.name: [r[m.name] for r in rows] for m in MEASURES}
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table)
        mapping = {
            "corporation_id + ward_id": "place_id",
            "ward_name": "name",
            "corporation_id": "parent_id",
            "Corporation": "parent_name",
            "Polygon": "geometry",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
