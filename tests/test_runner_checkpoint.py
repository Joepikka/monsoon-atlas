"""T243 commits and resumes immutable feed state through a local catalogue."""

import importlib
import json
import shutil
import sqlite3
import sys
from contextlib import closing, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from atlas.config import load_budgets
from atlas.data.budget import GB, ArchiveOnly, bytes_used
from atlas.ingest import checkpoint_bundle
from atlas.ingest.base import IngestError
from atlas.ingest.s01_collect import collect_weather
from atlas.ingest.s01_prepare import prepare_weather
from atlas.ingest.schedule import defer, open_control

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"
NOW = datetime(2026, 11, 5, 14, tzinfo=UTC)


@pytest.fixture
def runner(tmp_path, monkeypatch):
    disk = shutil.disk_usage(tmp_path)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: disk._replace(free=100 * GB))
    return importlib.import_module("atlas.ingest.runner_checkpoint")


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "feeds"
    with closing(open_control(path / "control.sqlite")):
        pass
    return path


def weather(request):
    name = (
        "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json"
        if request.url.path.endswith("meta.json")
        else "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json"
    )
    return httpx.Response(
        200, content=(FIXTURES / name).read_bytes(), headers={"content-type": "application/json"}
    )


def no_provider(request):
    pytest.fail(f"Restored cooldown let a request reach {request.url.host}")


def fingerprint(path):
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def set_cooldown(root):
    with closing(open_control(root / "control.sqlite")) as db:
        defer(db, "S01", (NOW + timedelta(hours=8)).timestamp())


def test_two_generations_resume_exact_fixture_state_and_cooldown(runner, root, tmp_path):
    store = tmp_path / "persistent"
    assert (
        collect_weather(
            root, transport=httpx.MockTransport(weather), clock=lambda: NOW, sleep=lambda _: None
        )["status"]
        == "captured"
    )
    prepared = prepare_weather(root, as_of=NOW)
    original = fingerprint(root)
    first = runner.commit_checkpoint(root, store, expected_head=None)

    root.rename(tmp_path / "first-workspace")
    assert runner.resume_checkpoint(root, store) == first
    assert fingerprint(root) == original
    assert prepare_weather(root, as_of=NOW)["sha256"] == prepared["sha256"]

    set_cooldown(root)
    latest = fingerprint(root)
    second = runner.commit_checkpoint(root, store, expected_head=first)
    assert second != first
    assert {p.name for p in (store / "objects").iterdir()} == {first, second}
    root.rename(tmp_path / "second-workspace")
    assert runner.resume_checkpoint(root, store) == second
    assert fingerprint(root) == latest
    assert (
        collect_weather(
            root,
            transport=httpx.MockTransport(no_provider),
            clock=lambda: NOW + timedelta(hours=7),
            sleep=lambda _: None,
        )["status"]
        == "deferred"
    )
    assert fingerprint(store / "objects" / first / "files") == original


def test_unchanged_is_idempotent_and_stale_writer_is_rejected_before_copy(
    runner, root, tmp_path, monkeypatch
):
    store = tmp_path / "persistent"
    first = runner.commit_checkpoint(root, store, expected_head=None)
    assert runner.commit_checkpoint(root, store, expected_head=first) == first
    assert [p.name for p in (store / "objects").iterdir()] == [first]

    def unexpected(*args, **kwargs):
        pytest.fail("A stale writer began copying")

    monkeypatch.setattr(checkpoint_bundle, "save_checkpoint", unexpected)
    for stale in (None, "a" * 64):
        with pytest.raises(IngestError, match="head"):
            runner.commit_checkpoint(root, store, expected_head=stale)
    root.rename(tmp_path / "old")
    assert runner.resume_checkpoint(root, store) == first


def test_failed_catalogue_advance_keeps_prior_head_and_retry_reuses_verified_object(
    runner, root, tmp_path, monkeypatch
):
    store = tmp_path / "persistent"
    first = runner.commit_checkpoint(root, store, expected_head=None)
    set_cooldown(root)
    lock = runner._locked_catalogue

    @contextmanager
    def interrupted(*args, **kwargs):
        with lock(*args, **kwargs) as db:
            yield db
            raise OSError("injected interruption before commit")

    with monkeypatch.context() as patch:
        patch.setattr(runner, "_locked_catalogue", interrupted)
        with pytest.raises(OSError, match="injected interruption"):
            runner.commit_checkpoint(root, store, expected_head=first)
    (orphan,) = {p.name for p in (store / "objects").iterdir()} - {first}
    newer = root.rename(tmp_path / "newer")
    assert runner.resume_checkpoint(root, store) == first
    root.rename(tmp_path / "earlier")
    newer.rename(root)
    assert runner.commit_checkpoint(root, store, expected_head=first) == orphan
    assert {p.name for p in (store / "objects").iterdir()} == {first, orphan}
    root.rename(tmp_path / "latest")
    assert runner.resume_checkpoint(root, store) == orphan


