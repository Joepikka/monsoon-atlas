"""T015 acceptance: the S15 (OpenFreeMap basemap) discovery record passes the discovery contract
only with cited evidence and explicit access, licence and history status."""

import json


def test_s15_discovery_contract(record):
    assert record("S15").problems() == []


def test_s15_status(record):
    d = record("S15").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "partial",
        "pass",
    )
    assert d.no_card and not d.account_required


def test_no_data_committed(record):
    assert record("S15").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S15").check_local_hashes()


def test_tilejson_revision_and_attribution(record):
    tj = json.loads(record("S15").raw("e06").read_text("utf-8"))
    assert tj["tiles"] == [
        "https://tiles.openfreemap.org/planet/20261101_080013_pt/{z}/{x}/{y}.pbf"
    ]
    for credit in ("OpenFreeMap", "&copy; OpenMapTiles", "Data from", "OpenStreetMap"):
        assert credit in tj["attribution"], credit
    assert (tj["version"], tj["minzoom"], tj["maxzoom"]) == ("3.16.0", 0, 14)


def test_style_and_tile_available(record):
    rec = record("S15")
    style = json.loads(rec.raw("e05").read_text("utf-8"))
    assert style["sources"]["openmaptiles"] == {
        "type": "vector",
        "url": "https://tiles.openfreemap.org/planet",
    }
    assert style["glyphs"].startswith("https://tiles.openfreemap.org/fonts/")
    tile = next(e for e in rec.manifest.evidence if e.id == "e07")
    assert tile.media_type == "application/vnd.mapbox-vector-tile" and tile.bytes > 10_000


def test_terms_limit_automated_downloads(record):
    terms = " ".join(record("S15").raw("e03").read_text("utf-8").split())
    assert "at most 3,000 tiles or 50 MB" in terms and "at most 4 parallel requests" in terms
    assert "at least 18 years old" in terms
