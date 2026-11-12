"""T221: the final acceptance page stays equal to the evidence it cites.

`docs/releases/final-features.json` is the source of truth for the feature audit; the page
`docs/releases/final.md` must render every row exactly as `feature_row` does. The release manifest
`docs/releases/final-manifest.json` pins SHA-256 hashes of the evidence files; regenerate it with
`.\\.venv\\Scripts\\python tests/test_final.py --manifest`, never by hand.
"""

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

from atlas.config import load_state

ROOT = Path(__file__).resolve().parents[1]
PAGE_PATH = "docs/releases/final.md"
RUNBOOK_PATH = "docs/runbooks/maintain.md"
FEATURES_PATH = "docs/releases/final-features.json"
MANIFEST_PATH = "docs/releases/final-manifest.json"
STATUSES = ["shipped-local", "built-not-mounted", "research-only", "blocked", "deferred"]
TIERS = ["MVP", "v1", "stretch"]
GATE_PAGES = ["ka", "ka-v1", "kl", "dl", "h11-ka"]
NOT_PERFORMED = "not performed: owner step"
CLAIM = re.compile(r"\b(delivered|shipped|complete|completed)\b", re.IGNORECASE)
H_STEP = re.compile(r"\bH\d\d\b")


def read(path: str) -> str:
    return (ROOT / path).read_text("utf-8")


def section(text: str, heading: str) -> str:
    """Body of a level-2 section, up to the next level-2 heading."""
    body = text.split(f"\n## {heading}\n", 1)[1]
    return body.split("\n## ", 1)[0]


def table_rows(text: str) -> list[list[str]]:
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in text.splitlines()]
    rows = [r for r in rows if len(r) > 1 and not set("".join(r)) <= set("-: ")]
    return rows[1:]  # drop the header row


def tracked() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return set(out.stdout.splitlines())


