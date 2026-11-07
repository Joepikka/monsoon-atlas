"""S32 KSEB daily reservoir report (T114, D46; field map in configs/sources/s32.yaml).

Today's readings only. Unknown datum and energy inflow never become inferred measurements.
Inconsistent rows retain identity/provenance but have null core measures (quarantine).
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S32"
URL = "https://kseb.in/dashboard/view/waterlevel"
HOSTS = {"kseb.in"}
MAPPING_VERSION = "s32-v1"
HEADERS = (
    "Name of Dam / Reservoir",
    "District",
    "Today's Water level (metre)",
    "Today's Live Storage (MCM)",
    "%Storage wrt Live Storage at FRL",
    "Same day previous year Water level (metre)",
    "Same day previous year Live Storage (MCM)",
    "Inflow MU",
    "Rainfall (mm)",
    "Blue level (metre)",
    "Orange level (metre)",
    "Red Level (metre)",
    "MWL (metre)",
    "FRL (metre)",
    "Spillway Crest Level (metre)",
    "Live Storage at FRL (MCM)",
    "Remarks",
)
CORE = ("level_m", "storage_mcm", "capacity_mcm")
MEASURES = pa.schema(
    [
        pa.field("reservoir_id", pa.string(), False),
        pa.field("reservoir_name", pa.string(), False),
        pa.field("operator", pa.string(), False),
        pa.field("district_code", pa.string(), False),
        pa.field("date_local", pa.date32(), False),
        pa.field("level_m", pa.float64(), True),
        pa.field("storage_mcm", pa.float64(), True),
        pa.field("capacity_mcm", pa.float64(), True),
        pa.field("inflow_m3s", pa.float64(), True),
        pa.field("inflow_missing_reason", pa.string(), False),
        pa.field("vertical_datum", pa.string(), True),
        pa.field("datum_missing_reason", pa.string(), False),
        pa.field("quality_details", pa.list_(pa.string()), False),
    ]
)


def _text(parts: list[str]) -> str:
    return " ".join("".join(parts).split())


class _Report(HTMLParser):
    """Read complete, flat HTML tables and report headings; never repair truncated tables."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self.headings: list[str] = []
        self.table = self.row = self.cell = self.heading = None

    def handle_starttag(self, tag, attrs):
        if tag == "h3":
            self.heading = []
        elif tag == "table":
            if self.table is not None:
                raise IngestError("S32: nested table layout changed")
            self.table = []
        elif self.table is not None:
            if tag == "tr":
                if self.row is not None:
                    raise IngestError("S32: unclosed row")
                self.row = []
            elif tag in {"td", "th"}:
                if self.row is None or self.cell is not None:
                    raise IngestError("S32: malformed cell")
                if any(k in {"rowspan", "colspan"} and v != "1" for k, v in attrs):
                    raise IngestError("S32: spanned columns changed")
                self.cell = []
            elif tag == "br" and self.cell is not None:
                self.cell.append(" ")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
        if self.heading is not None:
            self.heading.append(data)

    def handle_endtag(self, tag):
        if tag == "h3" and self.heading is not None:
            self.headings.append(_text(self.heading))
            self.heading = None
        elif self.table is not None:
            if tag in {"td", "th"}:
                if self.cell is None or self.row is None:
                    raise IngestError("S32: unmatched cell")
                self.row.append(_text(self.cell))
                self.cell = None
            elif tag == "tr":
                if self.row is None or self.cell is not None:
                    raise IngestError("S32: incomplete row")
                self.table.append(self.row)
                self.row = None
            elif tag == "table":
                if self.row is not None or self.cell is not None:
                    raise IngestError("S32: incomplete table")
                self.tables.append(self.table)
                self.table = None


def _number(value: str, *, feet: bool = False) -> tuple[float | None, bool]:
    if value == "":
        return None, False
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(ft)?", value.lower())
    if not match or (match[2] and not feet):
        raise ValueError("unrecognized numeric value or unit")
    number = float(match[1])
    if not (-float("inf") < number < float("inf")):
        raise ValueError("non-finite measurement")
    converted = bool(match[2])
    return number * 0.3048 if converted else number, converted


def _measurements(cells: list[str]) -> tuple[list, str | None, list[str], list[str]]:
    details = ["MU is energy", "vertical datum not stated"]
    try:
        level, converted = _number(cells[2], feet=True)
        storage, _ = _number(cells[3])
        pct, _ = _number(cells[4])
        mwl, _ = _number(cells[12], feet=True)
        capacity, _ = _number(cells[15])
        if converted:
            details.append("explicit feet converted to metres")
        problems = []
        if level is not None and (level < 0 or (mwl is not None and level > mwl)):
            problems.append("level outside stated range")
        if mwl is not None and mwl <= 0:
            problems.append("invalid maximum water level")
        if capacity is not None and capacity <= 0:
            problems.append("invalid live capacity")
        if storage is not None and storage < 0:
            problems.append("negative live storage")
        if pct is not None and pct < 0:
            problems.append("negative storage percentage")
        if None not in (storage, pct, capacity) and capacity > 0:
            if abs(pct - 100 * storage / capacity) > 0.1:
                problems.append("storage percentage mismatch")
        if problems:
            return [None] * 3, "quality_rejected", ["missing", "out_of_range"], details + problems
        if None in (level, storage, pct, mwl, capacity):
            return (
                [None] * 3,
                "not_reported",
                ["missing"],
                details + ["incomplete core measurements or checks"],
            )
    except ValueError as exc:
        return [None] * 3, "quality_rejected", ["missing", "unit_unverified"], details + [str(exc)]
    return [level, storage, capacity], None, [], details


