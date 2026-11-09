"""S08 IMD Pune 0.25 degree daily gridded rainfall (T058). Field map: configs/sources/s08.yaml.

Each year file is raw little-endian float32 with no header: one 135 x 129 grid per day,
longitude fastest, south to north, -999 outside the land mask (T057 evidence e03 to e06).
"""

from __future__ import annotations

import calendar
import hashlib
import time
from collections.abc import Sequence
from datetime import date, timedelta
from urllib.parse import parse_qs, urlsplit

import numpy as np
import pyarrow as pa

from atlas.config import SourceConfig
from atlas.contracts import FetchContext, RawArtifact
from atlas.data.validate import envelope_schema, validate_table, with_mapping
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.http import Fetcher

SOURCE_ID = "S08"
URL = "https://www.imdpune.gov.in/cmpg/Griddata/rainfall.php"
HOSTS = {"www.imdpune.gov.in"}
MAPPING_VERSION = "s08-v1"
LICENCE_ID = "S08-imd-disclaimer-no-reproduction"  # T057: raw stays local, derived outputs only
NX, NY, LON0, LAT0, STEP, UNDEF = 135, 129, 66.5, 6.5, 0.25, -999.0
# shortcut: a bounding box keeps the state's cells; T101 assigns cells to districts with polygons
# lat_min, lat_max, lon_min, lon_max. "kl" (T142, D127) also holds Tamil Nadu and Karnataka border
# cells: it is a cell box, not the Kerala boundary (S17 is not yet enabled for Kerala).
BOXES = {"ka": (11.5, 18.5, 74.0, 78.75), "kl": (8.25, 12.75, 74.75, 77.5)}
MEASURES = pa.schema(
    [
        pa.field("cell_id", pa.string(), False),
        pa.field("date_local", pa.date32(), False),
        pa.field("rain_mm", pa.float64(), True),
        pa.field("grid_resolution_deg", pa.float64(), False),
    ]
)


def _year(raw: RawArtifact) -> int:
    rain = parse_qs(urlsplit(raw.source_url).query).get("rain")
    if not rain or not rain[0].isdigit():
        raise IngestError(f"{SOURCE_ID}: no year in {raw.source_url}")
    return int(rain[0])


def read_grid(raw: RawArtifact) -> tuple[int, np.ndarray]:
    """(year, days x 129 x 135 float32 grid) after the size and land-mask checks (T057)."""
    year = _year(raw)
    days = 366 if calendar.isleap(year) else 365
    data = raw.path.read_bytes()
    if len(data) != days * NY * NX * 4:
        raise IngestError(
            f"{SOURCE_ID} {year}: {len(data)} bytes, expected {days} days of {NX}x{NY} float32"
        )
    grid = np.frombuffer(data, dtype="<f4").reshape(days, NY, NX)
    land = grid[0] != UNDEF
    # -999 on a land cell is a missing day (12 Oct 2023: 79 cells, D40); a sea cell that gains a
    # value is a real mask change and fails.
    if ((grid != UNDEF) & ~land).any():
        raise IngestError(f"{SOURCE_ID} {year}: land mask changes within the year")
    return year, grid


