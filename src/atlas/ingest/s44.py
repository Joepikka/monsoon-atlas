"""S44 district crime statistics (T088). Field map: configs/sources/s44.yaml; rules: D114.

Karnataka State Police annual tables republished by OpenCity: registered-case counts per police
unit, never names or case locations. Units are police jurisdictions, so each row keeps the
published unit with its kind (district, commissionerate, range subtotal, state total or no area);
mapping units to districts is a separate crosswalk. Registered cases are not crime incidence.
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import date

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.asof import local_midnight_utc
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S44"
HOSTS = {"data.opencity.in"}
_D = "https://data.opencity.in/dataset"
FILES = {  # tables listed on the OpenCity dataset pages (T087 e01, e02)
    2023: f"{_D}/e8f4a688-6afa-4a69-b7ba-3c99dd4abb62/resource/3c92405a-36e2-495e-8abd-ccebafb3cbb9"
    "/download/ffce2bf3-1202-489d-8af5-f156c2e9b793.csv",
    2024: f"{_D}/e2efa3e0-cb3a-4d5b-91ae-e08dcb471267/resource/3f1bbc2e-e7a0-450f-8831-6b31c140859c"
    "/download/2a1e057f-3b0b-42e4-ae4b-6cdb49902d31.csv",
}
NO_AREA = {"karnataka railways", "krailways", "coastal security police", "cid"}
MAPPING_VERSION = "s44-v1"
LICENCE_ID = "public-domain-opencity-ksp"
MEASURES = pa.schema(
    [
        pa.field("district_id", pa.string(), False),
        pa.field("unit_kind", pa.string(), False),
        pa.field("year", pa.int64(), False),
        pa.field("offence_category", pa.string(), False),
        pa.field("count", pa.int64(), True),
        pa.field("population_year", pa.int64(), True),
    ]
)


def unit_kind(name: str) -> str:
    low = name.lower()
    if low == "total":
        return "state_total"
    if low.endswith(" range"):
        return "range_subtotal"
    if low in NO_AREA:
        return "no_area"
    if low.endswith(" city"):
        return "commissionerate"
    return "district"


def _count(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    if not value.isdigit():
        raise IngestError(f"{SOURCE_ID}: not a case count: {value!r}")
    return int(value)


class S44:
    def __init__(self, state: str, fetcher: Fetcher | None = None):
        self.state, self.fetcher = state, fetcher

    def fetch(self, ctx: FetchContext, year: int) -> list[RawArtifact]:
        if year not in FILES:
            raise ValueError(f"no verified table for {year}")
        return [self.fetcher.fetch_bytes(ctx, FILES[year], mapping_version=MAPPING_VERSION)]

    def parse(self, raw: RawArtifact, config: SourceConfig, *, year: int) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        try:
            rows = list(csv.reader(io.StringIO(raw.path.read_bytes().decode("utf-8-sig"))))
        except (UnicodeDecodeError, csv.Error) as exc:
            raise IngestError(f"{SOURCE_ID}: unreadable CSV {raw.source_url}") from exc
        if len(rows) < 2:
            raise IngestError(f"{SOURCE_ID}: empty table {raw.source_url}")
        header = [h.strip() for h in rows[0]]
        if header[:2] == ["Sl No", "DISTRICT/UNITS"] and len(header) > 2:
            name_col, first = 1, 2  # offence heads (2024)
        elif header == ["Districts", "IPC Cases", "SLL Cases", "Total"]:
            name_col, first = 0, 1  # IPC, SLL and total (2022, 2023)
        else:
            raise IngestError(f"{SOURCE_ID}: columns changed: {header[:4]}")
        heads = header[first:]
        found: list[tuple[str, str, str, int | None]] = []
        for r in rows[1:]:
            if not any(c.strip() for c in r):
                continue
            if len(r) < len(header):
                raise IngestError(f"{SOURCE_ID}: short row {r[:2]}")
            name, values = r[name_col].strip(), r[first : first + len(heads)]
            if not any(v.strip() for v in values):
                continue  # a heading row such as "Commissionerates"
            kind = unit_kind(name)
            for head, value in zip(heads, values, strict=True):
                found.append((name, kind, head, _count(value)))
        if not found:
            raise IngestError(f"{SOURCE_ID}: no counts in {raw.source_url}")

        n, fetched = len(found), raw.fetched_at
        reasons = ["not_reported" if f[3] is None else None for f in found]
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"{year}|{u}|{h}".encode()).hexdigest() for u, _, h, _ in found
            ],
            "snapshot_id": [f"{SOURCE_ID}-{year}-{raw.sha256[:12]}"] * n,
            "observed_at": [None] * n,
            "valid_at": [local_midnight_utc(date(year + 1, 1, 1))] * n,
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [None] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["official"] * n,  # police totals republished by OpenCity
            "quality_flags": [["missing"] if r else [] for r in reasons],
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # "Other (Public Domain)" (T087 e01)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": reasons,
        }
        cols = {
            "district_id": [f[0] for f in found],
            "unit_kind": [f[1] for f in found],
            "year": [year] * n,
            "offence_category": [f[2] for f in found],
            "count": [f[3] for f in found],
            "population_year": [None] * n,  # not published (T087)
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | cols, schema=schema)
        validate_table(table, measures=["count"])
        mapping = {
            "DISTRICT/UNITS / Districts": "district_id",
            "column header": "offence_category",
            "cell value": "count",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
