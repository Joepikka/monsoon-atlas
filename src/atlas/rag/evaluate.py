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
from atlas.rag.retrieve import LOG_RULES, METHODS, retrieve

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
METHOD_NAMES = {
    "R0": "lexical BM25 retrieval",
    "R1": "BM25 top 50 reordered by e5 (D99 R1)",
    "R2": "BM25 and e5 rank fusion within the BM25 top 50 (D99 R2)",
    "R3": "BM25 and e5 rank fusion over both top-50 lists (D99 R3)",
}


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


def run_current(cases: list[dict], *, index: Path, as_of: datetime, rerank=None, **options) -> dict:
    """Answer each case with the current extractive Ask path (no language model).

    `rerank` is (embedder, passage vectors) for methods R1-R3 (D99); `options` go to
    `retrieve` (method, logs, log_rule).
    """
    answers = {}
    for case in cases:
        if case.get("scope", "mvp_en") != "mvp_en":
            continue
        computed = numeric.answer(case["question"])
        if computed is not None:
            answers[case["id"]] = computed
            continue
        embedder, vectors = rerank or (None, None)
        shown = retrieve(
            case["question"],
            as_of=as_of,
            index=index,
            embedder=embedder,
            vectors=vectors,
            **options,
        )
        answers[case["id"]] = {
            "mode": "extractive",
            "status": "quota_fallback" if shown else "insufficient_evidence",
            "answer": "\n".join(row["text"] for row in shown),
            "citations": [row["chunk_id"] for row in shown],
            "value": None,
        }
    return answers


def language_coverage(
    fixed: list[dict], numeric: list[dict], drafts: list[dict] | tuple = ()
) -> dict:
    """English is measured; drafts (T256) are review material and are never scored."""
    cases = fixed + numeric
    coverage = {
        "en": {
            "cases": len(cases),
            "drafted": None,
            "reviewed": len(cases),
            "status": "measured",
            "generation_allowed": False,
        }
    }
    for language in TRANSLATIONS:
        rows = [row for row in drafts if row["language"] == language]
        reviewed = sum(row["language_review"] == "reviewed" for row in rows)
        coverage[language] = {
            "cases": len(fixed),
            "drafted": len(rows),
            "reviewed": reviewed,
            "status": "not validated",
            "generation_allowed": False,
        }
    return coverage


def report(
    result: dict,
    coverage: dict,
    fixed: list[dict],
    as_of: datetime,
    corpus: tuple[int, int],
    method: str = "R0",
    log_rule: str = "L0",
) -> str:
    deferred = [c for c in fixed if c["scope"] != "mvp_en"]
    lines = [
        "# Ask evaluation (T254)",
        "",
        f"Generated by `python -m atlas.rag.evaluate` at as-of {as_of:%Y-%m-%d %H:%M} UTC. "
        f"System scored: {METHOD_NAMES[method]}, {LOG_NAMES[log_rule]}, with cited extractive "
        "excerpts; no language model is connected (Workers AI waits for H05).",
        "",
        f"Corpus: {corpus[0]} committed documents, {corpus[1]} chunks.",
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
        "| Language | Questions | Drafted translations | Reviewed | Status | Generation allowed |",
        "|---|---|---|---|---|---|",
    ]
    for language, values in coverage.items():
        cells = [language] + [
            "n/a" if values[key] is None else values[key]
            for key in ("cases", "drafted", "reviewed", "status", "generation_allowed")
        ]
        lines.append("| " + " | ".join(map(str, cells)) + " |")
    lines += [
        "",
        "English rows are the measured scores above. The Kannada, Malayalam and Hindi rows are "
        "machine drafts of the 50 fixed questions (`eval/rag/translations.jsonl`, status "
        "`machine_draft_unreviewed`), written without a native-speaker review; they are not "
        "scored, so those languages are not validated and their generation stays disabled "
        "(T181 step 3). The 10 numeric cases are not translated. The Kannada UI needs at least "
        "10 reviewed Kannada questions first (A7).",
        "",
    ]
    return "\n".join(lines)


def select_rule(index: Path, as_of: datetime, variants: dict, rerank=None) -> list[dict]:
    """Rank `variants` (name -> retrieve options) on dev cases and retrieval dev only.

    Order: dev evidence support, then dev recall, then the earlier (simpler) variant.
    """
    dev = [c for c in read_jsonl(EVAL / "questions.jsonl") if c["split"] == "dev"]
    questions = read_jsonl(EVAL / "retrieval_dev.jsonl")
    chunks = load_chunks(index)
    embedder, vectors = rerank or (None, None)
    table = []
    for name, options in variants.items():
        answers = run_current(dev, index=index, as_of=as_of, rerank=rerank, **options)
        support = score(dev, [], answers, chunks)["overall"]["evidence_support"]
        hits = []
        for item in questions:
            found = retrieve(
                item["question"],
                as_of=as_of,
                state=item.get("state", "ka"),
                index=index,
                embedder=embedder,
                vectors=vectors,
                **options,
            )
            hits.append(bool({row["doc_id"] for row in found} & set(item["gold"])))
        table.append(
            {"method": name, "dev_evidence_support": support, "dev_recall": sum(hits) / len(hits)}
        )
    order = list(variants)
    return sorted(
        table,
        key=lambda r: (-r["dev_evidence_support"], -r["dev_recall"], order.index(r["method"])),
    )


