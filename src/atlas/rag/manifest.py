"""T260 (child of T180): export the committed Ask index as a trusted D1 release (D95)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from atlas.rag.index import INDEX

OUTPUT = INDEX.with_name("ask-release.sql")
# Column order of worker/schema.sql ask_chunks after `release`.
FIELDS = (
    "chunk_id",
    "doc_id",
    "path",
    "heading",
    "text",
    "available_at",
    "expires_at",
    "states",
    "sha256",
)


class ManifestError(ValueError):
    """The index cannot be published as a trusted Ask release."""


def manifest(index: Path = INDEX) -> dict:
    """Return the release ID (SHA-256 of the canonical chunk list) and its chunks."""
    uri = Path(index).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        rows = db.execute(
            "SELECT c.chunk_id, c.doc_id, d.path, c.heading, c.text, d.available_at,"
            " d.expires_at, d.states, c.sha256"
            " FROM chunks c JOIN documents d USING (doc_id) ORDER BY c.chunk_id"
        ).fetchall()
    chunks = [dict(zip(FIELDS, row, strict=True)) for row in rows]
    if not chunks:
        raise ManifestError("The Ask index has no chunks")
    for item in chunks:
        if hashlib.sha256(item["text"].encode("utf-8")).hexdigest() != item["sha256"]:
            raise ManifestError(f"{item['chunk_id']} text does not match its SHA-256")
    body = json.dumps({"schema_version": 1, "chunks": chunks}, sort_keys=True, ensure_ascii=False)
    return {"release": hashlib.sha256(body.encode("utf-8")).hexdigest(), "chunks": chunks}


def literal(value: str | None) -> str:
    """SQLite literal on one line, so no statement splitter can cut a chunk."""
    if value is None:
        return "NULL"
    if "\x00" in value:
        raise ManifestError("Chunk text cannot contain NUL")
    text = value.replace("'", "''").replace("\r", "' || char(13) || '")
    return "'" + text.replace("\n", "' || char(10) || '") + "'"


def load_sql(release: dict) -> str:
    """Insert the new rows, then move the pointer, then delete old rows (D95)."""
    name = literal(release["release"])
    lines = [
        "INSERT OR IGNORE INTO ask_chunks VALUES ("
        + ",".join([name, *(literal(item[field]) for field in FIELDS)])
        + ");"
        for item in release["chunks"]
    ]
    lines.append(
        f"INSERT INTO ask_current VALUES (1,{name})"
        " ON CONFLICT(id) DO UPDATE SET release=excluded.release;"
    )
    lines.append(f"DELETE FROM ask_chunks WHERE release<>{name};")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=INDEX)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    release = manifest(args.index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".ask-", suffix=".sql", dir=args.output.parent)
    with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(load_sql(release))
    os.replace(temporary, args.output)
    print(
        json.dumps(
            {
                "release": release["release"],
                "chunks": len(release["chunks"]),
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
