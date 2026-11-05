"""T008 acceptance: the S28 (KWRIS) discovery record passes the discovery contract only with cited
evidence and explicit access, licence and history status. "blocked" is a result, not data."""


def test_s28_discovery_contract(record):
    assert record("S28").problems() == []


def test_s28_is_blocked_with_explicit_status(record):
    d = record("S28").discovery
    assert d.outcome == "blocked"
    assert (d.licence.status, d.history.status, d.units.status) == (
        "restricted",
        "not_public",
        "unlabelled",
    )
    assert d.no_card and d.account_required
    assert {"T027", "T092", "T095"} <= set(d.dependents)
    # No unit is assumed, so nothing is converted to the canonical units.
    assert all(f.unit_status != "labelled" for f in d.field_map)


def test_blocked_source_commits_no_data(record):
    assert record("S28").committed_files() == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    record("S28").check_local_hashes()
