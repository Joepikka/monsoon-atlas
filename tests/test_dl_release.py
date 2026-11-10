"""T166: Delhi release gate. Fast and offline: no network, no data/raw.

docs/releases/dl.md must match the Delhi source configs, the model registry, git and the
Karnataka and Kerala gates. A failure here means evidence changed without the page.
"""

import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

from atlas.analysis.prices import load_record
from atlas.config import load_state, load_yaml
from atlas.ingest.discovery import Discovery, check, load_manifest

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs/releases/dl.md").read_text("utf-8")
KA_PAGE = (ROOT / "docs/releases/ka-v1.md").read_text("utf-8")
KL_PAGE = (ROOT / "docs/releases/kl.md").read_text("utf-8")
STATES = {s: load_state(ROOT / f"configs/states/{s}.yaml") for s in ("ka", "kl", "dl")}
DL, KA, KL = ({x.source_id: x for x in STATES[s].sources} for s in ("dl", "ka", "kl"))
MODELS = ["M12", "M13", "M14", "M15"]
TRACKED = subprocess.run(
    ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
).stdout.splitlines()
spec = importlib.util.spec_from_file_location("audit", ROOT / "scripts/audit_dependencies.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


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
    assert [r[0] for r in rows] == list(DL)
    for sid, _name, outcome, enabled, licence, evidence, retry in rows:
        d, n = discovery(sid), sid.lower()
        manifest = load_manifest(ROOT / "tests/fixtures" / n / "manifest.json")
        assert check(d, manifest, source_enabled=DL[sid].enabled) == [], sid
        assert (outcome, enabled == "yes", licence) == (
            d.outcome,
            DL[sid].enabled,
            d.licence.status,
        )
        assert (ROOT / "docs/releases" / re.search(r"\((.+?)\)", evidence)[1]).exists(), sid
        assert bool(retry) == (not DL[sid].enabled), sid  # every disabled row says how to retry
        assert not DL[sid].enabled and (d.outcome == "available" or d.retry_condition), sid
    on = sum(s.enabled for s in DL.values())
    blocked = sum(discovery(s).outcome == "blocked" for s in DL)
    assert f"{on} of {len(DL)} Delhi sources enabled" in PAGE
    assert f"{blocked} have outcome `blocked`" in PAGE
    assert "S04" not in DL and KA["S04"].enabled  # CAMS: Karnataka only (D141)
    assert "enabled for\nKarnataka only" in PAGE


def test_models_are_blocked_with_null_scores_and_no_forecast_claims():
    rows = {r[0]: r for r in table(PAGE, "Models")}
    assert list(rows) == MODELS
    views = {
        "M12": ROOT / "reports/eda/08_delhi_transit/transit_view.json",
        "M14": ROOT / "reports/eda/09_delhi_air/air_view.json",
    }
    for model, row in rows.items():
        record = registry(f"{model.lower()}.json")
        config = load_record(ROOT / f"configs/models/{model.lower()}.yaml")
        assert (row[2], record["status"], config["status"]) == ("blocked",) * 3, model
        assert config["enabled"] is False and config["split_manifest"] is None, model
        for key in ("weights", "baseline_scores", "candidate_scores", "improvement"):
            assert record[key] is None, (model, key)
        assert record["prediction_rows"] == 0, model
        assert (ROOT / record["report"]).exists(), model
        blocked_by = ids(row[3], "S")
        assert blocked_by, model
        assert all(f"configs/sources/{s.lower()}.yaml" in record["evidence"] for s in blocked_by)
        assert any(not (DL.get(s) or KA[s]).enabled for s in blocked_by), model
        assert all(s in record["reason"] for s in blocked_by[:1]), model
        if model in views:  # the badge the UI card shows is the registry status
            view = json.loads(views[model].read_text("utf-8"))
            card = view["card"]
            assert (card["model_id"], card["status"]) == (model, record["status"])
            assert set(card) == {"status", "model_id", "reason", "coverage"}  # no score
    for cell in re.findall(r"\(((?:\.\./){2}[^)]+)\)", "".join(r[4] for r in rows.values())):
        assert (ROOT / "docs/releases" / cell).resolve().exists(), cell
    assert "No Delhi model is research-only" in PAGE
    assert not [p for p in TRACKED if re.search(r"reports/models/m1[2-5]-case-study", p)]
    # A forecast, probability or prediction is only ever mentioned to deny it or name a source.
    denial = re.compile(r"\b(no|not|never|nor|none|without|zero|0|blocked)\b|research-only", re.I)
    for line in PAGE.splitlines():
        if re.search(r"forecast|probabilit|predict", line, re.I) and not line.startswith(
            ("| S", "| M")
        ):
            assert denial.search(line), line


def test_label_windows_match_the_configs_and_none_has_started():
    rows = {r[0]: r for r in table(PAGE, "Label windows")}
    assert list(rows) == MODELS
    for model, row in rows.items():
        plan = load_record(ROOT / f"configs/models/{model.lower()}.yaml")["planned_splits"]
        span = [" to ".join(plan[k]) for k in ("train", "tune", "calibrate", "locked_test")]
        assert row[1:] == [plan["collect_from"], *span, "planned, not started"], model
        assert registry(f"{model.lower()}.json")["split_sha256"] is None, model
    assert not list((ROOT / "docs/studies").glob("*manifest*"))
    assert "calendar delay, not a development failure" in " ".join(PAGE.split())
    assert "shifts together" in PAGE and "No window has\nstarted" in PAGE


def test_layers_follow_their_dependencies():
    for _section, _layer, deps, status, _evidence in table(PAGE, "Layers"):
        sources, models = ids(deps, "S"), ids(deps, "M")
        down = [s for s in sources if discovery(s).outcome == "blocked"] + [
            m for m in models if registry(f"{m.lower()}.json")["status"] == "blocked"
        ]
        off = [s for s in sources if s not in DL or not DL[s].enabled]
        if status == "blocked":
            assert down, deps
        elif status == "not configured":
            assert not down and off, deps
        else:
            assert status == "built, not mounted pending H11" and deps == "none", deps
    for name in ("Transit", "AirQuality"):
        assert f"web/src/components/{name}.tsx" in PAGE
        assert (ROOT / f"web/src/components/{name}.tsx").exists()
    for path in (ROOT / "web/src").rglob("*.ts*"):  # not mounted: nothing outside imports them
        if path.parent.name != "components" and ".test." not in path.name:
            assert not re.search(r"/(Transit|AirQuality|ScoreCard)['\"]", path.read_text("utf-8"))


def test_nothing_is_published_without_data_and_no_accuracy_is_shown():
    rows = {r[0]: r[1] for r in table(PAGE, "Published and not published")}
    assert rows == {
        "Scheduled bus transit": "not published",
        "Live bus positions": "not published",
        "Observed air quality": "not published",
        "CAMS estimate for Delhi": "not published",
        "Blocked model cards (M12 to M15)": "published",
        "ETA accuracy": "none",
        "AQI accuracy": "none",
        "Portfolio export of the frozen study and metrics": "nothing exported",
    }
    assert discovery("S38").outcome == discovery("S24").outcome == "blocked"
    assert "available: false" in (ROOT / "worker/src/transit.ts").read_text("utf-8")
    for model in MODELS:  # no test labels, so no score of any kind exists
        record = registry(f"{model.lower()}.json")
        assert record["candidate_scores"] is None and record["prediction_rows"] == 0
    assert not [p for p in TRACKED if p.startswith(("data/", "web/public/"))]


def test_restricted_and_unverified_sources_commit_manifests_only():
    flagged = {s for s in DL if discovery(s).licence.status in ("restricted", "unverified")}
    rows = {r[0]: r for r in table(PAGE, "Licence audit")}
    assert set(rows) == flagged == {"S24", "S38"}
    for sid, row in rows.items():
        assert row[1] == discovery(sid).licence.status and row[2] == "manifest only"
        n = sid.lower()
        files = [
            p for p in TRACKED if p.startswith((f"tests/fixtures/{n}/", f"tests/fixtures/{n}_"))
        ]
        assert files == [f"tests/fixtures/{n}/manifest.json"], (sid, files)


def test_other_states_stay_functional_and_the_frozen_interfaces_unchanged():
    rows = table(KA_PAGE, "Frozen shared interfaces")
    assert len(rows) >= 6
    for path, digest in rows:
        data = (ROOT / path.strip("`")).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == digest.strip("`"), path
    on = {s: sum(x.enabled for x in STATES[s].sources) for s in STATES}
    ka_row, kl_row = table(PAGE, "Cross-state regression")[:2]
    assert f"{on['ka']} of {len(KA)} sources enabled" in KA_PAGE and "M05 approved" in ka_row[1]
    assert f"{on['ka']} of {len(KA)} sources enabled" in ka_row[1]
    assert f"{on['kl']} of {len(KL)} Kerala sources enabled" in KL_PAGE
    assert f"{on['kl']} of {len(KL)} Kerala sources enabled" in kl_row[1]
    release = registry("M05/v1.json")
    assert registry("M05/v1.approval.json")["decision"] == "approved"
    assert release["improvement"]["lower95"] > 0
    assert all(registry(f"m{n:02d}.json")["status"] == "blocked" for n in (7, 8, 9, 10))
    for row in table(PAGE, "Cross-state regression"):
        for test in re.findall(r"`(tests/[^`]+)`", row[2]):
            assert (ROOT / test).exists(), test
    assert "[ka-v1.md](ka-v1.md)" in PAGE and "[kl.md](kl.md)" in PAGE
    dl, ka, kl = STATES["dl"], STATES["ka"], STATES["kl"]
    for kind in ("raw_root", "clean_root", "publish_root"):
        paths = {getattr(s.paths, kind) for s in (dl, ka, kl)}
        assert len(paths) == 3 and getattr(dl.paths, kind).parts[-1] == "dl", kind
    assert not {"S28", "S32"} & set(DL)  # Karnataka and Kerala sources are not Delhi's


def test_no_card_audit_passes_for_every_delhi_source():
    for sid in DL:
        d = discovery(sid)
        assert d.no_card is True, sid
        assert DL[sid].cost in ("free", "free_with_key"), sid
        assert re.search(rf"\b{sid}\b", table(PAGE, "No-card audit")[0][0] if False else PAGE), sid
    assert audit.policy() == []
    assert "reports 0 problems" in " ".join(PAGE.split())


def test_owner_gated_items_are_listed_against_their_configs():
    rows = {r[0]: r for r in table(PAGE, "Owner-gated items")}
    assert list(rows) == ["H04", "S24 browser read", "H05, H06", "H11"]
    assert "H04" in discovery("S38").retry_condition
    assert "no new key is needed" in " ".join(discovery("S24").retry_condition.split())
    amendments = (ROOT / "docs/amendments.md").read_text("utf-8")
    assert re.search(r"\| H05 \| Create a free Cloudflare account", amendments)
    assert re.search(r"\| H06 \| Create a Hugging Face account", amendments)
    assert not (DL["S38"].enabled or DL["S24"].enabled or DL["S01"].enabled or DL["S02"].enabled)
    flat = " ".join(PAGE.split())
    assert "M15's retry is not an owner step: enable S01 and S02 for Delhi" in flat
    assert "Nothing here approves a public release" in flat
    decisions = (ROOT / "docs/decisions.md").read_text("utf-8")
    assert "D143" in decisions.split("\n- **D142")[0]
