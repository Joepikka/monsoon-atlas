"""Population exposure to a risk polygon (T143).

People are the native cells of a population raster (S16 WorldPop, 1 km). Each cell's people are
split by the share of its area inside the hazard (EPSG:6933, so shares are true areas), assuming
people are spread evenly inside a cell. Several hazard polygons are merged first, so overlaps are
counted once. Inside + outside always equals the total. No hazard polygon is invented here: the
caller supplies the polygons. Needs shapely and pyproj.
"""

from __future__ import annotations

from collections.abc import Iterable

from atlas.spatial.crosswalk import _projected

METHOD = (
    "Area-weighted: each cell's people are split by the share of the cell inside the union of the "
    "hazard polygons, assuming people are spread evenly within a cell. Overlaps count once."
)


def cell_polygon(cell_id: str, transform) -> bytes:
    """WKB box of an S16 cell id `wp1km_r<row>_c<col>`, from the raster's affine transform."""
    import shapely

    row, col = (int(x) for x in cell_id.removeprefix("wp1km_r").split("_c"))
    x0, y0 = transform @ (col, row)
    x1, y1 = transform @ (col + 1, row + 1)
    return shapely.to_wkb(shapely.box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))


def exposure(cells: Iterable[tuple[str, bytes, float]], hazards: Iterable[bytes]) -> dict:
    """People inside the union of `hazards` (WKB, lon/lat) from (id, WKB, people) cells."""
    import shapely

    cells = list(cells)
    total = float(sum(p for _, _, p in cells))
    parts = [shapely.make_valid(shapely.from_wkb(h)) for h in hazards]
    out = {
        "population_total": total,
        "population_inside": 0.0,
        "population_outside": total,
        "cells_touched": 0,
        "hazard_area_km2": 0.0,
        "coverage": None,
        "method": METHOD,
    }
    if not parts:
        return out
    hazard = shapely.union_all(parts)
    tree = shapely.STRtree([shapely.from_wkb(w) for _, w, _ in cells])
    hit = sorted(int(i) for i in tree.query(hazard, predicate="intersects"))
    hazard_m = shapely.union_all(list(_projected({"h": shapely.to_wkb(hazard)}).values()))
    cell_m = _projected({str(i): cells[i][1] for i in hit})
    inside, touched = 0.0, 0
    for i in hit:
        c = cell_m[str(i)]
        share = c.intersection(hazard_m).area / c.area if c.area else 0.0
        if share > 0:
            inside, touched = inside + cells[i][2] * share, touched + 1
    covered = shapely.union_all(list(cell_m.values())) if cell_m else None
    out.update(
        population_inside=inside,
        population_outside=total - inside,
        cells_touched=touched,
        hazard_area_km2=hazard_m.area / 1e6,
        coverage=(covered.intersection(hazard_m).area / hazard_m.area)
        if covered is not None and hazard_m.area
        else 0.0,
    )
    return out
