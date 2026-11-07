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
    assert d.outcome == "blocked" and d.licence.status == "open" and d.source_check.status == "pass"
    assert d.units.status == "unlabelled"
    price = next(f for f in d.field_map if f.canonical == "modal_inr_quintal")
    assert price.unit_status == "unlabelled"
    assert d.account_required and d.no_card
    assert all("api-key" not in e.url for e in rec.manifest.evidence)


def test_resource_licence_is_tied_to_publisher_evidence(record):
    rec = record("S23")
    resource = page(rec, "e04")["selected"]
    metadata = page(rec, "e05")["selected"]
    terms = page(rec, "e06")["selected"]["tabs"]
    assert metadata["uuid"] == [{"value": RESOURCE}]
    assert "AGMARKNET" in resource["catalog_info"]
    assert "licensed under the Government Open Data License-India" in resource["licence_notice"]
    assert any(link["url"] == "https://www.data.gov.in/Godl" for link in resource["licence_links"])
    assert "royalty-free" in terms["Permissible Use Of Data"]
    assert "Attribution:" in terms["Terms And Conditions Of Use Of Data"]
    # Neither a numeric licence code nor an empty metadata field establishes a price unit.
    assert metadata["field_meta_field"] == metadata["field_note"] == []


def test_browser_evidence_is_labelled_as_a_projection(record):
    rec = record("S23")
    for eid in ("e04", "e05", "e06"):
        evidence = next(e for e in rec.manifest.evidence if e.id == eid)
        capture = page(rec, eid)
        assert "projection" in evidence.shows.lower()
        assert capture["capture_method"] in {"browser_dom_projection", "browser_json_projection"}
        assert capture["source_url"] == evidence.url
        assert datetime.fromisoformat(capture["captured_at"]) == evidence.fetched_at
        assert capture["observed_status"] == evidence.status == 200
        assert capture["transformation"]
    metadata = page(rec, "e05")
    assert len(metadata["original_response_sha256"]) == 64
    assert metadata["original_response_bytes"] > 0


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
