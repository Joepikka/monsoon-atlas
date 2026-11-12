"""T244 composes verified runner recovery with real fixture capture."""

import gzip
import importlib
import json
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from atlas.data.budget import GB, ArchiveOnly
from atlas.ingest.admission import capture_admitted
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.runner_checkpoint import commit_checkpoint, resume_checkpoint
from atlas.ingest.schedule import open_control, run_bounded
from atlas.ingest.upload import upload_local

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ORIGIN = "http://127.0.0.1:8787"
NOW = datetime(2026, 11, 5, 14, tzinfo=UTC)
KEY = "local-runner-cycle-test-signing-key"


@pytest.fixture
def state(tmp_path, monkeypatch):
    cycle = importlib.import_module("atlas.ingest.runner_cycle")
    monkeypatch.setenv("ATLAS_INGEST_HMAC_KEY", KEY)
    disk = shutil.disk_usage(tmp_path)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: disk._replace(free=100 * GB))
    root, store = tmp_path / "feeds", tmp_path / "store"
    with closing(open_control(root / "control.sqlite")):
        pass
    digest = commit_checkpoint(root, store, expected_head=None)
    root.rename(tmp_path / "held-initial")
    return cycle, root, store, digest


def worker(admitted):
    value = {"state": "ka", "source_id": "S01", "admitted": admitted}
    if not admitted:
        value["reason"] = "not_due"
    return httpx.Response(201 if admitted else 200, json=value)


def weather(request):
    name = (
        "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json"
        if request.url.path.endswith("meta.json")
        else "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json"
    )
    return httpx.Response(
        200, content=(FIXTURES / name).read_bytes(), headers={"content-type": "application/json"}
    )


def unexpected(*args, **kwargs):
    pytest.fail("Unexpected capture, provider request or checkpoint save")


def connect_capture(monkeypatch, cycle, root, provider, *, admitted=True, now=NOW):
    def capture(path, **options):
        assert path == root and (root / "control.sqlite").is_file()
        return capture_admitted(
            path,
            **options,
            admission_transport=httpx.MockTransport(lambda _: worker(admitted)),
            provider_transport=httpx.MockTransport(provider),
            clock=lambda: now,
            sleep=lambda _: None,
        )

    monkeypatch.setattr(cycle, "capture_admitted", capture)


def run(state, **kwargs):
    cycle, root, store, _ = state
    return cycle.run_cycle(root, store, source_id="S01", origin=ORIGIN, **kwargs)


@pytest.mark.parametrize("outcome", ["captured", "deferred", "failed"])
def test_cycle_saves_capture_and_guard_even_after_handled_failure(state, monkeypatch, outcome):
    cycle, root, store, prior = state

    def provider(request):
        if outcome == "captured":
            return weather(request)
        if outcome == "deferred":
            return httpx.Response(429, headers={"Retry-After": "28800"})
        return httpx.Response(404)

    connect_capture(monkeypatch, cycle, root, provider)
    result = run(state)
    assert result["status"] == outcome, result
    assert result["restored_sha256"] == prior
    current = result["manifest_sha256"]
    assert current != prior
    if outcome == "captured":
        assert result["capture"]["http_attempts"] == 3
        assert (root / "weather/latest-pair.json").is_file()
    working = root.rename(root.parent / "held-result")

    # A new cycle sees the persisted local guard even when Worker grants admission.
    connect_capture(monkeypatch, cycle, root, unexpected, now=NOW + timedelta(minutes=1))
    following = run(state)
    assert following["status"] == ("deferred" if outcome == "deferred" else "not_due")
    assert following["capture"]["stage"] == "capture"
    assert following["restored_sha256"] == current
    assert (working / "control.sqlite").read_bytes() == (root / "control.sqlite").read_bytes()
    assert (store / "objects" / prior).is_dir()


