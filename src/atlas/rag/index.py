"""T252: build the local SQLite FTS5 index for the English Ask corpus (D87)."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from atlas.rag.corpus import CONFIG, ROOT, Document, chunk, committed_documents, load_config

INDEX = ROOT / "data/rag/index.sqlite"
SCHEMA = """
CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL, licence TEXT NOT NULL,
    language TEXT NOT NULL, states TEXT NOT NULL, available_at TEXT NOT NULL,
    expires_at TEXT, sha256 TEXT NOT NULL, git_commit TEXT NOT NULL
) STRICT;
CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY, doc_id TEXT NOT NULL REFERENCES documents(doc_id),
    section TEXT NOT NULL, heading TEXT NOT NULL, ordinal INTEGER NOT NULL, text TEXT NOT NULL,
    tokens INTEGER NOT NULL, sha256 TEXT NOT NULL
) STRICT;
CREATE VIRTUAL TABLE chunk_text USING fts5(
    chunk_id UNINDEXED, heading, text, tokenize='porter unicode61'
);
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL) STRICT;
"""


def build_index(
    documents: list[Document], output: Path, *, limit: int = 300, overlap: int = 50
) -> dict:
    """Write a new index beside `output` and replace it only after it is complete."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".rag-", suffix=".sqlite", dir=output.parent)
    os.close(handle)
    count = 0
    try:
        with closing(sqlite3.connect(temporary)) as db, db:
            db.executescript(SCHEMA)
            for document in documents:
                db.execute(
                    "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        document.doc_id,
                        document.path,
                        document.kind,
                        document.licence,
                        document.language,
                        "," + ",".join(document.states) + ",",
                        document.available_at,
                        document.expires_at,
                        document.sha256,
                        document.commit,
                    ),
                )
                for item in chunk(document, limit=limit, overlap=overlap):
                    db.execute(
                        "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?)",
                        (
                            item.chunk_id,
                            item.doc_id,
                            item.section,
                            item.heading,
                            item.ordinal,
                            item.text,
                            item.tokens,
                            item.sha256,
                        ),
                    )
                    db.execute(
                        "INSERT INTO chunk_text VALUES (?,?,?)",
                        (item.chunk_id, item.heading, item.text),
                    )
                    count += 1
            db.execute("INSERT INTO settings VALUES ('chunk_tokens', ?)", (str(limit),))
            db.execute("INSERT INTO settings VALUES ('overlap_tokens', ?)", (str(overlap),))
        os.replace(temporary, output)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return {"status": "built", "index": str(output), "documents": len(documents), "chunks": count}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, default=INDEX)
    args = parser.parse_args()
    config = load_config(args.config)
    documents = committed_documents(config)
    result = build_index(
        documents, args.output, limit=config["chunk_tokens"], overlap=config["overlap_tokens"]
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
