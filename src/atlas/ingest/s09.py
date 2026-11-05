"""S09 NDMA Sachet CAP alerts (T014). Field map: configs/sources/s09.yaml.

The RSS feed lists the latest 100 alerts; each links a CAP 1.2 file, and each CAP file names a
polygon file (T013 e02 to e04). Updates and cancels name the alerts they replace in
`references`; `supersede` drops replaced alerts. Events are stored as written.
"""

from __future__ import annotations

import hashlib
import re
import struct
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from datetime import UTC, datetime

import pyarrow as pa
import pyarrow.compute as pc

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S09"
BASE = "https://sachet.ndma.gov.in/cap_public_website"
FEED = f"{BASE}/rss/rss_india.xml"
HOSTS = {"sachet.ndma.gov.in"}
MAPPING_VERSION = "s09-v1"
LICENCE_ID = "public-domain-ndma-sachet"
NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}
# shortcut: a box (lat_min, lat_max, lon_min, lon_max) picks the state's alerts; T032 uses districts
BOXES = {"ka": (11.5, 18.5, 74.0, 78.75)}
STATE_NAMES = {"ka": "karnataka"}
MEASURES = pa.schema(
    [
        pa.field("alert_id", pa.string(), False),
        pa.field("sender", pa.string(), False),
        pa.field("msg_type", pa.string(), False),
        pa.field("sent_at", pa.timestamp("us", tz="UTC"), False),
        pa.field("effective_at", pa.timestamp("us", tz="UTC"), True),
        pa.field("expires_at", pa.timestamp("us", tz="UTC"), True),
        pa.field("event", pa.string(), False),
        pa.field("severity", pa.string(), False),
        pa.field("area_text", pa.string(), False),
        pa.field("geometry", pa.binary(), True),
        pa.field("instruction", pa.string(), True),
        pa.field("references", pa.string(), True),
    ]
)


def feed_identifiers(raw: RawArtifact) -> list[str]:
    """Identifiers of the CAP files the feed links, newest first."""
    try:
        root = ET.fromstring(raw.path.read_bytes())
    except ET.ParseError as exc:
        raise IngestError(f"{SOURCE_ID}: feed is not XML") from exc
    links = [i.findtext("link") or "" for i in root.iter("item")]
    return [m.group(1) for link in links if (m := re.search(r"identifier=(\d+)$", link))]


def rings(raw: RawArtifact | None) -> list[list[tuple[float, float]]]:
    """Unique (lon, lat) rings from a polygon file; the file lists points as 'lat,lon'."""
    if raw is None:
        return []
    out = []
    for text in dict.fromkeys(
        re.findall(r"<polygon>([^<]*)</polygon>", raw.path.read_text("utf-8"))
    ):
        points = [tuple(map(float, p.split(",")))[::-1] for p in text.split()]
        if len(points) >= 3:
            out.append(points if points[0] == points[-1] else [*points, points[0]])
    return out


def wkb_multipolygon(polygons: list[list[tuple[float, float]]]) -> bytes:
    """Little-endian WKB MultiPolygon with one exterior ring per polygon, x = lon, y = lat."""
    out = struct.pack("<BII", 1, 6, len(polygons))
    for ring in polygons:
        out += struct.pack("<BIII", 1, 3, 1, len(ring))
        out += b"".join(struct.pack("<dd", x, y) for x, y in ring)
    return out


def _time(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text).astimezone(UTC) if text else None


