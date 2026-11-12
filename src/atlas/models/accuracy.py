"""T257 (child of T046): accuracy rows and Karnataka release checklist from evidence (D92).

Unavailable metrics stay null; they are never shown as zero.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "docs/releases/ka.md"
WEB_FIXTURE = ROOT / "web/tests/fixtures/accuracy-ka.json"
DASHBOARD_DATA = ROOT / "web/src/dashboards.json"


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
        (
            "C1 evaluation report and model card",
            "blocked",
            "M07 has no model (data gate, T130: datum for 4 of 8 dams, D103); "
            "owner decides at the end (D104)",
        ),
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
            else "reports/rag.md gate not passed; research-only (D101); owner counts it for the "
            "MVP gate, labelled research-only (H11, D166)",
        ),
        (
            "Case study per core model (H14 review)",
            "pending" if all(_exists(f"reports/models/{n}") for n in studies) else "missing",
            "three case studies written; owner review pending",
        ),
        (
            "Accuracy page shows C1, C2 and M06",
            "pass" if _exists("web/src/pages/Accuracy.tsx") else "missing",
            "T259 page shows the rows; owner approved publishing the table (H11, D166); "
            "deployed with the site (D187)",
        ),
        (
            "Working real-data map, sources and Place Lens",
            "pass",
            "T038-T040 pass; live on monsoon-atlas.pages.dev (D187)",
        ),
        ("Priced data and reproducible price baseline", "blocked", "S23 denominator; M06 blocked"),
        (
            "Free-tier deployment on pages.dev",
            "pass",
            "deployed 12 Nov 2026 to monsoon-atlas.pages.dev on the free plan with no card "
            "(D180, D187); rollback: redeploy the previous release with scripts/deploy_site.py",
        ),
        (
            "Legal, boundary and licence audit",
            "pass",
            "H11 answers (D166) and public-release approval (D187); boundary disclaimer on the "
            "map; licence check at deployment found only open or derived-permitted data (D187)",
        ),
        (
            "Dependencies T045 and T041",
            "pass",
            "T045 releases built daily and archived privately (D185); T041 done (D177)",
        ),
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
        "Fallback: the dated static daily view stays the advertised fallback; every release "
        "stays in the private archive, so rollback is a redeploy of the previous one (D187).",
        "",
    ]
    return "\n".join(lines)


def release_json() -> str:
    """Accuracy release bytes for the web page (T259); approval and serving are H11 steps."""
    payload = {"schema_version": 1, "state": "ka", "rows": accuracy_rows()}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


GATE_PAGES = {
    "ka": "docs/releases/ka-v1.md",
    "kl": "docs/releases/kl.md",
    "dl": "docs/releases/dl.md",
}
# T217 (D161): analysis reports that exist, with the sources each one reads.
ANALYSES = [
    (
        "reports/eda/01_ka_quality/summary.json",
        "Karnataka feed quality (T106)",
        ["S08", "S10", "S01"],
    ),
    (
        "reports/eda/02_ka_rain/summary.json",
        "Karnataka gauge and grid rainfall (T107)",
        ["S29", "S08"],
    ),
    (
        "reports/eda/03_ka_prices/summary.json",
        "Karnataka price sources, no price rows",
        ["S22", "S23"],
    ),
    (
        "reports/eda/05_kl_flood2018/summary.json",
        "Kerala 2018 flood replay (T142)",
        ["S08", "S32", "S36"],
    ),
    (
        "reports/eda/06_rain_price/summary.json",
        "Rain and price event study, blocked",
        ["S22", "S23"],
    ),
    ("reports/eda/07_climate/summary.json", "Climate trends and projections", ["S08", "S06"]),
    ("reports/eda/08_delhi_transit/summary.json", "Delhi transit audit, blocked", ["S38"]),
    ("reports/eda/09_delhi_air/summary.json", "Delhi air audit, blocked", ["S24", "S04"]),
    ("reports/eda/10_spatial_statistics/summary.json", "Spatial statistics (T109)", ["S08", "S17"]),
    ("reports/sql_insights.md", "SQL insights (T224)", ["S29", "S08", "S32", "S44"]),
]


def _registry() -> list[dict]:
    """One card per model. Scores come only from a registry release (M05); never from text."""
    release = _json("models/registry/M05/v1.json")
    evaluation = _json("models/registry/M05/v1.evaluation.json")
    row = next(r for r in accuracy_rows() if r["model"] == "M05")
    cards = []
    for n in range(1, 21):
        mid = f"M{n:02d}"
        if mid == "M05":
            cards.append(
                {
                    "id": mid,
                    "state": "ka",
                    "status": row["status"],
                    "reason": "Ridge v1 beats persistence on the locked 2020 to 2024 test; "
                    "hindcast. v2 (refit with IMD 2025) is untested and not served (D170).",
                    "links": ["reports/models/m05.md", "reports/models/m05-card.md"],
                    "score": {
                        "label": "hindcast",
                        "metric": "MAE",
                        "model": release["candidate"],
                        "baseline": release["baseline"],
                        "test": release["cutoffs"]["test"],
                        "model_value": row["candidate"],
                        "baseline_value": row["baseline_value"],
                        "improvement": row["improvement"],
                        "ci95": row["ci95"],
                        "rows": evaluation["rows"],
                        "months": evaluation["months"],
                    },
                }
            )
            continue
        reg = _json(f"models/registry/{mid.lower()}.json")
        cards.append(
            {
                "id": mid,
                "state": reg["state"],
                "status": reg["status"],
                "reason": reg["reason"],
                "links": [reg["report"]],
                "score": None,
            }
        )
    return cards


def _sources() -> list[dict]:
    from atlas.config import load_state

    out = []
    for state in ("ka", "kl", "dl"):
        for s in load_state(ROOT / f"configs/states/{state}.yaml").sources:
            record = f"configs/sources/{s.source_id.lower()}.yaml"
            d = yaml.safe_load((ROOT / record).read_text("utf-8"))
            out.append(
                {
                    "state": state,
                    "id": s.source_id,
                    "name": s.name,
                    "enabled": s.enabled,
                    "outcome": d["outcome"],
                    "licence": d["licence"]["status"],
                    # Account-gated retry text names secret variables and upstream endpoints;
                    # the client gets a flag and the record link instead (tests/test_dl_poll.py).
                    "retry": None if d.get("account_required") else d.get("retry_condition"),
                    "owner_step": bool(d.get("account_required")) and d["outcome"] == "blocked",
                    "link": record,
                }
            )
    return out


def dashboard_data() -> dict:
    """T217 (D161): everything the four dashboards show, from files that already exist."""
    cards, sources = _registry(), _sources()
    flags = _json("reports/models/m16-flag-counts.json")["totals"]
    monitor = _json("models/registry/M05/v1.monitor-2025.json")
    states = {}
    for state in ("ka", "kl", "dl"):
        mine = [s for s in sources if s["state"] == state]
        models = [c["status"] for c in cards if c["state"] == state]
        states[state] = {
            "sources": len(mine),
            "enabled": sum(s["enabled"] for s in mine),
            "blocked": sum(s["outcome"] == "blocked" for s in mine),
            "models": len(models),
            "models_blocked": models.count("blocked"),
            "link": f"configs/states/{state}.yaml",
            "page": GATE_PAGES[state],
        }
    licence = {s["id"]: s["licence"] for s in sources}
    analyses = [
        {
            "link": path,
            "title": title,
            "sources": ids,
            "restricted": [i for i in ids if licence.get(i) == "restricted"],
        }
        for path, title, ids in ANALYSES
    ]
    return {
        "schema_version": 1,
        "models": cards,
        "sources": sources,
        "anomaly_queue": {
            "model": "M16",
            "label": "unadjudicated rule output, not incidents",
            "adjudicated": 0,
            "required": 100,
            "states": {
                k: {"evaluated": v["evaluated"], "flags": v["flags_z"]} for k, v in flags.items()
            },
            "links": ["reports/models/m16.md", "reports/models/m16-flag-counts.json"],
        },
        "drift": {
            "model": "M05",
            "period": monitor["period"],
            "rows": monitor["rows"],
            "flag": monitor["flag"],
            "mae_ratio": monitor["mae_ratio"],
            "ci95": [monitor["improvement"]["lower95"], monitor["improvement"]["upper95"]],
            "label": "hindcast, provisional",
            "link": "reports/models/m05-2025.md",
        },
        "analyses": analyses,
        "states": states,
        "series": [
            {
                "state": "ka",
                "name": "M05 MAE",
                "level": "district",
                "unit": "SPI-3",
                "span": _json("models/registry/M05/v1.json")["cutoffs"]["test"].split("/"),
                "normalisation": "climate_reference",  # SPI is standardised on 1981-2010
                "coverage": 1.0,
                "link": "reports/models/m05.md",
            }
        ],
    }


def dashboard_json() -> str:
    return json.dumps(dashboard_data(), indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(), "utf-8", newline="\n")
    # The browser fixture mirrors the committed records; it is test data, not a publication.
    WEB_FIXTURE.write_text(release_json(), "utf-8", newline="\n")
    DASHBOARD_DATA.write_text(dashboard_json(), "utf-8", newline="\n")
    written = (OUTPUT, WEB_FIXTURE, DASHBOARD_DATA)
    print(json.dumps({"written": [str(p.relative_to(ROOT)) for p in written]}))


if __name__ == "__main__":
    main()
