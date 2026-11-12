"""S36 KSDMA post-disaster assessment (T122). Field map: configs/sources/s36.yaml.

Three district tables from the 2018 flood memoranda PDFs (text layer read with pypdf): NRSC flooded
area "as on 16-7-2018" and human fatalities for each memorandum period. Rows keep the published
district name with document, page and source text; they are not mapped to district IDs and never
downscaled. The PDFs are copyrighted (all rights reserved): raw files stay in data/raw. Other
tables and the 2013 memorandum are not parsed.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from typing import NamedTuple

import pyarrow as pa
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.asof import local_midnight_utc
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S36"
HOSTS = {"sdma.kerala.gov.in"}
_U = "https://sdma.kerala.gov.in/wp-content/uploads/2019/08"
MAPPING_VERSION = "s36-v1"
LICENCE_ID = "ksdma-all-rights-reserved"


class Table(NamedTuple):
    url: str
    document: str
    submitted: date  # "Submitted on" date on the Disaster Memoranda page (T121 e03)
    period: tuple[date, date]
    page: int
    header: str  # table header line, which fixes the claim and its unit
    claim_type: str
    unit: str
    as_on: date | None
    rows: int


M1 = (f"{_U}/Memorandum1-Floods-2018.pdf", "Memorandum1-Floods-2018.pdf", date(2018, 8, 7))
M1 += ((date(2018, 5, 29), date(2018, 7, 31)),)
M2 = (f"{_U}/Memorandum2-Floods-2018.pdf", "Memorandum2-Floods-2018.pdf", date(2018, 9, 13))
M2 += ((date(2018, 8, 1), date(2018, 8, 30)),)
TABLES = (
    Table(*M1, 9, "District Flooded Area (ha)", "flooded_area_ha", "ha", date(2018, 7, 16), 7),
    Table(*M1, 14, "District Fatalities", "human_fatalities", "persons", None, 14),
    Table(*M2, 20, "District Fatalities", "human_fatalities", "persons", None, 14),
)
MEASURES = pa.schema(
    [
        pa.field("document_id", pa.string(), False),
        pa.field("page", pa.int64(), False),
        pa.field("district_id", pa.string(), False),
        pa.field("claim_type", pa.string(), False),
        pa.field("value", pa.int64(), False),
        pa.field("unit", pa.string(), False),
        pa.field("event_date", pa.date32(), True),
        pa.field("date_basis", pa.string(), False),
        pa.field("period_start", pa.date32(), False),
        pa.field("period_end", pa.date32(), False),
        pa.field("excerpt", pa.string(), False),
    ]
)
_ROW = re.compile(r"^([A-Za-z][A-Za-z ]*?)\s+(\d+)(?:\s+\d+)?$")


def page_text(path, page: int) -> str:
    try:
        return PdfReader(path).pages[page - 1].extract_text() or ""
    except (PyPdfError, OSError, IndexError, ValueError) as exc:
        raise IngestError(f"{SOURCE_ID}: unreadable PDF page {page}") from exc


def table_rows(text: str, spec: Table) -> list[tuple[str, int, str]]:
    """District rows under the table header, up to its Total row, checked against that total."""
    lines = [" ".join(line.split()) for line in text.splitlines()]
    start = next((i for i, line in enumerate(lines) if line.startswith(spec.header)), None)
    if start is None:
        raise IngestError(f"{SOURCE_ID}: columns changed on page {spec.page}: {spec.header!r}")
    rows: list[tuple[str, int, str]] = []
    for line in lines[start + 1 :]:
        m = _ROW.match(line)
        if m is None:
            raise IngestError(f"{SOURCE_ID}: unreadable row on page {spec.page}: {line!r}")
        if m[1] == "Total":
            if int(m[2]) != sum(r[1] for r in rows):
                raise IngestError(f"{SOURCE_ID}: rows do not sum to the Total on page {spec.page}")
            break
        rows.append((m[1], int(m[2]), line))
    else:
        raise IngestError(f"{SOURCE_ID}: no Total row on page {spec.page}")
    if len(rows) != spec.rows or len({r[0] for r in rows}) != spec.rows:
        raise IngestError(f"{SOURCE_ID}: expected {spec.rows} districts on page {spec.page}")
    return rows


class S36:
    def __init__(self, state: str = "kl", fetcher: Fetcher | None = None):
        self.state, self.fetcher = state, fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        if self.fetcher is None:
            raise IngestError(f"{SOURCE_ID}: shared Fetcher required")
        urls = dict.fromkeys(t.url for t in TABLES)  # one-off: each memorandum once
        return [self.fetcher.fetch_large(ctx, u, mapping_version=MAPPING_VERSION) for u in urls]

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        specs = [t for t in TABLES if t.url == raw.source_url]
        if not specs:
            raise IngestError(f"{SOURCE_ID}: no table map for {raw.source_url}")
        found = [
            (t, d, v, line)
            for t in specs
            for d, v, line in table_rows(page_text(raw.path, t.page), t)
        ]
        n, fetched = len(found), raw.fetched_at
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"{t.document}|{t.page}|{t.claim_type}|{d}".encode()).hexdigest()
                for t, d, _, _ in found
            ],
            "snapshot_id": [f"{SOURCE_ID}-{raw.sha256[:12]}"] * n,
            "observed_at": [local_midnight_utc(t.as_on) if t.as_on else None for t, *_ in found],
            "valid_at": [
                local_midnight_utc(t.as_on or t.period[1] + timedelta(days=1)) for t, *_ in found
            ],
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [local_midnight_utc(t.submitted) for t, *_ in found],
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["official"] * n,
            "quality_flags": [[] for _ in found],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [False] * n,  # all rights reserved (T121 licence)
            "place_id": [None] * n,  # published names only; no crosswalk guess
            "boundary_version": [None] * n,
            "missing_reason": [None] * n,
        }
        cols = {
            "document_id": [t.document for t, *_ in found],
            "page": [t.page for t, *_ in found],
            "district_id": [d for _, d, _, _ in found],
            "claim_type": [t.claim_type for t, *_ in found],
            "value": [v for _, _, v, _ in found],
            "unit": [t.unit for t, *_ in found],
            "event_date": [t.as_on for t, *_ in found],  # null for period totals (date_basis)
            "date_basis": ["as_on" if t.as_on else "period_total" for t, *_ in found],
            "period_start": [t.period[0] for t, *_ in found],
            "period_end": [t.period[1] for t, *_ in found],
            "excerpt": [line for *_, line in found],
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | cols, schema=schema)
        validate_table(table, measures=["value"])
        mapping = {
            "PDF file name": "document_id",
            "PDF page number": "page",
            "District": "district_id",
            "table header": "claim_type",
            "table row text": "excerpt",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
