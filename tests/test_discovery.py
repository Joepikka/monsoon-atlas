"""The discovery contract (D27) rejects incomplete records; the committed S28 record is the base."""

from pathlib import Path

import pytest

from atlas.config import load_yaml
from atlas.ingest.discovery import Discovery, check, load_manifest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def base():
    d = load_yaml(ROOT / "configs" / "sources" / "s28.yaml", Discovery)
    return d, load_manifest(ROOT / "tests" / "fixtures" / "s28" / "manifest.json")


def _with(d: Discovery, **changes) -> Discovery:
    return Discovery.model_validate(d.model_dump() | changes)


def test_base_record_passes(base):
    d, manifest = base
    assert check(d, manifest, source_enabled=False) == []


def test_rejects_uncited_claim(base):
    d, manifest = base
    bad = _with(d, licence=d.licence.model_dump() | {"evidence": ["e99"]})
    assert any("cites e99" in p for p in check(bad, manifest, source_enabled=False))


def test_rejects_unknown_licence_status(base):
    d, manifest = base
    bad = _with(d, licence=d.licence.model_dump() | {"status": "probably fine"})
    assert any("licence status" in p for p in check(bad, manifest, source_enabled=False))


def test_rejects_blocked_without_retry_condition(base):
    d, manifest = base
    bad = _with(d, retry_condition=None)
    assert any("retry condition" in p for p in check(bad, manifest, source_enabled=False))


def test_rejects_blocked_source_left_enabled(base):
    d, manifest = base
    assert any("enabled" in p for p in check(d, manifest, source_enabled=True))


def test_rejects_available_without_licence_or_history(base):
    d, manifest = base
    bad = _with(d, outcome="available")
    assert any("known licence" in p for p in check(bad, manifest, source_enabled=False))


def test_rejects_claim_without_evidence(base):
    d, _ = base
    with pytest.raises(ValueError):
        _with(d, history=d.history.model_dump() | {"evidence": []})


def test_rejects_manifest_for_another_source(base):
    d, manifest = base
    other = manifest.model_copy(update={"source_id": "S40"})
    assert any("manifest is for S40" in p for p in check(d, other, source_enabled=False))
