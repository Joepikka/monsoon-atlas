"""T013 acceptance: the S09 (NDMA Sachet CAP alerts) discovery record passes the discovery
contract only with cited evidence and explicit access, licence and history status."""

import re
import xml.etree.ElementTree as ET

CAP = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}


def alert(rec, eid) -> ET.Element:
    return ET.fromstring(rec.raw(eid).read_bytes())


def test_s09_discovery_contract(record):
    assert record("S09").problems() == []


def test_s09_status(record):
    d = record("S09").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "partial",
        "pass",
    )
    assert d.no_card and not d.account_required


def test_no_data_committed(record):
    assert record("S09").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S09").check_local_hashes()


def test_feed_is_public_domain_with_100_latest_items(record):
    feed = ET.fromstring(record("S09").raw("e02").read_bytes()).find("channel")
    assert feed.findtext("copyright") == "public domain"
    items = feed.findall("item")
    assert len(items) == 100
    assert all("FetchXMLFile?identifier=" in i.findtext("link") for i in items)


def test_updates_reference_earlier_alerts(record):
    rec = record("S09")
    types = {}
    for eid in ("e03", "e05", "e06", "e07", "e08", "e09"):
        a = alert(rec, eid)
        types[eid] = a.findtext("cap:msgType", namespaces=CAP)
        refs = a.findtext("cap:references", namespaces=CAP)
        if types[eid] == "Update":
            sender, ident, sent = refs.split(",")
            assert ident.startswith("IN-") and re.match(r"\d{4}-\d\d-\d\dT", sent), eid
        else:
            assert not refs, eid
    assert set(types.values()) == {"Alert", "Update"}


def test_area_text_always_and_geometry_from_polygon_file(record):
    rec = record("S09")
    for eid in ("e03", "e05", "e06", "e07", "e08", "e09"):
        a = alert(rec, eid)
        assert a.findtext("cap:info/cap:area/cap:areaDesc", namespaces=CAP), eid
        names = [
            p.findtext("cap:valueName", namespaces=CAP)
            for p in a.findall("cap:info/cap:parameter", CAP)
        ]
        assert "Polygon URL" in names, eid
    rings = re.findall(r"<polygon>([^<]*)</polygon>", rec.raw("e04").read_text("utf-8"))
    lat, lon = map(float, rings[0].split()[0].split(","))
    assert len(rings) == 14 and len(set(rings)) == 7  # each ring listed twice
    assert 11 < lat < 19 and 74 < lon < 79  # lat,lon order, inside Karnataka
