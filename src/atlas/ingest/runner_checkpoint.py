"""T243: keep a trusted local catalogue of immutable runner checkpoints."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import stat
import tempfile
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from atlas.config import load_budgets
from atlas.data.budget import ArchiveOnly
from atlas.ingest import checkpoint_bundle as bundles
from atlas.ingest.base import IngestError
from atlas.ingest.schedule import open_control


def _store_path(root: Path, store: Path, *, create: bool) -> Path:
    try:
        store = bundles._path(store)
    except FileNotFoundError:
        if not create:
            raise IngestError("Runner checkpoint store is missing") from None
        store = bundles._path(store, destination=True)
        bundles._disjoint(root, store)
        store.mkdir(exist_ok=True)
        store = bundles._path(store)
    bundles._disjoint(root, store)
    return store


@contextmanager
def _locked_catalogue(store: Path, *, create: bool) -> Iterator[sqlite3.Connection]:
    catalog = store / "catalog.sqlite"
    # Validate the SQLite target and its rollback file before SQLite can open either.
    for path in (catalog, store / "catalog.sqlite-journal"):
        try:
            details = bundles._stat(path)
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(details.st_mode):
            raise IngestError("Runner catalogue requires a regular SQLite file")
    for name in ("catalog.sqlite-wal", "catalog.sqlite-shm"):
        try:
            (store / name).lstat()
        except FileNotFoundError:
            continue
        raise IngestError("Runner catalogue requires rollback journal mode")

    if create and not catalog.exists() and any(store.iterdir()):
        raise IngestError("Runner catalogue is missing from a nonempty store")

    mode = "rwc" if create else "rw"
    with closing(sqlite3.connect(f"{catalog.as_uri()}?mode={mode}", uri=True, timeout=0)) as db, db:
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("PRAGMA synchronous=FULL")
        if db.execute("PRAGMA journal_mode").fetchone() != ("delete",):
            raise IngestError("Runner catalogue requires rollback journal mode")
        db.execute("BEGIN IMMEDIATE")
        if create:
            db.execute("""
                CREATE TABLE IF NOT EXISTS current_checkpoint (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    root TEXT NOT NULL,
                    digest TEXT NOT NULL
                ) STRICT
            """)
        yield db


def _head(db: sqlite3.Connection, root: Path) -> str | None:
    row = db.execute("SELECT root, digest FROM current_checkpoint WHERE singleton=1").fetchone()
    if row is None:
        return None
    retained_root, digest = row
    if retained_root != str(root):
        raise IngestError("Runner catalogue is bound to another feed root")
    if not isinstance(digest, str) or not re.fullmatch(bundles.HASH, digest):
        raise IngestError("Runner catalogue has an invalid head digest")
    return digest


def _set_head(db: sqlite3.Connection, root: Path, digest: str) -> None:
    db.execute(
        "INSERT INTO current_checkpoint(singleton, root, digest) VALUES(1, ?, ?) "
        "ON CONFLICT(singleton) DO UPDATE SET digest=excluded.digest",
        (str(root), digest),
    )


def _pending_catalogue_bytes(db: sqlite3.Connection, store: Path) -> int:
    pages = db.execute("PRAGMA page_count").fetchone()[0]
    page_size = db.execute("PRAGMA page_size").fetchone()[0]
    return max(0, pages * page_size - (store / "catalog.sqlite").stat().st_size)


def commit_checkpoint(root: Path, store: Path, *, expected_head: str | None) -> str:
    """Seal quiescent state and advance a matching head. None explicitly bootstraps."""
    if expected_head is not None and not re.fullmatch(bundles.HASH, expected_head):
        raise IngestError("Invalid expected runner checkpoint head")
    root = bundles._path(root)
    create = expected_head is None
    store = _store_path(root, store, create=create)
    with _locked_catalogue(store, create=create) as db:
        if _head(db, root) != expected_head:
            raise IngestError("Runner checkpoint head changed; resume the current generation")

        objects = store / "objects"
        objects.mkdir(exist_ok=True)
        objects = bundles._path(objects)
        with tempfile.TemporaryDirectory(prefix=".runner-", dir=objects) as temporary:
            staged = Path(temporary) / "bundle"
            digest = bundles.save_checkpoint(root, staged, additional_quota_roots=(store,))
            try:
                target = bundles._path(objects / digest)
            except FileNotFoundError:
                target = bundles._path(objects / digest, destination=True)
                install = True
            else:
                install = False
                # The newly sealed bytes already passed source reference checks.
                entries = bundles._manifest(target, root, digest)
                files = target / "files"
                bundles._verify_files(files, bundles._inventory(files, strict=True), entries)
            if digest != expected_head:
                _set_head(db, root, digest)
                # Pending SQLite pages may only reach the file after the copy check.
                bundles._reserve(root, target, _pending_catalogue_bytes(db, store), (store,))
            if install:
                staged.rename(target)
        # SQLite exposes the new head only after the immutable object is installed.
    return digest


def bootstrap_checkpoint(root: Path, store: Path) -> str:
    """Start an explicit new chain with empty control state; never replaces a root or store."""
    root = bundles._path(root, destination=True)
    store = bundles._path(store, destination=True)
    bundles._disjoint(root, store)
    root.mkdir()
    with closing(open_control(root / bundles.CONTROL)):
        pass
    return commit_checkpoint(root, store, expected_head=None)


def resume_checkpoint(root: Path, store: Path) -> str:
    """Restore the catalogue's current generation to the original absent root."""
    root = bundles._path(root, destination=True)
    store = _store_path(root, store, create=False)
    with _locked_catalogue(store, create=False) as db:
        digest = _head(db, root)
        if digest is None:
            raise IngestError("Runner catalogue has no committed head")
        bundles.restore_checkpoint(
            root, store / "objects" / digest, digest, additional_quota_roots=(store,)
        )
    return digest


