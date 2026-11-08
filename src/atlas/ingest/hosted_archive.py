"""T250: import a checkpoint ZIP bound to the selected hosted artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import stat
import struct
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from atlas.data.budget import ArchiveOnly
from atlas.ingest import checkpoint_bundle as bundles
from atlas.ingest.base import IngestError
from atlas.ingest.runner_checkpoint import _artifact_budget, import_checkpoint
from atlas.ingest.schedule import run_bounded

MAX_CENTRAL_BYTES = 16 * 1024**2
DEADLINE_S = 60


def _file_identity(details: os.stat_result) -> tuple[int, ...]:
    return (
        details.st_dev,
        details.st_ino,
        details.st_size,
        details.st_mtime_ns,
        details.st_ctime_ns,
    )


def _hash_exact(source: BinaryIO, size: int, output: BinaryIO | None = None) -> str:
    digest = hashlib.sha256()
    remaining = size
    while remaining:
        block = source.read(min(remaining, bundles.BLOCK))
        if not block:
            raise IngestError("Checkpoint ZIP content is shorter than expected")
        if output is not None:
            output.write(block)
        digest.update(block)
        remaining -= len(block)
    if source.read(1):
        raise IngestError("Checkpoint ZIP content is longer than expected")
    return digest.hexdigest()


def _central_count(stream: BinaryIO) -> int:
    # Check the pinned Python 3.12 parser's footer before ZipFile loads the directory.
    footer = zipfile._EndRecData(stream)
    if footer is None:
        raise IngestError("Checkpoint ZIP has no central directory")
    count = footer[zipfile._ECD_ENTRIES_TOTAL]
    if (
        footer[zipfile._ECD_DISK_NUMBER] != 0
        or footer[zipfile._ECD_DISK_START] != 0
        or footer[zipfile._ECD_ENTRIES_THIS_DISK] != count
        or not 1 <= count <= bundles.MEMBER_LIMIT + 1
        or not 1 <= footer[zipfile._ECD_SIZE] <= MAX_CENTRAL_BYTES
    ):
        raise IngestError("Checkpoint ZIP central directory exceeds its bounds")
    return count


def _members(archive: zipfile.ZipFile, expected_count: int) -> tuple[dict, set]:
    infos = archive.infolist()
    if len(infos) != expected_count:
        raise IngestError("Checkpoint ZIP directory count is inconsistent")
    files, directories = {}, set()
    for item in infos:
        is_dir = item.is_dir()
        name = item.filename.removesuffix("/") if is_dir else item.filename
        mode = stat.S_IFMT(item.external_attr >> 16)
        if (
            item.orig_filename != item.filename
            or "\\" in name
            or name in files
            or name in directories
            or item.flag_bits & 1
            or item.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
            or mode not in {0, stat.S_IFDIR if is_dir else stat.S_IFREG}
            or item.external_attr & stat.FILE_ATTRIBUTE_REPARSE_POINT
            or (is_dir and item.file_size != 0)
        ):
            raise IngestError("Checkpoint ZIP contains an unsupported or duplicate entry")
        if is_dir:
            directories.add(name)
        else:
            files[name] = item
    return files, directories


def _extract(archive: zipfile.ZipFile, item: zipfile.ZipInfo, path: Path, expected: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(item) as source, path.open("xb") as output:
        if _hash_exact(source, item.file_size, output) != expected:
            raise IngestError("Checkpoint ZIP member failed digest verification")


def _unpack(
    stream: BinaryIO, archive: Path, bundle: Path, root: Path, store: Path, expected_sha256: str
) -> None:
    try:
        count = _central_count(stream)
        with zipfile.ZipFile(stream) as zipped:
            files, directories = _members(zipped, count)
            manifest = files.get("manifest.json")
            if manifest is None or not 1 <= manifest.file_size <= bundles.MANIFEST_LIMIT:
                raise IngestError("Checkpoint ZIP has no bounded manifest")
            expanded = sum(item.file_size for item in files.values())
            _artifact_budget(expanded, 0)
            bundles._reserve(archive, store, expanded, ())
            (bundle / "files").mkdir(parents=True)
            _extract(zipped, manifest, bundle / "manifest.json", expected_sha256)
            entries = bundles._manifest(bundle, root, expected_sha256)
            expected = {f"files/{name}": entry for name, entry in entries.items()}
            if files.keys() != expected.keys() | {"manifest.json"} or any(
                files[name].file_size != entry["bytes"] for name, entry in expected.items()
            ):
                raise IngestError("Checkpoint ZIP inventory differs from the trusted manifest")
            parents = {
                parent.as_posix()
                for name in expected
                for parent in PurePosixPath(name).parents
                if parent != PurePosixPath(".")
            }
            if not directories <= parents:
                raise IngestError("Checkpoint ZIP contains an unlisted directory")
            for name, entry in expected.items():
                _extract(zipped, files[name], bundle / name, entry["sha256"])
    except (
        zipfile.BadZipFile,
        EOFError,
        NotImplementedError,
        UnicodeError,
        struct.error,
        zlib.error,
    ):
        raise IngestError("Checkpoint ZIP is malformed or unsupported") from None


def import_archive(
    root: Path,
    archive: Path,
    store: Path,
    *,
    expected_sha256: str,
    archive_sha256: str,
    archive_bytes: int,
) -> str:
    """Verify a quiescent raw ZIP and install only its verified checkpoint."""
    root = bundles._path(root, destination=True)
    store = bundles._path(store, destination=True)
    bundles._disjoint(root, store)
    if (
        not re.fullmatch(bundles.HASH, expected_sha256)
        or not re.fullmatch(bundles.HASH, archive_sha256)
        or type(archive_bytes) is not int
        or archive_bytes <= 0
    ):
        raise IngestError("Invalid selected checkpoint archive identity")
    _artifact_budget(archive_bytes, 0)
    archive = Path(archive).absolute()
    bundles._path(archive.parent)
    details = bundles._stat(archive)
    if not stat.S_ISREG(details.st_mode) or details.st_size != archive_bytes:
        raise IngestError("Checkpoint ZIP differs from the selected size")
    identity = _file_identity(details)
    with tempfile.TemporaryDirectory(prefix=".runner-zip-", dir=store.parent) as temporary:
        bundle = Path(temporary) / "bundle"
        with archive.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_size != archive_bytes:
                raise IngestError("Checkpoint ZIP changed before verification")
            if _hash_exact(stream, archive_bytes) != archive_sha256:
                raise IngestError("Checkpoint ZIP failed selected digest verification")
            _unpack(stream, archive, bundle, root, store, expected_sha256)
            if (
                _file_identity(os.fstat(stream.fileno())) != _file_identity(opened)
                or _file_identity(bundles._stat(archive)) != identity
            ):
                raise IngestError("Checkpoint ZIP changed during extraction")
        return import_checkpoint(root, bundle, store, expected_sha256)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=bundles.ROOT / ".cache/feeds")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--archive-bytes", required=True, type=int)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.child:
            digest = import_archive(
                args.root,
                args.archive,
                args.store,
                expected_sha256=args.expected_sha256,
                archive_sha256=args.archive_sha256,
                archive_bytes=args.archive_bytes,
            )
            result = {"status": "imported", "manifest_sha256": digest}
        else:
            result = run_bounded(
                [sys.executable, "-m", "atlas.ingest.hosted_archive", "--child", *sys.argv[1:]],
                timeout=DEADLINE_S,
            )
    except (ArchiveOnly, IngestError, OSError, ValueError, sqlite3.Error) as error:
        reason = (
            str(error) if isinstance(error, (ArchiveOnly, IngestError)) else type(error).__name__
        )
        result = {"status": "failed", "reason": reason}
    print(json.dumps(result))
    if not args.child and result["status"] != "imported":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
