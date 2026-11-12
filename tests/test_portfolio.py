"""T220 (D164): the portfolio pack stays traceable to committed records.

Five documents are checked: README.md, the case-study template, the demo script, the resume lines
and the glossary. Counts and M05 numbers are recomputed from the registry, the source records and
the reports; a claim that no file supports, or a blocked or unmeasured thing written as an
achievement, fails here.
"""

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC_PATHS = [
    "README.md",
    "docs/case-studies/template.md",
    "docs/portfolio/video.md",
    "docs/portfolio/resume.md",
    "docs/glossary.md",
]
DOCS = {path: (ROOT / path).read_text("utf-8") for path in DOC_PATHS}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
DATE = re.compile(r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}\b")


def read(path: str) -> str:
    return (ROOT / path).read_text("utf-8")


def section(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def numbers(text: str) -> set[str]:
    return {n.rstrip(".,") for n in NUMBER.findall(DATE.sub("", text))}


def blocks(text: str) -> list[str]:
    """Paragraphs, table rows and top-level bullets (with their sub-bullets)."""
    return [b for b in re.split(r"\n\s*\n|\n(?=- )|\n(?=\|)|\n(?=#)", text) if b.strip()]


def table_rows(text: str) -> list[list[str]]:
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in text.splitlines()]
    return [r for r in rows if len(r) > 1 and not set("".join(r)) <= set("-: ")]


# ---- facts, recomputed from the repository ----------------------------------------------------

DASH = json.loads(read("web/src/dashboards.json"))
MODELS = {m["id"]: m for m in DASH["models"]}
SOURCES = {
    d["source_id"]: d
    for d in (
        yaml.safe_load(p.read_text("utf-8"))
        for p in sorted((ROOT / "configs/sources").glob("s*.yaml"))
    )
}
M05 = json.loads(read("models/registry/M05/v1.json"))
M05_2025 = json.loads(read("models/registry/M05/v1.monitor-2025.json"))
M05_INTERVALS = json.loads(read("models/registry/M05/v1.intervals.json"))
M16_COUNTS = json.loads(read("reports/models/m16-flag-counts.json"))["totals"]["ka"]
STATE_CONFIGS = sorted((ROOT / "configs/states").glob("*.yaml"))
RAG_DOCS = yaml.safe_load(read("configs/rag.yaml"))["documents"]


def registry_status(model_id: str) -> str:
    """Status from the registry itself, not from the dashboard file."""
    if model_id == "M05":
        approval = json.loads(read("models/registry/M05/v1.approval.json"))
        assert approval["decision"] == "approved" and M05["status"] == "candidate_eligible"
        return "champion, hindcast (D43)"
    return json.loads(read(f"models/registry/{model_id.lower()}.json"))["status"]


def counts() -> dict:
    status = [registry_status(i) for i in MODELS]
    outcome = [d["outcome"] for d in SOURCES.values()]
    return {
        "measured": sum(s.startswith("champion") for s in status),
        "research_only": status.count("research_only"),
        "blocked": status.count("blocked"),
        "models": len(status),
        "sources": len(SOURCES),
        "available": outcome.count("available"),
        "source_blocked": outcome.count("blocked"),
        "states": len(STATE_CONFIGS),
    }


COUNTS = counts()
BASE, CAND = M05["baseline_scores"]["mae"], M05["candidate_scores"]["mae"]
IMP = M05["improvement"]
M05_TEXT = f"MAE {CAND:.3f} against {BASE:.3f}"
M05_CI = f"{IMP['mean']:.3f}, 95% CI {IMP['lower95']:.3f} to {IMP['upper95']:.3f}"
M05_2025_TEXT = f"MAE {M05_2025['mae']['ridge']:.3f} against {M05_2025['mae']['persistence']:.3f}"
V1_COVERAGE = re.search(r"80% interval coverage[^|]*\|\s*([\d.]+)", read("reports/models/m05.md"))
RECAL_COVERAGE = M05_INTERVALS["test"]["coverage"]