def select_method(index: Path, as_of: datetime, rerank) -> list[dict]:
    """D99: rank R0-R3 on dev cases and the retrieval dev set only; best first."""
    return select_rule(index, as_of, {m: {"method": m} for m in METHODS}, rerank)


def selection_report(table: list[dict], as_of: datetime) -> str:
    rows = [
        f"| {r['method']} | {METHOD_NAMES[r['method']]} | {r['dev_evidence_support']:.3f} "
        f"| {r['dev_recall']:.3f} |"
        for r in table
    ]
    return "\n".join(
        [
            "# Ask retrieval method selection (T264)",
            "",
            f"Generated by `python -m atlas.rag.evaluate --select` at as-of {as_of:%Y-%m-%d %H:%M}"
            " UTC. The rule was fixed in D99 before any embedding run: dev evidence support on the"
            " 27 dev cases, then recall on the 20 retrieval dev questions, then the simpler method."
            " Holdout cases (Q41-Q50) are not run here.",
            "",
            "| Method | Description | Dev evidence support | Dev recall |",
            "|---|---|---|---|",
            *rows,
            "",
            f"**Chosen: {table[0]['method']}.** It is set as `rerank_method` in `configs/rag.yaml`"
            " and `reports/rag.md` is then generated once with it.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "reports/rag.md")
    parser.add_argument("--index", type=Path, default=INDEX)
    parser.add_argument("--select", action="store_true", help="choose the D99 method on dev only")
    parser.add_argument("--select-logs", action="store_true", help="choose the D100 log rule")
    args = parser.parse_args()
    config = load_config()
    built = build_index(
        committed_documents(config),
        args.index,
        limit=config["chunk_tokens"],
        overlap=config["overlap_tokens"],
    )
    method = config.get("rerank_method", "R0")
    rerank = None
    if args.select or method != "R0":
        from atlas.rag.embed import Embedder, passage_vectors

        embedder = Embedder()
        rerank = (embedder, passage_vectors(args.index, embedder))
    as_of = datetime.now(UTC)
    logs = tuple(config.get("log_documents", ()))
    options = {"method": method, "logs": logs, "log_rule": config.get("log_rule", "L0")}
    if args.select_logs:
        variants = {rule: {"method": method, "logs": logs, "log_rule": rule} for rule in LOG_RULES}
        table = select_rule(args.index, as_of, variants, rerank)
        path = ROOT / "reports/rag-logs.md"
        path.write_text(logs_report(table, as_of, logs), "utf-8", newline="\n")
        print(json.dumps(table))
        return
    if args.select:
        table = select_method(args.index, as_of, rerank)
        path = ROOT / "reports/rag-rerank.md"
        path.write_text(selection_report(table, as_of), "utf-8", newline="\n")
        print(json.dumps(table))
        return
    fixed, numbers = read_jsonl(EVAL / "questions.jsonl"), read_jsonl(EVAL / "snapshot_gold.jsonl")
    result = score(
        fixed,
        numbers,
        run_current(fixed + numbers, index=args.index, as_of=as_of, rerank=rerank, **options),
        load_chunks(args.index),
    )
    coverage = language_coverage(fixed, numbers, read_jsonl(EVAL / "translations.jsonl"))
    corpus = (built["documents"], built["chunks"])
    text = report(result, coverage, fixed, as_of, corpus, method, options["log_rule"])
    args.report.write_text(text, "utf-8", newline="\n")
    summary = {"passed": result["passed"], "method": method, "log_rule": options["log_rule"]}
    print(json.dumps(summary | result["overall"]))


LOG_NAMES = {
    "L0": "any document at most two of five results",
    "L1": "each append-only log at most one of five results (D100 L1)",
    "L2": "each log at most one result and its BM25 score halved (D100 L2)",
}


def logs_report(table: list[dict], as_of: datetime, logs: tuple[str, ...]) -> str:
    rows = [
        f"| {r['method']} | {LOG_NAMES[r['method']]} | {r['dev_evidence_support']:.3f} "
        f"| {r['dev_recall']:.3f} |"
        for r in table
    ]
    return "\n".join(
        [
            "# Ask log-limit selection (T265)",
            "",
            f"Generated by `python -m atlas.rag.evaluate --select-logs` at as-of"
            f" {as_of:%Y-%m-%d %H:%M} UTC. Logs: {', '.join(logs)}. The rule was fixed in D100"
            " before any run: dev evidence support on the 27 dev cases, then recall on the 20"
            " retrieval dev questions, then the simpler rule. Holdout cases (Q41-Q50) are not"
            " run here.",
            "",
            "| Rule | Description | Dev evidence support | Dev recall |",
            "|---|---|---|---|",
            *rows,
            "",
            f"**Chosen: {table[0]['method']}.** It is set as `log_rule` in `configs/rag.yaml`"
            " and `reports/rag.md` is then generated once with it.",
            "",
        ]
    )


if __name__ == "__main__":
    main()