def _artifact_budget(payload_bytes: int, retained_bytes: int) -> int:
    if type(retained_bytes) is not int or retained_bytes < 0:
        raise IngestError("Retained artifact bytes must be a nonnegative integer")
    budget = load_budgets(bundles.ROOT / "configs/budgets.yaml").github_actions
    if payload_bytes + retained_bytes > budget.artifacts_mb * 1_000_000:
        raise ArchiveOnly("Checkpoint would exceed the configured artifact budget")
    return budget.artifact_retention_days


def offer_checkpoint(root: Path, store: Path, *, retained_artifact_bytes: int) -> dict:
    """Verify the current generation and report its exact local artifact candidate."""
    try:
        root = bundles._path(root)
    except FileNotFoundError:
        root = bundles._path(root, destination=True)
    store = _store_path(root, store, create=False)
    with _locked_catalogue(store, create=False) as db:
        digest = _head(db, root)
        if digest is None:
            raise IngestError("Runner catalogue has no committed head")
        bundle = bundles._path(store / "objects" / digest)
        entries = bundles._manifest(bundle, root, digest)
        size = bundles._stat(bundle / "manifest.json").st_size + sum(
            entry["bytes"] for entry in entries.values()
        )
        retention = _artifact_budget(size, retained_artifact_bytes)
        files = bundle / "files"
        bundles._verify_files(files, bundles._listed_inventory(files, entries), entries)
        bundles._check_references(files, entries, root)
    return {
        "status": "ready",
        "bundle_path": str(bundle),
        "manifest_sha256": digest,
        "payload_bytes": size,
        "retention_days": retention,
    }


def import_checkpoint(root: Path, bundle: Path, store: Path, expected_sha256: str) -> str:
    """Install a verified downloaded generation in an absent local store."""
    root = bundles._path(root, destination=True)
    bundle = bundles._path(bundle)
    store = bundles._path(store, destination=True)
    bundles._disjoint(root, store)
    bundles._disjoint(bundle, store)
    bundles._disjoint(bundle, root)
    entries = bundles._manifest(bundle, root, expected_sha256)
    manifest_size = bundles._stat(bundle / "manifest.json").st_size
    size = manifest_size + sum(entry["bytes"] for entry in entries.values())
    _artifact_budget(size, 0)
    before = bundles._listed_inventory(bundle / "files", entries)
    bundles._reserve(bundle, store, size, ())
    with tempfile.TemporaryDirectory(prefix=".runner-import-", dir=store.parent) as temporary:
        stage = Path(temporary)
        with _locked_catalogue(stage, create=True) as db:
            target = stage / "objects" / expected_sha256
            bundles._stage_members(bundle, target / "files", root, expected_sha256, entries, before)
            copied = bundles._copy_file(
                bundle / "manifest.json", target / "manifest.json", manifest_size
            )
            if copied != expected_sha256:
                raise IngestError("Checkpoint manifest changed during import")
            _set_head(db, root, expected_sha256)
            bundles._reserve(bundle, store, _pending_catalogue_bytes(db, stage), (stage,))
        bundles._absent(root)
        bundles._absent(store)
        stage.rename(store)
    return expected_sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in (
        "runner-save",
        "runner-restore",
        "runner-offer",
        "runner-import",
        "runner-bootstrap",
    ):
        action = commands.add_parser(command)
        action.add_argument("--root", type=Path, default=bundles.ROOT / ".cache/feeds")
        action.add_argument("--store", type=Path, required=True)
        if command == "runner-save":
            action.add_argument("--expected-head", required=True)
        elif command == "runner-offer":
            action.add_argument("--retained-artifact-bytes", type=int, required=True)
        elif command == "runner-import":
            action.add_argument("--bundle", type=Path, required=True)
            action.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    try:
        if args.command == "runner-save":
            expected = None if args.expected_head == "empty" else args.expected_head
            digest = commit_checkpoint(args.root, args.store, expected_head=expected)
            status = "saved"
        elif args.command == "runner-restore":
            digest = resume_checkpoint(args.root, args.store)
            status = "restored"
        elif args.command == "runner-bootstrap":
            digest = bootstrap_checkpoint(args.root, args.store)
            status = "bootstrapped"
        elif args.command == "runner-import":
            digest = import_checkpoint(args.root, args.bundle, args.store, args.expected_sha256)
            status = "imported"
        else:
            print(
                json.dumps(
                    offer_checkpoint(
                        args.root, args.store, retained_artifact_bytes=args.retained_artifact_bytes
                    )
                )
            )
            return
    except (ArchiveOnly, IngestError, OSError, sqlite3.Error) as error:
        reason = (
            str(error) if isinstance(error, (ArchiveOnly, IngestError)) else type(error).__name__
        )
        print(json.dumps({"status": "failed", "reason": reason}))
        raise SystemExit(1) from None
    print(json.dumps({"status": status, "manifest_sha256": digest}))


if __name__ == "__main__":
    main()