def known_numbers() -> set[str]:
    """Every number a pack sentence may use: computed facts plus numbers in the cited reports."""
    computed = {str(v) for v in COUNTS.values()} | {str(COUNTS["models"] - COUNTS["measured"])}
    computed |= {f"{RECAL_COVERAGE * 100:.1f}", str(round(float(V1_COVERAGE[1]) * 100))}
    computed |= {f"{M05_2025['mae']['ridge']:.3f}", f"{M05_2025['mae']['persistence']:.3f}"}
    computed |= {f"{CAND:.3f}", f"{BASE:.3f}", f"{IMP['mean']:.3f}", f"{IMP['lower95']:.3f}"}
    computed |= {f"{IMP['upper95']:.3f}", "95", str(len(RAG_DOCS))}
    cited = "reports/models/m05.md reports/models/m05-2025.md reports/models/m05-intervals.md"
    cited += " reports/models/m16.md reports/rag.md"
    text = " ".join(read(p) for p in cited.split())
    text += read("docs/decisions.md").split("- **D147")[1].split("\n- **D146")[0]
    return computed | numbers(text)


KNOWN = known_numbers()


# ---- (a) links --------------------------------------------------------------------------------

TRACKED = set(
    subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
)


def slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")


def link_problems(path: str, text: str) -> list[str]:
    problems = []
    anchors = {slug(h) for h in re.findall(r"(?m)^#+ (.+)$", text)}
    for target in LINK.findall(text):
        if target.startswith(("http://", "https://")):
            parsed = urlparse(target)  # external links are not fetched, only checked for syntax
            if not parsed.netloc or " " in target:
                problems.append(f"{path}: malformed external link {target}")
        elif target.startswith("#"):
            if target[1:] not in anchors:
                problems.append(f"{path}: no heading for {target}")
        else:
            file = (ROOT / path).parent.joinpath(target.split("#")[0]).resolve()
            rel = file.relative_to(ROOT).as_posix()
            if rel not in TRACKED and not any(t.startswith(rel.rstrip("/") + "/") for t in TRACKED):
                problems.append(f"{path}: {target} is not a tracked file or folder")
    return problems


@pytest.mark.parametrize("path", DOC_PATHS)
def test_every_relative_link_resolves_to_a_tracked_file(path):
    assert link_problems(path, DOCS[path]) == []


def test_link_checker_catches_bad_links():
    bad = "# Title\n[a](docs/no-such-file.md) [b](https://) [c](#missing) [d](#title)"
    assert len(link_problems("README.md", bad)) == 3


# ---- (b) model index --------------------------------------------------------------------------


def test_every_model_is_indexed_with_the_registry_status_and_reason():
    rows = {r[0]: r for r in table_rows(DOCS["README.md"]) if re.fullmatch(r"M\d\d", r[0])}
    assert sorted(rows) == [f"M{i:02d}" for i in range(1, 21)] == sorted(MODELS)
    for model_id, row in rows.items():
        model = MODELS[model_id]
        assert row[3] == model["status"] == registry_status(model_id), model_id
        assert row[4] == model["reason"], model_id
        assert all(f"({link})" in row[5] for link in model["links"]), model_id


def test_status_table_counts_match_the_registry():
    status = section(DOCS["README.md"], "## Status on", "## The one measured result")
    rows = {r[0].split(" ")[0]: r for r in table_rows(status) if r[-1].isdigit()}
    assert int(rows["Measured"][-1]) == COUNTS["measured"] == 1 and rows["Measured"][1] == "M05"
    assert int(rows["Research-only"][-1]) == COUNTS["research_only"]
    assert int(rows["Blocked"][-1]) == COUNTS["blocked"]
    assert (
        COUNTS["measured"] + COUNTS["research_only"] + COUNTS["blocked"] == COUNTS["models"] == 20
    )
    only_scored = [m["id"] for m in DASH["models"] if m["score"] is not None]
    assert only_scored == ["M05"]  # the dashboard data also shows one score
    c = COUNTS
    assert f"{c['sources']} ({c['available']} available, {c['source_blocked']} blocked)" in status


def test_licence_table_matches_every_source_record():
    rows = {r[0]: r for r in table_rows(DOCS["README.md"]) if re.fullmatch(r"S\d\d", r[0])}
    assert sorted(rows) == sorted(SOURCES)
    for source_id, row in rows.items():
        record = SOURCES[source_id]
        assert row[3:5] == [record["licence"]["status"], record["outcome"]], source_id
        assert f"(configs/sources/{source_id.lower()}.yaml)" in row[5]


def test_architecture_diagram_names_real_modules():
    diagram = section(DOCS["README.md"], "```mermaid", "```")
    paths = set(
        re.findall(
            r"\b(?:src/atlas/\w+|configs/\w+|models/registry|reports/models|web|worker)\b", diagram
        )
    )
    assert {"src/atlas/ingest", "src/atlas/data", "src/atlas/features", "src/atlas/rag"} <= paths
    assert {"src/atlas/models", "src/atlas/spatial", "worker", "web"} <= paths
    assert [p for p in paths if not (ROOT / p).exists()] == []


