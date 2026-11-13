"""T025 and T269 acceptance: the S23 (data.gov.in mandi prices) discovery record passes the
discovery contract only with cited evidence; T269 verifies Karnataka onion only and S23 stays
blocked until the T270 adapter."""

import json
from datetime import datetime
from pathlib import Path

RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"  # read by the owner from the dataset's API tab
HISTORY = "35985678-0d79-46b4-9ed6-6f13308a1d24"  # variety-wise history resource (D201, T269)
CATALOG = "6141ea17-a69d-4713-b600-0a43c8fd9a6c"
RAW = Path(__file__).resolve().parents[2] / "data" / "raw"


def page(rec, eid) -> dict:
    return json.loads(rec.raw(eid).read_text("utf-8"))


def test_s23_discovery_contract(record):
    assert record("S23").problems() == []


def test_s23_status_and_no_key_in_evidence(record):
    rec = record("S23")
    d = rec.discovery
    assert d.outcome == "blocked" and d.licence.status == "open" and d.source_check.status == "pass"
    assert (
        d.units.status == "onion_only"
        and "Rs./Quintal" in d.units.detail
        and "D201" in d.units.detail
    )
    price = next(f for f in d.field_map if f.canonical == "modal_inr_quintal")
    assert price.unit_status == "labelled" and "Onion only" in price.detail
    assert d.account_required and d.no_card
    assert all("api-key" not in e.url for e in rec.manifest.evidence)
    for e in rec.manifest.evidence:
        path = RAW / e.raw_path
        if path.exists():
            assert b"api-key" not in path.read_bytes(), e.id


def test_only_karnataka_onion_is_verified_and_s23_stays_blocked(record):
    """Units are per commodity; nothing but Onion may be read until H16 records another unit."""
    d = record("S23").discovery
    assert d.outcome == "blocked" and d.retry_condition.startswith("T270: adapter")
    assert "State=Karnataka, Commodity=Onion only" in d.units.detail
    assert "H16" in d.units.detail and "H16" in d.retry_condition
    assert "T270" in d.dependents


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


# T269: the variety-wise history resource.


def rows(rec, *eids) -> list[dict]:
    return [r for eid in eids for r in page(rec, eid)["records"]]


def key(r) -> str:
    return json.dumps(r, sort_keys=True)


PAGES = [f"e{i:02d}" for i in range(9, 20)]  # limit 10000, offsets 0 to 100000


def test_history_resource_is_the_same_catalogue(record):
    rec = record("S23")
    meta = page(rec, "e07")
    assert meta["index_name"] == HISTORY and meta["status"] == "ok"
    assert meta["title"] == "Variety-wise Daily Market Prices Data of Commodity"
    assert meta["catalog_uuid"] == CATALOG
    assert page(rec, "e05")["selected"]["field_catalog_reference"][0]["target_uuid"] == CATALOG
    assert [f["id"] for f in meta["field"]] == [
        "Arrival_Date", "Commodity", "Commodity_Code", "District", "Grade", "Market",
        "Max_Price", "Min_Price", "Modal_Price", "State", "Variety",
    ]  # fmt: skip
    assert HISTORY in rec.discovery.landing_url


def test_page_sizes_and_stable_total(record):
    rec = record("S23")
    assert [page(rec, e)["count"] for e in ("e07", "e08", "e09")] == [1000, 5000, 10000]
    assert {page(rec, e)["total"] for e in ["e07", "e08", *PAGES]} == {103423}
    assert sum(page(rec, e)["count"] for e in PAGES) == 103423


def test_offset_paging_duplicates_rows(record):
    """Offset paging is unstable, so the backfill must query one Arrival_Date per request."""
    rec = record("S23")
    paged = rows(rec, *PAGES)
    assert len(paged) == 103423 and len({key(r) for r in paged}) == 93423
    first, third = {key(r) for r in rows(rec, "e09")}, {key(r) for r in rows(rec, "e11")}
    assert len(first & third) == 9271
    assert not {key(r) for r in rows(rec, "e07")} & first  # limit 1000 vs 10000 first pages
    assert "Arrival_Date per request" in rec.discovery.retry_condition


def test_date_filter_is_complete_and_stable(record):
    rec = record("S23")
    paged = {key(r) for r in rows(rec, *PAGES)}
    for eid, day, n in [
        ("e20", "02/01/2019", 14), ("e21", "15/07/2004", 0), ("e22", "15/07/2026", 24),
        ("e23", "04/11/2026", 23), ("e24", "12/11/2026", 18), ("e25", "13/11/2026", 0),
    ]:  # fmt: skip
        got = rows(rec, eid)
        assert page(rec, eid)["total"] == len(got) == n, eid
        assert {(r["State"], r["Commodity"], r["Arrival_Date"]) for r in got} <= {
            ("Karnataka", "Onion", day)
        }
        day_paged = {k for k in paged if json.loads(k)["Arrival_Date"] == day}
        assert day_paged <= {key(r) for r in got}, eid  # the day query holds every paged row
    assert len({key(r) for r in rows(rec, "e23")} - paged) == 10
    assert {key(r) for r in rows(rec, "e23")} == {key(r) for r in rows(rec, "e26")}


def test_history_span_and_publication_lag(record):
    rec = record("S23")
    d = rec.discovery
    days = {datetime.strptime(r["Arrival_Date"], "%d/%m/%Y").date() for r in rows(rec, *PAGES)}
    assert (min(days).isoformat(), max(days).isoformat()) == (d.earliest_date, d.latest_date)
    daily = page(rec, "e27")
    assert daily["index_name"] == RESOURCE
    assert {r["arrival_date"] for r in daily["records"]} == {"13/11/2026"}
    assert page(rec, "e25")["total"] == 0  # the history has no 13/11 rows yet: about a day behind


def test_onion_quality_counts_match_the_record(record):
    rec = record("S23")
    distinct = [json.loads(k) for k in {key(r) for r in rows(rec, *PAGES)}]
    price = [
        tuple(float(r[f]) for f in ("Min_Price", "Modal_Price", "Max_Price")) for r in distinct
    ]
    assert sum(not lo <= mid <= hi for lo, mid, hi in price) == 20
    assert sum(min(lo, hi) <= 0 for lo, _, hi in price) == 31
    assert min(mid for _, mid, _ in price) > 0
    keys = [
        (r["Arrival_Date"], r["District"], r["Market"], r["Variety"], r["Grade"]) for r in distinct
    ]
    assert len(keys) - len(set(keys)) == 3
    assert (
        len({r["District"] for r in distinct}) == 41 and len({r["Market"] for r in distinct}) == 164
    )
    assert {r["Commodity_Code"] for r in distinct} == {"23", 23}
