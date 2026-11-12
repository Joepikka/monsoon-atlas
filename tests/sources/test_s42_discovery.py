"""T127 acceptance: the S42 (Sentinel-1 / NDVI imagery) discovery record passes the discovery
contract only with cited evidence and explicit access, licence and history status."""

import json
import re


def text(path) -> str:
    page = path.read_text(encoding="utf-8", errors="replace")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))


def test_s42_discovery_contract(record):
    assert record("S42").problems() == []


def test_s42_is_blocked_on_an_account_with_explicit_status(record):
    d = record("S42").discovery
    assert d.outcome == "blocked"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "fail",
    )
    assert d.no_card and d.account_required
    assert {"T128", "T145"} <= set(d.dependents)
    assert "CDSE_USERNAME" in d.retry_condition and "CDSE_PASSWORD" in d.retry_condition
    assert len(d.failed_fetches) == 1 and "401" in d.failed_fetches[0].error


def test_only_manifest_committed(record):
    assert record("S42").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S42").check_local_hashes()


def test_catalogue_search_is_keyless_but_download_needs_a_token(record):
    r = record("S42")
    odata = text(r.raw("e06"))
    assert "Authorization: Bearer $ACCESS_TOKEN" in odata
    assert "must have an access token to download products" in text(r.raw("e07"))
    assert "need to register as a user" in text(r.raw("e03"))
    assert r.discovery.failed_fetches[0].url.startswith("https://download.dataspace.copernicus.eu/")


def test_catalogue_samples_hold_the_mapped_fields(record):
    r = record("S42")
    s1 = json.loads(r.raw("e12").read_text(encoding="utf-8"))["value"][0]
    attrs = {a["Name"]: a["Value"] for a in s1["Attributes"]}
    assert s1["Name"].endswith(".SAFE") and s1["ContentDate"]["Start"].endswith("Z")
    assert s1["S3Path"].startswith("/eodata/Sentinel-1/")
    assert (attrs["productType"], attrs["polarisationChannels"]) == ("IW_GRDH_1S-COG", "VV&VH")
    s2 = json.loads(r.raw("e13").read_text(encoding="utf-8"))["value"][0]
    attrs = {a["Name"]: a["Value"] for a in s2["Attributes"]}
    assert attrs["productType"] == "S2MSI2A" and 0 <= attrs["cloudCover"] <= 100


def test_stac_item_gives_crs_scale_and_authenticated_assets(record):
    item = json.loads(record("S42").raw("e14").read_text(encoding="utf-8"))["features"][0]
    red = item["assets"]["B04_10m"]
    assert item["properties"]["eo:cloud_cover"] > 0 and red["proj:code"].startswith("EPSG:")
    assert (red["raster:scale"], red["raster:offset"], red["nodata"]) == (0.0001, -0.1, 0)
    assert red["href"].startswith("s3://eodata/") and red["auth:refs"] == ["s3"]
    assert "B08_10m" in item["assets"]


def test_legal_notice_allows_reuse_with_attribution(record):
    r = record("S42")
    assert "free, full and open" in text(r.raw("e03"))
    assert r.raw("e04").read_bytes().startswith(b"%PDF")