# ---- (c) numeric claims -----------------------------------------------------------------------


def test_readme_m05_claims_are_recomputed_from_the_release():
    text = DOCS["README.md"]
    assert M05_TEXT in text and M05_CI in text and M05_2025_TEXT in text
    assert M05_2025["flag"] == "holds" and 'the flag is "holds"' in text
    assert (
        f"{RECAL_COVERAGE * 100:.1f}%" in text
        and f"({round(float(V1_COVERAGE[1]) * 100)}% in v1" in text
    )
    assert not M05_INTERVALS["publishable"] and M05_INTERVALS["gate"] == [0.75, 0.85]
    assert M05_2025["interval80"]["shown"] is False
    assert IMP["lower95"] > 0 and M05["baseline"] == "persistence"
    assert f"{M05_2025['months']} months" in text  # below the 24-month release minimum


def test_status_and_m05_sections_use_no_unsourced_number():
    text = DOCS["README.md"]
    scanned = section(text, "## Status on", "## Model index")
    assert numbers(scanned) - KNOWN == set()


def test_readme_lessons_match_their_reports():
    text = DOCS["README.md"]
    assert f"{M16_COUNTS['cell_days']:,}" in text and f"{M16_COUNTS['flags_z']:,}" in text
    assert "6,644,980 of 8,875,440" in text and "6,644,980" in read("reports/models/m16.md")
    gate = json.loads(read("models/registry/m16.json"))["label_gate"]
    assert gate["adjudicated_flags"] == 0 and f"0 of {gate['required']} flags" in text
    rag = read("reports/rag.md")
    assert re.search(r"\| all \| 45 \| 1\.00 \| 0\.82 \| 1\.00 \| 0\.77 \|", rag)  # frozen, D187
    assert "Corpus: 31 committed documents, 521 chunks." in rag
    assert "correctness 0.82 and evidence support 0.77 against a 0.95 gate" in text
    assert "down from 0.89 and 0.86 on 8 Nov" in text and "D187" in text


def test_resume_counts_and_metrics_are_recomputed():
    text = " ".join(DOCS["docs/portfolio/resume.md"].split())
    c = COUNTS
    assert f"{c['sources']} public data sources" in text
    assert f"{c['available']} available and {c['source_blocked']} blocked" in text
    assert f"({c['states']} states)" in text
    assert f"{c['measured']} of {c['models']} planned models" in text
    assert f"the other {c['models'] - c['measured']} models as blocked or research-only" in text
    assert M05_TEXT in text and M05_CI in text
    assert f"{len(RAG_DOCS)} project documents" in text
    assert f"{M16_COUNTS['cell_days']:,}" in text and "6,644,980" in text
    resume = section(DOCS["docs/portfolio/resume.md"], "## Usable now", "## Placeholder lines")
    assert numbers(resume) - KNOWN - {"1", "3"} == set()


def test_resume_usable_lines_have_sources_and_no_placeholders():
    resume = DOCS["docs/portfolio/resume.md"]
    usable = section(resume, "## Usable now", "## Placeholder lines")
    items = [b for b in re.split(r"\n(?=- \*\*)", usable) if b.startswith("- **")]
    assert len(items) == 4
    for item in items:
        assert "Source:" in item and LINK.search(item), item[:60]
        assert not re.search(r"\[[A-Za-z][^\]\n]*\](?!\()", item), item[
            :60
        ]  # no bracket placeholder
    placeholders = resume.split("## Placeholder lines")[1]
    lines = [b for b in re.split(r"\n(?=- \*\*)", placeholders) if b.startswith("- **")]
    assert len(lines) == 4
    for line in lines:
        assert re.search(r"\[[A-Za-z][^\]\n]*\]", line) and "Not usable" in line, line[:60]


# ---- (d) forbidden claims ---------------------------------------------------------------------

NEGATED = re.compile(r"\b(not|no|nothing|never|none|without|waits?|until|nor|neither)\b", re.I)
FORBIDDEN = re.compile(
    r"\b(deployed|production|live at|live demo|demo link|screenshot|badge)\b", re.I
)
PASSING = re.compile(r"\b(pass|passes|passed|meets?|met)\b", re.I)
NOT_PASSING = re.compile(r"\b(not|no|nothing|fail|fails|failed|below|hidden|without|until)\b", re.I)
OTHER_MODEL = re.compile(r"\bM(?:0[1-46-9]|1\d|20)\b")
METRIC = re.compile(r"\b\d+\.\d+\b|\d+(?:\.\d+)?%")
LANDING_URLS = {d["landing_url"] for d in SOURCES.values() if d.get("landing_url")}


