"""T241 restores exact retained local feed evidence at its original path."""

import hashlib
import importlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from atlas.data.budget import ArchiveOnly, StorageQuota
from atlas.ingest.base import IngestError
from atlas.ingest.s01_collect import collect_weather
from atlas.ingest.s01_prepare import prepare_weather
from atlas.ingest.s09 import FEED
from atlas.ingest.s09_collect import collect
from atlas.ingest.s09_prepare import prepare
from atlas.ingest.schedule import open_control

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"
CUTOFF = datetime(2026, 11, 5, 14, tzinfo=UTC)
CAP = "1793881986295019"
REAL_DISK_USAGE = shutil.disk_usage


@pytest.fixture(autouse=True)
def reserve_available(monkeypatch, tmp_path):
    usage = REAL_DISK_USAGE(tmp_path)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: usage._replace(free=100 * 1024**3))


def checkpoint():
    return importlib.import_module("atlas.ingest.checkpoint_bundle")


def weather(request):
    metadata = request.url.path.endswith("meta.json")
    fixture = (
        "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json"
        if metadata
        else "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json"
    )
    return httpx.Response(
        200, content=(FIXTURES / fixture).read_bytes(), headers={"content-type": "application/json"}
    )


def cap(request):
    if str(request.url) == FEED:
        # Limit the fixture replay to a retained CAP document. Its bytes stay exact.
        feed = ET.fromstring((FIXTURES / "s09_sachet_rss_india_2026-11-05.xml").read_bytes())
        channel = feed.find("channel")
        for item in channel.findall("item"):
            if not item.findtext("link").endswith(CAP):
                channel.remove(item)
        body = ET.tostring(feed)
    else:
        body = (FIXTURES / f"s09_sachet_cap_{request.url.params['identifier']}.xml").read_bytes()
    return httpx.Response(
        200, content=body, headers={"content-type": "application/xml", "etag": '"retained-fixture"'}
    )


def unchanged_cap(request):
    assert request.headers["if-none-match"] == '"retained-fixture"'
    return httpx.Response(304)


def replay(collector, root, when, handler):
    return collector(
        root, transport=httpx.MockTransport(handler), clock=lambda: when, sleep=lambda _: None
    )


@pytest.fixture
def feed(tmp_path):
    root = tmp_path / "feeds"
    assert replay(collect, root, CUTOFF, cap)["validated"] == 1
    assert replay(collect_weather, root, CUTOFF, weather)["status"] == "captured"
    prepare(root / "raw", root / "prepared", as_of=CUTOFF)
    prepare_weather(root, as_of=CUTOFF)

    def partial_weather(request):
        if request.url.path.endswith("meta.json"):
            return weather(request)
        return httpx.Response(429, headers={"retry-after": "7200"})

    when = CUTOFF + timedelta(hours=6)
    result = replay(collect_weather, root, when, partial_weather)
    assert result["status"] == "deferred" and result["http_attempts"] == 2
    return root


@pytest.fixture
def control_only(tmp_path):
    root = tmp_path / "feeds"
    with closing(open_control(root / "control.sqlite")):
        pass
    return root


