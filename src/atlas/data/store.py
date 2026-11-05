"""Immutable partitioned Parquet store and the rebuildable DuckDB cache (plan T006, D03).

Layout: {root}/{source}/state={state}/year={yyyy}/month={mm}/part-{sha16}.parquet
Shards target 64 MB, row groups 16 MB (estimated from in-memory row size). Each file is named
by its content hash and written temp-then-rename, so files are never overwritten.
Parquet is the truth; the DuckDB file is a cache that can always be rebuilt from a manifest.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from atlas.config import DuckDbBudget
from atlas.contracts import DatasetManifest, ManifestFile
from atlas.data.budget import StorageQuota

SHARD_BYTES = 64 * 1024**2
ROW_GROUP_BYTES = 16 * 1024**2


def _rows_for(table: pa.Table, target_bytes: int) -> int:
    per_row = max(1, table.nbytes // max(1, table.num_rows))
    return max(1, target_bytes // per_row)


def _write_file(table: pa.Table, directory: Path, row_group_rows: int) -> tuple[Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".parquet")
    os.close(fd)
    try:
        pq.write_table(table, tmp, row_group_size=row_group_rows, compression="zstd")
        sha = hashlib.sha256(Path(tmp).read_bytes()).hexdigest()
        target = directory / f"part-{sha[:16]}.parquet"
        if target.exists():
            Path(tmp).unlink()  # identical content already stored
        else:
            os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return target, sha


def write_partitioned(
    table: pa.Table, root: Path, *, quota: StorageQuota | None = None
) -> list[ManifestFile]:
    """Write a validated envelope table, partitioned by source/state/year/month of valid_at
    (available_at when valid_at is null). Returns manifest entries with paths relative to root."""
    root = Path(root)
    if quota is not None:
        quota.ensure_can_ingest(table.nbytes)
    when = pc.coalesce(table["valid_at"], table["available_at"])
    keyed = table.append_column("_y", pc.year(when)).append_column("_m", pc.month(when))
    groups = keyed.group_by(["source_id", "state", "_y", "_m"]).aggregate([]).to_pylist()
    out = []
    for g in sorted(groups, key=lambda g: (g["source_id"], g["state"], g["_y"], g["_m"])):
        mask = pc.and_(
            pc.and_(
                pc.equal(keyed["source_id"], g["source_id"]), pc.equal(keyed["state"], g["state"])
            ),
            pc.and_(pc.equal(keyed["_y"], g["_y"]), pc.equal(keyed["_m"], g["_m"])),
        )
        part = keyed.filter(mask).drop_columns(["_y", "_m"])
        directory = (
            root
            / g["source_id"]
            / f"state={g['state']}"
            / f"year={g['_y']:04d}"
            / f"month={g['_m']:02d}"
        )
        shard_rows, rg_rows = _rows_for(part, SHARD_BYTES), _rows_for(part, ROW_GROUP_BYTES)
        for start in range(0, part.num_rows, shard_rows):
            shard = part.slice(start, shard_rows)
            path, sha = _write_file(shard, directory, rg_rows)
            out.append(
                ManifestFile(
                    path=path.relative_to(root).as_posix(),
                    sha256=sha,
                    bytes=path.stat().st_size,
                    rows=shard.num_rows,
                )
            )
    return out


def verify_files(manifest: DatasetManifest, root: Path) -> None:
    """Every manifest file must exist with the recorded hash, size and row count."""
    for f in manifest.files:
        path = Path(root) / f.path
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != f.sha256 or len(data) != f.bytes:
            raise ValueError(f"{f.path}: bytes do not match the manifest")
        if pq.ParquetFile(path).metadata.num_rows != f.rows:
            raise ValueError(f"{f.path}: row count does not match the manifest")


def rebuild_cache(
    manifest: DatasetManifest, root: Path, db_path: Path, duck: DuckDbBudget
) -> dict[str, int]:
    """Rebuild the DuckDB cache from the manifest's Parquet files into a new file, then swap it
    in. One writer only; the old cache stays usable until the swap. Returns rows per source."""
    verify_files(manifest, root)
    by_source: dict[str, list[str]] = {}
    for f in manifest.files:
        by_source.setdefault(f.path.split("/")[0], []).append((Path(root) / f.path).as_posix())
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = db_path.with_suffix(".rebuild.duckdb")
    tmp.unlink(missing_ok=True)
    con = duckdb.connect(str(tmp))
    try:
        con.execute(f"SET memory_limit = '{duck.memory_limit_gb}GB'")
        con.execute(f"SET threads = {duck.threads}")
        counts = {}
        for source, files in sorted(by_source.items()):
            con.execute(
                f'CREATE TABLE "{source}" AS SELECT * FROM read_parquet(?, union_by_name = true)',
                [files],
            )
            counts[source] = con.execute(f'SELECT count(*) FROM "{source}"').fetchone()[0]
        con.execute("CHECKPOINT")
    finally:
        con.close()
    os.replace(tmp, db_path)
    return counts
