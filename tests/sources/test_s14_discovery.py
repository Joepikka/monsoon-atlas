"""T067 acceptance: the S14 (AWS Terrarium terrain) discovery record passes the discovery
contract; the Terrarium formula and the land and sea samples are checked against the evidence."""

import html
import re

import pytest


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def decoded(rec, eid) -> list[float]:
    image = pytest.importorskip("PIL.Image")  # geo lock (D35)
    px = image.open(rec.raw(eid)).convert("RGB").load()
    return [
        px[i, j][0] * 256 + px[i, j][1] + px[i, j][2] / 256 - 32768
        for i in range(256)
        for j in range(256)
    ]


def test_s14_discovery_contract(record):
    assert record("S14").problems() == []


def test_s14_status(record):
    d = record("S14").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert (d.earliest_date, d.latest_date) == (None, None)
    assert all("504" in f.error for f in d.failed_fetches)


def test_no_data_committed(record):
    assert record("S14").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S14").check_local_hashes()


def test_formula_and_attribution_text(record):
    rec = record("S14")
    assert "(red * 256 + green + blue / 256) - 32768" in text(rec, "e03")
    licence = text(rec, "e02")
    assert "Attribution is required for many terrain tile data providers" in licence
    assert "GMTED2010 and SRTM terrain data courtesy of the U.S. Geological Survey" in licence


def test_land_and_sea_samples_decode_plausibly(record):
    rec = record("S14")
    bengaluru = decoded(rec, "e05")
    assert 700 < min(bengaluru) and max(bengaluru) < 1000  # Bengaluru plateau
    sea = decoded(rec, "e06")
    assert min(sea) < -2000 and sum(v < 0 for v in sea) > 0.9 * len(sea)  # sea floor
