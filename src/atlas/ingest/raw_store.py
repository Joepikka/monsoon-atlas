"""Content-addressed raw artifact store with an append-only ledger.

Layout (plan section 4): {raw_root}/{source}/{yyyy-mm-dd}/{sha256}.{ext}
Ledger: {raw_root}/ledger.jsonl, one JSON object per fetch (including 304 not-modified).
Files are written to a temp file and renamed, so an interrupted write never replaces or
truncates existing data.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from atlas import jsonl
from atlas.contracts import RawArtifact
from atlas.data.budget import StorageQuota

LEDGER = "ledger.jsonl"


class RawStore:
    def __init__(self, root: Path, quota: StorageQuota | None = None):
        self.root = Path(root)
        self.quota = quota

    def put(
        self, content: bytes, source_id: str, fetched_at: datetime, ext: str
    ) -> tuple[Path, str]:
        """Store bytes under their SHA256. Identical content is never written twice.
        Raises ArchiveOnly when the storage quota stop threshold would be reached."""
        sha = hashlib.sha256(content).hexdigest()
        target = self.root / source_id / fetched_at.date().isoformat() / f"{sha}.{ext}"
        if target.exists():
            return target, sha
        if self.quota is not None:
            self.quota.ensure_can_ingest(len(content))
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".tmp-", suffix=f".{ext}")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, target)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return target, sha

    def record(self, artifact: RawArtifact, http: dict[str, Any]) -> None:
        """Append one ledger entry. `http` must already be free of credentials."""
        jsonl.append(
            self.root / LEDGER, {"artifact": artifact.model_dump(mode="json"), "http": http}
        )

    def entries(self) -> list[dict[str, Any]]:
        return jsonl.read(self.root / LEDGER)

    def latest_ok(self, source_url: str) -> dict[str, Any] | None:
        """Most recent stored (HTTP 200) entry for a URL, used for conditional GET and 304."""
        for entry in reversed(self.entries()):
            art = entry["artifact"]
            if art["source_url"] == source_url and art["response_status"] == 200:
                return entry
        return None
