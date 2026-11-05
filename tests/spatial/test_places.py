"""T032 acceptance: boundary-version changes retain identity history; H3 is never labelled ward;
distance comparisons use metres; an ambiguous place query asks for a selection. Built on the
real S17 districts, S40 wards and S16 population (local raw files; geo lock needed)."""

import json
from functools import cache
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pytest

pytest.importorskip("shapely")
pytest.importorskip("h3")
pytest.importorskip("pyproj")

from atlas.config import load_state  # noqa: E402
from atlas.contracts import RawArtifact  # noqa: E402
from atlas.ingest.s17 import S17  # noqa: E402
from atlas.ingest.s40 import S40  # noqa: E402
from atlas.spatial.crosswalk import area_weights, population_weights  # noqa: E402
from atlas.spatial.places import (  # noqa: E402
    SCHEMA,
    Gazetteer,
    analysis_level,
    distance_m,
    from_source,
    h3_cells,
)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
KA = load_state(ROOT / "configs" / "states" / "ka.yaml")


def artifact(source: str, eid: str) -> RawArtifact:
    manifest = json.loads((ROOT / f"tests/fixtures/{source}/manifest.json").read_text("utf-8"))
    e = next(x for x in manifest["evidence"] if x["id"] == eid)
    if not (RAW / e["raw_path"]).exists():
        pytest.skip("raw evidence is local only")
    return RawArtifact(
        sha256=e["sha256"],
        path=RAW / e["raw_path"],
        fetched_at=e["fetched_at"],
        media_type=e["media_type"],
        response_status=e["status"],
        source_url=e["url"],
        schema_mapping_version="test",
    )


@cache
def districts() -> pa.Table:
    table = S17("ka").parse(artifact("s17", "e06"), KA.source("S17"), adm1=artifact("s17", "e05"))
    return from_source(table, "district")


@cache
def wards() -> pa.Table:
    return from_source(S40().parse(artifact("s40", "e04"), KA.source("S40")), "ward")


def district(name: str) -> dict:
    return districts().filter(pc.equal(districts()["name"], name)).to_pylist()[0]


@cache
def gazetteer() -> Gazetteer:
    g = Gazetteer()
    g.add(districts())
    g.add(wards())
    return g


def test_boundary_version_change_keeps_identity_history():
    g = Gazetteer()
    g.add(districts())
    newer = districts().set_column(
        districts().schema.get_field_index("boundary_version"),
        "boundary_version",
        pa.array(["geoboundaries-IND-ADM2-next"] * districts().num_rows),
    )
    g.add(newer)
    g.add(districts())  # re-adding an existing version changes nothing
    mysore = district("Mysore")["place_id"]
    assert g.versions(mysore) == ["geoboundaries-IND-ADM2-9469f09", "geoboundaries-IND-ADM2-next"]
    current = {r["place_id"]: r for r in g.current()}
    assert current[mysore]["boundary_version"] == "geoboundaries-IND-ADM2-next"
    assert len(current) == 30
    # A version crosswalk links old and new units by shared area, in square metres.
    old = {mysore: district("Mysore")["geometry"]}
    links = area_weights(old, {f"{mysore}@next": district("Mysore")["geometry"]})
    assert links.num_rows == 1 and abs(links["weight_area"][0].as_py() - 1) < 1e-9
    assert 6.0e9 < links["overlap_m2"][0].as_py() < 7.5e9  # Mysuru district is about 6,800 km2


def test_h3_cells_are_never_wards():
    blr = district("Bangalore")
    for res in (7, 8):
        cells = h3_cells(blr["geometry"], res, blr["place_id"], blr["boundary_version"])
        assert cells.schema.equals(SCHEMA) and cells.num_rows > 50
        assert set(cells["kind"].to_pylist()) == {"h3"}
        assert all(p.startswith(f"h3:{res}:") for p in cells["place_id"].to_pylist())
        assert not any("ward" in n.lower() for n in cells["name"].to_pylist())
        assert not set(cells["place_id"].to_pylist()) & set(wards()["place_id"].to_pylist())
    disguised = cells.set_column(1, "kind", pa.array(["h3"] * cells.num_rows)).set_column(
        2, "name", pa.array(["Ward 1"] * cells.num_rows)
    )
    with pytest.raises(ValueError, match="must not look like wards"):
        Gazetteer().add(disguised)


def test_distances_are_metres():
    bengaluru, mysuru = (77.5946, 12.9716), (76.6394, 12.2958)
    d = distance_m(*bengaluru, *mysuru)
    assert 125_000 < d < 131_000  # about 128 km, not about 1.2 "degrees"


def test_ambiguous_query_asks_for_selection():
    g = gazetteer()
    both = g.search("bangalore")
    assert both.needs_selection and {c["name"] for c in both.candidates} == {
        "Bangalore",
        "Bangalore Rural",
    }
    one = g.search("  MYSORE ")
    assert not one.needs_selection and one.candidates[0]["kind"] == "district"
    assert not g.search("zz").candidates  # too short: no suggestions, no autocomplete
    assert not any("query" in k for k in vars(g))  # queries are not stored


def test_point_lookup_and_district_fallback():
    g = gazetteer()
    vidhana_soudha = (77.5907, 12.9796)
    assert g.locate(*vidhana_soudha, "district") == [district("Bangalore")["place_id"]]
    ward = g.locate(*vidhana_soudha, "ward")
    assert len(ward) == 1 and ward[0].startswith("gba2025-c1-")  # Central corporation
    assert analysis_level(verified_subdistricts=False) == "district"  # no taluk polygons (T030)


def test_ward_to_district_crosswalk_by_area_and_population():
    import rasterio
    from rasterio.windows import from_bounds

    ward_geoms = dict(
        zip(wards()["place_id"].to_pylist(), wards()["geometry"].to_pylist(), strict=True)
    )
    near = districts().filter(
        pc.is_in(districts()["name"], pa.array(["Bangalore", "Bangalore Rural", "Ramanagara"]))
    )
    targets = dict(zip(near["place_id"].to_pylist(), near["geometry"].to_pylist(), strict=True))
    by_area = area_weights(ward_geoms, targets)
    sums = pc.sum(by_area["weight_area"]).as_py() / len(set(by_area["source_id"].to_pylist()))
    assert len(set(by_area["source_id"].to_pylist())) == 369 and 0.98 < sums <= 1.0 + 1e-9

    with rasterio.open(artifact("s16", "e05").path) as src:
        window = from_bounds(77.3, 12.7, 77.9, 13.3, src.transform)
        data = src.read(1, window=window)
        transform = src.window_transform(window)
    points = [
        (*rasterio.transform.xy(transform, r, c), float(data[r, c]))
        for r in range(data.shape[0])
        for c in range(data.shape[1])
        if data[r, c] > 0
    ]
    by_people = population_weights(points, ward_geoms, targets)
    per_ward = pc.sum(by_people["weight_population"]).as_py() / len(
        set(by_people["source_id"].to_pylist())
    )
    assert abs(per_ward - 1) < 1e-9  # each ward's people are fully assigned
    # WorldPop R2025A puts about 6.0 million people in the 369 GBA wards in 2025, well below
    # other estimates for Bengaluru: an undercount to flag, not to hide (docs/sources/s16.md).
    assert 5.5e6 < pc.sum(by_people["population"]).as_py() < 6.5e6
