"""T257 (child of T046): accuracy rows and Karnataka release checklist from evidence (D92).

Unavailable metrics stay null; they are never shown as zero.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "docs/releases/ka.md"
WEB_FIXTURE = ROOT / "web/tests/fixtures/accuracy-ka.json"


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text("utf-8"))


def accuracy_rows() -> list[dict]:
    """C1 (M07), C2 (M05) and secondary M06, as A3 requires on the accuracy page."""
    release = _json("models/registry/M05/v1.json")
    approved = _json("models/registry/M05/v1.approval.json")["decision"] == "approved"
    m06 = _json("models/registry/m06.json")
    return [
        {
            "model": "M07",
            "core": "C1",
            "target": "Kerala dam level seven days ahead",
            "baseline": None,
            "test": None,
            "metric": None,
            "candidate": None,
            "baseline_value": None,
            "improvement": None,
            "ci95": None,
            "status": "blocked at data gate (T130); no model",
            "report": "reports/models/m07-case-study.md",
        },
        {
            "model": "M05",
            "core": "C2",
            "target": "District SPI-3 of the issue month; drought is SPI-3 < -1",
            "baseline": release["baseline"],
            "test": release["cutoffs"]["test"],
            "metric": "MAE",
            "candidate": release["candidate_scores"]["mae"],
            "baseline_value": release["baseline_scores"]["mae"],
            "improvement": release["improvement"]["mean"],
            "ci95": [release["improvement"]["lower95"], release["improvement"]["upper95"]],
            "status": "champion, hindcast (D43)" if approved else release["status"],
            "report": "reports/models/m05.md",
        },
        {
            "model": "M06",
            "core": "secondary",
            "target": "Kolar tomato price spike",
            "baseline": None,
            "test": None,
            "metric": None,
            "candidate": m06["candidate_scores"],
            "baseline_value": m06["baseline_scores"],
            "improvement": m06["improvement"],
            "ci95": None,
            "status": m06["status"],
            "report": m06["report"],
        },
    ]


def _exists(path: str) -> bool:
    return (ROOT / path).is_file()


def release_checks() -> list[dict]:
    """Each T046/A3 check with its current evidence; only 'pass' counts toward release."""
    rag = (ROOT / "reports/rag.md").read_text("utf-8")
    ask_passed = re.search(r"\*\*Gate: passed\.\*\*", rag) is not None
    studies = ["m05-case-study.md", "m07-case-study.md", "ask-case-study.md"]
    checks = [
        ("C1 evaluation report and model card", "blocked", "M07 has no model (data gate, T130)"),
        (
            "C2 evaluation report and model card",
            "pass"
            if _exists("reports/models/m05.md") and _exists("reports/models/m05-card.md")
            else "missing",
            "reports/models/m05.md present; separate model card "
            + ("present" if _exists("reports/models/m05-card.md") else "not written"),
        ),
        (
            "C3 passes T181 English thresholds",
            # D101: a failing C3 is research-only (A3), never shown as pass; H11 decides.
            "pass" if ask_passed else "research-only",
            "reports/rag.md gate passed"
            if ask_passed
            else "reports/rag.md gate not passed; research-only (D101), owner decides at H11",
        ),
        (
            "Case study per core model (H14 review)",
            "pending" if all(_exists(f"reports/models/{n}") for n in studies) else "missing",
            "three case studies written; owner review pending",
        ),
        (
            "Accuracy page shows C1, C2 and M06",
            "local" if _exists("web/src/pages/Accuracy.tsx") else "missing",
            "T259 page shows the rows locally; no approved release published (H11)",
        ),
        ("Working real-data map, sources and Place Lens", "local", "T038-T040 pass locally"),
        ("Priced data and reproducible price baseline", "blocked", "S23 denominator; M06 blocked"),
        ("Free-tier deployment on pages.dev", "blocked", "H05 token and capability probe"),
        ("Legal, boundary and licence audit", "pending", "H11 review before public layers"),
        ("Dependencies T045 and T041", "blocked", "T045 needs H05/H06; T041 needs S18"),
    ]
    return [{"check": c, "status": s, "evidence": e} for c, s, e in checks]


def _cell(value) -> str:
    if value is None or value == []:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, list):
        return " to ".join(_cell(v) for v in value)
    return str(value)


def render() -> str:
    rows, checks = accuracy_rows(), release_checks()
    releasable = all(check["status"] == "pass" for check in checks)
    lines = [
        "# Karnataka MVP release checklist (T046 preparation)",
        "",
        "Generated by `python -m atlas.models.accuracy` from committed evidence. "
        "Unavailable values are not zero.",
        "",
        f"**Release status: {'ready for H11 review' if releasable else 'not releasable'}.**",
        "",
        "## Accuracy table",
        "",
        "| Model | Core | Target | Baseline | Test | Metric | Model value | Baseline value "
        "| Improvement | 95% CI | Status |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    keys = ("model", "core", "target", "baseline", "test", "metric", "candidate")
    keys += ("baseline_value", "improvement", "ci95", "status")
    for row in rows:
        lines.append("| " + " | ".join(_cell(row[k]) for k in keys) + " |")
    lines += ["", "## Gate checks", "", "| Check | Status | Evidence |", "|---|---|---|"]
    for check in checks:
        lines.append(f"| {check['check']} | {check['status']} | {check['evidence']} |")
    lines += [
        "",
        "Fallback: the dated static daily view stays the advertised fallback; nothing is "
        "deployed, so no rollback is needed yet.",
        "",
    ]
    return "\n".join(lines)


def release_json() -> str:
    """Accuracy release bytes for the web page (T259); approval and serving are H11 steps."""
    payload = {"schema_version": 1, "state": "ka", "rows": accuracy_rows()}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(), "utf-8", newline="\n")
    # The browser fixture mirrors the committed records; it is test data, not a publication.
    WEB_FIXTURE.write_text(release_json(), "utf-8", newline="\n")
    print(json.dumps({"written": [str(p.relative_to(ROOT)) for p in (OUTPUT, WEB_FIXTURE)]}))


if __name__ == "__main__":
    main()
