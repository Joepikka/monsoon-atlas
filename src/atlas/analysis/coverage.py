"""T041: BMTC population coverage study (Bengaluru, Bangalore district of S17).

A stop "covers" the walkable road length within RADIUS_M metres of it along the S18 OSM walking
network (D174), measured from the network node nearest the stop (the snap distance counts toward
the 500 m). A WorldPop 1 km cell (S16) is covered in proportion to its walkable length that is
covered, so each person is counted at most once however many catchments overlap, and covered plus
uncovered population equals the district total exactly. Cells with no mapped walkway count as
uncovered. Service is the scheduled BMTC weekday timetable of the unofficial Vonter GTFS (S30,
T029), not observed operations. Distances are great-circle metres along OSM ways.
"""

from __future__ import annotations

import heapq
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RADIUS_M = 500.0
SNAP_MAX_M = 100.0  # a stop farther than this from any walkable node is reported unsnapped
NO_WALK = frozenset({"motorway", "motorway_link"})  # plus any way tagged foot=no
SERVICE_DATE = date(2026, 9, 9)  # a Wednesday in the BMTC feed's single all-days service
DISTRICT = "Bangalore"
Node = tuple[float, float]  # (lon, lat) rounded to 1e-7 degrees: shared OSM nodes coincide


def metres(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371008.8 * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class Edge:
    u: Node
    v: Node
    length_m: float
    mid: Node


def walk_edges(ways: Iterable[tuple[str, list[tuple[float, float]]]]) -> list[Edge]:
    """Segments of walkable ways; `ways` yields (tags_json, [(lon, lat), ...])."""
    out = []
    for tags_json, coords in ways:
        tags = json.loads(tags_json)
        if tags.get("highway") in NO_WALK or tags.get("foot") == "no":
            continue
        pts = [(round(x, 7), round(y, 7)) for x, y in coords]
        for a, b in zip(pts, pts[1:], strict=False):
            if a != b:
                mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                out.append(Edge(a, b, metres(*a, *b), mid))
    return out


def snap(stops: list[tuple[str, float, float]], nodes: list[Node]) -> dict[str, tuple[Node, float]]:
    """Nearest walkable node of each stop within SNAP_MAX_M (KD-tree on local metres)."""
    from scipy.spatial import cKDTree

    if not nodes or not stops:
        return {}
    lat0 = sum(n[1] for n in nodes) / len(nodes)
    kx = 111_320.0 * math.cos(math.radians(lat0))
    tree = cKDTree([(x * kx, y * 110_574.0) for x, y in nodes])
    out = {}
    for stop_id, lon, lat in stops:
        _, i = tree.query((lon * kx, lat * 110_574.0))
        d = metres(lon, lat, *nodes[i])
        if d <= SNAP_MAX_M:
            out[stop_id] = (nodes[i], d)
    return out


def catchment(
    edges: list[Edge], sources: dict[Node, float], radius: float = RADIUS_M
) -> list[float]:
    """Covered metres of each edge: the part within `radius` of any source along the network."""
    graph: dict[Node, list[tuple[Node, float]]] = defaultdict(list)
    for e in edges:
        graph[e.u].append((e.v, e.length_m))
        graph[e.v].append((e.u, e.length_m))
    best = {n: d for n, d in sources.items() if d <= radius}
    queue = [(d, n) for n, d in best.items()]
    heapq.heapify(queue)
    while queue:
        d, n = heapq.heappop(queue)
        if d > best.get(n, math.inf):
            continue
        for m, length in graph[n]:
            nd = d + length
            if nd <= radius and nd < best.get(m, math.inf):
                best[m] = nd
                heapq.heappush(queue, (nd, m))
    covered = []
    for e in edges:
        du, dv = best.get(e.u, math.inf), best.get(e.v, math.inf)
        reach = max(0.0, radius - du) + max(0.0, radius - dv)
        covered.append(min(e.length_m, reach))
    return covered


def cell_coverage(
    population: dict[str, float],
    edge_cells: list[str | None],
    edges: list[Edge],
    covered: list[float],
) -> list[dict]:
    """Per cell: population, walkable and covered metres, covered population (never above pop)."""
    walk, cov = Counter(), Counter()
    for cell, e, c in zip(edge_cells, edges, covered, strict=True):
        if cell is not None:
            walk[cell] += e.length_m
            cov[cell] += c
    rows = []
    for cell, pop in sorted(population.items()):
        w = walk.get(cell, 0.0)
        frac = cov[cell] / w if w else 0.0
        rows.append(
            {
                "cell_id": cell,
                "population": pop,
                "walk_m": w,
                "covered_m": cov.get(cell, 0.0),
                "covered_fraction": frac,
                "covered_population": pop * frac,
            }
        )
    return rows


def trips_per_hour(first_departures: list[int]) -> dict[int, int]:
    """Trips by the service hour of their first departure (hours past 23 stay above 23)."""
    counts = Counter(sec // 3600 for sec in first_departures)
    return {h: counts.get(h, 0) for h in range(max(24, max(counts, default=0) + 1))}


def run(out: Path) -> dict:  # pragma: no cover - needs local raw files (data/raw)
    """Build the study from local evidence and write the report files into `out`."""
    import csv

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
    from atlas.ingest.s30 import S30, open_feed, rows

    state = load_state(ROOT / "configs/states/ka.yaml")
    adm1, adm2 = evidence("s17", "e05"), evidence("s17", "e06")
    districts = S17("ka").parse(adm2, state.source("S17"), adm1=adm1)
    row = next(r for r in districts.to_pylist() if r["name"] == DISTRICT)
    area = shapely.from_wkb(row["geometry"])
    shapely.prepare(area)

    pbf = evidence("s18", "e05")
    cache = ROOT / "data/clean/S18" / f"walk-{pbf.sha256[:12]}-{row['place_id']}.parquet"
    if not cache.exists():
        adapter = S18("ka", shapely.to_wkb(area))
        parts = [
            t.filter(pc.equal(t["feature_kind"], "road")).select(
                ["osm_id", "tags_json", "geometry"]
            )
            for t in adapter.parse_batches(pbf, state.source("S18"))
        ]
        cache.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.concat_tables(parts), cache)
    roads = pq.read_table(cache)
    ways = (
        (t, list(shapely.from_wkb(g).coords))
        for t, g in zip(roads["tags_json"].to_pylist(), roads["geometry"].to_pylist(), strict=True)
    )
    edges = walk_edges(ways)
    nodes = sorted({n for e in edges for n in (e.u, e.v)})

    feed = evidence("s30", "e12")
    times = S30("ka").parse(feed, state.source("S30"), service_date=SERVICE_DATE)
    served = set(times["stop_id"].to_pylist())
    stops_all = [
        (s["stop_id"], float(s["stop_lon"]), float(s["stop_lat"]))
        for s in rows(open_feed(feed), "stops.txt")
    ]
    stops = [s for s in stops_all if s[0] in served and area.contains(shapely.Point(s[1], s[2]))]
    snapped = snap(stops, nodes)
    sources: dict[Node, float] = {}
    for node, d in snapped.values():
        sources[node] = min(d, sources.get(node, math.inf))
    covered = catchment(edges, sources)

    worldpop = evidence("s16", "e05")
    cells = S16("ka", 2025).parse(worldpop, state.source("S16"), boundary=adm1)
    with rasterio.open(worldpop.path) as src:
        transform = src.transform

        def cell_of(lon: float, lat: float) -> str:
            r, c = src.index(lon, lat)
            return f"wp1km_r{r}_c{c}"

        centre = {}
        for cid in cells["cell_id"].to_pylist():
            r, c = (int(x[1:]) for x in cid.split("_")[1:])
            x, y = transform * (c + 0.5, r + 0.5)
            centre[cid] = (x, y)
    population = {
        cid: pop
        for cid, pop in zip(
            cells["cell_id"].to_pylist(), cells["population"].to_pylist(), strict=True
        )
        if area.contains(shapely.Point(*centre[cid]))
    }
    edge_cells = [cell_of(*e.mid) for e in edges]
    edge_cells = [c if c in population else None for c in edge_cells]
    table = cell_coverage(population, edge_cells, edges, covered)

    first = (
        times.group_by("trip_id").aggregate([("departure_sec", "min")])["departure_sec_min"]
    ).to_pylist()
    hours = trips_per_hour([s for s in first if s is not None])

    total = sum(population.values())
    covered_pop = sum(r["covered_population"] for r in table)
    no_walk = sum(r["population"] for r in table if r["walk_m"] == 0)
    summary = {
        "district": {
            "name": DISTRICT,
            "place_id": row["place_id"],
            "boundary_version": row["boundary_version"],
        },
        "service_date": SERVICE_DATE.isoformat(),
        "radius_m": RADIUS_M,
        "snap_max_m": SNAP_MAX_M,
        "inputs": {
            "S16": worldpop.sha256,
            "S17": adm2.sha256,
            "S18": pbf.sha256,
            "S30": feed.sha256,
        },
        "population": {
            "total": round(total),
            "covered": round(covered_pop),
            "uncovered": round(total) - round(covered_pop),  # exact: covered + uncovered = total
            "covered_share": round(covered_pop / total, 4),
            "in_cells_without_mapped_walkway": round(no_walk),
            "cells": len(population),
        },
        "network": {
            "walk_edges": len(edges),
            "walk_km": round(sum(e.length_m for e in edges) / 1000, 1),
            "covered_km": round(sum(covered) / 1000, 1),
        },
        "stops": {
            "served_in_district": len(stops),
            "snapped": len(snapped),
            "unsnapped": len(stops) - len(snapped),
            "median_snap_m": round(sorted(d for _, d in snapped.values())[len(snapped) // 2], 1),
        },
        "trips": {"service_day_trips": len(first), "peak_hour": max(hours, key=hours.get)},
        "limits": [
            "Scheduled supply only: the BMTC GTFS is unofficial (Vonter, scraped from the Namma "
            "BMTC app, known timetable errors, only routes with live tracking), as of 8 Sep 2026.",
            "OSM walking network completeness is unknown: unmapped footpaths shorten catchments, "
            "and population in cells with no mapped walkway counts as uncovered.",
            "WorldPop 2025 is a modelled estimate at 1 km; coverage inside a cell is assumed "
            "proportional to covered walkable length.",
            "Stops outside the district boundary are not used, which can under-count coverage "
            "near the edge.",
            "Access only: no frequency threshold, crowding, fares or safety is assessed.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(
        json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    with open(out / "cell_coverage.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(
            ["cell_id", "lon", "lat", "population", "walk_m", "covered_m", "covered_population"]
        )
        for r in table:
            x, y = centre[r["cell_id"]]
            w.writerow(
                [
                    r["cell_id"],
                    f"{x:.5f}",
                    f"{y:.5f}",
                    f"{r['population']:.1f}",
                    f"{r['walk_m']:.0f}",
                    f"{r['covered_m']:.0f}",
                    f"{r['covered_population']:.1f}",
                ]
            )
    with open(out / "trips_per_hour.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["service_hour", "trips_starting"])
        w.writerows(hours.items())
    return {"summary": summary, "cells": table, "centre": centre, "hours": hours}
