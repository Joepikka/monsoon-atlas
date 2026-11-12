"""Karnataka official warning archive (D189).

Every S09 snapshot the Worker has stored is read through its signed export (atlas.data.hot_export)
and every official CAP warning record in them is kept once, with the times this project first and
last saw it. The text, severity, issue and expiry times are the provider's own; nothing is edited
or inferred. The Sachet feed keeps no history, so the archive starts at the first stored snapshot
(12 Nov 2026) and only grows from there. Not an emergency service.
"""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime

KEEP = (
    "id",
    "title",
    "severity",
    "issued_at",
    "valid_at",
    "expires_at",
    "area_text",
    "warning_text",
    "instruction",
    "source_url",
    "longitude",
    "latitude",
)


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def warnings_from_rows(rows: list[dict]) -> list[dict]:
    """Rows from hot_export.verify_row (S09 only); one entry per CAP warning record ID."""
    seen: dict[str, dict] = {}
    for row in sorted(rows, key=lambda r: r["as_of"]):
        if row["source_id"] != "S09":
            continue
        snapshot = json.loads(gzip.decompress(row["payload_gzip"]))["snapshot"]
        for record in snapshot["records"]:
            if record.get("kind") != "alert" or record.get("provenance") != "official":
                continue  # the archive holds official warnings only
            entry = seen.get(record["id"])
            if entry is None:
                entry = {k: record.get(k) for k in KEEP}
                entry["first_seen"] = record["fetched_at"]
                seen[record["id"]] = entry
            entry["last_seen"] = record["fetched_at"]
    return sorted(seen.values(), key=lambda e: (e["issued_at"] or "", e["id"]), reverse=True)


def archive_body(warnings: list[dict], since: str | None, now: datetime) -> dict:
    return {
        "schema_version": 1,
        "state": "ka",
        "source_id": "S09",
        "archive_since": since,
        "built_at": now.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "count": len(warnings),
        "note": (
            "Official NDMA Sachet CAP warnings for Karnataka as issued, kept from the first stored "
            "snapshot; the feed itself keeps no history. Not an emergency service: follow official "
            "channels and call 112 in an emergency."
        ),
        "warnings": warnings,
    }