def test_worker_denial_reuses_restored_generation_without_save(state, monkeypatch):
    cycle, root, store, prior = state
    connect_capture(monkeypatch, cycle, root, unexpected, admitted=False)
    monkeypatch.setattr(cycle, "commit_checkpoint", unexpected)
    result = run(state)
    assert result["status"] == "not_due"
    assert result["manifest_sha256"] == prior
    assert [p.name for p in (store / "objects").iterdir()] == [prior]


@pytest.mark.parametrize("damage", ["existing", "corrupt", "missing", "key"])
def test_preflight_or_restore_failure_never_calls_capture(state, monkeypatch, damage):
    cycle, root, store, prior = state
    monkeypatch.setattr(cycle, "capture_admitted", unexpected)
    if damage == "existing":
        root.mkdir()
        (root / "keep.txt").write_text("retain", encoding="utf-8")
    elif damage == "corrupt":
        path = store / "objects" / prior / "files/control.sqlite"
        with path.open("r+b") as stream:
            stream.write(b"Damaged")
    elif damage == "missing":
        (store / "catalog.sqlite").rename(store / "held-catalogue")
    else:
        monkeypatch.delenv("ATLAS_INGEST_HMAC_KEY")
    result = run(state)
    assert result["status"] == "failed"
    assert result["stage"] == ("preflight" if damage == "key" else "restore")
    assert root.exists() == (damage == "existing")
    if damage == "existing":
        assert (root / "keep.txt").read_text(encoding="utf-8") == "retain"


@pytest.mark.parametrize("with_upload", [False, True])
def test_commit_refusal_preserves_working_state_and_prior_head(state, monkeypatch, with_upload):
    cycle, root, store, prior = state
    connect_capture(monkeypatch, cycle, root, weather)
    fixed_cutoff(monkeypatch, cycle)
    if with_upload:
        monkeypatch.setattr(cycle, "upload_local", unexpected, raising=False)

    def refuse(path, target, *, expected_head):
        assert (path, target, expected_head) == (root, store, prior)
        raise ArchiveOnly("simulated storage stop")

    monkeypatch.setattr(cycle, "commit_checkpoint", refuse)
    result = run(state, upload=with_upload) if with_upload else run(state)
    assert result["status"] == "failed" and result["stage"] == "checkpoint"
    assert result["restored_sha256"] == prior
    assert result["capture"]["status"] == "captured"
    assert "manifest_sha256" not in result
    assert (root / "weather/latest-pair.json").is_file()
    root.rename(root.parent / "recoverable-working-state")
    assert resume_checkpoint(root, store) == prior


def fixed_cutoff(monkeypatch, cycle):
    class Clock:
        @staticmethod
        def now(timezone):
            assert timezone == UTC
            return NOW

    monkeypatch.setattr(cycle, "datetime", Clock, raising=False)


def test_upload_starts_after_checkpoint_and_not_due_retries_exact_bytes(state, monkeypatch):
    cycle, root, store, prior = state
    connect_capture(monkeypatch, cycle, root, weather)
    fixed_cutoff(monkeypatch, cycle)
    sent = []

    def sender(frozen, **options):
        with closing(sqlite3.connect(store / "catalog.sqlite")) as db:
            (digest,) = db.execute("SELECT digest FROM current_checkpoint").fetchone()
        assert digest != prior and frozen == store / "objects" / digest / "files"

        def worker_upload(request):
            assert request.url.path == "/internal/ingest"
            sent.append(request.content)
            envelope = json.loads(gzip.decompress(request.content))
            assert envelope["source_id"] == "S01"
            assert envelope["snapshot"]["as_of"] == "2026-11-05T14:00:00Z"
            assert envelope["snapshot"]["records"][0]["provenance"] == "model"
            if len(sent) == 1:
                raise httpx.ReadTimeout("lost acknowledgement", request=request)
            return httpx.Response(200, json={"status": "unchanged", "snapshot_id": "a" * 64})

        return upload_local(frozen, **options, transport=httpx.MockTransport(worker_upload))

    monkeypatch.setattr(cycle, "upload_local", sender, raising=False)
    failed = run(state, upload=True)
    assert (failed["status"], failed["stage"]) == ("failed", "upload")
    assert failed["prepare"]["status"] == "prepared"
    assert failed["manifest_sha256"] != prior
    root.rename(root.parent / "held-upload-result")

    connect_capture(monkeypatch, cycle, root, unexpected, admitted=False)
    monkeypatch.setattr(cycle, "prepare_weather", unexpected, raising=False)
    retried = run(state, upload=True)
    assert (retried["status"], retried["stage"]) == ("unchanged", "upload")
    assert retried["manifest_sha256"] == failed["manifest_sha256"]
    assert len(sent) == 2 and sent[0] == sent[1]


