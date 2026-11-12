"""T218 (D162): licence-cleared exports as static shards with a manifest.

Only a source with an available, open discovery record may be exported; the check is the T185
gate (`require_open_source`), not a second licence rule. Each shard holds at most 10,000 rows and
10 MiB. web/src/export.ts builds the same manifest in the browser from the same records.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

from atlas.spatial.context import _discovery
from atlas.spatial.tiles import require_open_source

MAX_ROWS = 10_000
MAX_BYTES = 10 * 1024 * 1024


def export_manifest(
    source_id: str, rows: Sequence[dict], *, max_rows: int = MAX_ROWS, max_bytes: int = MAX_BYTES
) -> tuple[dict, list[bytes]]:
    """(manifest, shards) for rows of one source, or SourceUnavailable if it may not be exported."""
    require_open_source(source_id, "an export")
    lines = [
        json.dumps(r, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n" for r in rows
    ]
    shards: list[bytes] = []
    chunk: list[bytes] = []
    for line in lines:
        if len(line) > max_bytes:
            raise ValueError("one row exceeds the shard size limit")
        if chunk and (len(chunk) >= max_rows or sum(map(len, chunk)) + len(line) > max_bytes):
            shards.append(b"".join(chunk))
            chunk = []
        chunk.append(line)
    if chunk:
        shards.append(b"".join(chunk))
    manifest = {
        "schema_version": 1,
        "source_id": source_id,
        "licence": _discovery(source_id)["licence"]["status"],
        "rows": len(lines),
        "content_sha256": hashlib.sha256(b"".join(shards)).hexdigest(),
        "shards": [
            {
                "path": f"shard-{i + 1:04d}.ndjson",
                "rows": s.count(b"\n"),
                "bytes": len(s),
                "sha256": hashlib.sha256(s).hexdigest(),
            }
            for i, s in enumerate(shards)
        ],
    }
    return manifest, shards
