"""Many-to-many crosswalks between place sets, weighted by area or population (T032).

Areas are measured in square metres in an equal-area projection (EPSG:6933), never in
degrees. A weight is the share of the source unit that falls in the target unit, so the
weights of one source sum to about 1 when the targets cover it. Needs shapely and pyproj.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping

import pyarrow as pa

EQUAL_AREA = "EPSG:6933"
AREA_SCHEMA = pa.schema(
    [
        pa.field("source_id", pa.string(), False),
        pa.field("target_id", pa.string(), False),
        pa.field("overlap_m2", pa.float64(), False),
        pa.field("weight_area", pa.float64(), False),
    ]
)
POPULATION_SCHEMA = pa.schema(
    [
        pa.field("source_id", pa.string(), False),
        pa.field("target_id", pa.string(), False),
        pa.field("population", pa.float64(), False),
        pa.field("weight_population", pa.float64(), False),
    ]
)


def _projected(geoms: Mapping[str, bytes]):
    import numpy as np
    import shapely
    from pyproj import Transformer

    to_m = Transformer.from_crs("EPSG:4326", EQUAL_AREA, always_xy=True).transform
    out = {}
    for key, blob in geoms.items():
        g = shapely.make_valid(shapely.from_wkb(blob))
        out[key] = shapely.transform(g, lambda xy: np.column_stack(to_m(xy[:, 0], xy[:, 1])))
    return out


def area_weights(
    sources: Mapping[str, bytes], targets: Mapping[str, bytes], min_weight: float = 1e-6
):
    """Rows (source_id, target_id, overlap_m2, weight_area) for every overlapping pair."""
    import shapely

    src, tgt = _projected(sources), _projected(targets)
    keys = list(tgt)
    tree = shapely.STRtree([tgt[k] for k in keys])
    rows = []
    for s_id, s_geom in src.items():
        area = s_geom.area
        for i in tree.query(s_geom, predicate="intersects"):
            overlap = s_geom.intersection(tgt[keys[i]]).area
            if area and overlap / area >= min_weight:
                rows.append((s_id, keys[i], overlap, overlap / area))
    names = AREA_SCHEMA.names
    return pa.Table.from_pylist(
        [dict(zip(names, r, strict=True)) for r in rows], schema=AREA_SCHEMA
    )


def population_weights(
    points: Iterable[tuple[float, float, float]],
    sources: Mapping[str, bytes],
    targets: Mapping[str, bytes],
):
    """Population of (lon, lat, people) points split over source x target pairs.

    weight_population is the share of a source unit's people that live in the target unit.
    Points outside every source unit are ignored; nothing is resampled.
    """
    import shapely

    def index(geoms):
        keys = list(geoms)
        return keys, shapely.STRtree([shapely.from_wkb(geoms[k]) for k in keys])

    s_keys, s_tree = index(sources)
    t_keys, t_tree = index(targets)
    pairs: dict[tuple[str, str], float] = defaultdict(float)
    totals: dict[str, float] = defaultdict(float)
    for lon, lat, people in points:
        p = shapely.Point(lon, lat)
        s_hit = s_tree.query(p, predicate="intersects")
        if not len(s_hit):
            continue
        s_id = s_keys[int(s_hit[0])]
        totals[s_id] += people
        for i in t_tree.query(p, predicate="intersects")[:1]:
            pairs[(s_id, t_keys[int(i)])] += people
    rows = [
        {"source_id": s, "target_id": t, "population": v, "weight_population": v / totals[s]}
        for (s, t), v in sorted(pairs.items())
        if totals[s] > 0
    ]
    return pa.Table.from_pylist(rows, schema=POPULATION_SCHEMA)
