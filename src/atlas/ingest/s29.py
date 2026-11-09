"""S29 OpenCity KSNDMC annual rainfall (T080). Field map: configs/sources/s29.yaml; rules: D113.

Annual totals only: one CSV per year for districts, taluks and hoblis (rows marked D, T or H, then
unmarked region and State totals) and one 2023 file of station totals. Areas have no codes, so
the ID is the published name path; a path repeated within a file is flagged duplicate. The 2025
file has no level marker and is refused rather than guessed. Files are fetched 10 seconds apart
(robots.txt Crawl-Delay).
"""

from __future__ import annotations

import csv
import hashlib
import io
import time
from collections import Counter
from collections.abc import Callable
from datetime import date

import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.asof import local_midnight_utc
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S29"
HOSTS = {"data.opencity.in"}
PAUSE_S = 10.0  # robots.txt Crawl-Delay: 10 (T079 e01)
_R = "https://data.opencity.in/dataset/03e23dd0-8f29-4249-a28a-67bdf8fd07b3/resource"
_FILES = {  # resource id and file name per year, as listed on the dataset page (T079 e02)
    2020: ("cc183e5a-5408-4431-8dad-0f350d66deff", "741349d2-9f58-45ae-9744-b6d5c10a8b7f.csv"),
    2021: ("534eace1-0121-4054-80a0-cf3ce1f9a04b", "275cb296-b3aa-4c96-b614-c3c3ca19dec0.csv"),
    2022: ("50aed54d-bc1e-41cf-8776-9bc1ca6e3500", "d9c463e4-3203-49fd-95c3-33b79f85c9b3.csv"),
    2023: ("dcedf0af-82ae-414b-b2b7-5c6adf560262", "0dbfcd4a-75d8-4c78-8594-b2aece2e479c.csv"),
    2024: ("9a86a46b-e7ca-4703-a17e-91daf9af1385", "0ec5ad8d-be55-4e92-a942-6918c025735b.csv"),
    2025: ("b1b9805f-1df4-4049-bce7-31563c33710f", "karnataka_rainfall_2025_table1_1.csv"),
}
FILES = {year: f"{_R}/{rid}/download/{name}" for year, (rid, name) in _FILES.items()}
MARKER = "District(D)/Taluk(T)/Hobli(H)"
# layout name -> (name column, normal column, actual column, departure column)
LAYOUTS = {
    "seasonal": (2, 12, 13, 14),  # 2020: annual columns after the seasonal ones
    "annual": (1, 2, 3, 4),  # 2021, 2022, 2024
}
LEVELS = {"D": "district", "T": "taluk", "H": "hobli"}
MAPPING_VERSION = "s29-v1"
LICENCE_ID = "public-domain-opencity-ksndmc"
MEASURES = pa.schema(
    [
        pa.field("area_level", pa.string(), False),
        pa.field("area_id", pa.string(), False),
        pa.field("year", pa.int64(), False),
        pa.field("rain_mm", pa.float64(), True),
        pa.field("normal_mm", pa.float64(), True),
        pa.field("departure_pct", pa.float64(), True),
        pa.field("coverage", pa.float64(), True),
    ]
)


def _rows(raw: RawArtifact) -> list[list[str]]:
    data = raw.path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    try:
        return list(csv.reader(io.StringIO(text)))
    except csv.Error as exc:
        raise IngestError(f"{SOURCE_ID}: unreadable CSV {raw.source_url}") from exc