def contents(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def rewrite_manifest(bundle, change):
    path = bundle / "manifest.json"
    manifest = json.loads(path.read_bytes())
    change(manifest["files"])
    encoded = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest()


def no_provider(_):
    pytest.fail("Restored admission should deny this provider request")


def test_round_trip_recovers_capture_history_prepared_bytes_and_admission(feed, tmp_path):
    api = checkpoint()
    cap_cutoff = CUTOFF + timedelta(minutes=1)
    prepare(feed / "raw", feed / "prepared", as_of=cap_cutoff)
    before = contents(feed)
    assert len([p for p in before if p.startswith("weather/pairs/")]) == 2
    assert len([p for p in before if p.startswith("prepared/") and p.endswith(".inputs.json")]) == 2
    (feed / ".env").write_text("unrelated operator file", encoding="utf-8")
    (feed / "prepared/.tmp-interrupted.json").write_text("partial", encoding="utf-8")
    bundle = tmp_path / "bundle"
    digest = api.save_checkpoint(feed, bundle)
    assert digest == hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    assert contents(bundle / "files") == before
    assert api.save_checkpoint(feed, tmp_path / "second-bundle") == digest

    prior = feed.rename(tmp_path / "held-aside")
    api.restore_checkpoint(feed, bundle, digest)
    assert contents(feed) == before
    assert contents(prior)[".env"] == b"unrelated operator file"
    for result in (
        prepare(feed / "raw", feed / "prepared", as_of=cap_cutoff),
        prepare_weather(feed, as_of=CUTOFF),
    ):
        payload = Path(result["payload_path"]).relative_to(feed).as_posix()
        assert Path(result["payload_path"]).read_bytes() == before[payload]
        assert result["records"] > 0
    assert replay(collect, feed, CUTOFF + timedelta(minutes=14), no_provider)["status"] == "not_due"
    assert (
        replay(collect_weather, feed, CUTOFF + timedelta(hours=7), no_provider)["status"]
        == "deferred"
    )
    assert (
        replay(collect_weather, feed, CUTOFF + timedelta(hours=8), no_provider)["status"]
        == "not_due"
    )


@pytest.mark.parametrize("damage", ["manifest", "bytes", "missing", "extra", "traversal", "alias"])
def test_restore_refuses_damaged_bundle(control_only, tmp_path, damage):
    api = checkpoint()
    bundle = tmp_path / "bundle"
    digest = api.save_checkpoint(control_only, bundle)
    before = control_only.rename(tmp_path / "held-aside")
    control = bundle / "files/control.sqlite"
    if damage == "manifest":
        with (bundle / "manifest.json").open("ab") as stream:
            stream.write(b"\n")
    elif damage == "bytes":
        with control.open("r+b") as stream:
            stream.write(b"Damage")
    elif damage == "missing":
        control.unlink()
    elif damage == "extra":
        (control.parent / ".env").write_text("unexpected", encoding="utf-8")
    else:
        name = "../control.sqlite" if damage == "traversal" else "Control.sqlite"
        digest = rewrite_manifest(bundle, lambda files: files[0].update(path=name))

    with pytest.raises(IngestError):
        api.restore_checkpoint(control_only, bundle, digest)
    assert not control_only.exists()
    assert (before / "control.sqlite").is_file()


@pytest.mark.parametrize("missing", ["control", "cap", "ledger", "weather", "pair", "prepared"])
def test_consistent_manifest_cannot_hide_missing_authoritative_evidence(feed, tmp_path, missing):
    api = checkpoint()
    bundle = tmp_path / "bundle"
    api.save_checkpoint(feed, bundle)
    pair = json.loads((feed / "weather/latest-pair.json").read_bytes())["path"]
    if missing == "control":
        name = "control.sqlite"
    elif missing == "cap":
        with closing(sqlite3.connect(feed / "control.sqlite")) as db:
            artifact = db.execute("SELECT artifact_json FROM cap_documents").fetchone()[0]
        name = Path(json.loads(artifact)["path"]).relative_to(feed).as_posix()
    elif missing == "ledger":
        name = "raw/ledger.jsonl"
    elif missing == "weather":
        receipt = json.loads((feed / pair).read_bytes())
        name = Path(receipt["requests"][1]["artifact"]["path"]).relative_to(feed).as_posix()
    elif missing == "pair":
        name = pair
    else:
        name = "prepared/" + json.loads((feed / "prepared/prepared.json").read_bytes())["inputs"]
    removed = bundle / "files" / name
    removed.unlink()
    while not any(removed.parent.iterdir()):
        removed = removed.parent
        removed.rmdir()

    def omit(files):
        files[:] = [entry for entry in files if entry["path"] != name]

    digest = rewrite_manifest(bundle, omit)
    feed.rename(tmp_path / "held-aside")
    with pytest.raises(IngestError):
        api.restore_checkpoint(feed, bundle, digest)
    assert not feed.exists()


def test_original_absent_destination_is_required(control_only, tmp_path):
    api = checkpoint()
    bundle = tmp_path / "bundle"
    before = contents(control_only)
    digest = api.save_checkpoint(control_only, bundle)
    with pytest.raises(IngestError):
        api.save_checkpoint(control_only, bundle)
    with pytest.raises(IngestError):
        api.save_checkpoint(control_only, control_only / "nested-bundle")
    with pytest.raises(IngestError):
        api.restore_checkpoint(control_only, bundle, digest)
    with pytest.raises(IngestError):
        api.restore_checkpoint(tmp_path / "different-path", bundle, digest)
    assert contents(control_only) == before
    assert contents(bundle / "files") == before


def test_hardlinked_source_or_bundle_member_is_refused(control_only, tmp_path):
    api = checkpoint()
    bundle = tmp_path / "bundle"
    original = control_only / "control.sqlite"
    os.link(original, tmp_path / "linked-control")
    with pytest.raises(IngestError):
        api.save_checkpoint(control_only, bundle)
    assert not bundle.exists()
    (tmp_path / "linked-control").unlink()
    digest = api.save_checkpoint(control_only, bundle)
    control_only.rename(tmp_path / "held-aside")
    os.link(bundle / "files/control.sqlite", tmp_path / "linked-member")
    with pytest.raises(IngestError):
        api.restore_checkpoint(control_only, bundle, digest)
    assert not control_only.exists()


def test_case_alias_in_source_cannot_hide_known_state(control_only, tmp_path):
    api = checkpoint()
    (control_only / "Prepared").mkdir()
    with pytest.raises(IngestError):
        api.save_checkpoint(control_only, tmp_path / "bundle")
    assert not (tmp_path / "bundle").exists()


def test_unclosed_sqlite_sidecar_is_refused(control_only, tmp_path):
    api = checkpoint()
    with closing(sqlite3.connect(control_only / "control.sqlite")) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("INSERT INTO local_admission(source) VALUES ('S09')")
        db.commit()
        assert (control_only / "control.sqlite-wal").exists()
        with pytest.raises(IngestError):
            api.save_checkpoint(control_only, tmp_path / "bundle")
    assert not (tmp_path / "bundle").exists()


def test_copied_database_must_pass_sqlite_integrity(control_only, tmp_path):
    api = checkpoint()
    bundle = tmp_path / "bundle"
    api.save_checkpoint(control_only, bundle)
    control_only.rename(tmp_path / "held-aside")
    damage = b"not a SQLite database"
    (bundle / "files/control.sqlite").write_bytes(damage)
    digest = rewrite_manifest(
        bundle,
        lambda files: files[0].update(bytes=len(damage), sha256=hashlib.sha256(damage).hexdigest()),
    )
    with pytest.raises(IngestError):
        api.restore_checkpoint(control_only, bundle, digest)
    assert not control_only.exists()


@pytest.mark.parametrize("status", [200, 304])
def test_checkpoint_refuses_retimed_cap_ledger(feed, tmp_path, status):
    api = checkpoint()
    cutoff = CUTOFF
    if status == 304:
        cutoff += timedelta(minutes=15)
        assert replay(collect, feed, cutoff, unchanged_cap)["validated"] == 1
        prepare(feed / "raw", feed / "prepared", as_of=cutoff)
    bundle = tmp_path / "bundle"
    api.save_checkpoint(feed, bundle)
    name = "raw/ledger.jsonl"
    ledger = feed / name
    before = ledger.read_bytes()
    entries = [json.loads(line) for line in before.splitlines()]
    artifact = next(
        entry["artifact"]
        for entry in entries
        if entry["artifact"]["source_url"].endswith(CAP)
        and entry["artifact"]["response_status"] == status
    )
    artifact["fetched_at"] = (cutoff + timedelta(seconds=1)).isoformat()
    changed = "".join(json.dumps(entry) + "\n" for entry in entries).encode()
    ledger.write_bytes(changed)

    with pytest.raises(IngestError):
        api.save_checkpoint(feed, tmp_path / "inconsistent")
    assert ledger.read_bytes() == changed
    ledger.write_bytes(before)
    (bundle / "files" / name).write_bytes(changed)

    def rehash(files):
        entry = next(entry for entry in files if entry["path"] == name)
        entry.update(bytes=len(changed), sha256=hashlib.sha256(changed).hexdigest())

    digest = rewrite_manifest(bundle, rehash)
    feed.rename(tmp_path / "held-aside")
    with pytest.raises(IngestError):
        api.restore_checkpoint(feed, bundle, digest)
    assert not feed.exists()


def test_checkpoint_retains_repeated_cap_bytes_on_new_day_and_304(feed, tmp_path):
    api = checkpoint()
    refetched = CUTOFF + timedelta(days=1)
    assert replay(collect, feed, refetched, cap)["validated"] == 1
    checked = refetched + timedelta(minutes=15)
    assert replay(collect, feed, checked, unchanged_cap)["validated"] == 1
    with closing(sqlite3.connect(feed / "control.sqlite")) as db:
        encoded = db.execute("SELECT artifact_json FROM cap_documents").fetchone()[0]
    artifact = json.loads(encoded)
    assert datetime.fromisoformat(artifact["fetched_at"]) == CUTOFF
    assert Path(artifact["path"]).parent.name == refetched.date().isoformat()
    assert artifact["response_status"] == 304
    prepared = prepare(feed / "raw", feed / "prepared", as_of=checked)
    manifest = json.loads(Path(prepared["inputs_path"]).read_bytes())
    assert datetime.fromisoformat(manifest["inputs"][0]["checked_at"]) == checked

    bundle = tmp_path / "bundle"
    digest = api.save_checkpoint(feed, bundle)
    prior = feed.rename(tmp_path / "held-aside")
    api.restore_checkpoint(feed, bundle, digest)
    assert contents(feed) == contents(prior)
    result = prepare(feed / "raw", feed / "prepared", as_of=checked)
    assert result["sha256"] == prepared["sha256"]


def test_checkpoint_refuses_cap_control_without_matching_origin_event(feed, tmp_path):
    api = checkpoint()
    with closing(sqlite3.connect(feed / "control.sqlite")) as db, db:
        encoded = db.execute("SELECT artifact_json FROM cap_documents").fetchone()[0]
        changed = json.loads(encoded)
        changed["fetched_at"] = (CUTOFF - timedelta(seconds=1)).isoformat()
        db.execute(
            "UPDATE cap_documents SET artifact_json=?,content_fetched_at=? WHERE identifier=?",
            (json.dumps(changed), changed["fetched_at"], CAP),
        )
    with pytest.raises(IngestError):
        api.save_checkpoint(feed, tmp_path / "inconsistent")


@pytest.mark.parametrize("failure", ["copy", "mutation", "quota", "space"])
def test_save_failure_never_publishes_or_leaves_staging(
    control_only, tmp_path, monkeypatch, failure
):
    api = checkpoint()
    original = control_only / "control.sqlite"
    bundle = tmp_path / "bundle"
    before = original.read_bytes()
    changed = before[:-1] + bytes([before[-1] ^ 1])
    actual_copy = api._copy_file

    def copy_file(source, destination, *args):
        if failure == "copy":
            destination.write_bytes(b"partial copy")
            raise OSError("simulated interruption")
        result = actual_copy(source, destination, *args)
        original.write_bytes(changed)
        return result

    def quota(*_):
        raise ArchiveOnly("test archive-only quota")

    if failure == "quota":
        monkeypatch.setattr(StorageQuota, "ensure_can_ingest", quota)
    elif failure == "space":
        usage = shutil.disk_usage(tmp_path)
        monkeypatch.setattr(shutil, "disk_usage", lambda _: usage._replace(free=0))
    else:
        monkeypatch.setattr(api, "_copy_file", copy_file)

    with pytest.raises((IngestError, OSError, ArchiveOnly)):
        api.save_checkpoint(control_only, bundle)
    assert set(tmp_path.iterdir()) == {control_only}
    assert original.read_bytes() == (changed if failure == "mutation" else before)


def test_checkpoint_cli_round_trip(control_only, tmp_path, monkeypatch, capsys):
    api = checkpoint()
    bundle = tmp_path / "bundle"
    powershell = shutil.which("powershell")
    args = ["--root", str(control_only), "--bundle", str(bundle)]

    def run(command, *options):
        if (
            powershell
            and (ROOT / ".venv/Scripts/python.exe").is_file()
            and REAL_DISK_USAGE(tmp_path).free >= 21 * 1024**3
        ):
            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-File",
                    str(ROOT / "scripts/feeds.ps1"),
                    command,
                    *args,
                    *options,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=ROOT,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            return json.loads(result.stdout)
        monkeypatch.setattr(sys, "argv", ["checkpoint_bundle", command, *args, *options])
        api.main()
        return json.loads(capsys.readouterr().out)

    saved = run("checkpoint-save")
    assert saved["status"] == "saved"
    prior = control_only.rename(tmp_path / "held-aside")
    restored = run("checkpoint-restore", "--expected-sha256", saved["manifest_sha256"])
    assert restored["status"] == "restored"
    assert contents(control_only) == contents(prior)
