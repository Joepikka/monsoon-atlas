"""Release manifests, published last (plan T006).

{manifest_dir}/{release_id}.json   immutable manifest per release, never deleted automatically
{manifest_dir}/latest.json         pointer: current release + the two previous ones (rollback)

publish() verifies files, writes the manifest, runs the upload hook, and only then moves the
pointer. If anything fails before the pointer moves, the current release is unchanged.
data_revision is derived from file contents; published_at is the publish time. Neither is an
observation time.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from atlas.contracts import DatasetManifest, ManifestFile
from atlas.data.store import verify_files

ROLLBACK_DEPTH = 2
POINTER = "latest.json"


def data_revision(files: Sequence[ManifestFile]) -> str:
    h = hashlib.sha256()
    for f in sorted(files, key=lambda f: f.path):
        h.update(f"{f.path}\0{f.sha256}\n".encode())
    return h.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class ManifestStore:
    def __init__(self, manifest_dir: Path, data_root: Path):
        self.dir = Path(manifest_dir)
        self.data_root = Path(data_root)

    def build(
        self,
        release_id: str,
        files: Sequence[ManifestFile],
        *,
        source_versions: dict[str, str] | None = None,
        published_at: datetime | None = None,
    ) -> DatasetManifest:
        current = self.current()
        return DatasetManifest(
            release_id=release_id,
            schema_version=1,
            data_revision=data_revision(files),
            published_at=published_at or datetime.now(UTC),
            parent_release_id=current.release_id if current else None,
            files=tuple(files),
            source_versions=source_versions or {},
            total_bytes=sum(f.bytes for f in files),
        )

    def _pointer(self) -> dict:
        path = self.dir / POINTER
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def load(self, release_id: str) -> DatasetManifest:
        text = (self.dir / f"{release_id}.json").read_text(encoding="utf-8")
        return DatasetManifest.model_validate_json(text)

    def current(self) -> DatasetManifest | None:
        pointer = self._pointer()
        return self.load(pointer["current"]) if pointer.get("current") else None

    def history(self) -> list[str]:
        return list(self._pointer().get("previous", []))

    def publish(
        self, manifest: DatasetManifest, upload: Callable[[DatasetManifest], None] | None = None
    ) -> str:
        verify_files(manifest, self.data_root)
        path = self.dir / f"{manifest.release_id}.json"
        if path.exists() and self.load(manifest.release_id) != manifest:
            raise ValueError(f"release {manifest.release_id} already exists with other content")
        _atomic_write(path, manifest.model_dump_json(indent=2))
        if upload is not None:
            upload(manifest)  # e.g. Hugging Face push; an exception stops before the pointer moves
        pointer = self._pointer()
        previous = (
            [pointer["current"], *pointer.get("previous", [])] if pointer.get("current") else []
        )
        _atomic_write(
            self.dir / POINTER,
            json.dumps({"current": manifest.release_id, "previous": previous[:ROLLBACK_DEPTH]}),
        )
        return manifest.release_id

    def rollback(self) -> str:
        pointer = self._pointer()
        previous = pointer.get("previous", [])
        if not previous:
            raise ValueError("no previous release to roll back to")
        _atomic_write(
            self.dir / POINTER, json.dumps({"current": previous[0], "previous": previous[1:]})
        )
        return previous[0]