def sha256(path: str) -> str:
    """SHA-256 with line endings normalised to LF, as in docs/releases/ka-v1.md."""
    return hashlib.sha256((ROOT / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def manifest_files() -> list[str]:
    globs = [
        "models/registry/*.json",
        "models/registry/M05/*.json",
        "configs/sources/*.yaml",
        "configs/states/*.yaml",
        "requirements/*.txt",
    ]
    files = {p.relative_to(ROOT).as_posix() for g in globs for p in ROOT.glob(g)}
    files |= {f"docs/releases/{name}.md" for name in GATE_PAGES}
    files |= {
        "docs/releases/kl-ml.json",
        FEATURES_PATH,
        "web/src/dashboards.json",
        "reports/rag.md",
        "web/package-lock.json",
        "worker/package-lock.json",
    }
    return sorted(files)


def feature_row(f: dict) -> str:
    """The page row for one feature; the page must contain exactly this line."""
    tasks = ", ".join(f["tasks"]) + f" (plan {f['plan_task']})"
    evidence = ", ".join(f"`{p}`" for p in f["evidence"])
    tests = ", ".join(f"`{p}`" for p in f["tests"]) or "none"
    parts = [f["blocker"]] if f["blocker"] else []
    if f["owner_steps"]:
        parts.append(f"Owner: {', '.join(f['owner_steps'])}.")
    blocker = " ".join(parts) or "none"
    cells = [f["id"], f["name"], f["states"], f["tier"], f["status"], tasks, evidence, tests]
    return "| " + " | ".join(cells + [blocker, f["notes"] or "none"]) + " |"


def status_counts(features: list[dict]) -> list[str]:
    count = Counter((f["status"], f["tier"]) for f in features)
    rows = []
    for s in STATUSES:
        by_tier = [count[(s, t)] for t in TIERS]
        rows.append("| " + " | ".join([s, *map(str, by_tier), str(sum(by_tier))]) + " |")
    totals = [sum(count[(s, t)] for s in STATUSES) for t in TIERS]
    rows.append("| " + " | ".join(["total", *map(str, totals), str(sum(totals))]) + " |")
    return rows


def registry_status(model_id: str) -> str:
    if model_id == "M05":
        approval = json.loads(read("models/registry/M05/v1.approval.json"))
        release = json.loads(read("models/registry/M05/v1.json"))
        assert approval["decision"] == "approved" and release["status"] == "candidate_eligible"
        return "approved"
    return json.loads(read(f"models/registry/{model_id.lower()}.json"))["status"]


PAGE = read(PAGE_PATH)
RUNBOOK = read(RUNBOOK_PATH)
FEATURES = json.loads(read(FEATURES_PATH))["features"]
SOURCE_FILES = sorted((ROOT / "configs/sources").glob("s*.yaml"))
SOURCES = {d["source_id"]: d for d in (yaml.safe_load(p.read_text("utf-8")) for p in SOURCE_FILES)}
TRACKED = tracked()


def test_every_plan_feature_appears_once_with_an_allowed_status():
    assert [f["id"] for f in FEATURES] == [f"F{i:03d}" for i in range(1, 65)]
    for f in FEATURES:
        assert f["status"] in STATUSES, f["id"]
        assert f["tier"] in TIERS, f["id"]
        assert re.fullmatch(r"T\d{3}", f["plan_task"]), f["id"]
        assert f["tasks"] and f["evidence"], f["id"]
        page_rows = [line for line in PAGE.splitlines() if line.startswith(f"| {f['id']} |")]
        assert page_rows == [feature_row(f)], f"{f['id']} row differs from the JSON"


def test_every_evidence_and_test_path_exists_and_is_tracked():
    for f in FEATURES:
        for path in f["evidence"] + f["tests"]:
            assert path in TRACKED, f"{f['id']}: {path} is not a tracked file"


def test_rows_that_are_not_shipped_never_claim_delivery():
    for f in FEATURES:
        if f["status"] != "shipped-local":
            text = f"{f['blocker']} {f['notes']}"
            assert not CLAIM.search(text), f"{f['id']} uses a delivery word: {text}"
            assert f["blocker"], f"{f['id']} needs a blocker or reason"


def test_shipped_rows_cite_an_existing_test():
    test_file = re.compile(r"(^tests/.*test_[\w]+\.py$)|(\.test\.ts$)|(^web/tests/.*\.spec\.ts$)")
    for f in FEATURES:
        if f["status"] == "shipped-local":
            assert any(test_file.search(p) and p in TRACKED for p in f["tests"]), f["id"]


def test_page_status_counts_equal_the_json():
    body = section(PAGE, "Feature audit")
    for row in status_counts(FEATURES):
        assert row in body.splitlines(), f"missing or wrong count row {row}"


def test_page_model_statuses_equal_the_registry():
    rows = {r[0]: r[2] for r in table_rows(section(PAGE, "Models")) if re.fullmatch(r"M\d\d", r[0])}
    assert sorted(rows) == [f"M{i:02d}" for i in range(1, 21)]
    for model_id, status in rows.items():
        assert status == registry_status(model_id), model_id


def test_manifest_hashes_match_the_files():
    manifest = json.loads(read(MANIFEST_PATH))
    assert sorted(manifest["files"]) == manifest_files(), "manifest file list is stale; regenerate"
    for path, digest in manifest["files"].items():
        assert path in TRACKED or path == FEATURES_PATH, path
        assert sha256(path) == digest, f"{path} changed; regenerate the manifest"


def test_every_source_record_is_no_card():
    no_card = [s for s, d in SOURCES.items() if d.get("no_card") is True]
    assert len(SOURCES) == 44
    assert f"{len(no_card)} of {len(SOURCES)} source records have `no_card: true`" in PAGE
    exceptions = sorted(set(SOURCES) - set(no_card))
    assert not exceptions, f"list these in the page as exceptions: {exceptions}"


def test_no_manual_check_is_marked_passed():
    body = section(PAGE, "Manual checks (plan section 14)")
    rows = table_rows(body)
    assert len(rows) >= 4
    for row in rows:
        assert row[-1] == NOT_PERFORMED, row
    assert not re.search(r"\bpass(ed|es)?\b", body, re.IGNORECASE)


def test_state_configs_load_and_enable_only_available_licensed_sources():
    restricted = set()
    for path in sorted((ROOT / "configs/states").glob("*.yaml")):
        state = load_state(path)
        for src in state.sources:
            if src.enabled:
                record = SOURCES[src.source_id]
                assert record["outcome"] == "available", (path.name, src.source_id)
                assert record["licence"]["status"] != "unverified", (path.name, src.source_id)
                if record["licence"]["status"] == "restricted":
                    restricted.add(src.source_id)
    listed = re.search(r"Enabled restricted sources: ([S\d, ]+)\.", PAGE)
    assert listed and set(listed[1].replace(" ", "").split(",")) == restricted


def test_pages_make_no_deployment_claim_and_link_no_live_site():
    negation = re.compile(r"\b(no|not|never|nothing|none|until|before|without|unless)\b", re.I)
    claim = re.compile(r"\b(deployed|deployment|hosted|live site|released|publicly)\b", re.I)
    for name, text in [(PAGE_PATH, PAGE), (RUNBOOK_PATH, RUNBOOK)]:
        for url in re.findall(r"https?://[^\s)>`]+", text):
            assert re.match(r"https?://(127\.0\.0\.1|localhost)[:/]", url), f"{name}: {url}"
        for line in text.splitlines():
            if claim.search(line):
                assert negation.search(line), f"{name}: unnegated claim: {line}"


def test_owner_tasks_name_every_open_h_step():
    handoff = read("docs/HANDOFF.md")
    handoff = handoff.split("\n## 8. Current state", 1)[1].split("\n## 10. ", 1)[0]
    open_in_pages = set(H_STEP.findall(handoff))
    for name in GATE_PAGES:
        open_in_pages |= set(H_STEP.findall(read(f"docs/releases/{name}.md")))
    amendments = set(re.findall(r"^\| (H\d\d) \|", read("docs/amendments.md"), re.M))
    assert len(amendments) == 14
    owner = section(PAGE, "Owner tasks")
    open_ids = {r[0] for r in table_rows(owner.split("### Done", 1)[0]) if H_STEP.fullmatch(r[0])}
    done_ids = {r[0] for r in table_rows(owner.split("### Done", 1)[1]) if H_STEP.fullmatch(r[0])}
    assert not open_ids & done_ids
    assert open_in_pages <= open_ids, f"missing open steps: {open_in_pages - open_ids}"
    assert amendments <= open_ids | done_ids, f"unaccounted: {amendments - open_ids - done_ids}"


def test_twenty_plan_sections_are_mapped_to_tracked_files():
    rows = table_rows(section(PAGE, "Plan sections audit"))
    assert [r[0] for r in rows] == [str(i) for i in range(1, 21)]
    for row in rows:
        paths = re.findall(r"`([^`]+)`", row[2])
        assert paths, row
        for path in paths:
            folder = path.rstrip("/") + "/"
            assert path in TRACKED or any(t.startswith(folder) for t in TRACKED), path


def test_runbook_cites_only_existing_files():
    cited = r"`((?:scripts|docs|tests|src|configs|\.github|reports|web|models)/[^`\s]+)`"
    for path in re.findall(cited, RUNBOOK):
        path = path.rstrip("/")
        if "sNN" in path:  # a per-source placeholder, not a file
            continue
        assert path in TRACKED or any(t.startswith(path + "/") for t in TRACKED), path


if __name__ == "__main__":
    if sys.argv[1:] != ["--manifest"]:
        sys.exit("usage: python tests/test_final.py --manifest")
    data = {
        "note": "Generated by tests/test_final.py --manifest. Never edit by hand.",
        "hash": "SHA-256 of the file bytes with CRLF normalised to LF",
        "files": {path: sha256(path) for path in manifest_files()},
    }
    (ROOT / MANIFEST_PATH).write_text(json.dumps(data, indent=2) + "\n", "utf-8", newline="\n")
    print(f"wrote {MANIFEST_PATH} ({len(data['files'])} files)")
