"""T019 acceptance: the S17 (geoBoundaries) discovery record passes the discovery contract only
with cited evidence and explicit access, licence and history status."""

import json


def load(rec, eid):
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def test_s17_discovery_contract(record):
    assert record("S17").problems() == []


def test_s17_status(record):
    d = record("S17").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "partial",
        "pass",
    )
    assert d.no_card and not d.account_required


def test_no_data_committed(record):
    assert record("S17").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S17").check_local_hashes()


def test_metadata_count_is_not_the_file_count(record):
    rec = record("S17")
    meta = load(rec, "e03")
    assert (meta["admUnitCount"], meta["boundaryYearRepresented"]) == ("736", "2021")
    assert meta["boundaryLicense"] == "Open Data Commons Open Database License 1.0"
    features = load(rec, "e06")["features"]
    assert len(features) == 735
    assert len({f["properties"]["shapeID"] for f in features}) == 735
    assert {f["geometry"]["type"] for f in features} == {"Polygon", "MultiPolygon"}


def test_no_disputed_boundary_field_and_closed_rings(record):
    rec = record("S17")
    features = load(rec, "e06")["features"]
    assert set(features[0]["properties"]) == {
        "shapeName",
        "shapeISO",
        "shapeID",
        "shapeGroup",
        "shapeType",
    }
    for f in features:
        g = f["geometry"]
        parts = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        assert all(r[0] == r[-1] and len(r) >= 4 for p in parts for r in p), f["properties"][
            "shapeID"
        ]
    adm1 = load(rec, "e04")
    assert adm1["boundaryYearRepresented"] == "2011" and adm1["admUnitCount"] == "36"
