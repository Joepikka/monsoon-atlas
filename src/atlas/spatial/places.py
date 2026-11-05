"""Place identity, H3 analysis cells and a local gazetteer (T032).

Official places keep their source IDs, which are namespaced (`gb-IND-ADM2-...` for geoBoundaries
districts, `gba2025-c<corp>-w<ward>` for GBA wards). Each row also carries `boundary_version`;
adding a new version keeps every earlier version, so identity history is never lost. H3 cells
are analysis cells with kind "h3" and IDs `h3:<res>:<index>`; they are never called wards.

The gazetteer searches only the local place table: queries are not stored or logged, no
remote geocoder is called and there is no autocomplete. Needs shapely, h3 and pyproj (geo lock).
"""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

KINDS = ("state", "district", "ward", "h3")
H3_RESOLUTIONS = (7, 8)
SCHEMA = pa.schema(
    [
        pa.field("place_id", pa.string(), False),
        pa.field("kind", pa.string(), False),
        pa.field("name", pa.string(), False),
        pa.field("parent_id", pa.string(), True),
        pa.field("boundary_version", pa.string(), False),
        pa.field("geometry", pa.binary(), False),
    ]
)


def analysis_level(verified_subdistricts: bool) -> str:
    """Subdistrict (taluk) analysis only with verified boundaries; otherwise districts (T030)."""
    return "taluk" if verified_subdistricts else "district"


def from_source(table: pa.Table, kind: str) -> pa.Table:
    """Place rows from an S17 (districts) or S40 (wards) adapter table."""
    if kind not in ("district", "ward"):
        raise ValueError(f"official kind must be district or ward, not {kind}")
    rows = {
        "place_id": table["place_id"],
        "kind": pa.array([kind] * table.num_rows),
        "name": table["name"],
        "parent_id": table["parent_id"],
        "boundary_version": table["boundary_version"],
        "geometry": table["geometry"],
    }
    return pa.Table.from_pydict(rows, schema=SCHEMA)


def h3_cells(boundary_wkb: bytes, resolution: int, parent_id: str, version: str) -> pa.Table:
    """H3 cells whose centre lies in the boundary, as kind "h3" analysis cells."""
    import h3
    import shapely

    if resolution not in H3_RESOLUTIONS:
        raise ValueError(f"H3 resolution must be one of {H3_RESOLUTIONS}")
    shape = shapely.from_wkb(boundary_wkb)
    cells = sorted(h3.geo_to_cells(shape.__geo_interface__, resolution))
    polygons = [
        shapely.Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(c)]).wkb for c in cells
    ]
    rows = {
        "place_id": [f"h3:{resolution}:{c}" for c in cells],
        "kind": ["h3"] * len(cells),
        "name": [f"H3 cell r{resolution} {c}" for c in cells],
        "parent_id": [parent_id] * len(cells),
        "boundary_version": [f"h3-v4-r{resolution}|{version}"] * len(cells),
        "geometry": polygons,
    }
    return pa.Table.from_pydict(rows, schema=SCHEMA)


def distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Geodesic distance in metres on WGS84 (never degrees)."""
    from pyproj import Geod

    return abs(Geod(ellps="WGS84").inv(lon1, lat1, lon2, lat2)[2])


@dataclass(frozen=True)
class Match:
    candidates: list[dict]

    @property
    def needs_selection(self) -> bool:
        """More than one place fits: the user must choose; never pick one silently."""
        return len(self.candidates) > 1


class Gazetteer:
    """Places by ID with every boundary version kept, point lookup and name search."""

    def __init__(self) -> None:
        self._rows: list[dict] = []  # insertion order = version order
        self._tree = None

    def add(self, places: pa.Table) -> None:
        if [(f.name, f.type) for f in places.schema] != [(f.name, f.type) for f in SCHEMA]:
            raise ValueError("place table does not match the places schema")
        places = places.cast(SCHEMA)
        bad = set(places["kind"].to_pylist()) - set(KINDS)
        if bad:
            raise ValueError(f"unknown place kinds {sorted(bad)}")
        h3_named_ward = [
            r["place_id"]
            for r in places.to_pylist()
            if r["kind"] == "h3"
            and ("ward" in r["name"].lower() or not r["place_id"].startswith("h3:"))
        ]
        if h3_named_ward:
            raise ValueError(f"H3 cells must not look like wards: {h3_named_ward[:3]}")
        known = {(r["place_id"], r["boundary_version"]) for r in self._rows}
        self._rows += [
            r for r in places.to_pylist() if (r["place_id"], r["boundary_version"]) not in known
        ]
        self._tree = None

    def versions(self, place_id: str) -> list[str]:
        """Every boundary version this place has had, oldest first."""
        return [r["boundary_version"] for r in self._rows if r["place_id"] == place_id]

    def current(self) -> list[dict]:
        latest: dict[str, dict] = {}
        for r in self._rows:
            latest[r["place_id"]] = r
        return list(latest.values())

    def locate(self, lon: float, lat: float, kind: str) -> list[str]:
        """IDs of current places of this kind that contain the point."""
        import shapely

        if self._tree is None:
            rows = self.current()
            geoms = [shapely.from_wkb(r["geometry"]) for r in rows]
            self._tree = (shapely.STRtree(geoms), rows, geoms)
        tree, rows, geoms = self._tree
        point = shapely.Point(lon, lat)
        hits = tree.query(point, predicate="intersects")
        return sorted(rows[i]["place_id"] for i in hits if rows[i]["kind"] == kind)

    def search(self, query: str, kinds: tuple[str, ...] = ("district", "ward")) -> Match:
        """Case-insensitive match on the start of the name; the query is not kept."""
        text = " ".join(query.lower().split())
        if len(text) < 3:
            return Match([])
        found = [
            {
                "place_id": r["place_id"],
                "kind": r["kind"],
                "name": r["name"],
                "parent_id": r["parent_id"],
            }
            for r in self.current()
            if r["kind"] in kinds and r["name"].lower().startswith(text)
        ]
        exact = [c for c in found if c["name"].lower() == text]
        return Match(exact if len(exact) == 1 and len(found) == 1 else found)