def _enabled(config: SourceConfig) -> None:
    if config.source_id != SOURCE_ID:
        raise IngestError("S32: wrong source config")
    if not config.enabled:
        raise SourceUnavailable("S32 is disabled; T113 discovery and T114 adapter must pass")


class S32:
    def __init__(
        self, config: SourceConfig, day: date | None = None, fetcher: Fetcher | None = None
    ):
        self.config, self.day, self.fetcher = config, day, fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        _enabled(self.config)
        if (ctx.source_id, ctx.state) != (SOURCE_ID, "kl"):
            raise IngestError("S32: fetch context must be S32/Kerala")
        if self.fetcher is None:
            raise IngestError("S32: shared Fetcher required")
        return [
            self.fetcher.fetch_bytes(
                ctx,
                URL,
                mapping_version=MAPPING_VERSION,
                params={"date": self.day.isoformat()} if self.day else None,
            )
        ]

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        _enabled(config)
        if raw.response_status not in {200, 304} or raw.media_type.split(";")[0] != "text/html":
            raise IngestError("S32: expected a successful HTML report")
        parsed_url = urlsplit(raw.source_url)
        if (parsed_url.scheme, parsed_url.netloc, parsed_url.path) != (
            "https",
            "kseb.in",
            "/dashboard/view/waterlevel",
        ):
            raise IngestError("S32: unexpected report URL")
        body = raw.path.read_bytes()
        if hashlib.sha256(body).hexdigest() != raw.sha256:
            raise IngestError("S32: raw hash mismatch")
        parser = _Report()
        try:
            parser.feed(body.decode("utf-8"))
            parser.close()
        except UnicodeDecodeError as exc:
            raise IngestError("S32: invalid HTML encoding") from exc
        if any(x is not None for x in (parser.table, parser.row, parser.cell, parser.heading)):
            raise IngestError("S32: incomplete HTML report")
        headings = [h for h in parser.headings if "WATER LEVELS OF MAIN RESERVOIRS" in h]
        if len(headings) != 1:
            raise IngestError("S32: missing or duplicate report title")
        title = re.fullmatch(
            r"DAILY REPORT - WATER LEVELS OF MAIN RESERVOIRS "
            r"\(As on (\d{2}-[A-Za-z]{3}-\d{4})\) 7\.00 AM\.",
            headings[0],
        )
        if not title:
            raise IngestError("S32: report date/time format changed")
        try:
            day = datetime.strptime(title[1], "%d-%b-%Y").date()
        except ValueError as exc:
            raise IngestError("S32: invalid report date") from exc
        requested = parse_qs(parsed_url.query).get("date", [])
        if (self.day and day != self.day) or (requested and requested != [day.isoformat()]):
            raise IngestError("S32: report date differs from requested date")
        observed = datetime(
            day.year, day.month, day.day, 7, tzinfo=ZoneInfo("Asia/Kolkata")
        ).astimezone(UTC)
        if observed > raw.fetched_at:
            raise IngestError("S32: observation is after fetch time")
        tables = [t for t in parser.tables if t and t[0] and t[0][0] == HEADERS[0]]
        if len(tables) != 1 or tuple(tables[0][0]) != HEADERS:
            raise IngestError("S32: missing, duplicate or changed columns")
        rows, identities = [], set()
        for cells in tables[0][1:]:
            if len(cells) != len(HEADERS):
                raise IngestError("S32: row width changed")
            name, district = cells[:2]
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            if not slug or not re.fullmatch(r"[A-Z]+", district):
                raise IngestError("S32: missing or invalid reservoir identity")
            reservoir = f"kseb:{district.lower()}:{slug}"
            if reservoir in identities:
                raise IngestError("S32: duplicate dam observation")
            identities.add(reservoir)
            values, reason, flags, details = _measurements(cells)
            rows.append(
                {
                    "source_id": SOURCE_ID,
                    "state": "kl",
                    "record_id": hashlib.sha256(
                        f"{reservoir}|{observed.isoformat()}|{raw.sha256}".encode()
                    ).hexdigest(),
                    "snapshot_id": f"S32-{raw.fetched_at:%Y%m%dT%H%M%SZ}-{raw.sha256[:12]}",
                    "observed_at": observed,
                    "valid_at": observed,
                    "issued_at": None,
                    "available_at": raw.fetched_at,
                    "fetched_at": raw.fetched_at,
                    "published_at": None,
                    "source_url": raw.source_url,
                    "raw_sha256": raw.sha256,
                    "schema_version": 1,
                    "mapping_version": MAPPING_VERSION,
                    "provenance": "official",
                    "quality_flags": flags,
                    "licence_id": "cc-by-sa-2.5-in-kseb",
                    "redistribution_allowed": True,
                    "place_id": None,
                    "boundary_version": None,
                    "missing_reason": reason,
                    "reservoir_id": reservoir,
                    "reservoir_name": name,
                    "operator": "KSEB",
                    "district_code": district,
                    "date_local": day,
                    **dict(zip(CORE, values, strict=True)),
                    "inflow_m3s": None,
                    "inflow_missing_reason": "not_reported",
                    "vertical_datum": None,
                    "datum_missing_reason": "not_reported",
                    "quality_details": details,
                }
            )
        table = pa.Table.from_pylist(rows, schema=pa.schema([*envelope_schema(), *MEASURES]))
        validate_table(table, measures=CORE)
        return with_mapping(
            table,
            {
                HEADERS[0]: "reservoir_id",
                HEADERS[1]: "district_code",
                HEADERS[2]: "level_m",
                HEADERS[3]: "storage_mcm",
                HEADERS[15]: "capacity_mcm",
                "report title date": "date_local",
            },
            MAPPING_VERSION,
        )
