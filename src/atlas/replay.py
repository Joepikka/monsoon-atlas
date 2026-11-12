"""T045: reopen a published release by its snapshot ID, exactly as it was known (D185).

A snapshot ID is the SHA-256 of the release bytes. Replay reads those bytes, checks the hash, and
checks that nothing in the release was fetched or became available after its cutoff, so a shared
report cannot pick up later data. It never fetches or rebuilds anything.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

DIGEST = re.compile(r"[0-9a-f]{64}")


class ReplayError(Exception):
    pass


def t(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def replay(root: Path, snapshot_id: str, state: str = "ka") -> dict:
    if not DIGEST.fullmatch(snapshot_id):
        raise ReplayError("a snapshot ID is a 64-character lowercase SHA-256")
    path = Path(root) / "data" / state / "releases" / f"{snapshot_id}.json"
    if not path.is_file():
        raise ReplayError(f"release {snapshot_id[:12]} is not in this archive")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != snapshot_id:
        raise ReplayError("release bytes do not match the snapshot ID")
    release = json.loads(data)
    cutoff = t(release["as_of"])
    for record in release["records"]:
        if t(record["fetched_at"]) > cutoff or t(record["available_at"]) > cutoff:
            raise ReplayError(f"record {record['id']} was not known at the cutoff")
    for facility in release["facilities"]:
        if t(facility["fetched_at"]) > cutoff:
            raise ReplayError(f"facility {facility['facility_id']} was not known at the cutoff")
    for health in release["sources"]:
        if health["last_success_at"] and t(health["last_success_at"]) > cutoff:
            raise ReplayError(f"{health['source_id']} health is later than the cutoff")
    return release