class S09:
    def __init__(self, state: str, fetcher: Fetcher | None = None):
        if state not in BOXES:
            raise SourceUnavailable(f"{SOURCE_ID}: no alert filter for state {state}")
        self.state, self.fetcher = state, fetcher

    def fetch(self, ctx: FetchContext, known: Iterable[str] = ()) -> list[RawArtifact]:
        """[feed, then (CAP, polygon) for each identifier not already known], 1 s apart."""
        feed = self.fetcher.fetch_bytes(ctx, FEED, mapping_version=MAPPING_VERSION)
        out, skip = [feed], set(known)
        for ident in feed_identifiers(feed):
            if ident in skip:
                continue
            for path in ("FetchXMLFile", "FetchPolygonXMLFile"):
                time.sleep(1.0)
                url = f"{BASE}/{path}"
                out.append(
                    self.fetcher.fetch_bytes(
                        ctx, url, mapping_version=MAPPING_VERSION, params={"identifier": ident}
                    )
                )
        return out

    def in_state(self, sender: str, area: str, polygons) -> bool:
        lat_min, lat_max, lon_min, lon_max = BOXES[self.state]
        name = STATE_NAMES[self.state]
        inside = any(
            lat_min <= y <= lat_max and lon_min <= x <= lon_max for r in polygons for x, y in r
        )
        return inside or name in sender.lower() or name in area.lower()

    def parse(
        self, raw: RawArtifact, config: SourceConfig, *, polygon: RawArtifact | None = None
    ) -> pa.Table:
        """One CAP file to at most one row (English info block); empty if not in the state."""
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        try:
            root = ET.fromstring(raw.path.read_bytes())
        except ET.ParseError as exc:
            raise IngestError(f"{SOURCE_ID}: CAP file is not XML: {raw.source_url}") from exc
        if root.tag != f"{{{NS['cap']}}}alert":
            raise IngestError(f"{SOURCE_ID}: not a CAP 1.2 alert")
        infos = root.findall("cap:info", NS)
        info = next(
            (i for i in infos if (i.findtext("cap:language", "", NS)).lower().startswith("en")),
            infos[0] if infos else None,
        )
        get = lambda el, tag: (el.findtext(f"cap:{tag}", None, NS) or "").strip() or None  # noqa: E731
        required = {t: get(root, t) for t in ("identifier", "sender", "sent", "msgType")}
        if info is None or None in required.values():
            raise IngestError(
                f"{SOURCE_ID}: CAP fields missing: {sorted(k for k, v in required.items() if not v)}"  # noqa: E501
            )
        area = info.find("cap:area", NS)
        fields = {
            t: get(info, t) for t in ("event", "severity", "effective", "expires", "instruction")
        }
        area_text = get(area, "areaDesc") if area is not None else None
        if not fields["event"] or not fields["severity"] or not area_text:
            raise IngestError(f"{SOURCE_ID}: event, severity or area text missing")

        polygons = rings(polygon)
        rows = []
        if self.in_state(required["sender"], area_text, polygons):
            rows.append(
                {
                    "alert_id": required["identifier"],
                    "sender": required["sender"],
                    "msg_type": required["msgType"],
                    "sent_at": _time(required["sent"]),
                    "effective_at": _time(fields["effective"]),
                    "expires_at": _time(fields["expires"]),
                    "event": fields["event"],
                    "severity": fields["severity"],
                    "area_text": area_text,
                    "geometry": wkb_multipolygon(polygons) if polygons else None,
                    "instruction": fields["instruction"],
                    "references": get(root, "references"),
                }
            )
        n, fetched = len(rows), raw.fetched_at
        sha = raw.sha256 + (polygon.sha256 if polygon else "")
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"{r['alert_id']}|{sha}".encode()).hexdigest() for r in rows
            ],
            "snapshot_id": [f"{SOURCE_ID}-{r['alert_id']}-{raw.sha256[:12]}" for r in rows],
            "observed_at": [None] * n,
            "valid_at": [r["effective_at"] or r["sent_at"] for r in rows],
            "issued_at": [r["sent_at"] for r in rows],
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [r["sent_at"] for r in rows],
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["official"] * n,
            "quality_flags": [[] for _ in rows],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # public domain (T013 e02)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": [None] * n,
        }
        measures = {f.name: [r[f.name] for r in rows] for f in MEASURES}
        table = pa.Table.from_pydict(
            common | measures, schema=pa.schema([*envelope_schema(), *MEASURES])
        )
        validate_table(table)
        mapping = {
            "cap:identifier": "alert_id",
            "cap:sent": "sent_at",
            "cap:info/cap:effective": "effective_at",
            "cap:info/cap:expires": "expires_at",
            "cap:info/cap:event": "event",
            "cap:info/cap:severity": "severity",
            "cap:area/cap:areaDesc": "area_text",
            "Polygon URL file": "geometry",
            "cap:info/cap:instruction": "instruction",
            "cap:references": "references",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)


def supersede(table: pa.Table) -> pa.Table:
    """Drop alerts that a later Update or Cancel references, and the Cancel messages themselves."""
    replaced = {
        ref.split(",")[1]
        for refs in table["references"].drop_null().to_pylist()
        for ref in refs.split()
        if ref.count(",") == 2
    }
    keep = pc.and_(
        pc.invert(pc.is_in(table["alert_id"], pa.array(sorted(replaced), pa.string()))),
        pc.not_equal(table["msg_type"], "Cancel"),
    )
    return table.filter(keep)
