"""T143 acceptance: exposure conserves population and counts overlapping hazards once; the
experimental route algorithm returns "unavailable" when disconnected and always carries the
not-a-safe-route label; a stale or missing shelter record disables shelter routing; the real road
network (S18) and shelter records (S43) are unavailable while their sources are blocked.
Real-data part: S16 cells over an H3 analysis cell (local raw files; geo lock needed)."""

import json
from datetime import date
from pathlib import Path

import pytest

pytest.importorskip("shapely")
pytest.importorskip("pyproj")
import shapely  # noqa: E402

from atlas.spatial.exposure import cell_polygon, exposure  # noqa: E402
from atlas.spatial.routes import (  # noqa: E402
    GUIDANCE_URL,
    ROUTE_LABEL,
    compare_routes,
    shelter_route,
)

ROOT = Path(__file__).resolve().parents[2]


def box(x0, y0, x1, y1):
    return shapely.to_wkb(shapely.box(x0, y0, x1, y1))


def grid():
    """A 3x3 grid of 0.01-degree test cells with 100 people each (test input, not WorldPop)."""
    return [
        (f"c{r}{c}", box(c * 0.01, r * 0.01, (c + 1) * 0.01, (r + 1) * 0.01), 100.0)
        for r in range(3)
        for c in range(3)
    ]


def test_population_is_conserved_and_overlaps_count_once():
    a, b = box(0, 0, 0.015, 0.01), box(0.005, 0, 0.02, 0.01)  # overlap on x 0.005-0.015
    one = exposure(grid(), [a])
    assert one["population_inside"] == pytest.approx(150, rel=1e-3)
    both = exposure(grid(), [a, b])
    assert both["population_inside"] == pytest.approx(200, rel=1e-3)  # union x 0-0.02, not 150+150
    assert exposure(grid(), [a, a])["population_inside"] == pytest.approx(one["population_inside"])
    for r in (one, both):
        assert r["population_inside"] + r["population_outside"] == pytest.approx(900)
    assert both["coverage"] == pytest.approx(1.0)
    off = exposure(grid(), [box(1, 1, 1.01, 1.01)])  # hazard beyond the raster
    assert off["population_inside"] == 0 and off["coverage"] == 0.0
    assert exposure(grid(), [])["population_inside"] == 0


LINE = [("a", "b", 100, False), ("b", "c", 100, False), ("a", "d", 50, True), ("d", "c", 50, False)]


def test_route_avoids_high_risk_edges_and_is_always_labelled():
    r = compare_routes(LINE, "a", "c")
    assert r["status"] == "experimental"
    assert r["avoiding"]["path"] == ["a", "b", "c"] and r["avoiding"]["length_m"] == 200
    assert r["shortest"]["path"] == ["a", "d", "c"] and r["shortest"]["high_risk_edges"] == 1
    assert r["label"] == ROUTE_LABEL and "not a safe route" in r["label"].lower()
    assert r["guidance_url"] == GUIDANCE_URL


def test_disconnected_graph_returns_unavailable():
    for edges, dest in ((LINE[2:], "b"), ([("a", "b", 1, True)], "b"), (LINE, "zzz")):
        r = compare_routes(edges, "a", dest)
        assert r["status"] == "unavailable" and r["label"] == ROUTE_LABEL


def test_real_roads_and_shelters_are_unavailable_without_graph_or_record():
    r = compare_routes(None, "a", "b")
    assert r["status"] == "unavailable" and "graph not built" in r["reason"]
    s = shelter_route(None, None, "a", date(2026, 11, 9))
    assert s["status"] == "disabled" and "S43 blocked" in s["reason"]
    assert GUIDANCE_URL in (ROOT / "configs/sources/s36.yaml").read_text("utf-8")


def test_stale_shelter_disables_routing():
    shelter = {
        "shelter_id": "x",
        "name": "test shelter",
        "node": "c",
        "official_date": "2026-11-08",
    }
    ok = shelter_route(shelter, LINE, "a", date(2026, 11, 9))
    assert ok["status"] == "experimental" and ok["shelter"]["shelter_id"] == "x"
    for today in (date(2026, 11, 12), date(2026, 11, 7)):  # too old, and dated in the future
        r = shelter_route(shelter, LINE, "a", today)
        assert r["status"] == "disabled" and "not current" in r["reason"]


def test_real_s16_cells_conserve_population_over_an_h3_cell():
    rasterio = pytest.importorskip("rasterio")
    h3 = pytest.importorskip("h3")
    import pyarrow.compute as pc

    from atlas.config import load_state
    from atlas.contracts import RawArtifact
    from atlas.ingest.s16 import S16

    def artifact(source, eid):
        manifest = json.loads((ROOT / f"tests/fixtures/{source}/manifest.json").read_text("utf-8"))
        e = next(x for x in manifest["evidence"] if x["id"] == eid)
        if not (ROOT / "data/raw" / e["raw_path"]).exists():
            pytest.skip("raw evidence is local only")
        return RawArtifact(
            sha256=e["sha256"],
            path=ROOT / "data/raw" / e["raw_path"],
            fetched_at=e["fetched_at"],
            media_type=e["media_type"],
            response_status=e["status"],
            source_url=e["url"],
            schema_mapping_version="test",
        )

    ka = load_state(ROOT / "configs/states/ka.yaml")
    raw = artifact("s16", "e05")
    table = S16("ka", 2025).parse(raw, ka.source("S16"), boundary=artifact("s17", "e05"))
    with rasterio.open(raw.path) as src:
        transform = src.transform
    ids, pops = table["cell_id"].to_pylist(), table["population"].to_pylist()
    cells = [(i, cell_polygon(i, transform), p) for i, p in zip(ids, pops, strict=True)]

    def hexagon(c):
        return shapely.Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)])

    centre = h3.latlng_to_cell(12.97, 77.59, 5)  # Bengaluru, a real H3 analysis cell
    inner = shapely.to_wkb(hexagon(centre))
    outer = shapely.to_wkb(shapely.union_all([hexagon(c) for c in h3.grid_disk(centre, 1)]))
    total = pc.sum(table["population"]).as_py()
    a, both = exposure(cells, [inner]), exposure(cells, [inner, outer])
    assert a["population_total"] == pytest.approx(total)
    assert a["population_inside"] + a["population_outside"] == pytest.approx(total)
    assert 0 < a["population_inside"] < both["population_inside"] < total
    assert exposure(cells, [outer])["population_inside"] == pytest.approx(both["population_inside"])
    assert both["coverage"] > 0.99


def test_web_contract(web_check):
    assert ROUTE_LABEL in (ROOT / "web/src/components/RouteComparison.tsx").read_text("utf-8")
    web_check("run", "test", "--", "src/components/RouteComparison.test.ts")
