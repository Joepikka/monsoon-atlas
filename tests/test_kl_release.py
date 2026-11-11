"""T144: Kerala release gate. Fast and offline: no network, no data/raw.

docs/releases/kl.md must match the Kerala source configs, the model registry, the T142 replay
file, git and the Karnataka gate. A failure here means evidence changed without the page.
"""

import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from atlas.config import load_state, load_yaml
from atlas.ingest.discovery import Discovery, check, load_manifest

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs/releases/kl.md").read_text("utf-8")
KA_PAGE = (ROOT / "docs/releases/ka-v1.md").read_text("utf-8")
KL = {s.source_id: s for s in load_state(ROOT / "configs/states/kl.yaml").sources}
KA = {s.source_id: s for s in load_state(ROOT / "configs/states/ka.yaml").sources}
BLOCKED_MODELS = ["M07", "M08", "M09", "M10"]
TRACKED = subprocess.run(
    ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
).stdout.splitlines()


def table(page: str, heading: str) -> list[list[str]]:
    """Body rows of the first markdown table under `## heading`."""
    section = page.split(f"\n## {heading}", 1)[1].split("\n## ", 1)[0]
    block = []
    for line in section.splitlines():
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


def test_source_table_matches_configs_and_discovery():
    rows = table(PAGE, "Sources")
    assert [r[0] for r in rows] == list(KL)
    for sid, _name, outcome, enabled, licence, evidence, retry in rows:
        d, n = discovery(sid), sid.lower()
        manifest = load_manifest(ROOT / "tests/fixtures" / n / "manifest.json")
        assert check(d, manifest, source_enabled=KL[sid].enabled) == [], sid
        assert (outcome, enabled == "yes", licence) == (
            d.outcome,
            KL[sid].enabled,
            d.licence.status,
        ), sid
        assert (ROOT / "docs/releases" / re.search(r"\((.+?)\)", evidence)[1]).exists(), sid
        assert bool(retry) == (not KL[sid].enabled), sid  # every disabled row says how to retry
        if d.outcome == "blocked":
            assert d.retry_condition and not KL[sid].enabled, sid
        if KL[sid].enabled:
            assert d.outcome == "available" and KL[sid].verified_by, sid
    on = sum(s.enabled for s in KL.values())
    blocked = sum(discovery(s).outcome == "blocked" for s in KL)
    assert f"{on} of {len(KL)} Kerala sources enabled" in PAGE
    assert f"{blocked} have outcome `blocked`" in PAGE


def test_models_are_blocked_with_null_scores_and_no_forecast_claims():
    rows = {r[0]: r for r in table(PAGE, "Models")}
    assert list(rows) == BLOCKED_MODELS
    for model, row in rows.items():
        record = registry(f"{model.lower()}.json")
        assert (row[2], record["status"]) == ("blocked", "blocked"), model
        for key in ("weights", "baseline_scores", "candidate_scores", "improvement"):
            assert record[key] is None, (model, key)
        assert record["prediction_rows"] == 0, model
        assert (ROOT / record["report"]).exists(), model
        blocked_by = ids(row[3], "S")
        assert blocked_by, model
        assert all(f"configs/sources/{s.lower()}.yaml" in record["evidence"] for s in blocked_by)
        assert any(not (KL.get(s) or KA[s]).enabled for s in blocked_by), model
    for cell in re.findall(r"\(((?:\.\./){2}[^)]+)\)", "".join(r[4] for r in rows.values())):
        assert (ROOT / "docs/releases" / cell).resolve().exists(), cell
    assert "No Kerala model is research-only" in PAGE
    # A forecast, probability or prediction is only ever mentioned to deny it or name a source.
    denial = re.compile(r"\b(no|not|never|nor|none|without|zero|0|blocked)\b|research-only", re.I)
    for line in PAGE.splitlines():
        if re.search(r"forecast|probabilit|predict", line, re.I) and not line.startswith(
            ("| S", "| M")
        ):
            assert denial.search(line), line


def test_layers_follow_their_dependencies():
    for _section, _layer, deps, status, _evidence in table(PAGE, "Layers"):
        sources, models = ids(deps, "S"), ids(deps, "M")
        ok = all((KL.get(s) or KA[s]).enabled for s in sources) and not set(models) & set(
            BLOCKED_MODELS
        )
        if status == "blocked":
            assert not ok, deps
        else:
            assert status in {"measured", "built, not mounted pending H11"} and ok, deps