def test_preparation_failure_saves_capture_without_upload(state, monkeypatch):
    cycle, root, store, prior = state
    connect_capture(monkeypatch, cycle, root, weather)

    def unavailable(*args, **kwargs):
        raise SourceUnavailable("simulated unusable projection")

    monkeypatch.setattr(cycle, "prepare_weather", unavailable, raising=False)
    monkeypatch.setattr(cycle, "upload_local", unexpected, raising=False)
    failed = run(state, upload=True)
    assert (failed["status"], failed["stage"]) == ("failed", "prepare")
    assert failed["capture"]["status"] == "captured"
    assert failed["manifest_sha256"] != prior
    root.rename(root.parent / "held-unprepared")
    connect_capture(monkeypatch, cycle, root, unexpected, admitted=False)
    following = run(state, upload=True)
    assert following["status"] == "not_due"
    assert following["manifest_sha256"] == failed["manifest_sha256"]
    assert (root / "weather/latest-pair.json").is_file()


def test_timeout_reaps_child_and_keeps_in_progress_root(state, tmp_path, monkeypatch):
    cycle, root, store, prior = state
    # Run the real no-descendant launcher with a shorter test deadline.
    child = tmp_path / "slow_cycle.py"
    child.write_text(
        "import sys, time\n"
        "import shutil\n"
        "usage = shutil.disk_usage('.')\n"
        "shutil.disk_usage = lambda _: usage._replace(free=100 * 1024**3)\n"
        "from pathlib import Path\n"
        "from atlas.ingest import runner_cycle as cycle\n"
        "from atlas.ingest.schedule import defer, open_control\n"
        "from contextlib import closing\n"
        "def pause(root, **kwargs):\n"
        "    with closing(open_control(root / 'control.sqlite')) as db:\n"
        "        defer(db, 'S01', 1793890000)\n"
        "    time.sleep(60)\n"
        "cycle.capture_admitted = pause\n"
        "cycle.run_cycle(Path(sys.argv[1]), Path(sys.argv[2]), source_id='S01', "
        f"origin={ORIGIN!r})\n",
        encoding="utf-8",
    )
    assert run_bounded([sys.executable, str(child), str(root), str(store)], timeout=10)[
        "status"
    ] == ("deadline")
    assert root.exists()
    assert (root / "control.sqlite").read_bytes() != (
        store / "objects" / prior / "files/control.sqlite"
    ).read_bytes()
    monkeypatch.setattr(cycle, "capture_admitted", unexpected)
    assert run(state)["stage"] == "restore"
    assert [p.name for p in (store / "objects").iterdir()] == [prior]


def test_cli_runs_one_bounded_child_and_keeps_key_out_of_arguments(state, monkeypatch, capsys):
    cycle, root, store, _ = state
    command = []

    def deadline(args, *, timeout):
        command.extend(args)
        assert timeout == 150
        return {"status": "deadline", "coverage": "partial"}

    monkeypatch.setattr(cycle, "run_bounded", deadline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "runner-cycle",
            "--root",
            str(root),
            "--store",
            str(store),
            "--origin",
            ORIGIN,
            "--source",
            "S01",
            "--upload-local",
        ],
    )
    with pytest.raises(SystemExit, match="1"):
        cycle.main()
    assert command[:4] == [sys.executable, "-m", "atlas.ingest.runner_cycle", "--child"]
    assert command.count("--upload-local") == 1
    assert KEY not in repr(command)
    assert json.loads(capsys.readouterr().out)["status"] == "deadline"
