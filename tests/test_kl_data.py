"""T226/T129: state isolation, Kerala dam registry, datum status and label audit report.

These checks do not certify M07 training readiness (datum gate unmet, T118 pending).
"""

import json
import re
from pathlib import Path

import pytest
import yaml

from atlas.config import load_state, load_yaml
from atlas.ingest.discovery import Discovery
from atlas.ingest.s32 import _Report

ROOT = Path(__file__).resolve().parents[1]
S32_MANIFEST = ROOT / "tests/fixtures/s32/manifest.json"


def test_kerala_config_exists():
    assert (ROOT / "configs/states/kl.yaml").is_file(), "T226 Kerala bootstrap is missing"


@pytest.fixture
def kl():
    path = ROOT / "configs/states/kl.yaml"
    assert path.is_file(), "T226 Kerala bootstrap is missing"
    return load_state(path)


def test_state_paths_cannot_mix_karnataka_and_kerala(kl):
    ka = load_state(ROOT / "configs/states/ka.yaml")
    assert (ka.state_id, kl.state_id, kl.name) == ("ka", "kl", "Kerala")
    assert (kl.storage_tz, kl.display_tz) == ("UTC", "Asia/Kolkata")
    for kind in ("raw_root", "clean_root", "publish_root"):
        ka_path, kl_path = getattr(ka.paths, kind), getattr(kl.paths, kind)
        assert not kl_path.is_absolute()
        assert ".." not in kl_path.parts
        assert kl_path.parts[-1] == "kl"
        assert ka_path != kl_path and ka_path not in kl_path.parents
        assert kl_path not in ka_path.parents


def test_kerala_does_not_enable_unimplemented_or_ka_only_adapters(kl):
    assert {"S32", "S33", "S34", "S35", "S36", "S37", "S40", "S41", "S42", "S43"} <= {
        source.source_id for source in kl.sources
    }
    # S06 and S08 are national/global grids whose verify tasks passed (T142, D127).
    assert {s.source_id for s in kl.sources if s.enabled} == {"S06", "S08", "S32", "S36"}
    # Karnataka discovery is not evidence for Kerala wards or flood labels.
    assert kl.source("S40").verified_by is None
    assert kl.source("S43").verified_by is None
    with pytest.raises(KeyError):
        kl.source("S28")  # Karnataka reservoir source must not leak into Kerala.


@pytest.mark.parametrize("source_id", ["S32", "S33", "S34", "S35", "S36", "S37", "S41", "S42"])
def test_existing_discovery_references_belong_to_kerala(kl, source_id):
    source = kl.source(source_id)
    discovery = load_yaml(ROOT / source.verified_by, Discovery)
    assert discovery.source_id == source_id
    assert discovery.state == "kl"
    assert discovery.verify_task == source.verify_task
    # Only T114 (S32) and T122 (S36) are completed Kerala adapters; discovery alone enables nothing.
    assert source.enabled == (source_id in {"S32", "S36"})
    if source_id in {"S33", "S35", "S37", "S41", "S42"}:
        assert discovery.outcome == "blocked"


# --- T129: dam registry, datum status, precedence and label audit report ---

REGISTRY = ROOT / "configs/states/kl/dams.yaml"
REPORT = ROOT / "docs/labels/kerala.md"


def _registry():
    return yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))


def _s32_ids_from_report() -> set[str]:
    # Same identity rule as the S32 adapter, applied to the captured 05-Nov-2026 report.
    parser = _Report()
    parser.feed((ROOT / "tests/fixtures/s32_kseb_e02.html").read_text(encoding="utf-8"))
    (table,) = [t for t in parser.tables if t and t[0][0] == "Name of Dam / Reservoir"]
    return {
        f"kseb:{c[1].lower()}:{re.sub(r'[^a-z0-9]+', '-', c[0].lower()).strip('-')}"
        for c in table[1:]
    }


def test_two_states_have_isolated_configs():
    ka, kl = (load_state(ROOT / f"configs/states/{s}.yaml") for s in ("ka", "kl"))
    assert {s.source_id for s in kl.sources} - {s.source_id for s in ka.sources} >= {"S32", "S36"}
    assert kl.source("S33").verified_by == "configs/sources/s33.yaml"
    assert not kl.source("S33").enabled
    assert _registry()["state_id"] == "kl"
    # The registry sits outside the StateConfig-validated *.yaml glob.
    assert REGISTRY.parent.name == "kl" and REGISTRY.parent != REGISTRY.parent.parent


def test_every_registered_dam_id_is_in_source_evidence():
    ids = [d["reservoir_id"] for d in _registry()["dams"]]
    assert len(ids) == len(set(ids)) == 16
    assert set(ids) == _s32_ids_from_report()


def test_datum_is_unknown_unless_manual_evidence_names_it():
    evidence = {e["id"]: e["shows"] for e in json.loads(S32_MANIFEST.read_text())["evidence"]}
    dams = _registry()["dams"]
    for dam in dams:
        assert set(dam["datum_evidence"]) <= set(evidence), dam["reservoir_id"]
        if dam["datum_status"] == "known":
            assert dam["datum"] == "MSL"
            assert any(
                "MSL" in evidence[e] or "msl" in evidence[e] or "mean sea" in evidence[e]
                for e in dam["datum_evidence"]
            ), dam["reservoir_id"]
        else:
            assert dam["datum_status"] == "unknown" and "datum" not in dam
    known = {d["reservoir_id"] for d in dams if d["datum_status"] == "known"}
    assert len(known) == 4 < _registry()["datum_gate"]["required_known_dams"]


def test_dam_level_precedence_and_monthly_never_daily():
    order = _registry()["daily_level_precedence"]
    assert [p["source_id"] for p in order] == ["S32", "S34", "S33"]
    assert [p.get("enabled", True) for p in order] == [True, False, False]
    assert order[2]["daily_label_allowed"] is False


def test_history_report_has_required_sections_and_exclusions():
    text = REPORT.read_text(encoding="utf-8")
    for heading in (
        "## History availability report",
        "### Label families held",
        "### EXCLUDED labels",
    ):
        assert heading in text
    for excluded in (
        "S36 district period totals",
        "Pre-2018 negatives",
        "S34 KSDMA dam reports",
        "S33 monthly dam statistics",
        "Landslide labels (S37)",
        "Kerala ward or taluk geometry (S40)",
        "Kerala institutional shelters",
    ):
        assert excluded in text
    assert "never reused for Kerala" in text
    assert "no monthly-to-daily or period-to-daily interpolation" in text
