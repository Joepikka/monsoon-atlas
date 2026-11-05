"""T008 acceptance: the S28 (KWRIS) discovery record passes the discovery contract only with cited
evidence and explicit access, licence and history status. "blocked" is a result, not data."""

import hashlib
from pathlib import Path

import pytest

from atlas.config import load_state, load_yaml
from atlas.ingest.discovery import Discovery, check, load_manifest

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "configs" / "sources" / "s28.yaml"
MANIFEST = ROOT / "tests" / "fixtures" / "s28" / "manifest.json"
RAW = ROOT / "data" / "raw"


def s28_enabled() -> bool:
    ka = load_state(ROOT / "configs" / "states" / "ka.yaml")
    return next(s for s in ka.sources if s.source_id == "S28").enabled


@pytest.fixture
def record():
    return load_yaml(RECORD, Discovery), load_manifest(MANIFEST)


def test_s28_discovery_contract(record):
    d, manifest = record
    assert check(d, manifest, source_enabled=s28_enabled()) == []


def test_s28_is_blocked_with_explicit_status(record):
    d, _ = record
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


def test_blocked_source_commits_no_data():
    assert sorted(p.name for p in MANIFEST.parent.iterdir()) == ["manifest.json"]


def test_local_evidence_matches_manifest(record):
    _, manifest = record
    if not RAW.exists():
        pytest.skip("raw evidence is local only (not redistributed)")
    for e in manifest.evidence:
        path = RAW / e.raw_path
        assert path.exists(), e.id
        assert hashlib.sha256(path.read_bytes()).hexdigest() == e.sha256, e.id


# --- the contract rejects incomplete records ------------------------------------------------


def _with(d: Discovery, **changes) -> Discovery:
    return Discovery.model_validate(d.model_dump() | changes)


def test_rejects_uncited_claim(record):
    d, manifest = record
    bad = _with(d, licence=d.licence.model_dump() | {"evidence": ["e99"]})
    assert any("cites e99" in p for p in check(bad, manifest, source_enabled=False))


def test_rejects_unknown_licence_status(record):
    d, manifest = record
    bad = _with(d, licence=d.licence.model_dump() | {"status": "probably fine"})
    assert any("licence status" in p for p in check(bad, manifest, source_enabled=False))


def test_rejects_blocked_without_retry_condition(record):
    d, manifest = record
    bad = _with(d, retry_condition=None)
    assert any("retry condition" in p for p in check(bad, manifest, source_enabled=False))


def test_rejects_blocked_source_left_enabled(record):
    d, manifest = record
    assert any("enabled" in p for p in check(d, manifest, source_enabled=True))


def test_rejects_available_without_licence_or_history(record):
    d, manifest = record
    bad = _with(d, outcome="available")
    assert any("known licence" in p for p in check(bad, manifest, source_enabled=False))


def test_rejects_claim_without_evidence(record):
    d, _ = record
    with pytest.raises(ValueError):
        _with(d, history=d.history.model_dump() | {"evidence": []})
