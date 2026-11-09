"""T055 acceptance: the S07 (NASA POWER daily point) discovery record passes the discovery
contract only with cited evidence and explicit access, licence and history status; fill values,
units and product changes are checked against the raw responses."""

import html
import json
import re

FILL = -999.0


def body(rec, eid) -> dict:
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def test_s07_discovery_contract(record):
    assert record("S07").problems() == []


def test_s07_status(record):
    d = record("S07").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert d.no_card and not d.account_required
    assert (d.earliest_date, d.latest_date) == ("1981-01-01", "2026-11-07")
    assert all("404" in f.error for f in d.failed_fetches)


def test_no_data_committed(record):
    assert record("S07").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S07").check_local_hashes()


def test_robots_licence_and_scripted_use_evidence(record):
    rec = record("S07")
    robots = rec.raw("e01").read_text(encoding="utf-8")
    assert "Disallow: /api/" in robots and "Allow: /api/pages/" in robots
    assert "scripted application" in text(rec, "e04")
    registry = text(rec, "e29")
    assert "There are no restrictions on the use, access, and/or download" in registry
    assert "Creative Commons BY 4.0" in registry


def test_units_fill_value_and_community(record):
    rec = record("S07")
    ag, re_ = body(rec, "e16"), body(rec, "e17")
    assert ag["header"]["fill_value"] == FILL and ag["header"]["time_standard"] == "UTC"
    units = {k: v["units"] for k, v in ag["parameters"].items()}
    assert units == {"PRECTOTCORR": "mm/day", "T2M": "C", "ALLSKY_SFC_SW_DWN": "MJ/m^2/day"}
    assert re_["parameters"]["ALLSKY_SFC_SW_DWN"]["units"] == "kW-hr/m^2/day"
    mj = ag["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]["20240701"]
    kwh = re_["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]["20240701"]
    assert (mj, kwh) == (12.11, 3.3629) and round(mj / kwh, 2) == 3.6
    lst = body(rec, "e18")
    assert lst["header"]["time_standard"] == "LST"
    assert lst["properties"]["parameter"]["T2M"] != ag["properties"]["parameter"]["T2M"]


def test_history_and_fill_values(record):
    days = body(record("S07"), "e19")["properties"]["parameter"]
    for name in ("PRECTOTCORR", "T2M"):
        filled = [d for d, v in days[name].items() if v == FILL]
        assert filled == ["20261108"], name
        assert min(days[name]) == "19810101"
    solar = [d for d, v in days["ALLSKY_SFC_SW_DWN"].items() if v != FILL]
    assert (solar[0], solar[-1]) == ("19840101", "20260831")
    assert min(v for v in days["PRECTOTCORR"].values() if v != FILL) >= 0


def test_products_are_named_per_request_and_switch_in_october_2026(record):
    rec = record("S07")
    sources = {eid: body(rec, eid)["header"]["sources"] for eid in ("e20", "e23", "e26", "e27")}
    assert sources == {
        "e20": ["MERRA2", "SRB"],
        "e23": ["MERRA2"],
        "e26": ["MERRA2", "GEOSIT"],
        "e27": ["GEOSIT"],
    }
    assert body(rec, "e19")["header"]["sources"] == ["MERRA2", "GEOSIT", "SRB", "SYN1DEG"]
