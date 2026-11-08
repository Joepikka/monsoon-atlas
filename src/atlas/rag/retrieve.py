"""T252: as-of, state and language filtered BM25 retrieval over the local Ask index (D87)."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from atlas.rag.corpus import utc_text
from atlas.rag.index import INDEX

MAX_QUESTION = 500
TERM = re.compile(r"\w+")
STOPWORDS = frozenset(
    "a an and are as at be by can could do does for from how i if in is it its my of on or "
    "the this that to was what when where which who why will with".split()
)


def _terms(question: str) -> list[str]:
    seen = []
    for term in TERM.findall(question.lower()):
        if term not in STOPWORDS and term not in seen:
            seen.append(term)
    return seen


def _shingles(text: str) -> set[str]:
    words = TERM.findall(text.lower())
    return {" ".join(words[i : i + 3]) for i in range(max(1, len(words) - 2))}


METHODS = ("R0", "R1", "R2", "R3")
RRF_K = 60


def _order(method: str, lexical: list[str], cosine: dict[str, float], candidates: int) -> list[str]:
    """R1: e5 order of the BM25 top 50; R2/R3: reciprocal rank fusion (D99)."""
    by_cosine = lambda keys: sorted(keys, key=lambda key: (-cosine[key], key))  # noqa: E731
    if method == "R1":
        return by_cosine(lexical)
    dense = by_cosine(lexical if method == "R2" else cosine)[:candidates]
    fused: dict[str, float] = {}
    for ranking in (lexical, dense):
        for rank, key in enumerate(ranking, start=1):
            fused[key] = fused.get(key, 0.0) + 1 / (RRF_K + rank)
    return sorted(fused, key=lambda key: (-fused[key], key))


def retrieve(
    question: str,
    *,
    as_of: datetime,
    state: str = "ka",
    language: str = "en",
    index: Path = INDEX,
    candidates: int = 50,
    limit: int = 5,
    per_document: int = 2,
    max_context_tokens: int = 3000,
    method: str = "R0",
    embedder=None,
    vectors: dict | None = None,
) -> list[dict]:
    """Return at most `limit` distinct chunks known at `as_of`; question text is never SQL.

    At most `per_document` chunks come from one document, so long logs cannot crowd out
    the specific source or model report. `method` R1-R3 reorder candidates with e5 (D99):
    `embedder` embeds the question and `vectors` holds the passage vectors.
    """
    if method not in METHODS:
        raise ValueError(f"Unknown retrieval method {method}")
    if not isinstance(question, str) or not 0 < len(question) <= MAX_QUESTION:
        raise ValueError(f"Questions must contain 1 to {MAX_QUESTION} characters")
    cutoff = utc_text(as_of)
    terms = _terms(question)
    if not terms:
        return []
    # Each term is a quoted FTS5 string, so user text cannot inject query operators.
    match = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
    columns = """c.chunk_id, c.doc_id, c.section, c.heading, c.text, c.tokens, c.sha256,
               d.path, d.kind, d.licence, d.available_at, d.git_commit"""
    filters = """d.available_at <= ? AND (d.expires_at IS NULL OR d.expires_at > ?)
          AND d.language = ?
          AND (instr(d.states, ',' || ? || ',') > 0 OR instr(d.states, ',all,') > 0)"""
    query = f"""
        SELECT {columns}, bm25(chunk_text, 0.0, 2.0, 1.0) AS score
        FROM chunk_text JOIN chunks c ON c.chunk_id = chunk_text.chunk_id
        JOIN documents d ON d.doc_id = c.doc_id
        WHERE chunk_text MATCH ? AND {filters}
        ORDER BY score, c.chunk_id LIMIT ?
    """
    uri = f"{Path(index).absolute().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(query, (match, cutoff, cutoff, language, state, candidates)).fetchall()
        if method != "R0":
            known = f"SELECT {columns}, 0.0 AS score FROM chunks c JOIN documents d"
            known += f" ON d.doc_id = c.doc_id WHERE {filters}"
            pool = {
                row["chunk_id"]: row for row in db.execute(known, (cutoff, cutoff, language, state))
            }
    if method != "R0":
        question_vector = embedder.query(question)
        cosine = {key: float(vectors[key] @ question_vector) for key in pool}
        rows = [
            pool[key] for key in _order(method, [r["chunk_id"] for r in rows], cosine, candidates)
        ]

    selected, shingles, budget = [], [], max_context_tokens
    for row in rows:
        current = _shingles(row["text"])
        if (
            row["tokens"] > budget
            or sum(item["doc_id"] == row["doc_id"] for item in selected) >= per_document
            or any(len(current & other) / max(1, len(current | other)) > 0.5 for other in shingles)
        ):
            continue
        selected.append(dict(row))
        shingles.append(current)
        budget -= row["tokens"]
        if len(selected) == limit:
            break
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--as-of", type=datetime.fromisoformat, default=datetime.now(UTC))
    parser.add_argument("--state", default="ka")
    parser.add_argument("--index", type=Path, default=INDEX)
    args = parser.parse_args()
    results = retrieve(args.question, as_of=args.as_of, state=args.state, index=args.index)
    print(json.dumps([{k: v for k, v in row.items() if k != "text"} for row in results]))


if __name__ == "__main__":
    main()
