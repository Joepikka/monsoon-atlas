"""T110: Karnataka v1 handoff gate. Fast and offline: no network, no data/raw.

docs/releases/ka-v1.md must match the source configs, the model registry and the frozen
shared interfaces. A failure here means evidence changed without the gate page (or the reverse).
"""

import hashlib
import importlib
import json
import re
from pathlib import Path

import pytest

from atlas.config import load_state, load_yaml
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.discovery import Discovery, check, load_manifest
from atlas.models.accuracy import release_checks
from atlas.spatial.context import layer_status

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs/releases/ka-v1.md").read_text("utf-8")
SOURCES = load_state(ROOT / "configs/states/ka.yaml").sources
BY_ID = {s.source_id: s for s in SOURCES}
BLOCKED_MODELS = ["M01", "M02", "M03", "M04", "M06"]
NO_ADAPTER = {"S28"}  # T008 ended at discovery; there is no adapter by design


def table(heading: str, after: str = "") -> list[list[str]]:
    """Body rows of the first markdown table under `## heading` (after the text `after`)."""
    section = PAGE.split(f"\n## {heading}", 1)[1].split("\n## ", 1)[0]
    lines = section.split(after, 1)[1].splitlines() if after else section.splitlines()
    block = []
    for line in lines:
        if line.startswith("|"):
            block.append([c.strip() for c in line.strip("|").split("|")])
        elif block:
            break
    return block[2:]  # drop the header and the separator


def discovery(source_id: str) -> Discovery:
    return load_yaml(ROOT / "configs/sources" / f"{source_id.lower()}.yaml", Discovery)


def registry(name: str) -> dict:
    return json.loads((ROOT / "models/registry" / name).read_text("utf-8"))


def ids(cell: str, prefix: str) -> list[str]:
    return re.findall(rf"\b{prefix}\d{{2}}\b", cell)


def test_every_source_has_a_discovery_record_that_passes_the_contract():
    for s in SOURCES:
        n = s.source_id.lower()
        d = discovery(s.source_id)
        manifest = load_manifest(ROOT / "tests/fixtures" / n / "manifest.json")
        assert check(d, manifest, source_enabled=s.enabled) == [], s.source_id
        assert (d.state, d.verify_task) == ("ka", s.verify_task), s.source_id
        assert (ROOT / "docs/sources" / f"{n}.md").exists(), s.source_id
        assert (ROOT / "tests/sources" / f"test_{n}_discovery.py").exists(), s.source_id


def test_enabled_sources_are_available_with_a_known_licence_and_a_full_stack():
    for s in SOURCES:
        d = discovery(s.source_id)
        n = s.source_id.lower()
        assert s.enabled == (d.outcome == "available"), s.source_id
        if not s.enabled:
            continue
        assert d.licence.status != "unverified", s.source_id
        assert s.verified_by == f"configs/sources/{n}.yaml", s.source_id
        for path in (f"src/atlas/ingest/{n}.py", f"schemas/{n}.json", f"tests/sources/test_{n}.py"):
            assert (ROOT / path).exists(), path


def test_blocked_sources_stay_disabled_with_a_retry_condition_and_no_rows():
    blocked = [s for s in SOURCES if not s.enabled]
    assert blocked  # the gate documents blocked sources; it does not hide them
    for s in blocked:
        d = discovery(s.source_id)
        assert d.retry_condition and d.dependents, s.source_id
        assert s.verified_by is None, s.source_id
        path = ROOT / "src/atlas/ingest" / f"{s.source_id.lower()}.py"
        if not path.exists():
            assert s.source_id in NO_ADAPTER, s.source_id
            continue
        adapter = getattr(
            importlib.import_module(f"atlas.ingest.{s.source_id.lower()}"), s.source_id
        )
        with pytest.raises(SourceUnavailable):
            adapter().fetch(None)
        with pytest.raises(SourceUnavailable):
            adapter().parse(None, None)


