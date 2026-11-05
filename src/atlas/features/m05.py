"""M05 Karnataka drought outlook: target, features, data gate and splits (T101).

Unit: district (S17, geoBoundaries 2021 lines, 30 districts), because no Karnataka taluk
polygons are verified (T030, D29). Rain: S08 IMD daily grids summed by month per 0.25 degree
cell, then averaged per district with weights equal to the cell's overlap area in m2.

Target at issue month t (issued 00:00 IST on day 1 of t): SPI-3 of month t, the standardised
3-month total of t-2..t, using a gamma distribution (with a zero-rain share) fitted per district
and calendar month on 1981-2010 only. Drought = SPI-3 < -1.0. Features use months up to t-1.
This is a hindcast (D39): S08 files are yearly, so live issue-time rain is not available.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa

from atlas.contracts import RawArtifact
from atlas.data.asof import local_midnight_utc
from atlas.ingest.base import IngestError, SourceUnavailable
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s08 import LAT0, LON0, STEP, UNDEF, URL, read_grid, state_cells
from atlas.models.splits import DatasetSplit, write_manifest

REFERENCE = (1981, 2010)
MIN_YEARS = 30
DROUGHT_SPI = -1.0
SCALES = (1, 3, 6)
PURGE_DAYS = 92  # the 3-month SPI-3 window: no training target may share a month with a test target


def year_artifacts(raw_root: Path, years: range) -> list[RawArtifact]:
    """Stored S08 year files found through the raw ledger (fetched by the S08 adapter)."""
    store, out = RawStore(raw_root), []
    for year in years:
        entry = store.latest_ok(f"{URL}?rain={year}")
        if entry is None:
            raise SourceUnavailable(f"S08 {year} is not in {raw_root}; fetch it first")
        a = entry["artifact"]
        out.append(RawArtifact.model_validate(a | {"path": Path(a["path"])}))
    return out


def _cell_polygons(rows: np.ndarray, cols: np.ndarray, ids: list[str]) -> dict[str, bytes]:
    import shapely

    half = STEP / 2
    return {
        cid: shapely.box(
            LON0 + STEP * c - half,
            LAT0 + STEP * r - half,
            LON0 + STEP * c + half,
            LAT0 + STEP * r + half,
        ).wkb
        for r, c, cid in zip(rows, cols, ids, strict=True)
    }


def district_monthly_rain(raws: list[RawArtifact], districts: pa.Table) -> pa.Table:
    """(place_id, name, month, rain_mm): area-weighted monthly district rain."""
    from atlas.spatial.crosswalk import area_weights

    weights = mask = ids = None
    out = {"place_id": [], "name": [], "month": [], "rain_mm": []}
    names = dict(zip(districts["place_id"].to_pylist(), districts["name"].to_pylist(), strict=True))
    for raw in sorted(raws, key=lambda a: a.source_url):
        year, grid = read_grid(raw)
        land = grid[0] != UNDEF
        if mask is None:
            mask = land
            rows, cols, ids = state_cells("ka", land)
            targets = dict(
                zip(
                    districts["place_id"].to_pylist(),
                    districts["geometry"].to_pylist(),
                    strict=True,
                )
            )
            w = area_weights(_cell_polygons(rows, cols, ids), targets)
            index = {cid: i for i, cid in enumerate(ids)}
            weights = {d: ([], []) for d in names}
            for s, t, m2 in zip(
                w["source_id"].to_pylist(),
                w["target_id"].to_pylist(),
                w["overlap_m2"].to_pylist(),
                strict=True,
            ):
                weights[t][0].append(index[s])
                weights[t][1].append(m2)
        elif not (land == mask).all():
            raise IngestError(f"S08 {year}: land mask differs from the first year")
        daily = grid[:, rows, cols].astype(np.float64)
        starts = [(date(year, m, 1) - date(year, 1, 1)).days for m in range(1, 13)]
        absent = np.add.reduceat(daily == UNDEF, starts, axis=0) > 0  # cell-months with a gap
        monthly = np.add.reduceat(np.where(daily == UNDEF, 0.0, daily), starts, axis=0)
        for d, (idx, m2) in weights.items():
            if not idx:
                raise IngestError(f"district {d} has no S08 land cells")
            w = np.where(absent[:, idx], 0.0, np.asarray(m2))  # drop gappy cells, D40
            share = w.sum(axis=1)
            values = np.where(
                share > 0, (monthly[:, idx] * w).sum(axis=1) / np.where(share > 0, share, 1), np.nan
            )
            for m in range(12):
                out["place_id"].append(d)
                out["name"].append(names[d])
                out["month"].append(date(year, m + 1, 1))
                out["rain_mm"].append(None if np.isnan(values[m]) else float(values[m]))
    return pa.table(
        out,
        schema=pa.schema(
            [
                ("place_id", pa.string()),
                ("name", pa.string()),
                ("month", pa.date32()),
                ("rain_mm", pa.float64()),
            ]
        ),
    )


def _spi(totals: np.ndarray, years: np.ndarray) -> np.ndarray:
    """SPI for one district, one calendar month and one scale; NaN where totals are NaN."""
    from scipy import stats

    ref = totals[(years >= REFERENCE[0]) & (years <= REFERENCE[1]) & np.isfinite(totals)]
    if len(ref) < 25:
        raise IngestError("fewer than 25 reference years for an SPI fit")
    zero = (ref <= 0).mean()
    wet = ref[ref > 0]
    if len(wet) >= 5 and wet.std() > 0:
        a, _, scale = stats.gamma.fit(wet, floc=0)
        cdf = zero + (1 - zero) * stats.gamma.cdf(np.where(totals > 0, totals, 0), a, scale=scale)
    else:  # almost always dry in this month: rank-based probabilities instead of a fit
        cdf = np.array([(ref <= x).mean() if np.isfinite(x) else np.nan for x in totals])
    return stats.norm.ppf(np.clip(cdf, 1e-6, 1 - 1e-6))


def spi_table(monthly: pa.Table) -> pa.Table:
    """Monthly rain plus spi1, spi3 and spi6 per district (reference 1981-2010 only)."""
    rows = monthly.to_pylist()
    by_district: dict[str, list[dict]] = {}
    for r in rows:
        by_district.setdefault(r["place_id"], []).append(r)
    out = []
    for series in by_district.values():
        series.sort(key=lambda r: r["month"])
        rain = np.array([np.nan if r["rain_mm"] is None else r["rain_mm"] for r in series])
        months = np.array([r["month"].month for r in series])
        years = np.array([r["month"].year for r in series])
        for k in SCALES:
            total = np.full(len(rain), np.nan)
            total[k - 1 :] = np.convolve(rain, np.ones(k), mode="valid")
            spi = np.full(len(rain), np.nan)
            for m in range(1, 13):
                sel = months == m
                spi[sel] = _spi(total[sel], years[sel])
            spi[np.isnan(total)] = np.nan
            for r, v in zip(series, spi, strict=True):
                r[f"spi{k}"] = None if np.isnan(v) else float(v)
        out += series
    return pa.Table.from_pylist(out)


def feature_rows(spi: pa.Table) -> pa.Table:
    """One row per district and issue month t: features from month t-1, target SPI-3 of t."""
    by_district: dict[str, list[dict]] = {}
    for r in spi.to_pylist():
        by_district.setdefault(r["place_id"], []).append(r)
    rows = []
    for series in by_district.values():
        series.sort(key=lambda r: r["month"])
        for prev, cur in zip(series, series[1:], strict=False):
            if prev["spi6"] is None or cur["spi3"] is None:
                continue
            rows.append(
                {
                    "place_id": cur["place_id"],
                    "name": cur["name"],
                    "issue_at": local_midnight_utc(cur["month"]),
                    "known_until": prev["month"],
                    "month_of_year": cur["month"].month,
                    "spi1_lag1": prev["spi1"],
                    "spi3_lag1": prev["spi3"],
                    "spi6_lag1": prev["spi6"],
                    "rain_lag1_mm": prev["rain_mm"],
                    "target_spi3": cur["spi3"],
                    "target_drought": cur["spi3"] < DROUGHT_SPI,
                    "target_month": cur["month"],
                }
            )
    return pa.Table.from_pylist(rows)


def gate(monthly: pa.Table, *, verified_taluks: bool) -> dict:
    """M05 data gate: at least 30 years of rain; without taluk polygons the unit is district."""
    years = sorted({m.year for m in monthly["month"].to_pylist()})
    reasons = (
        [] if len(years) >= MIN_YEARS else [f"only {len(years)} years of rain, need {MIN_YEARS}"]
    )
    unit = (
        "taluk"
        if verified_taluks
        else "district (no verified taluk polygons; geoBoundaries 2021 lines)"
    )
    return {
        "status": "blocked" if reasons else "ok",
        "reasons": reasons,
        "unit": unit,
        "years": [years[0], years[-1]] if years else [],
    }


def export_predictions(gate_result: dict, predictions: pa.Table) -> pa.Table:
    """A blocked model exports no prediction rows."""
    if gate_result["status"] != "ok":
        raise SourceUnavailable(f"M05 blocked: {'; '.join(gate_result['reasons'])}")
    return predictions


def splits() -> list[DatasetSplit]:
    """Plan dates (train 1981-2016, tune 2017-2018, calibrate 2019, test 2020-2024), purged."""
    train_end = date(2016, 9, 30)  # 93 days before 2017-01-01: no shared SPI-3 window
    periods = {
        "tune": (date(2017, 1, 1), date(2018, 12, 31)),
        "calibrate": (date(2019, 1, 1), date(2019, 12, 31)),
        "test": (date(2020, 1, 1), date(2024, 12, 31)),
    }
    return [
        DatasetSplit(
            name=name,
            train_start=date(1981, 7, 1),
            train_end=train_end,
            test_start=start,
            test_end=end,
            purge_days=PURGE_DAYS,
        )
        for name, (start, end) in periods.items()
    ]


def write_split_manifest(path: Path) -> str:
    return write_manifest(splits(), path)
