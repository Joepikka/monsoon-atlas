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
) -> list[dict]:
    """Return at most `limit` distinct chunks known at `as_of`; question text is never SQL.

    At most `per_document` chunks come from one document, so long logs cannot crowd out
    the specific source or model report.
    """
    if not isinstance(question, str) or not 0 < len(question) <= MAX_QUESTION:
        raise ValueError(f"Questions must contain 1 to {MAX_QUESTION} characters")
    cutoff = utc_text(as_of)
    terms = _terms(question)
    if not terms:
        return []
    # Each term is a quoted FTS5 string, so user text cannot inject query operators.
    match = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
    query = """
        SELECT c.chunk_id, c.doc_id, c.section, c.heading, c.text, c.tokens, c.sha256,
               d.path, d.kind, d.licence, d.available_at, d.git_commit,
               bm25(chunk_text, 0.0, 2.0, 1.0) AS score
        FROM chunk_text JOIN chunks c ON c.chunk_id = chunk_text.chunk_id
        JOIN documents d ON d.doc_id = c.doc_id
        WHERE chunk_text MATCH ? AND d.available_at <= ?
          AND (d.expires_at IS NULL OR d.expires_at > ?) AND d.language = ?
          AND (instr(d.states, ',' || ? || ',') > 0 OR instr(d.states, ',all,') > 0)
        ORDER BY score, c.chunk_id LIMIT ?
    """
    uri = f"{Path(index).absolute().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(query, (match, cutoff, cutoff, language, state, candidates)).fetchall()

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