def state_cells(state: str, land: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Row and column indexes and IDs of land cells inside the state's cell box."""
    lat = LAT0 + STEP * np.arange(NY)
    lon = LON0 + STEP * np.arange(NX)
    lat_min, lat_max, lon_min, lon_max = BOXES[state]
    box = ((lat >= lat_min) & (lat <= lat_max))[:, None] & ((lon >= lon_min) & (lon <= lon_max))[
        None, :
    ]
    rows, cols = np.nonzero(land & box)
    cells = [f"imd025_{lat[r]:.2f}N_{lon[c]:.2f}E" for r, c in zip(rows, cols, strict=True)]
    return rows, cols, cells


class S08:
    def __init__(self, state: str, years: Sequence[int], fetcher: Fetcher | None = None):
        if state not in BOXES:
            raise SourceUnavailable(f"{SOURCE_ID}: no cell box for state {state}")
        self.state, self.years, self.fetcher = state, list(years), fetcher

    def fetch(self, ctx: FetchContext) -> list[RawArtifact]:
        """One request per year file, 3 s apart (no robots.txt or quota is published)."""
        out = []
        for i, year in enumerate(self.years):
            if i:
                time.sleep(3.0)
            out.append(
                self.fetcher.fetch_bytes(
                    ctx, URL, mapping_version=MAPPING_VERSION, params={"rain": str(year)}
                )
            )
        return out

    def parse(self, raw: RawArtifact, config: SourceConfig) -> pa.Table:
        if not config.enabled:
            raise SourceUnavailable(f"{SOURCE_ID} is disabled; {config.verify_task} must pass")
        year, grid = read_grid(raw)
        days = grid.shape[0]
        rows, cols, cells = state_cells(self.state, grid[0] != UNDEF)
        values = grid[:, rows, cols].astype(np.float64).ravel()  # day-major, cell-minor
        missing = values == UNDEF
        bad = missing | ~np.isfinite(values) | (values < 0)

        n = len(values)
        day_list = [date(year, 1, 1) + timedelta(d) for d in range(days)]
        cell_col = cells * days
        date_col = np.repeat(np.array(day_list, dtype="datetime64[D]"), len(cells))
        # Neither the page nor Pai et al. (2014) gives the 24-hour window: use its latest
        # possible end, 08:30 IST (03:00 UTC) on the next day, so daily features cannot leak.
        valid_at = (date_col + np.timedelta64(1, "D")).astype("datetime64[us]") + np.timedelta64(
            3, "h"
        )
        record_ids = [
            hashlib.sha256(f"{c}|{d}|{raw.sha256}".encode()).hexdigest()
            for c, d in zip(cell_col, date_col.astype(str), strict=True)
        ]
        rain = pa.array(np.where(bad, np.nan, values), pa.float64(), mask=bad)
        common = {
            "source_id": pa.array([SOURCE_ID] * n),
            "state": pa.array([self.state] * n),
            "record_id": pa.array(record_ids),
            "snapshot_id": pa.array([f"{SOURCE_ID}-{year}-{raw.sha256[:16]}"] * n),
            "observed_at": pa.nulls(n, pa.timestamp("us", tz="UTC")),
            "valid_at": pa.array(valid_at, pa.timestamp("us", tz="UTC")),
            "issued_at": pa.nulls(n, pa.timestamp("us", tz="UTC")),
            "available_at": pa.array([raw.fetched_at] * n, pa.timestamp("us", tz="UTC")),
            "fetched_at": pa.array([raw.fetched_at] * n, pa.timestamp("us", tz="UTC")),
            "published_at": pa.nulls(n, pa.timestamp("us", tz="UTC")),
            "source_url": pa.array([raw.source_url] * n),
            "raw_sha256": pa.array([raw.sha256] * n),
            "schema_version": pa.array([1] * n, pa.int64()),
            "mapping_version": pa.array([MAPPING_VERSION] * n),
            "provenance": pa.array(["official"] * n),
            "quality_flags": pa.array(
                [
                    ["missing"] if m else ["out_of_range"] if b else []
                    for m, b in zip(missing, bad, strict=True)
                ],
                pa.list_(pa.string()),
            ),
            "licence_id": pa.array([LICENCE_ID] * n),
            "redistribution_allowed": pa.array([False] * n),
            "place_id": pa.nulls(n, pa.string()),
            "boundary_version": pa.nulls(n, pa.string()),
            "missing_reason": pa.array(
                [
                    "not_reported" if m else "quality_rejected" if b else None
                    for m, b in zip(missing, bad, strict=True)
                ],
                pa.string(),
            ),
        }
        measures = {
            "cell_id": pa.array(cell_col),
            "date_local": pa.array(date_col, pa.date32()),
            "rain_mm": rain,
            "grid_resolution_deg": pa.array([STEP] * n, pa.float64()),
        }
        schema = pa.schema([*envelope_schema(), *MEASURES])
        table = pa.Table.from_pydict(common | measures, schema=schema)
        validate_table(table, measures=["rain_mm"])
        mapping = {"record index + year": "date_local", "grid I,J": "cell_id", "rf": "rain_mm"}
        return with_mapping(table, mapping, MAPPING_VERSION)
