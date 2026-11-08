"""T254 (child of T181): English Ask gold cases, numeric gold and deterministic scoring (D89)."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

from atlas.rag import numeric
from atlas.rag.corpus import ROOT, committed_documents, load_config
from atlas.rag.index import INDEX, build_index
from atlas.rag.retrieve import retrieve

EVAL = ROOT / "eval/rag"
THRESHOLDS = {
    "faithfulness": 0.95,
    "correctness": 0.85,
    "valid_citations": 1.0,
    "evidence_support": 0.95,
    "refusal_accuracy": 0.95,
}
TRANSLATIONS = ("kn", "ml", "hi")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def normal(text: str) -> str:
    return " ".join(text.replace("’", "'").lower().split())


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def numeric_gold(case: dict) -> dict:
    """Recompute an answered numeric gold value from its committed source file."""
    gold = case["gold"]
    if gold["status"] != "answered":
        return gold
    data = json.loads((ROOT / gold["path"]).read_text("utf-8"))
    if gold["source_id"] == "S02":
        limit = date.fromisoformat(case["as_of"])
        rows = zip(data["daily"]["time"], data["daily"]["precipitation_sum"], strict=True)
        known = [(day, value) for day, value in rows if value is not None]
        day, value = [(d, v) for d, v in known if date.fromisoformat(d) <= limit][-1]
        return gold | {
            "value": float(value),
            "date": day,
            "unit": data["daily_units"]["precipitation_sum"],
        }
    if gold["source_id"] == "S09":
        now = _time(case["as_of"])
        active = (
            _time(data["valid_at"]) <= now < _time(data["expires_at"])
            and _time(data["available_at"]) <= now
        )
        return gold | {"value": sorted([data["id"]] if active else [])}
    if gold["source_id"] == "M05":
        improvement = data["improvement"]
        return gold | {"value": {key: improvement[key] for key in ("mean", "lower95", "upper95")}}
    raise ValueError(f"No deterministic gold rule for {case['id']}")


def load_chunks(index: Path) -> dict[str, dict]:
    with closing(sqlite3.connect(f"{Path(index).absolute().as_uri()}?mode=ro", uri=True)) as db:
        rows = db.execute("SELECT chunk_id, doc_id, text FROM chunks").fetchall()
    return {chunk_id: {"doc_id": doc_id, "text": text} for chunk_id, doc_id, text in rows}


def _mean(values: list[bool]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def score(fixed: list[dict], numeric: list[dict], answers: dict, chunks: dict) -> dict:
    """Score candidate answers; an invalid citation or numeric value fails its case."""
    results = []
    for case in [c for c in fixed if c["scope"] == "mvp_en"] + numeric:
        answer = answers.get(case["id"], {"status": "missing", "citations": [], "answer": ""})
        is_numeric = case["id"].startswith("N")
        gold = numeric_gold(case) if is_numeric else None
        allowed = set(chunks) | ({gold.get("path")} if is_numeric else set())
        valid = all(citation in allowed for citation in answer["citations"]) and (
            bool(answer["citations"]) or answer["status"] != "answered"
        )
        text = "\n".join(chunks[c]["text"] for c in answer["citations"] if c in chunks)
        claims = NUMBER.findall(answer.get("answer", ""))
        faithful = valid and all(number in text for number in claims if not is_numeric)
        row = {
            "id": case["id"],
            "split": "numeric" if is_numeric else case["split"],
            "valid": valid,
        }
        if is_numeric:
            if gold["status"] == "answered":
                row["correct"] = valid and (
                    answer["status"] == "answered"
                    and answer.get("value") == gold["value"]
                    and answer.get("unit") == gold["unit"]
                    and gold["path"] in answer["citations"]
                )
            else:
                row["refusal"] = answer["status"] != "answered" and answer.get("value") is None
                row["correct"] = row["refusal"]
            # A numeric claim is faithful only when it matches the gold; no claim is faithful.
            row["faithful"] = valid and (answer["status"] != "answered" or row["correct"])
        else:
            cited = [chunks[c] for c in answer["citations"] if c in chunks]
            row["supported"] = valid and any(
                item["doc_id"] == doc and normal(phrase) in normal(item["text"])
                for item in cited
                for doc, phrase in case["support"]
            )
            # Extractive results are scored by their evidence; generated text needs review.
            row["correct"] = (
                row["supported"]
                if answer.get("mode") == "extractive"
                else bool(answer.get("reviewed_correct")) and row["supported"]
            )
            row["faithful"] = faithful
        results.append(row)

    def metrics(rows: list[dict]) -> dict:
        return {
            "cases": len(rows),
            "faithfulness": _mean([r["faithful"] for r in rows]),
            "correctness": _mean([r["correct"] for r in rows]),
            "valid_citations": _mean([r["valid"] for r in rows]),
            "evidence_support": _mean([r["supported"] for r in rows if "supported" in r]),
            "refusal_accuracy": _mean([r["refusal"] for r in rows if "refusal" in r]),
        }

    overall = metrics(results)
    return {
        "overall": overall,
        "slices": {
            s: metrics([r for r in results if r["split"] == s])
            for s in ("dev", "holdout", "numeric")
        },
        # Thresholds plus zero tolerance: any invalid citation or wrong/unsupported number fails.
        "passed": all(overall[k] is not None and overall[k] >= v for k, v in THRESHOLDS.items())
        and all(r["faithful"] for r in results),
        "failures": [
            r["id"] for r in results if not (r["valid"] and r["correct"] and r["faithful"])
        ],
    }


def run_current(cases: list[dict], *, index: Path, as_of: datetime) -> dict:
    """Answer each case with the current extractive Ask path (no language model)."""
    answers = {}
    for case in cases:
        if case.get("scope", "mvp_en") != "mvp_en":
            continue
        computed = numeric.answer(case["question"])
        if computed is not None:
            answers[case["id"]] = computed
            continue
        shown = retrieve(case["question"], as_of=as_of, index=index)
        answers[case["id"]] = {
            "mode": "extractive",
            "status": "quota_fallback" if shown else "insufficient_evidence",
            "answer": "\n".join(row["text"] for row in shown),
            "citations": [row["chunk_id"] for row in shown],
            "value": None,
        }
    return answers


def language_coverage(fixed: list[dict], numeric: list[dict]) -> dict:
    cases = fixed + numeric
    coverage = {"en": {"cases": len(cases), "reviewed": len(cases), "generation_allowed": False}}
    for language in TRANSLATIONS:
        reviewed = sum(
            case.get("translations", {}).get(language, {}).get("reviewed") is True for case in cases
        )
        coverage[language] = {
            "cases": len(cases),
            "reviewed": reviewed,
            "generation_allowed": False,
        }
    return coverage


def report(result: dict, coverage: dict, fixed: list[dict], as_of: datetime) -> str:
    deferred = [c for c in fixed if c["scope"] != "mvp_en"]
    lines = [
        "# Ask evaluation (T254)",
        "",
        f"Generated by `python -m atlas.rag.evaluate` at as-of {as_of:%Y-%m-%d %H:%M} UTC. "
        "System scored: lexical retrieval with cited extractive excerpts; no language model "
        "is connected (Workers AI waits for H05).",
        "",
        "## Gold cases",
        "",
        f"- {len(fixed)} fixed English questions from plan section 12 (Q41-Q50 held out) and "
        "10 numeric snapshot cases: 60 English gold cases.",
        f"- {len(fixed) - len(deferred)} fixed questions resolve to indexed documents; "
        f"{len(deferred)} are deferred because their sources or model cards are not indexed:",
        "  " + ", ".join(f"{c['id']}" for c in deferred) + ".",
        "- Numeric gold values are recomputed from committed files: S02 ERA5 sample (N01), "
        "S09 CAP sample (N02) and the approved M05 release (N07). The other seven numeric cases "
        "require a refusal because the data is blocked or unpublished.",
        "",
        "## Results",
        "",
        "| Slice | Cases | Faithfulness | Correctness | Valid citations | Evidence support "
        "| Refusal accuracy |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, values in [("all", result["overall"]), *result["slices"].items()]:
        cells = [
            values[k]
            for k in (
                "faithfulness",
                "correctness",
                "valid_citations",
                "evidence_support",
                "refusal_accuracy",
            )
        ]
        lines.append(
            f"| {name} | {values['cases']} | "
            + " | ".join("n/a" if v is None else f"{v:.2f}" for v in cells)
            + " |"
        )
    lines += [
        "",
        "| Threshold | " + " | ".join(f"{k} >= {v:.2f}" for k, v in THRESHOLDS.items()) + " |",
        "|---|---|---|---|---|---|",
        "",
        f"**Gate: {'passed' if result['passed'] else 'not passed'}.** Failing cases: "
        + (", ".join(result["failures"]) or "none")
        + ".",
        "",
        "Extractive correctness means the cited chunk contains the gold fact; generated answers "
        "will also need reviewed correctness. Numeric questions with real values fail until a "
        "structured numeric answer path exists. The methods document was written from the plan "
        "with the fixed question list known, so holdout retrieval is not an independent test of "
        "document coverage.",
        "",
        "## Languages",
        "",
        "| Language | Gold cases | Reviewed translations | Generation allowed |",
        "|---|---|---|---|",
    ]
    for language, values in coverage.items():
        cells = (language, values["cases"], values["reviewed"], values["generation_allowed"])
        lines.append("| " + " | ".join(map(str, cells)) + " |")
    lines += [
        "",
        "No translation is reviewed, so Kannada, Malayalam and Hindi generation stays disabled. "
        "The Kannada UI needs at least 10 reviewed Kannada questions first (A7).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "reports/rag.md")
    parser.add_argument("--index", type=Path, default=INDEX)
    args = parser.parse_args()
    config = load_config()
    build_index(
        committed_documents(config),
        args.index,
        limit=config["chunk_tokens"],
        overlap=config["overlap_tokens"],
    )
    fixed, numeric = read_jsonl(EVAL / "questions.jsonl"), read_jsonl(EVAL / "snapshot_gold.jsonl")
    as_of = datetime.now(UTC)
    result = score(
        fixed,
        numeric,
        run_current(fixed + numeric, index=args.index, as_of=as_of),
        load_chunks(args.index),
    )
    args.report.write_text(report(result, language_coverage(fixed, numeric), fixed, as_of), "utf-8")
    print(json.dumps({"passed": result["passed"], **result["overall"]}))


if __name__ == "__main__":
    main()