@pytest.mark.parametrize("path", DOC_PATHS)
def test_no_deployment_demo_or_achievement_claim_without_a_negation(path):
    bad = [b[:80] for b in blocks(DOCS[path]) if FORBIDDEN.search(b) and not NEGATED.search(b)]
    assert bad == []


@pytest.mark.parametrize("path", DOC_PATHS)
def test_only_source_landing_pages_are_linked_externally(path):
    urls = re.findall(r"https?://[^\s)>\"'`]+", DOCS[path])
    assert [u for u in urls if u.rstrip(".,;") not in LANDING_URLS] == []


@pytest.mark.parametrize("path", DOC_PATHS)
def test_no_accuracy_number_for_a_model_other_than_m05(path):
    bad = [b[:80] for b in blocks(DOCS[path]) if OTHER_MODEL.search(b) and METRIC.search(b)]
    assert bad == []


@pytest.mark.parametrize("path", DOC_PATHS)
def test_interval_coverage_is_never_shown_as_passing(path):
    bad = [
        b[:80]
        for b in blocks(DOCS[path])
        if re.search(r"interval|coverage", b, re.I)
        and PASSING.search(b)
        and not NOT_PASSING.search(b)
    ]
    assert bad == []


@pytest.mark.parametrize("path", DOC_PATHS)
def test_kw_live_appears_only_in_the_no_reuse_statement(path):
    lines = [x for x in DOCS[path].splitlines() if re.search(r"kw[ -]?live", x, re.I)]
    assert all("reuses no" in x and "KW Live" in x for x in lines if "](" not in x)


def test_no_blocked_model_is_called_measured_or_released():
    text = DOCS["README.md"]
    for model_id in MODELS:
        if model_id != "M05":
            row = next(r for r in table_rows(text) if r[0] == model_id)
            assert row[3] in {"blocked", "research_only"} and "champion" not in " ".join(row)
    assert "Nothing is deployed" in text and "No demo URL exists" in text


# ---- (e) demo script, template, glossary -----------------------------------------------------


def test_video_page_says_not_recorded_and_marks_every_shot():
    video = DOCS["docs/portfolio/video.md"]
    assert "not recorded: owner step" in video.lower()
    shots = [r for r in table_rows(video) if re.fullmatch(r"\d\d:\d\d-\d\d:\d\d", r[0])]
    assert [r[0] for r in shots][0] == "00:00-00:25" and shots[-1][0].endswith("03:00")
    assert len(shots) == 7
    for row in shots:
        assert row[2] in {"yes", "partly", "no"}, row[0]
        if row[2] == "no":
            assert "not shown" in (row[3] + row[4]).lower(), row[0]
    hidden = " ".join(video.split())
    assert "D42" in hidden and "not mounted (D127" in hidden


def test_case_study_template_keeps_the_outline_and_the_citation_rules():
    template = DOCS["docs/case-studies/template.md"]
    outline = re.findall(r"(?m)^## (.+)$", read("reports/models/m05-case-study.md"))
    fenced = section(template, "```markdown", "\n```")
    mine = re.findall(r"(?m)^## (.+)$", fenced)  # the M05 study may extend a heading's wording
    assert len(mine) == len(outline) == 15
    assert all(full.startswith(short) for short, full in zip(mine, outline, strict=True))
    rules = " ".join(template.split())
    assert "Every number must cite a committed file" in rules
    assert "states the gate that failed" in rules and "no model was fitted" in rules
    assert "H14" in template


def test_glossary_terms_are_used_elsewhere_in_the_repository():
    files = [ROOT / "README.md", *(ROOT / "docs").rglob("*.md"), *(ROOT / "reports").rglob("*.md")]
    files += (ROOT / "src").rglob("*.py")
    corpus = " ".join(f.read_text("utf-8").lower() for f in files if f.name != "glossary.md")
    rows = [r for r in table_rows(DOCS["docs/glossary.md"]) if r[0] != "Term"]
    assert len(rows) >= 30
    unused = []
    for row in rows:
        aliases = [a.strip().lower() for a in re.split(r",|\(|\)", row[0]) if a.strip()]
        if not any(a in corpus for a in aliases):
            unused.append(row[0])
    assert unused == []