@pytest.mark.parametrize("damage", ["catalogue", "object", "member", "digest"])
def test_invalid_store_leaves_missing_target_absent(runner, root, tmp_path, damage):
    store = tmp_path / "persistent"
    digest = runner.commit_checkpoint(root, store, expected_head=None)
    prior = fingerprint(root)
    held = root.rename(tmp_path / "held")
    if damage == "catalogue":
        (store / "catalog.sqlite").rename(store / "catalog.held")
    elif damage == "object":
        (store / "objects" / digest).rename(store / "object.held")
    elif damage == "digest":
        with closing(sqlite3.connect(store / "catalog.sqlite")) as db, db:
            db.execute("UPDATE current_checkpoint SET digest='../invalid'")
    else:
        control = store / "objects" / digest / "files/control.sqlite"
        with control.open("r+b") as stream:
            stream.write(b"Corrupt")
    with pytest.raises((IngestError, OSError, sqlite3.Error)):
        runner.resume_checkpoint(root, store)
    assert not root.exists()
    assert fingerprint(held) == prior
    if damage == "catalogue":
        assert not (store / "catalog.sqlite").exists()


def test_bootstrap_cannot_replace_lost_catalogue_beside_objects(runner, root, tmp_path):
    store = tmp_path / "persistent"
    digest = runner.commit_checkpoint(root, store, expected_head=None)
    catalog = store / "catalog.sqlite"
    catalog.rename(tmp_path / "held-catalogue")
    with pytest.raises(IngestError, match="catalogue"):
        runner.commit_checkpoint(root, store, expected_head=None)
    assert not catalog.exists()
    assert {p.name for p in (store / "objects").iterdir()} == {digest}


def test_store_lock_serializes_commit_and_resume(runner, root, tmp_path):
    store = tmp_path / "persistent"
    first = runner.commit_checkpoint(root, store, expected_head=None)
    with closing(sqlite3.connect(store / "catalog.sqlite")) as db, db:
        db.execute("BEGIN IMMEDIATE")
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            runner.commit_checkpoint(root, store, expected_head=first)
        root.rename(tmp_path / "held")
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            runner.resume_checkpoint(root, store)
    assert runner.resume_checkpoint(root, store) == first


def test_wrong_root_and_nested_store_are_refused(runner, root, tmp_path):
    with pytest.raises(IngestError, match="disjoint"):
        runner.commit_checkpoint(root, root / "nested", expected_head=None)
    store = tmp_path / "persistent"
    first = runner.commit_checkpoint(root, store, expected_head=None)
    with pytest.raises(IngestError):
        runner.resume_checkpoint(root, store)
    other = tmp_path / "other"
    with pytest.raises(IngestError):
        runner.resume_checkpoint(other, store)
    with closing(open_control(other / "control.sqlite")):
        pass
    with pytest.raises(IngestError, match="root"):
        runner.commit_checkpoint(other, store, expected_head=first)


def test_quota_counts_all_stored_generations_before_staging(runner, root, tmp_path, monkeypatch):
    store = tmp_path / "persistent"
    first = runner.commit_checkpoint(root, store, expected_head=None)
    set_cooldown(root)
    second = runner.commit_checkpoint(root, store, expected_head=first)
    budget = load_budgets(ROOT / "configs/budgets.yaml")
    single_copy_allowance = (
        bytes_used([root])
        + 2 * bytes_used([store / "objects" / second])
        + (store / "catalog.sqlite").stat().st_size
        + 8192  # Head update journal margin. A single retained bundle fits.
    )
    budget = budget.model_copy(
        update={
            "storage": budget.storage.model_copy(
                update={
                    "archive_budget_gb": single_copy_allowance
                    / GB
                    / budget.storage.stop_at_fraction
                }
            )
        }
    )
    monkeypatch.setattr(checkpoint_bundle, "ROOT", tmp_path)
    monkeypatch.setattr(checkpoint_bundle, "load_budgets", lambda _: budget)
    with pytest.raises(ArchiveOnly):
        runner.commit_checkpoint(root, store, expected_head=second)
    assert {p.name for p in (store / "objects").iterdir()} == {first, second}


def test_bootstrap_quota_counts_pending_catalogue_before_install(
    runner, root, tmp_path, monkeypatch
):
    store = tmp_path / "persistent"
    budget = load_budgets(ROOT / "configs/budgets.yaml")
    stop_bytes = 2 * bytes_used([root]) + 4096
    storage = budget.storage.model_copy(
        update={"archive_budget_gb": stop_bytes / GB / budget.storage.stop_at_fraction}
    )
    monkeypatch.setattr(checkpoint_bundle, "ROOT", tmp_path)
    monkeypatch.setattr(
        checkpoint_bundle, "load_budgets", lambda _: budget.model_copy(update={"storage": storage})
    )
    with pytest.raises(ArchiveOnly):
        runner.commit_checkpoint(root, store, expected_head=None)
    assert not list((store / "objects").iterdir())


def test_command_reports_head_for_the_next_run(runner, root, tmp_path, monkeypatch, capsys):
    store = tmp_path / "persistent"
    argv = ["runner_checkpoint", "runner-save", "--root", str(root), "--store", str(store)]
    monkeypatch.setattr(sys, "argv", argv + ["--expected-head", "empty"])
    runner.main()
    saved = json.loads(capsys.readouterr().out)
    assert saved["status"] == "saved"
    root.rename(tmp_path / "held")
    monkeypatch.setattr(sys, "argv", [argv[0], "runner-restore", *argv[2:]])
    runner.main()
    assert json.loads(capsys.readouterr().out) == {
        "status": "restored",
        "manifest_sha256": saved["manifest_sha256"],
    }
