"""T073 acceptance: the S21 (Datameet railways) discovery record passes the discovery contract;
the pinned commit, CC0 licence, file contents and stop order are checked against the evidence."""

import html
import json
import re
from collections import defaultdict

COMMIT = "e0c538a1e41ae5eace454d2818902e1065608e16"


def body(rec, eid):
    return json.loads(rec.raw(eid).read_text(encoding="utf-8"))


def test_s21_discovery_contract(record):
    assert record("S21").problems() == []


def test_s21_status(record):
    d = record("S21").discovery
    assert d.outcome == "available"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "open",
        "available",
        "pass",
    )
    assert (d.earliest_date, d.latest_date) == (None, "2016-08-08")


def test_no_data_committed(record):
    assert record("S21").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S21").check_local_hashes()


def test_pinned_commit_and_cc0(record):
    rec = record("S21")
    commit = body(rec, "e04")
    assert (
        commit["sha"] == COMMIT and commit["commit"]["committer"]["date"] == "2016-08-08T07:20:00Z"
    )
    assert all(COMMIT in e.url for e in rec.manifest.evidence if e.id in ("e06", "e07", "e08"))
    readme = re.sub(
        r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", rec.raw("e02").read_text("utf-8")))
    )
    assert "License CC0" in readme and body(rec, "e03")["license"] is None


def test_contents_none_strings_and_stop_order(record):
    rec = record("S21")
    stations = body(rec, "e06")["features"]
    assert len(stations) == 8990 and sum(s["geometry"] is None for s in stations) == 293
    assert sum(s["properties"].get("state") == "Karnataka" for s in stations) == 301
    stops = body(rec, "e08")
    assert len(stops) == 417080 and len(body(rec, "e07")["features"]) == 5208
    by_train = defaultdict(list)
    for stop in stops:
        by_train[stop["train_number"]].append(stop)
    assert sum(v[0]["arrival"] == "None" for v in by_train.values()) == 5174
    assert sum(v[-1]["departure"] == "None" for v in by_train.values()) == 5164
    rising = sum(
        all(a["id"] < b["id"] for a, b in zip(v, v[1:], strict=False)) for v in by_train.values()
    )
    assert (len(by_train), rising) == (5208, 5199)