def _number(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise IngestError(f"{SOURCE_ID}: not a number: {value!r}") from exc


def _layout(header: list[str]) -> str:
    if header[:4] == ["DISTRICT", "TALUK", "STATION", "TOTAL_RAIN (mm)"]:
        return "station"
    if header and header[0] == MARKER:
        if header[12:14] == ["Annual Normal(mm)", "Annual Actual (mm)"]:
            return "seasonal"
        if header[2:4] == ["Normal (mm)", "Actual (mm)"]:
            return "annual"
    if header and header[0] == "Sl.No":
        raise IngestError(f"{SOURCE_ID}: unmarked layout (no D/T/H column); levels unknown (D113)")
    raise IngestError(f"{SOURCE_ID}: columns changed: {header[:6]}")


class S29:
    def __init__(
        self,
        state: str,
        years: tuple[int, ...] = (2020, 2021, 2022, 2023, 2024),
        fetcher: Fetcher | None = None,
        pause: Callable[[float], None] = time.sleep,
    ):
        unknown = set(years) - set(FILES)
        if unknown:
            raise ValueError(f"no published file for {sorted(unknown)}")
        self.state, self.years, self.fetcher, self.pause = state, years, fetcher, pause

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        out = []
        for i, year in enumerate(self.years):
            if i:
                self.pause(PAUSE_S)
            out.append(self.fetcher.fetch_bytes(ctx, FILES[year], mapping_version=MAPPING_VERSION))
        return out

    def parse(self, raw: RawArtifact, config: SourceConfig, *, year: int) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        rows = _rows(raw)
        if len(rows) < 2:
            raise IngestError(f"{SOURCE_ID}: empty file {raw.source_url}")
        layout = _layout(rows[0])
        found: list[tuple[str, str, float | None, float | None, float | None]] = []
        if layout == "station":
            for r in rows[1:]:
                if not any(c.strip() for c in r):
                    continue
                path = " / ".join(c.strip() for c in r[:3])
                found.append(("station", path, _number(r[3]), None, None))
        else:
            name_col, normal_col, actual_col, dep_col = LAYOUTS[layout]
            district = taluk = None
            for r in rows[1:]:
                if not any(c.strip() for c in r):
                    continue
                marker, name = r[0].strip(), r[name_col].strip()
                if marker == "D":
                    district, taluk, path = name, None, name
                elif marker == "T":
                    taluk, path = name, f"{district} / {name}"
                elif marker == "H":
                    path = f"{district} / {taluk} / {name}"
                elif not marker and name:
                    level = "state" if name.lower() == "state" else "region"
                    marker, path = level, name.split(".", 1)[-1]
                else:
                    raise IngestError(f"{SOURCE_ID}: unknown level marker {marker!r}")
                if marker in LEVELS and (district is None or (marker == "H" and taluk is None)):
                    raise IngestError(f"{SOURCE_ID}: {name} appears before its district or taluk")
                found.append(
                    (
                        LEVELS.get(marker, marker),
                        path,
                        _number(r[actual_col]),
                        _number(r[normal_col]),
                        _number(r[dep_col]),
                    )
                )
        if not found:
            raise IngestError(f"{SOURCE_ID}: no rainfall rows in {raw.source_url}")
        repeats = Counter((level, path) for level, path, *_ in found)
        for _, _, rain, normal, _ in found:
            if any(v is not None and v < 0 for v in (rain, normal)):
                raise IngestError(f"{SOURCE_ID}: negative rainfall in {raw.source_url}")

        n, fetched = len(found), raw.fetched_at
        cols = {
            "area_level": [f[0] for f in found],
            "area_id": [f[1] for f in found],
            "year": [year] * n,
            "rain_mm": [f[2] for f in found],
            "normal_mm": [f[3] for f in found],
            "departure_pct": [f[4] for f in found],
            "coverage": [None] * n,  # not published (D113)
        }
        reasons = ["not_reported" if f[2] is None else None for f in found]
        flags = [
            (["duplicate"] if repeats[(f[0], f[1])] > 1 else []) + (["missing"] if r else [])
            for f, r in zip(found, reasons, strict=True)
        ]
        end = local_midnight_utc(date(year + 1, 1, 1))  # annual total for the calendar year
        common = {
            "source_id": [SOURCE_ID] * n,
            "state": [self.state] * n,
            "record_id": [
                hashlib.sha256(f"{year}|{level}|{path}|{i}".encode()).hexdigest()
                for i, (level, path, *_) in enumerate(found)
            ],
            "snapshot_id": [f"{SOURCE_ID}-{year}-{raw.sha256[:12]}"] * n,
            "observed_at": [None] * n,
            "valid_at": [end] * n,
            "issued_at": [None] * n,
            "available_at": [fetched] * n,
            "fetched_at": [fetched] * n,
            "published_at": [None] * n,
            "source_url": [raw.source_url] * n,
            "raw_sha256": [raw.sha256] * n,
            "schema_version": [1] * n,
            "mapping_version": [MAPPING_VERSION] * n,
            "provenance": ["official"] * n,  # KSNDMC totals republished by OpenCity
            "quality_flags": flags,
            "licence_id": [LICENCE_ID] * n,
            "redistribution_allowed": [True] * n,  # "Other (Public Domain)" (T079 e02)
            "place_id": [None] * n,
            "boundary_version": [None] * n,
            "missing_reason": reasons,
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | cols, schema=schema)
        validate_table(table, measures=["rain_mm"])
        mapping = {
            "D/T/H rows and names": "area_level, area_id",
            "Actual (mm) / Annual Actual (mm) / TOTAL_RAIN (mm)": "rain_mm",
            "Normal (mm) / Annual Normal(mm)": "normal_mm",
            "% DEP / Departure (%)": "departure_pct",
        }
        return with_mapping(table, mapping, MAPPING_VERSION)
