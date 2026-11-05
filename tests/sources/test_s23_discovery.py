"""T025 acceptance: the S23 (data.gov.in mandi prices) discovery record passes the discovery
contract only with cited evidence and explicit access, licence and history status."""

import json
from datetime import datetime

RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"  # read by the owner from the dataset's API tab


def page(rec, eid) -> dict:
    return json.loads(rec.raw(eid).read_text("utf-8"))


def test_s23_discovery_contract(record):
    assert record("S23").problems() == []


def test_s23_status_and_no_key_in_evidence(record):
    rec = record("S23")
    d = rec.discovery
    assert (
        d.outcome == "blocked"
        and d.licence.status == "unverified"
        and d.source_check.status == "pass"
    )
    assert d.account_required and d.no_card
    assert all("api-key" not in e.url for e in rec.manifest.evidence)


def test_no_data_committed(record):
    assert record("S23").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S23").check_local_hashes()


def test_resource_id_is_echoed_by_the_api(record):
    meta = page(record("S23"), "e01")
    assert meta["index_name"] == RESOURCE and meta["status"] == "ok"
    assert (
        meta["title"] == "Current Daily Price of Various Commodities from Various Markets (Mandi)"
    )


def test_pagination_dates_and_price_order(record):
    rec = record("S23")
    first, second = page(rec, "e02"), page(rec, "e03")
    assert first["total"] == second["total"] == 565 and first["count"] == second["count"] == 100
    rows = first["records"] + second["records"]
    assert len({json.dumps(r, sort_keys=True) for r in rows}) == 200
    assert {r["state"] for r in rows} == {"Karnataka"}
    assert {datetime.strptime(r["arrival_date"], "%d/%m/%Y").date().isoformat() for r in rows} == {
        "2026-11-05"
    }
    assert all(0 < r["min_price"] <= r["modal_price"] <= r["max_price"] for r in rows)
