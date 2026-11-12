"""T063 acceptance: the S12 (CelesTrak orbit elements) discovery record passes the discovery
contract with cited evidence; TLE checksums, epochs and the 6-digit catalog gap are checked
against the raw evidence."""

import html
import json
import re
from datetime import UTC, datetime, timedelta


def text(rec, eid) -> str:
    page = re.sub(r"<script.*?</script>|<[^>]+>", " ", rec.raw(eid).read_text("utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(page))


def tle_objects(rec) -> list[tuple[str, str, str]]:
    lines = rec.raw("e07").read_text(encoding="ascii").splitlines()
    return [(lines[i].strip(), lines[i + 1], lines[i + 2]) for i in range(0, len(lines), 3)]


def checksum_ok(line: str) -> bool:
    total = sum(int(c) if c.isdigit() else c == "-" for c in line[:68])
    return total % 10 == int(line[68])


def tle_epoch(line1: str) -> datetime:
    year, day = int(line1[18:20]), float(line1[20:32])
    start = datetime(2000 + year if year < 57 else 1900 + year, 1, 1, tzinfo=UTC)
    return start + timedelta(days=day - 1)


def test_s12_discovery_contract(record):
    assert record("S12").problems() == []


def test_s12_status(record):
    d = record("S12").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "restricted",
        "partial",
        "pass",
    )
    assert d.no_card and not d.account_required
    tle = [f for f in d.field_map if f.canonical.startswith("tle_line")]
    assert all(f.upstream is None and f.unit_status == "absent" for f in tle)


def test_no_data_committed(record):
    assert record("S12").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S12").check_local_hashes()


def test_usage_policy_and_robots(record):
    rec = record("S12")
    assert "Disallow: /NORAD/elements/gp*.php" in rec.raw("e01").read_text("utf-8")
    policy = text(rec, "e05")
    assert "only download data once per update" in policy
    assert "For GP data, updates are once every 2 hours" in policy
    assert "should immediately stop querying when it receives any non-HTTP 200" in policy


def test_tle_checksums_and_epochs_match_omm(record):
    rec = record("S12")
    omm = {o["NORAD_CAT_ID"]: o for o in json.loads(rec.raw("e08").read_text("utf-8"))}
    tles = tle_objects(rec)
    assert len(tles) == 15
    for name, line1, line2 in tles:
        assert checksum_ok(line1) and checksum_ok(line2), name
        epoch = datetime.fromisoformat(omm[int(line1[2:7])]["EPOCH"]).replace(tzinfo=UTC)
        assert abs(tle_epoch(line1) - epoch) < timedelta(milliseconds=1), name


def test_six_digit_objects_are_missing_from_tle(record):
    rec = record("S12")
    omm = json.loads(rec.raw("e08").read_text("utf-8"))
    tle_ids = {int(line1[2:7]) for _, line1, _ in tle_objects(rec)}
    missing = sorted(o["OBJECT_NAME"] for o in omm if o["NORAD_CAT_ID"] not in tle_ids)
    assert missing == ["CREW DRAGON 13", "DRAGON CRS-35", "PROGRESS-MS 35", "SOYUZ-MS 29"]
    assert all(o["NORAD_CAT_ID"] > 99999 for o in omm if o["NORAD_CAT_ID"] not in tle_ids)
    assert "We ran out of 5-digit catalog numbers on 2026-07-11" in text(rec, "e02")
