"""T085 acceptance: the S43 (official shelters and flood impact labels) discovery record passes the
discovery contract only with cited evidence and explicit access, licence and history status."""

import pandas as pd


def test_s43_discovery_contract(record):
    assert record("S43").problems() == []


def test_s43_is_blocked_with_explicit_status(record):
    d = record("S43").discovery
    assert d.outcome == "blocked"
    assert (d.licence.status, d.history.status, d.source_check.status) == (
        "unverified",
        "not_public",
        "fail",
    )
    assert {"T086", "T089", "T090", "T091"} <= set(d.dependents)
    assert {f.url for f in d.failed_fetches} == {
        "https://bbmp.gov.in/",
        "https://gba.karnataka.gov.in/",
    }


def test_no_labels_committed(record):
    assert record("S43").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S43").check_local_hashes()


def complaints(record) -> pd.DataFrame:
    df = pd.read_csv(record("S43").raw("e08"), encoding="cp1252", low_memory=False)
    dash = pd.to_datetime(df["created_at"], format="%m-%d-%Y %H:%M", errors="coerce")
    slash = pd.to_datetime(df["created_at"], format="%m/%d/%Y %H:%M", errors="coerce")
    return df.assign(t=dash.fillna(slash))


def test_complaint_dates_are_month_first(record):
    t = complaints(record)["t"]
    assert t.notna().all()
    assert t.is_monotonic_increasing  # month-first reading puts every row in time order
    assert (str(t.min().date()), str(t.max().date())) == ("2019-01-01", "2022-07-31")


def test_flooding_complaint_counts_match_record(record):
    df = complaints(record)
    flood = df[df["sub_category_title"] == "Flooding/Waterlogging Of Roads And Footpaths"]
    ward_days = flood.assign(day=flood["t"].dt.date).drop_duplicates(["ward_id", "day"])
    monsoon = ward_days[ward_days["t"].dt.month.between(6, 11)]
    assert (len(flood), len(ward_days), len(monsoon)) == (226, 215, 136)
    assert monsoon.groupby(monsoon["t"].dt.year).size().to_dict() == {
        2019: 52,
        2020: 34,
        2021: 35,
        2022: 15,
    }
