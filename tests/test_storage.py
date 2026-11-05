"""T006 acceptance: failed upload leaves current manifest unchanged; quota stop preserves all
existing snapshots; rebuild from Parquet equals original counts."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError
from test_asof import fixture_rows, row, table  # real Open-Meteo fixture rows
from typer.testing import CliRunner

from atlas.cli import app
from atlas.config import DuckDbBudget, StorageBudget
from atlas.data import store as store_mod
from atlas.data.asof import local_midnight_utc
from atlas.data.budget import ArchiveOnly, QuotaLedger, StorageQuota
from atlas.data.manifest import ManifestStore, data_revision
from atlas.data.store import rebuild_cache, write_partitioned
from atlas.ingest.raw_store import RawStore

ROOT = Path(__file__).resolve().parents[1]
DUCK = DuckDbBudget(memory_limit_gb=1, threads=1)
PUBLISHED = datetime(2026, 11, 5, 7, 0, tzinfo=UTC)


def mixed_table():
    """Real July 2024 rows plus one August row and one S01 row -> 3 partitions."""
    rows = fixture_rows()
    aug = local_midnight_utc(date(2024, 8, 1))
    rows.append(row(aug, 2.5, available=aug + timedelta(days=5), snapshot="snap-1"))
    rows.append(dict(rows[0], source_id="S01", record_id="r-s01"))
    return table(rows)


def snapshot_hashes(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def published(tmp_path, release="r1", upload=None):
    clean = tmp_path / "clean"
    files = write_partitioned(mixed_table(), clean)
    ms = ManifestStore(tmp_path / "manifests", clean)
    manifest = ms.build(release, files, published_at=PUBLISHED)
    ms.publish(manifest, upload=upload)
    return ms, manifest, clean


# --- partitioned Parquet ---------------------------------------------------------------------


def test_partitions_by_source_state_year_month_and_hashes_files(tmp_path):
    files = write_partitioned(mixed_table(), tmp_path)
    dirs = sorted({f.path.rsplit("/", 1)[0] for f in files})
    # IST midnights fall on the previous UTC day: 1 Jul IST -> June; 1 Aug IST -> July.
    assert dirs == [
        "S01/state=ka/year=2024/month=06",
        "S02/state=ka/year=2024/month=06",
        "S02/state=ka/year=2024/month=07",
    ]
    for f in files:
        data = (tmp_path / f.path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == f.sha256
        assert Path(f.path).name == f"part-{f.sha256[:16]}.parquet"
    assert sum(f.rows for f in files) == mixed_table().num_rows


def test_partition_uses_utc_month_of_valid_at(tmp_path):
    # 2024-07-01 00:00 IST is 2024-06-30 18:30 UTC, so it lands in the June partition.
    files = write_partitioned(table(fixture_rows()[:1]), tmp_path)
    assert files[0].path.startswith("S02/state=ka/year=2024/month=06/")


def test_rewrite_is_idempotent(tmp_path):
    a = write_partitioned(mixed_table(), tmp_path)
    before = snapshot_hashes(tmp_path)
    b = write_partitioned(mixed_table(), tmp_path)
    assert a == b and snapshot_hashes(tmp_path) == before


def test_shards_and_row_groups_respect_targets(tmp_path, monkeypatch):
    big = table(fixture_rows() * 50)
    monkeypatch.setattr(store_mod, "SHARD_BYTES", big.nbytes // 4)
    monkeypatch.setattr(store_mod, "ROW_GROUP_BYTES", big.nbytes // 16)
    files = write_partitioned(big, tmp_path)
    july = [f for f in files if "month=07" in f.path]
    assert len(july) > 1  # split into several shards
    assert pq.ParquetFile(tmp_path / july[0].path).metadata.num_row_groups > 1
    assert sum(f.rows for f in files) == big.num_rows


# --- manifests -------------------------------------------------------------------------------


def test_publish_sets_current_and_revision_is_not_observation_time(tmp_path):
    ms, manifest, _ = published(tmp_path)
    current = ms.current()
    assert current == manifest
    assert current.data_revision == data_revision(manifest.files)
    assert current.published_at == PUBLISHED
    assert current.parent_release_id is None


def test_failed_upload_leaves_current_manifest_unchanged(tmp_path):
    ms, first, clean = published(tmp_path)
    pointer_before = (tmp_path / "manifests" / "latest.json").read_text()

    def broken_upload(manifest):
        raise ConnectionError("Hugging Face upload failed")

    files = write_partitioned(table(fixture_rows()[:2]), clean)
    second = ms.build("r2", files, published_at=PUBLISHED + timedelta(days=1))
    with pytest.raises(ConnectionError):
        ms.publish(second, upload=broken_upload)
    assert ms.current() == first
    assert (tmp_path / "manifests" / "latest.json").read_text() == pointer_before


def test_retains_two_previous_and_never_deletes_old_manifests(tmp_path):
    ms, _, clean = published(tmp_path, "r1")
    files = write_partitioned(mixed_table(), clean)
    for rid in ("r2", "r3", "r4"):
        ms.publish(ms.build(rid, files, published_at=PUBLISHED))
    assert ms.current().release_id == "r4"
    assert ms.history() == ["r3", "r2"]
    assert (tmp_path / "manifests" / "r1.json").exists()  # history is never deleted
    assert ms.rollback() == "r3" and ms.current().release_id == "r3"


def test_publish_rejects_tampered_file(tmp_path):
    clean = tmp_path / "clean"
    files = write_partitioned(mixed_table(), clean)
    ms = ManifestStore(tmp_path / "manifests", clean)
    (clean / files[0].path).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="do not match"):
        ms.publish(ms.build("r1", files, published_at=PUBLISHED))
    assert ms.current() is None


# --- quota -----------------------------------------------------------------------------------


def test_quota_stop_preserves_all_existing_snapshots(tmp_path):
    ms, _, clean = published(tmp_path)
    roots = (clean, tmp_path / "manifests")
    used = StorageQuota(roots, 1, 0.8, 0.95).used()
    full = StorageQuota(roots, budget_bytes=int(used / 0.96), warn_at=0.8, stop_at=0.95)
    assert full.status() == "archive_only"
    before = snapshot_hashes(tmp_path)

    with pytest.raises(ArchiveOnly, match="Existing snapshots are kept"):
        write_partitioned(table(fixture_rows()[:1]), clean, quota=full)
    raw = RawStore(tmp_path / "raw", quota=full)
    with pytest.raises(ArchiveOnly):
        raw.put(b"new raw bytes", "S02", PUBLISHED, "json")

    assert snapshot_hashes(tmp_path) == before  # nothing deleted, nothing changed
    assert ms.current().release_id == "r1"


def test_quota_warn_status_still_allows_ingest(tmp_path):
    _, _, clean = published(tmp_path)
    used = StorageQuota((clean,), 1, 0.8, 0.95).used()
    warn = StorageQuota((clean,), budget_bytes=int(used / 0.85), warn_at=0.8, stop_at=0.95)
    assert warn.status() == "warn"
    assert warn.ensure_can_ingest(0) == "warn"


def test_storage_budget_thresholds_must_be_ordered():
    with pytest.raises(ValidationError):
        StorageBudget(
            preflight_min_free_gb=20,
            archive_budget_gb=20,
            warn_at_fraction=0.95,
            stop_at_fraction=0.8,
        )


# --- rebuildable cache -----------------------------------------------------------------------


def test_rebuild_from_parquet_equals_original_counts(tmp_path):
    ms, manifest, clean = published(tmp_path)
    original = mixed_table()
    expected = {
        s: sum(1 for x in original["source_id"].to_pylist() if x == s)
        for s in set(original["source_id"].to_pylist())
    }
    db = tmp_path / "cache" / "atlas.duckdb"
    assert rebuild_cache(manifest, clean, db, DUCK) == expected
    assert rebuild_cache(manifest, clean, db, DUCK) == expected  # repeatable
    assert sum(expected.values()) == sum(f.rows for f in manifest.files)


def test_failed_rebuild_keeps_old_cache(tmp_path):
    _, manifest, clean = published(tmp_path)
    db = tmp_path / "cache" / "atlas.duckdb"
    rebuild_cache(manifest, clean, db, DUCK)
    old = db.read_bytes()
    (clean / manifest.files[0].path).write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        rebuild_cache(manifest, clean, db, DUCK)
    assert db.read_bytes() == old


# --- usage ledger and CLI --------------------------------------------------------------------


def test_ledger_totals_and_cli_check(tmp_path):
    ledger = QuotaLedger(tmp_path / "data" / "quota" / "ledger.jsonl")
    day = datetime(2026, 11, 5, 3, 0, tzinfo=UTC)
    ledger.record("open_meteo", "calls", 1500, at=day)
    ledger.record("open_meteo", "calls", 400, at=day + timedelta(hours=1))
    ledger.record("open_meteo", "calls", 999, at=day - timedelta(days=1))  # other day
    with open(ledger.path, "a", encoding="utf-8") as f:
        f.write('{"at": "2026-11-05T09')  # torn line
    assert ledger.totals(day.date())[("open_meteo", "calls")] == 1900

    runner = CliRunner()
    args = ["quota", "--check", "--data-root", str(tmp_path / "data"), "--budgets",
            str(ROOT / "configs/budgets.yaml"), "--day", "2026-11-05"]  # fmt: skip
    ok = runner.invoke(app, args)
    assert ok.exit_code == 0, ok.output
    report = json.loads(ok.output[: ok.output.rindex("}") + 1])
    assert report["storage_status"] == "ok"

    ledger.record("open_meteo", "calls", 200, at=day)  # 2100 > 2000/day cap
    over = runner.invoke(app, args)
    assert over.exit_code == 3


def test_ledger_rejects_non_utc_time(tmp_path):
    from datetime import timezone

    with pytest.raises(ValueError, match="UTC"):
        QuotaLedger(tmp_path / "l.jsonl").record(
            "open_meteo", "calls", 1, at=datetime(2026, 11, 5, tzinfo=timezone(timedelta(hours=5)))
        )


def test_envelope_types_survive_parquet(tmp_path):
    files = write_partitioned(mixed_table(), tmp_path)
    back = pq.read_table(tmp_path / files[0].path)
    assert back.schema.field("valid_at").type == pa.timestamp("us", tz="UTC")
