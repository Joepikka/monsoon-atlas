"""Karnataka hospital access equity (D195).

For every WorldPop 2025 1 km cell (S16) in Karnataka, the straight-line distance from the cell
centre to the nearest OpenStreetMap hospital (S18, `amenity=hospital`). Each person counts once,
weighted by the cell's population. Per district (S17): population-weighted mean and median
distance, the share of people beyond 5 and 10 km, and statewide inequality (weighted Gini and a
Lorenz curve of distance across people).

Limits, reported with every number: straight-line, not travel distance or time; OSM hospitals are
volunteer-mapped and thinner in rural areas, so remote distances are upper bounds; public and
private hospitals of any size count the same; WorldPop is a model at 1 km.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

EARTH_KM = 6371.0088


def nearest_km(cells: np.ndarray, sites: np.ndarray) -> np.ndarray:
    """Great-circle km from each (lon, lat) cell to its nearest site (exact for the KD-tree pick).

    The KD-tree runs on 3-D unit vectors, where the chord order equals the great-circle order,
    so the nearest site is exact everywhere, not only near one latitude."""
    from scipy.spatial import cKDTree

    def unit(lonlat: np.ndarray) -> np.ndarray:
        lon, lat = np.radians(lonlat[:, 0]), np.radians(lonlat[:, 1])
        return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])

    chord, _ = cKDTree(unit(sites)).query(unit(cells))
    return 2 * EARTH_KM * np.arcsin(np.clip(chord / 2, 0, 1))


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cum = np.cumsum(w)
    return float(v[np.searchsorted(cum, q * cum[-1])])


def weighted_gini(values: np.ndarray, weights: np.ndarray) -> float:
    """Gini of `values` across people (weights = people); 0 = everyone equally far."""
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cw = np.cumsum(w)
    cvw = np.cumsum(v * w)
    total_w, total_vw = cw[-1], cvw[-1]
    if total_vw == 0:
        return 0.0
    # area under the Lorenz curve by trapezoids over population shares
    x = np.concatenate([[0], cw / total_w])
    y = np.concatenate([[0], cvw / total_vw])
    area = np.trapezoid(y, x)
    return float(1 - 2 * area)


def lorenz(values: np.ndarray, weights: np.ndarray, points: int = 21) -> list[list[float]]:
    """[population share, distance share] at evenly spaced population shares."""
    order = np.argsort(values)
    v, w = values[order], weights[order]
    x = np.concatenate([[0], np.cumsum(w) / w.sum()])
    y = np.concatenate([[0], np.cumsum(v * w) / (v * w).sum()])
    grid = np.linspace(0, 1, points)
    return [[round(float(g), 3), round(float(np.interp(g, x, y)), 4)] for g in grid]


def summarise(km: np.ndarray, people: np.ndarray) -> dict:
    total = float(people.sum())
    return {
        "people": round(total),
        "mean_km": round(float((km * people).sum() / total), 2),
        "median_km": round(weighted_quantile(km, people, 0.5), 2),
        "p90_km": round(weighted_quantile(km, people, 0.9), 2),
        "share_beyond_5km": round(float(people[km > 5].sum() / total), 4),
        "share_beyond_10km": round(float(people[km > 10].sum() / total), 4),
    }


def by_district(km: np.ndarray, people: np.ndarray, district: Sequence[str | None]) -> list[dict]:
    names = np.array([d if d is not None else "" for d in district])
    rows = []
    for name in sorted(set(names) - {""}):
        mask = names == name
        if people[mask].sum() > 0:
            rows.append({"district": name, **summarise(km[mask], people[mask])})
    return sorted(rows, key=lambda r: -r["mean_km"])


def km_between(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_KM * math.asin(math.sqrt(a))


def build(out) -> dict:  # pragma: no cover - needs local raw files (data/raw)
    """Write the report files into `out` (a Path); returns the summary."""
    import csv
    import json
    from pathlib import Path

    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    import rasterio
    import shapely

    from atlas.config import load_state
    from atlas.ingest.s16 import S16
    from atlas.ingest.s17 import S17
    from atlas.ingest.s18 import S18
    from atlas.ingest.s18_prepare import evidence

    root = Path(__file__).resolve().parents[3]
    out = Path(out)
    state = load_state(root / "configs/states/ka.yaml")
    adm1, adm2 = evidence("s17", "e05"), evidence("s17", "e06")
    districts = S17("ka").parse(adm2, state.source("S17"), adm1=adm1).to_pylist()
    shapes = [shapely.from_wkb(d["geometry"]) for d in districts]
    area = shapely.union_all(shapes)

    pbf = evidence("s18", "e05")
    cache = root / "data/clean/S18" / f"hospitals-{pbf.sha256[:12]}.parquet"
    if not cache.exists():
        parts = [
            t.filter(pc.equal(t["feature_kind"], "hospital")).select(["osm_id", "geometry"])
            for t in S18("ka", shapely.to_wkb(area)).parse_batches(pbf, state.source("S18"))
        ]
        cache.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.concat_tables(parts), cache)
    hosp = pq.read_table(cache)
    centres = shapely.centroid(shapely.from_wkb(hosp["geometry"].to_pylist()))
    sites = np.column_stack([shapely.get_x(centres), shapely.get_y(centres)])

    worldpop = evidence("s16", "e05")
    cells = S16("ka", 2025).parse(worldpop, state.source("S16"), boundary=adm1)
    ids = cells["cell_id"].to_pylist()
    people = np.array(cells["population"].to_pylist(), dtype=float)
    with rasterio.open(worldpop.path) as src:
        rc = np.array([[int(x[1:]) for x in i.split("_")[1:]] for i in ids])
        xs, ys = rasterio.transform.xy(src.transform, rc[:, 0], rc[:, 1], offset="center")
    lonlat = np.column_stack([np.asarray(xs, float), np.asarray(ys, float)])

    tree = shapely.STRtree(shapes)
    points = shapely.points(lonlat)
    hit_cell, hit_shape = tree.query(points, predicate="within")
    district = [None] * len(ids)
    for c, s in zip(hit_cell, hit_shape, strict=True):
        district[c] = districts[s]["name"]

    km = nearest_km(lonlat, sites)
    state_row = summarise(km, people)
    rows = by_district(km, people, district)
    summary = {
        "state": "ka",
        "hospitals": int(len(sites)),
        "cells": int(len(ids)),
        "unassigned_people": round(float(people[[d is None for d in district]].sum())),
        "statewide": state_row | {"gini": round(weighted_gini(km, people), 4)},
        "lorenz": lorenz(km, people),
        "inputs": {"S16": worldpop.sha256, "S17": adm2.sha256, "S18": pbf.sha256},
        "limits": [
            "Straight-line distance from the 1 km cell centre, not road distance or travel time.",
            "OpenStreetMap hospitals are volunteer-mapped and thinner in rural areas, so remote "
            "distances are upper bounds; clinics and primary health centres tagged otherwise "
            "are not counted.",
            "Public and private hospitals of any size count the same; capacity is unknown.",
            "WorldPop 2025 is a modelled 1 km population estimate.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(
        json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    with open(out / "district_access.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return {"summary": summary, "rows": rows, "lonlat": lonlat, "people": people, "km": km}
