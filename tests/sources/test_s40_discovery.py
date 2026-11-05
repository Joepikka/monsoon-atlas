"""T030 acceptance: the S40 (ward and taluk polygons) discovery record passes the discovery contract
only with cited evidence and explicit access, licence and history status."""

import re
import xml.etree.ElementTree as ET

KML = {"k": "http://www.opengis.net/kml/2.2"}


def placemarks(path):
    return ET.parse(path).getroot().findall(".//k:Placemark", KML)


def fields(pm) -> dict[str, str]:
    return {d.get("name"): d.text for d in pm.findall(".//k:SimpleData", KML)}


def test_s40_discovery_contract(record):
    assert record("S40").problems() == []


def test_s40_status(record):
    d = record("S40").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.units.status) == ("open", "available", "labelled")
    assert d.no_card and not d.account_required
    assert any(f.canonical == "geometry" and f.unit_status == "labelled" for f in d.field_map)


def test_no_polygons_committed(record):
    assert record("S40").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S40").check_local_hashes()


def test_gba_2025_wards_have_published_unique_keys(record):
    pms = placemarks(record("S40").raw("e04"))
    keys = {(fields(p)["corporation_id"], fields(p)["ward_id"]) for p in pms}
    assert len(pms) == len(keys) == 369


def test_bbmp_2015_ward_numbers_come_from_published_names(record):
    names = [p.findtext("k:name", namespaces=KML) for p in placemarks(record("S40").raw("e07"))]
    numbers = sorted(
        int(re.fullmatch(r"Ward\s+(\d+)", n.replace("\xa0", " ")).group(1)) for n in names
    )
    assert numbers == list(range(1, 199))


def test_ward_files_lie_inside_bengaluru(record):
    for eid in ("e04", "e07", "e08", "e09"):
        root = ET.parse(record("S40").raw(eid)).getroot()
        for c in root.iter("{http://www.opengis.net/kml/2.2}coordinates"):
            for point in c.text.split():
                lon, lat = map(float, point.split(",")[:2])
                assert 77.3 < lon < 77.9 and 12.7 < lat < 13.3, eid