def test_source_table_matches_the_configs():
    rows = table("Sources")
    assert [r[0] for r in rows] == [s.source_id for s in SOURCES]
    for sid, _name, outcome, enabled, licence, evidence, retry in rows:
        d = discovery(sid)
        assert (outcome, enabled == "yes", licence) == (
            d.outcome,
            BY_ID[sid].enabled,
            d.licence.status,
        )
        assert (ROOT / "docs/releases" / re.search(r"\((.+?)\)", evidence)[1]).exists(), sid
        assert bool(retry) == (not BY_ID[sid].enabled), sid
    enabled = sum(s.enabled for s in SOURCES)
    assert f"{enabled} of {len(SOURCES)} sources enabled" in PAGE


def test_model_table_matches_the_registry():
    rows = {r[0]: r for r in table("Models")}
    assert list(rows) == ["M01", "M02", "M03", "M04", "M05", "M06"]
    for model in BLOCKED_MODELS:
        record = registry(f"{model.lower()}.json")
        assert (rows[model][2], record["status"]) == ("blocked", "blocked"), model
        for key in ("weights", "baseline_scores", "candidate_scores", "improvement"):
            assert record[key] is None, (model, key)
        assert record["prediction_rows"] == 0, model
        assert (ROOT / record["report"]).exists(), model
        sources = ids(rows[model][3], "S")
        assert sources, model
        assert all(f"configs/sources/{s.lower()}.yaml" in record["evidence"] for s in sources), (
            model
        )
        assert any(not BY_ID[s].enabled for s in sources), model  # blocked because a source is
    for cell in re.findall(r"\(((?:\.\./){2}[^)]+)\)", "".join(r[4] for r in rows.values())):
        assert (ROOT / "docs/releases" / cell).resolve().exists(), cell


def test_m05_v1_release_is_present_and_approved():
    release = registry("M05/v1.json")
    assert registry("M05/v1.approval.json")["decision"] == "approved"
    assert release["status"] == "candidate_eligible"
    assert release["improvement"]["lower95"] > 0  # AGENTS.md promotion rule
    assert {r[0]: r[2] for r in table("Models")}["M05"] == "approved"
    checks = {c["check"]: c["status"] for c in release_checks()}
    slots = {r[0]: r[2] for r in table("Models", after="Core slots")}
    assert slots == {"C1": "blocked", "C2": "approved", "C3": "research-only"}
    assert checks["C1 evaluation report and model card"] == "blocked"
    assert checks["C2 evaluation report and model card"] == "pass"
    assert checks["C3 passes T181 English thresholds"] == "research-only"


def test_layers_are_measured_blocked_or_built_not_mounted():
    approved = {"M05"}
    mounted = {"F015": "fire", "F019": "rera", "F020": "buildings", "F022": "crime"}
    layers = {layer["layer"]: layer for layer in layer_status()}
    for feature, _name, deps, status, _evidence in table("Layers"):
        sources, models = ids(deps, "S"), ids(deps, "M")
        ok = all(BY_ID[s].enabled for s in sources) and all(m in approved for m in models)
        if status == "blocked":
            assert not ok, feature
        else:
            assert status in {"measured", "built, not mounted pending H11"} and ok, feature
        if feature in mounted:
            assert layers[mounted[feature]]["available"] == ok, feature


def test_frozen_interfaces_match_their_hashes():
    rows = table("Frozen shared interfaces")
    assert len(rows) >= 6
    for path, digest in rows:
        data = (ROOT / path.strip("`")).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == digest.strip("`"), (
            f"{path} changed: add a decision entry and update docs/releases/ka-v1.md"
        )
    assert {"src/atlas/contracts.py", "src/atlas/ingest/base.py", "schemas/common.json"} <= {
        p.strip("`") for p, _ in rows
    }


def test_history_dependent_models_are_listed_and_decision_is_recorded():
    listed = {r[0] for r in table("Unresolved history-dependent models")}
    assert listed == set(BLOCKED_MODELS)
    assert "D122" in (ROOT / "docs/decisions.md").read_text("utf-8").split("\n- **D121")[0]
    assert "does not\napprove a public release" in PAGE
