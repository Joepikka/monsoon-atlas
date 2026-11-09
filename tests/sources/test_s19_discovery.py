"""T069 acceptance: the S19 (Google Open Buildings) discovery record passes the discovery contract;
the licence choice, Karnataka's shard size and the sample shard's columns, confidence range and
uniqueness are checked against the evidence."""

import csv
import gzip
import html
import io
import json
import re


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def test_s19_discovery_contract(record):
    assert record("S19").problems() == []


def test_s19_status(record):
    d = record("S19").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert d.failed_fetches == []


def test_no_data_committed(record):
    assert record("S19").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S19").check_local_hashes()


def test_dual_licence_and_no_owner_data(record):
    page = text(record("S19"), "e01")
    assert "Creative Commons Attribution (CC BY-4.0) license and the Open Data Commons" in page
    assert "you can pick which of the two licenses you prefer" in page
    assert "no information about the type of building, its street address" in page


def test_karnataka_shard_is_3bb(record):
    cells = json.loads(record("S19").raw("e02").read_text("utf-8"))["features"]
    by_id = {f["properties"]["tile_id"]: f["properties"] for f in cells}
    assert len(cells) == 333 and by_id["3bb"]["size_mb"] == 4834.4
    assert by_id["3bb"]["tile_url"].endswith("/v3/polygons_s2_level_4_gzip/3bb_buildings.csv.gz")


def test_sample_columns_confidence_and_uniqueness(record):
    csv.field_size_limit(10**9)
    raw = record("S19").raw("e04").read_bytes()
    rows = list(csv.DictReader(io.TextIOWrapper(gzip.open(io.BytesIO(raw)), encoding="utf-8")))
    assert list(rows[0]) == [
        "latitude",
        "longitude",
        "area_in_meters",
        "confidence",
        "geometry",
        "full_plus_code",
    ]
    confidence = [float(r["confidence"]) for r in rows]
    assert len(rows) == 40789 and (min(confidence), max(confidence)) == (0.65, 0.9704)
    assert sum(c >= 0.75 for c in confidence) == 26065
    assert len({r["full_plus_code"] for r in rows}) == len({r["geometry"] for r in rows}) == 40789
