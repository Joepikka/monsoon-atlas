"""T065 acceptance: the S13 (NASA GIBS) discovery record passes the discovery contract; layer
dates, the blank default-date tile and the open-data policy are checked against the evidence."""

import html
import re
import xml.etree.ElementTree as ET

import pytest

NS = {"w": "http://www.opengis.net/wmts/1.0", "ows": "http://www.opengis.net/ows/1.1"}
LAYER = "VIIRS_NOAA20_CorrectedReflectance_TrueColor"


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def layer(rec, name):
    root = ET.parse(rec.raw("e06")).getroot()
    return next(
        lay
        for lay in root.findall(".//w:Contents/w:Layer", NS)
        if lay.find("ows:Identifier", NS).text == name
    )


def test_s13_discovery_contract(record):
    assert record("S13").problems() == []


def test_s13_status(record):
    d = record("S13").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert (d.earliest_date, d.latest_date) == ("2018-01-05", "2026-11-09")
    assert all("404" in f.error for f in d.failed_fetches)


def test_no_data_committed(record):
    assert record("S13").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S13").check_local_hashes()


def test_open_data_policy_and_tile_pattern(record):
    rec = record("S13")
    policy = text(rec, "e05")
    assert "available to all users" in policy and "Suomi NPP is no longer delivering" in policy
    assert "{ LayerIdentifier }/default/{ Time }/{ TileMatrixSet }" in text(rec, "e03")


def test_layer_dates_template_and_suomi_end(record):
    rec = record("S13")
    noaa = layer(rec, LAYER)
    dim = noaa.find("w:Dimension", NS)
    ranges = [v.text for v in dim.findall("w:Value", NS)]
    assert (dim.find("w:Default", NS).text, len(ranges)) == ("2026-11-09", 5)
    assert ranges[0].startswith("2018-01-05/") and "2022-01-14/2026-11-09/P1D" in ranges
    template = noaa.find("w:ResourceURL", NS).get("template")
    assert template.endswith(
        f"{LAYER}/default/{{Time}}/{{TileMatrixSet}}/{{TileMatrix}}/{{TileRow}}/{{TileCol}}.jpeg"
    )
    snpp = layer(rec, "VIIRS_SNPP_CorrectedReflectance_TrueColor").find("w:Dimension", NS)
    assert snpp.find("w:Default", NS).text == "2026-11-02"


def test_default_date_tile_is_blank_and_previous_day_is_imagery(record):
    image = pytest.importorskip("PIL.Image")  # pillow is in the geo lock
    rec = record("S13")
    today = image.open(rec.raw("e08")).convert("L").histogram()
    previous = image.open(rec.raw("e07")).convert("L").histogram()
    assert today[0] == sum(today) == 256 * 256  # every pixel black: not yet imaged
    assert sum(previous[201:]) > 0.05 * sum(previous)  # bright cloud is data