def test_2018_chronology_matches_the_replay_file():
    path = ROOT / "reports/eda/05_kl_flood2018/replay2018.json"
    if not path.exists():  # untracked since the H11 answer (D166): holds S08 rain, local only
        pytest.skip("replay2018.json holds S08 rainfall and is local only (D166)")
    replay = json.loads(path.read_text("utf-8"))
    end = replay["window"]["end"]
    assert replay["forecast_vintages"] == [] and "**0 forecast vintages**" in PAGE
    for r in replay["records"]:
        known = bool(r["known_from"]) and r["known_from"] <= end
        assert r["mode"] == ("as_known" if known else "reconstructed"), r["id"]
        assert r["source_id"] != "S08" or r["mode"] == "reconstructed", r["id"]  # grid is later
    counts = collections.Counter(
        (r["source_id"], r["kind"], r["mode"], r["known_from"] or "none") for r in replay["records"]
    )
    rows = table(PAGE, "2018 chronology audit")
    assert {(r[0], r[1], r[2], r[3]): int(r[4]) for r in rows} == dict(counts)
    modes = collections.Counter(r["mode"] for r in replay["records"])
    assert f"{modes['as_known']} records are `as_known`, {modes['reconstructed']} are" in PAGE
    assert f"{len(replay['records'])} records" in PAGE
    assert "memoranda submission dates" in PAGE and "2019 upload path" in PAGE  # D127


def test_restricted_sources_commit_manifests_only():
    restricted = {s for s in KL if discovery(s).licence.status == "restricted"}
    rows = table(PAGE, "Licence audit")
    assert {r[0] for r in rows} == restricted
    # T218 (D162): the web manifest is the one tracked file under web/public; it holds no data.
    published = [p for p in TRACKED if p.startswith(("data/", "web/public/"))]
    assert published in ([], ["web/public/manifest.webmanifest"])
    for sid in restricted:
        n = sid.lower()
        files = [
            p for p in TRACKED if p.startswith((f"tests/fixtures/{n}/", f"tests/fixtures/{n}_"))
        ]
        assert files == [f"tests/fixtures/{n}/manifest.json"], (sid, files)


def test_malayalam_labels_are_complete_and_flagged_for_review():
    data = json.loads((ROOT / "docs/releases/kl-ml.json").read_text("utf-8"))
    assert data["_status"] == "machine-drafted, needs native review before release (owner H11)"
    strings = data["strings"]
    required = {
        "layer_dams": "Dams",
        "layer_flood": "Flood",
        "layer_landslide": "Landslide",
        "scheduled_not_live": "Scheduled, not live",
        "not_a_safe_route": "not a safe route",
        "research_only": "research-only",
        "blocked": "blocked",
    }
    for key, english in required.items():
        assert strings[key]["en"] == english, key
    for key, pair in strings.items():
        assert re.search(r"[ഀ-ൿ]", pair["ml"]), key  # Malayalam script, not English
    assert "machine-drafted and need native review before release (owner H11)" in PAGE


def test_owner_gated_items_are_listed_against_their_configs():
    rows = {r[0] for r in table(PAGE, "Owner-gated items")}
    assert {"H11", "H12", "H15", "T118", "S18", "S41"} <= rows
    assert "H12" in discovery("S26").retry_condition
    assert "H15" in discovery("S42").retry_condition
    assert not (KL["S34"].enabled or KL["S42"].enabled or KL["S26"].enabled)
    assert "Nothing here\napproves a public release" in PAGE
    assert "D129" in (ROOT / "docs/decisions.md").read_text("utf-8").split("\n- **D128")[0]


def test_karnataka_stays_functional_and_the_frozen_interfaces_unchanged():
    rows = table(KA_PAGE, "Frozen shared interfaces")
    assert len(rows) >= 6
    for path, digest in rows:
        data = (ROOT / path.strip("`")).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == digest.strip("`"), path
    on = sum(s.enabled for s in KA.values())
    assert f"{on} of {len(KA)} sources enabled" in KA_PAGE
    release = registry("M05/v1.json")
    assert registry("M05/v1.approval.json")["decision"] == "approved"
    assert release["improvement"]["lower95"] > 0
    assert "[ka-v1.md](ka-v1.md)" in PAGE
