"""Seal and restore a quiescent local feed tree at its original path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime
from pathlib import Path, PureWindowsPath

from atlas.config import load_budgets
from atlas.contracts import RawArtifact
from atlas.data.budget import GB, ArchiveOnly, StorageQuota
from atlas.ingest.base import IngestError
from atlas.ingest.http import EXT
from atlas.ingest.prepared import MAX_BYTES, ROOT, canonical, utc
from atlas.ingest.raw_store import LEDGER
from atlas.ingest.s01_collect import POINTS, RETURNED_POINT, ROLES, latest_pair
from atlas.ingest.s01_prepare import MODEL, PROFILE, receipt_time
from atlas.ingest.s09_prepare import CAP_URL

HASH = r"[0-9a-f]{64}"
DAY = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
RAW_DIR = {"S09": "raw", "S01": "weather/raw"}
PAIR_DIR = "weather/pairs/S01"
OUTPUT = {"S09": "prepared", "S01": "weather/prepared"}
CONTROL = "control.sqlite"
GUARD = "prepared-control.sqlite"
LATEST = "weather/latest-pair.json"
DATABASES = {CONTROL, *(f"{base}/{GUARD}" for base in OUTPUT.values())}
FIXED = {LATEST, *DATABASES, *(f"{base}/prepared.json" for base in OUTPUT.values())}
FIXED.update(f"{base}/{LEDGER}" for base in RAW_DIR.values())
OBJECT_DIRS = {PAIR_DIR: {"json"}}
OBJECT_DIRS.update({f"{base}/{source}": {*EXT.values(), "bin"} for source, base in RAW_DIR.items()})
OBJECT = re.compile(
    "|".join(
        f"{base}/{DAY}/{HASH}\\.(?:{'|'.join(sorted(extensions))})"
        for base, extensions in OBJECT_DIRS.items()
    )
)
IMMUTABLE = re.compile(rf"(?:prepared|weather/prepared)/{HASH}(?:\.inputs)?\.json")
DIRECTORIES = {"weather", *RAW_DIR.values(), *OUTPUT.values(), "weather/pairs", *OBJECT_DIRS}
DATED_DIR = re.compile(rf"(?:{'|'.join(OBJECT_DIRS)})/{DAY}")
SIDECARS = {f"{path}-{suffix}" for path in DATABASES for suffix in ("journal", "wal", "shm")}
LAYOUT_ALIASES = re.compile(
    "|".join(
        [
            *map(re.escape, FIXED | DIRECTORIES | SIDECARS),
            OBJECT.pattern,
            IMMUTABLE.pattern,
            DATED_DIR.pattern,
        ]
    ),
    re.IGNORECASE,
)
MANIFEST_LIMIT = 16 * 1024**2
INPUT_LIMIT = 64 * 1024**2
MEMBER_LIMIT = 100_000
BLOCK = 1024**2

# URL, content digest, clock, required original path (if any), required HTTP status (if any).
type CapEvent = tuple[str, str, datetime, str | None, int | None]


def _member(name: str) -> bool:
    return name in FIXED or bool(OBJECT.fullmatch(name) or IMMUTABLE.fullmatch(name))


def _stat(path: Path) -> os.stat_result:
    details = path.lstat()
    if (
        getattr(details, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        or not (stat.S_ISREG(details.st_mode) or stat.S_ISDIR(details.st_mode))
        or (stat.S_ISREG(details.st_mode) and details.st_nlink != 1)
    ):
        raise IngestError("Checkpoint path contains a link, reparse point or special file")
    return details


def _path(path: Path, *, destination: bool = False) -> Path:
    path = Path(path).absolute()
    if not path.name or path.drive.startswith("\\\\") or ".." in path.parts:
        raise IngestError("Checkpoint paths must identify local directories without traversal")
    if os.name == "nt" and any(
        PureWindowsPath(part).is_reserved() or ":" in part or part.rstrip(" .") != part
        for part in path.parts[1:]
    ):
        raise IngestError("Checkpoint path uses a Windows alias")
    for parent in reversed(path.parents):
        if not stat.S_ISDIR(_stat(parent).st_mode):
            raise IngestError("Checkpoint parent must be an existing directory")
    if destination:
        _absent(path)
        return path.parent.resolve(strict=True) / path.name
    if not stat.S_ISDIR(_stat(path).st_mode):
        raise IngestError("Checkpoint source must be a directory")
    return path.resolve(strict=True)


def _absent(path: Path) -> None:
    try:
        path.lstat()
    except FileNotFoundError:
        return
    raise IngestError("Checkpoint destination already exists")


def _disjoint(source: Path, destination: Path) -> None:
    if source.is_relative_to(destination) or destination.is_relative_to(source):
        raise IngestError("Checkpoint source and destination must be disjoint")


def _inventory(root: Path, *, strict: bool) -> dict[str, tuple]:
    files = {}
    directories = set()
    pending = [root]
    while pending:
        for path in pending.pop().iterdir():
            name = path.relative_to(root).as_posix()
            details = _stat(path)
            is_dir = stat.S_ISDIR(details.st_mode)
            if name in SIDECARS:
                raise IngestError("Checkpoint requires closed SQLite files without sidecars")
            if name in DIRECTORIES or DATED_DIR.fullmatch(name):
                if not is_dir:
                    raise IngestError("Checkpoint layout requires a directory")
                pending.append(path)
                directories.add(name)
            elif _member(name):
                if is_dir:
                    raise IngestError("Checkpoint layout requires a regular file")
                files[name] = (
                    details.st_size,
                    details.st_mtime_ns,
                    details.st_ctime_ns,
                    details.st_dev,
                    details.st_ino,
                )
            elif strict:
                raise IngestError("Checkpoint bundle contains an unlisted member")
            elif LAYOUT_ALIASES.fullmatch("/".join(part.rstrip(" .") for part in name.split("/"))):
                raise IngestError("Checkpoint layout contains an aliased member")
            if len(files) + len(directories) > MEMBER_LIMIT:
                raise IngestError("Checkpoint inventory exceeds its member bound")
    if strict:
        implied = {p.as_posix() for name in files for p in Path(name).parents if p != Path(".")}
        if directories != implied:
            raise IngestError("Checkpoint bundle contains an unlisted directory")
    if CONTROL not in files:
        raise IngestError("Checkpoint requires the shared control.sqlite database")
    return files


def _reserve(
    source: Path, destination: Path, incoming: int, additional_quota_roots: tuple[Path, ...]
) -> None:
    budget = load_budgets(ROOT / "configs/budgets.yaml").storage
    roots = {ROOT / "data", source, *additional_quota_roots}
    roots = {p for p in roots if not any(p != other and p.is_relative_to(other) for other in roots)}
    StorageQuota.from_budget(roots, budget).ensure_can_ingest(incoming)
    if shutil.disk_usage(destination.parent).free - incoming < budget.preflight_min_free_gb * GB:
        raise ArchiveOnly("Checkpoint would exceed the storage free-space reserve")


def _copy_file(source: Path, destination: Path, size: int) -> str:
    _stat(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with source.open("rb") as incoming, destination.open("xb") as output:
        remaining = size
        while remaining:
            block = incoming.read(min(remaining, BLOCK))
            if not block:
                raise IngestError("Checkpoint source changed size during copying")
            output.write(block)
            digest.update(block)
            remaining -= len(block)
        if incoming.read(1):
            raise IngestError("Checkpoint source changed size during copying")
        output.flush()
        os.fsync(output.fileno())
    return digest.hexdigest()


def _read(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        body = stream.read(limit + 1)
    if len(body) > limit:
        raise IngestError("Checkpoint metadata exceeds its byte bound")
    return body


def _verify_files(root: Path, inventory: dict, entries: dict) -> None:
    if inventory.keys() != entries.keys():
        raise IngestError("Checkpoint file inventory differs from the manifest")
    for name, entry in entries.items():
        with (root / name).open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if inventory[name][0] != entry["bytes"] or digest != entry["sha256"]:
            raise IngestError("Checkpoint file differs from the manifest")
        if (OBJECT.fullmatch(name) or IMMUTABLE.fullmatch(name)) and digest != (
            Path(name).name.split(".", 1)[0]
        ):
            raise IngestError("Checkpoint immutable file has the wrong content identity")


def _object_reference(entries: dict, name: str, digest: str, under: str) -> None:
    if (
        not name.startswith(under + "/")
        or not OBJECT.fullmatch(name)
        or name not in entries
        or entries[name]["sha256"] != digest
    ):
        raise IngestError("Checkpoint authoritative reference is missing or invalid")


def _raw_reference(
    entries: dict, original: Path, artifact: dict, source: str
) -> tuple[RawArtifact, str]:
    raw = RawArtifact.model_validate(artifact)
    relative = raw.path.relative_to(original).as_posix()
    if str(original / relative) != artifact["path"] or raw.response_status not in {200, 304}:
        raise IngestError("Checkpoint raw path or status is not canonical")
    if raw.schema_mapping_version != f"{source.lower()}-v1":
        raise IngestError("Checkpoint raw artifact has the wrong source mapping")
    _object_reference(entries, relative, raw.sha256, f"{RAW_DIR[source]}/{source}")
    return raw, relative


def _check_sqlite(
    path: Path, entries: dict, original: Path, required: set, cap_events: set[CapEvent]
) -> None:
    # Immutable mode only reads the staged main file, with no recovery or sidecar writes.
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.execute("PRAGMA trusted_schema=OFF")
        if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise IngestError("Checkpoint SQLite integrity check failed")
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_schema WHERE type='table'")}
        expected = {"prepare_guard"} if path.name == GUARD else {"local_admission", "cap_documents"}
        if not expected <= tables:
            raise IngestError("Checkpoint SQLite file is missing a required table")
        if path.name == GUARD:
            db.execute("SELECT id FROM prepare_guard LIMIT 0")
            return
        db.execute("SELECT source, admitted_at, retry_at FROM local_admission LIMIT 0")
        for identifier, artifact, origin in db.execute(
            "SELECT identifier, artifact_json, content_fetched_at FROM cap_documents"
        ):
            if artifact is not None:
                raw, relative = _raw_reference(entries, original, json.loads(artifact), "S09")
                if (
                    not CAP_URL.fullmatch(raw.source_url)
                    or raw.source_url.rsplit("=", 1)[-1] != identifier
                    or raw.fetched_at != receipt_time(origin)
                ):
                    raise IngestError("Checkpoint CAP control disagrees with its artifact")
                required.add((relative, raw.source_url))
                # A later day's identical 200 can move the artifact path while keeping its origin.
                cap_events.add((raw.source_url, raw.sha256, raw.fetched_at, None, 200))
            elif origin is not None:
                raise IngestError("Checkpoint CAP content clock has no artifact")


def _check_prepared(
    stage: Path, entries: dict, source: str, receipts: dict, cap_events: set[CapEvent]
) -> None:
    base = OUTPUT[source]
    manifests, payloads = {}, {}
    for name in entries:
        if not name.startswith(base + "/") or not IMMUTABLE.fullmatch(name):
            continue
        digest = Path(name).name.split(".", 1)[0]
        if name.endswith(".inputs.json"):
            document = json.loads(_read(stage / name, INPUT_LIMIT))
            if (document["schema_version"], document["source_id"], document["state"]) != (
                1,
                source,
                "ka",
            ):
                raise IngestError("Checkpoint prepared inputs have the wrong identity")
            manifests[digest] = document["as_of"]
            cutoff = receipt_time(document["as_of"])
            for item in document["inputs"]:
                if source == "S09":
                    relative = "raw/" + item["path"]
                    _object_reference(entries, relative, item["sha256"], "raw/S09")
                    origin = receipt_time(item["content_fetched_at"])
                    checked = receipt_time(item["checked_at"])
                    if not origin <= checked <= cutoff:
                        raise IngestError("Checkpoint prepared CAP clocks disagree with the cutoff")
                    identity = (item["source_url"], item["sha256"])
                    cap_events.add((*identity, origin, relative, 200))
                    cap_events.add((*identity, checked, None, None))
                elif receipts.get(item["receipt_path"]) != item:
                    raise IngestError(
                        "Checkpoint prepared weather inputs disagree with their receipt"
                    )
        else:
            payloads[digest] = name
    for digest, name in payloads.items():
        envelope = json.loads(_read(stage / name, MAX_BYTES))
        snapshot = envelope["snapshot"]
        if (envelope["source_id"], snapshot["state"], snapshot["as_of"]) != (
            source,
            "ka",
            manifests.get(snapshot["data_revision"]),
        ) or snapshot["data_revision"] not in manifests:
            raise IngestError("Checkpoint prepared snapshot disagrees with its input manifest")
        payloads[digest] = (snapshot["data_revision"], snapshot["as_of"])
    head = f"{base}/prepared.json"
    if head in entries:
        pointer = json.loads(_read(stage / head, 4096))
        digest, revision = pointer["sha256"], pointer["inputs_sha256"]
        if (
            (pointer["schema_version"], pointer["status"], pointer["source_id"], pointer["state"])
            != (1, "prepared_only", source, "ka")
            or pointer["payload"] != f"{digest}.json"
            or pointer["inputs"] != f"{revision}.inputs.json"
            or payloads.get(digest) != (revision, pointer["as_of"])
        ):
            raise IngestError("Checkpoint prepared pointer disagrees with its immutable files")


def _check_references(stage: Path, entries: dict, original: Path) -> None:
    try:
        required = set()
        cap_events: set[CapEvent] = set()
        for name in DATABASES.intersection(entries):
            _check_sqlite(stage / name, entries, original, required, cap_events)

        receipts = {}
        for name, entry in entries.items():
            if not name.startswith(PAIR_DIR + "/"):
                continue
            pair = json.loads(_read(stage / name, BLOCK))
            requests = pair["requests"]
            roles = tuple(item["role"] for item in requests)
            outcome = pair["outcome"]
            if (
                (pair["schema_version"], pair["source_id"], pair["state"]) != (1, "S01", "ka")
                or (pair["profile"], pair["requested_model"]) != (PROFILE, MODEL)
                or pair["requested_points"] != [list(point) for point in POINTS]
                or roles != ROLES[: len(roles)]
                or outcome not in {"validated", "deferred", "unavailable", "failed"}
                or (outcome == "validated" and roles != ROLES)
            ):
                raise IngestError("Checkpoint weather receipt has invalid capture identity")
            inputs = []
            clocks = []
            for item in requests:
                raw, relative = _raw_reference(entries, original, item["artifact"], "S01")
                required.add((relative, raw.source_url))
                clocks.append(raw.fetched_at)
                inputs.append(
                    {
                        "role": item["role"],
                        "sha256": raw.sha256,
                        "source_url": raw.source_url,
                        "path": relative,
                        "fetched_at": utc(raw.fetched_at),
                    }
                )
            if outcome == "validated":
                clocks = [
                    receipt_time(pair["capture_started_at"]),
                    *clocks,
                    receipt_time(pair["captured_at"]),
                ]
                receipt_time(pair["model_initialization"])
                if clocks != sorted(clocks) or pair["returned_points"] != [list(RETURNED_POINT)]:
                    raise IngestError("Checkpoint weather receipt has invalid clocks or grid")
                receipts[name] = {
                    "receipt_path": name,
                    "receipt_sha256": entry["sha256"],
                    "captured_at": pair["captured_at"],
                    "requests": inputs,
                }
        if LATEST in entries:
            pointer = json.loads(_read(stage / LATEST, 4096))
            _object_reference(entries, pointer["path"], pointer["sha256"], PAIR_DIR)
            if (pointer["schema_version"], pointer["source_id"], pointer["state"]) != (
                1,
                "S01",
                "ka",
            ):
                raise IngestError("Checkpoint weather head has the wrong identity")
            latest_pair(stage)
        for source in OUTPUT:
            _check_prepared(stage, entries, source, receipts, cap_events)
        for source, base in RAW_DIR.items():
            name = f"{base}/{LEDGER}"
            if name not in entries:
                continue
            with (stage / name).open("rb") as ledger:
                while line := ledger.readline(BLOCK + 1):
                    if len(line) > BLOCK:
                        raise IngestError("Checkpoint raw ledger entry exceeds its byte bound")
                    entry = json.loads(line)
                    raw, relative = _raw_reference(entries, original, entry["artifact"], source)
                    if entry["http"]["status"] != raw.response_status:
                        raise IngestError("Checkpoint ledger has inconsistent HTTP status")
                    if raw.response_status == 200:
                        required.discard((relative, raw.source_url))
                    if source == "S09":
                        event = (raw.source_url, raw.sha256, raw.fetched_at)
                        cap_events.discard((*event, None, None))
                        if raw.response_status == 200:
                            cap_events.discard((*event, None, 200))
                            cap_events.discard((*event, relative, 200))
        if required:
            raise IngestError("Checkpoint required evidence has no original raw ledger entry")
        if cap_events:
            raise IngestError("Checkpoint CAP clocks have no matching raw ledger event")
    except (
        KeyError,
        TypeError,
        ValueError,
        AttributeError,
        RecursionError,
        sqlite3.Error,
    ) as error:
        raise IngestError(
            f"Checkpoint reference validation failed ({type(error).__name__})"
        ) from None


def _manifest(bundle: Path, original: Path, expected: str) -> dict:
    if {path.name for path in bundle.iterdir()} != {"manifest.json", "files"}:
        raise IngestError("Checkpoint bundle must contain only manifest.json and files")
    if not stat.S_ISREG(_stat(bundle / "manifest.json").st_mode) or not stat.S_ISDIR(
        _stat(bundle / "files").st_mode
    ):
        raise IngestError("Checkpoint bundle has an invalid layout")
    encoded = _read(bundle / "manifest.json", MANIFEST_LIMIT)
    if not re.fullmatch(HASH, expected) or hashlib.sha256(encoded).hexdigest() != expected:
        raise IngestError("Checkpoint manifest does not match the saved SHA-256")
    try:
        manifest = json.loads(encoded)
        if (
            set(manifest) != {"schema_version", "root", "files"}
            or type(manifest["schema_version"]) is not int
            or manifest["schema_version"] != 1
            or manifest["root"] != str(original)
            or not 1 <= len(manifest["files"]) <= MEMBER_LIMIT
            or canonical(manifest).encode("utf-8") != encoded
        ):
            raise IngestError("Checkpoint manifest is invalid or targets another feed root")
        entries = {}
        previous = ""
        for entry in manifest["files"]:
            name = entry["path"]
            if (
                set(entry) != {"path", "bytes", "sha256"}
                or not _member(name)
                or name <= previous
                or type(entry["bytes"]) is not int
                or entry["bytes"] < 0
                or not re.fullmatch(HASH, entry["sha256"])
            ):
                raise IngestError("Checkpoint manifest contains an invalid file entry")
            entries[name] = entry
            previous = name
        return entries
    except (TypeError, ValueError, KeyError, RecursionError):
        raise IngestError("Checkpoint manifest is malformed") from None


def save_checkpoint(
    root: Path, bundle: Path, *, additional_quota_roots: tuple[Path, ...] = ()
) -> str:
    """Copy quiescent feed state and return the canonical manifest SHA-256."""
    root, bundle = _path(root), _path(bundle, destination=True)
    _disjoint(root, bundle)
    before = _inventory(root, strict=False)
    entries = {
        name: {"path": name, "bytes": before[name][0], "sha256": "0" * 64}
        for name in sorted(before)
    }
    manifest = {"schema_version": 1, "root": str(root), "files": list(entries.values())}
    manifest_size = len(canonical(manifest).encode("utf-8"))
    if manifest_size > MANIFEST_LIMIT:
        raise IngestError("Checkpoint manifest exceeds its byte bound")
    _reserve(
        root,
        bundle,
        sum(entry["bytes"] for entry in entries.values()) + manifest_size,
        additional_quota_roots,
    )
    with tempfile.TemporaryDirectory(prefix=".checkpoint-", dir=bundle.parent) as temporary:
        stage = Path(temporary)
        files = stage / "files"
        for name, entry in entries.items():
            entry["sha256"] = _copy_file(root / name, files / name, entry["bytes"])
        _verify_files(files, _inventory(files, strict=True), entries)
        _check_references(files, entries, root)
        _verify_files(root, _inventory(root, strict=False), entries)
        if _inventory(root, strict=False) != before:
            raise IngestError("Checkpoint source changed during export")
        encoded = canonical(manifest).encode("utf-8")
        with (stage / "manifest.json").open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        _absent(bundle)
        stage.rename(bundle)
    return hashlib.sha256(encoded).hexdigest()


def _listed_inventory(files: Path, entries: dict) -> dict:
    before = _inventory(files, strict=True)
    if {name: info[0] for name, info in before.items()} != {
        name: entry["bytes"] for name, entry in entries.items()
    }:
        raise IngestError("Checkpoint bundle inventory or size differs from the manifest")
    return before


def _stage_members(
    bundle: Path, stage: Path, root: Path, expected_sha256: str, entries: dict, before: dict
) -> None:
    files = bundle / "files"
    for name, entry in entries.items():
        if _copy_file(files / name, stage / name, entry["bytes"]) != entry["sha256"]:
            raise IngestError("Checkpoint bundle bytes differ from the manifest")
    _verify_files(stage, _inventory(stage, strict=True), entries)
    _check_references(stage, entries, root)
    if _inventory(files, strict=True) != before:
        raise IngestError("Checkpoint bundle changed during restore")
    _manifest(bundle, root, expected_sha256)


def restore_checkpoint(
    root: Path,
    bundle: Path,
    expected_sha256: str,
    *,
    additional_quota_roots: tuple[Path, ...] = (),
) -> None:
    """Verify staged state against a separately retained digest and restore it."""
    root, bundle = _path(root, destination=True), _path(bundle)
    _disjoint(bundle, root)
    entries = _manifest(bundle, root, expected_sha256)
    before = _listed_inventory(bundle / "files", entries)
    _reserve(
        bundle, root, sum(entry["bytes"] for entry in entries.values()), additional_quota_roots
    )
    with tempfile.TemporaryDirectory(prefix=".checkpoint-", dir=root.parent) as temporary:
        stage = Path(temporary)
        _stage_members(bundle, stage, root, expected_sha256, entries, before)
        _absent(root)
        stage.rename(root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("checkpoint-save", "checkpoint-restore"):
        action = commands.add_parser(command)
        action.add_argument("--root", type=Path, default=ROOT / ".cache/feeds")
        action.add_argument("--bundle", type=Path, required=True)
        if command == "checkpoint-restore":
            action.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    try:
        if args.command == "checkpoint-save":
            digest = save_checkpoint(args.root, args.bundle)
            result = {"status": "saved", "manifest_sha256": digest}
        else:
            restore_checkpoint(args.root, args.bundle, args.expected_sha256)
            result = {"status": "restored", "manifest_sha256": args.expected_sha256}
    except (IngestError, OSError, ArchiveOnly) as error:
        reason = type(error).__name__ if isinstance(error, OSError) else str(error)
        print(json.dumps({"status": "failed", "reason": reason}))
        raise SystemExit(1) from None
    print(json.dumps(result))


if __name__ == "__main__":
    main()
