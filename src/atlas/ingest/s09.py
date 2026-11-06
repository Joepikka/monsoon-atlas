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
from collections.abc import Mapping
from datetime import UTC, datetime

import pyarrow as pa

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
    return list(feed_versions(raw))


def feed_versions(raw: RawArtifact) -> dict[str, str]:
    """Local fingerprints of actual RSS items, not provider CAP revision IDs."""
    try:
        root = ET.fromstring(raw.path.read_bytes())
    except ET.ParseError as exc:
        raise IngestError(f"{SOURCE_ID}: feed is not XML") from exc
    if root.tag != "rss" or root.find("channel") is None:
        raise IngestError(f"{SOURCE_ID}: not an RSS channel")
    versions = {}
    for item in root.iter("item"):
        match = re.search(r"identifier=(\d+)$", item.findtext("link") or "")
        if match is None:
            raise IngestError(f"{SOURCE_ID}: RSS item has no supported CAP link")
        ident = match.group(1)
        version = hashlib.sha256(ET.tostring(item, encoding="utf-8")).hexdigest()
        if ident in versions and versions[ident] != version:
            raise IngestError(f"{SOURCE_ID}: conflicting RSS versions for one identifier")
        versions[ident] = version
    return versions


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
    if text is None:
        return None
    try:
        value = datetime.fromisoformat(text)
    except ValueError as exc:
        raise IngestError(f"{SOURCE_ID}: invalid CAP timestamp") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise IngestError(f"{SOURCE_ID}: CAP timestamp requires a UTC offset")
    return value.astimezone(UTC)


class S09:
    def __init__(self, state: str, fetcher: Fetcher | None = None):
        if state not in BOXES:
            raise SourceUnavailable(f"{SOURCE_ID}: no alert filter for state {state}")
        self.state, self.fetcher = state, fetcher

    def fetch(self, ctx: FetchContext, known: Mapping[str, str] | None = None) -> list[RawArtifact]:
        """[feed, then (CAP, polygon) for unknown/changed RSS items], 1 s apart.

        `known` maps numeric identifiers to item fingerprints. The caller expires
        this cache and checkpoints entries only after successful processing.
        Bare identifiers cannot establish that linked CAP content is unchanged.
        """
        if known is not None and (
            not isinstance(known, Mapping)
            or any(
                not isinstance(ident, str)
                or not ident.isdigit()
                or not isinstance(version, str)
                or not re.fullmatch(r"[a-f0-9]{64}", version)
                for ident, version in known.items()
            )
        ):
            raise IngestError(f"{SOURCE_ID}: known cache requires RSS version fingerprints")
        feed = self.fetcher.fetch_bytes(ctx, FEED, mapping_version=MAPPING_VERSION)
        out, cache = [feed], known or {}
        for ident, version in feed_versions(feed).items():
            if cache.get(ident) == version:
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
        status, scope = get(root, "status"), get(root, "scope")
        if (
            status not in {"Actual", "Exercise", "System", "Test", "Draft"}
            or scope not in {"Public", "Restricted", "Private"}
            or required["msgType"] not in {"Alert", "Update", "Cancel", "Ack", "Error"}
        ):
            raise IngestError(f"{SOURCE_ID}: missing or unsupported CAP lifecycle fields")
        area = info.find("cap:area", NS)
        fields = {
            t: get(info, t) for t in ("event", "severity", "effective", "expires", "instruction")
        }
        area_text = get(area, "areaDesc") if area is not None else None
        if not fields["event"] or not fields["severity"] or not area_text:
            raise IngestError(f"{SOURCE_ID}: event, severity or area text missing")

        polygons = rings(polygon)
        rows = []
        if (
            status == "Actual"
            and scope == "Public"
            and self.in_state(required["sender"], area_text, polygons)
        ):
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
    """Apply only Update/Cancel references to exact (sender,identifier,sent) targets.

    Unmatched/malformed references stay unresolved; control messages are not
    active hazard warnings. Input order does not confer authority on a reference.
    """
    rows = table.select(["sender", "alert_id", "sent_at", "msg_type", "references"]).to_pylist()
    replaced = set()
    for row in rows:
        if row["msg_type"] not in {"Update", "Cancel"}:
            continue
        for reference in (row["references"] or "").split():
            parts = reference.split(",")
            if len(parts) != 3 or not parts[0] or not parts[1]:
                continue
            try:
                sent = _time(parts[2])
            except IngestError:
                continue
            identity = (parts[0], parts[1], sent)
            if identity != (row["sender"], row["alert_id"], row["sent_at"]):
                replaced.add(identity)
    keep = [
        row["msg_type"] in {"Alert", "Update"}
        and (row["sender"], row["alert_id"], row["sent_at"]) not in replaced
        for row in rows
    ]
    return table.filter(pa.array(keep, type=pa.bool_()))
