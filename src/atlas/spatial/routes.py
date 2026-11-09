"""Experimental route comparison and shelter routing (T143).

Not an emergency service and never a safe route: road closures and flood depth are unknown, and
a "high-risk" edge only means it was flagged by the supplied risk layer. There is no verified road
network (S18 is blocked, D34) and no verified official shelter record (S43 is blocked, D124), so
real use returns "unavailable" or "disabled". The algorithm is tested on small hand-built graphs.
"""

from __future__ import annotations

import heapq
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
ROUTE_LABEL = "Experimental route, not a safe route; road closures and flood depth unknown."
GUIDANCE_URL = "https://sdma.kerala.gov.in/disaster-memoranda/"  # S36 landing_url (KSDMA)
SHELTER_MAX_AGE_DAYS = 2  # a shelter record older than this is not "current"
Edge = tuple[str, str, float, bool]  # (from node, to node, length in metres, high-risk flag)


def _outcome(source_id: str) -> str:
    return yaml.safe_load((ROOT / f"configs/sources/{source_id.lower()}.yaml").read_text("utf-8"))[
        "outcome"
    ]


def _wrap(**fields) -> dict:
    return {"label": ROUTE_LABEL, "guidance_url": GUIDANCE_URL, **fields}


def _unavailable(reason: str) -> dict:
    return _wrap(status="unavailable", reason=reason)


def _dijkstra(edges: list[Edge], origin: str, dest: str, avoid_risk: bool):
    graph: dict[str, list[tuple[str, float, bool]]] = {}
    for u, v, length, risky in edges:
        if length < 0:
            raise ValueError("edge length must be >= 0")
        if avoid_risk and risky:
            continue
        graph.setdefault(u, []).append((v, length, risky))
        graph.setdefault(v, []).append((u, length, risky))
    best, prev, queue = {origin: 0.0}, {}, [(0.0, origin)]
    while queue:
        d, u = heapq.heappop(queue)
        if u == dest:
            path, risky_edges = [dest], 0
            while path[-1] != origin:
                u, risky = prev[path[-1]]
                path.append(u)
                risky_edges += risky
            return d, path[::-1], risky_edges
        if d > best.get(u, float("inf")):
            continue
        for v, length, risky in graph.get(u, []):
            if d + length < best.get(v, float("inf")):
                best[v], prev[v] = d + length, (u, risky)
                heapq.heappush(queue, (d + length, v))
    return None


def compare_routes(edges: list[Edge] | None, origin: str, dest: str) -> dict:
    """Shortest route vs shortest route that excludes high-risk edges; unavailable if none."""
    if edges is None:
        return _unavailable(
            f"no verified road network (S18 {_outcome('S18')}); no route is computed"
        )
    plain = _dijkstra(edges, origin, dest, avoid_risk=False)
    avoiding = _dijkstra(edges, origin, dest, avoid_risk=True)
    if avoiding is None:
        return _unavailable("no route avoids the high-risk edges (graph disconnected)")
    return _wrap(
        status="experimental",
        avoiding={"length_m": avoiding[0], "path": avoiding[1]},
        shortest={"length_m": plain[0], "path": plain[1], "high_risk_edges": plain[2]},
    )


def shelter_route(shelter: dict | None, edges: list[Edge] | None, origin: str, today: date) -> dict:
    """Route to a shelter, only when its record carries a current official date."""
    if shelter is None:
        return _wrap(
            status="disabled",
            reason=f"no verified official shelter record (S43 {_outcome('S43')})",
        )
    age = (today - date.fromisoformat(shelter["official_date"])).days
    if not 0 <= age <= SHELTER_MAX_AGE_DAYS:
        return _wrap(
            status="disabled",
            reason=f"shelter record dated {shelter['official_date']} is not current "
            f"(window {SHELTER_MAX_AGE_DAYS} days)",
        )
    route = compare_routes(edges, origin, shelter["node"])
    return route | {"shelter": {k: shelter[k] for k in ("shelter_id", "name", "official_date")}}
