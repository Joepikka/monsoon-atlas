"""T247 verifies a transported generation before the next runner opens it."""

import hashlib
import json
import shutil
import sys
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from atlas.data.budget import GB, ArchiveOnly
from atlas.ingest import checkpoint_bundle
from atlas.ingest import runner_checkpoint as runner
from atlas.ingest.base import IngestError
from atlas.ingest.s01_collect import collect_weather
from atlas.ingest.s01_prepare import prepare_weather
from atlas.ingest.schedule import defer, open_control

FIXTURES = Path(__file__).resolve().parent / "fixtures"
NOW = datetime(2026, 11, 5, 14, tzinfo=UTC)


@pytest.fixture
def state(tmp_path, monkeypatch):
    usage = shutil.disk_usage(tmp_path)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: usage._replace(free=100 * GB))
    root, store = tmp_path / "feeds", tmp_path / "original-store"
    with closing(open_control(root / "control.sqlite")):
        pass
    digest = runner.commit_checkpoint(root, store, expected_head=None)
    return root, store, digest


def weather(request):
    name = (
        "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json"
        if request.url.path.endswith("meta.json")
        else "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json"
    )
    return httpx.Response(
        200, content=(FIXTURES / name).read_bytes(), headers={"content-type": "application/json"}
    )


def contents(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_transferred_current_generation_restores_real_bytes_and_cooldown(state, tmp_path):
    root, store, old = state
    assert (
        collect_weather(
            root, transport=httpx.MockTransport(weather), clock=lambda: NOW, sleep=lambda _: None
        )["status"]
        == "captured"
    )
    prepared = prepare_weather(root, as_of=NOW)
    with closing(open_control(root / "control.sqlite")) as db:
        defer(db, "S01", (NOW + timedelta(hours=8)).timestamp())
    current = runner.commit_checkpoint(root, store, expected_head=old)
    assert current != old
    offer = runner.offer_checkpoint(root, store, retained_artifact_bytes=0)
    candidate = Path(offer["bundle_path"])
    assert candidate == store / "objects" / current
    assert offer["manifest_sha256"] == current
    assert offer["payload_bytes"] == sum(len(data) for data in contents(candidate).values())
    assert offer["retention_days"] == 7
    assert {p.name for p in candidate.iterdir()} == {"manifest.json", "files"}

    downloaded = tmp_path / "downloaded"
    shutil.copytree(candidate, downloaded)
    working = root.rename(tmp_path / "held-working-tree")
    destination = tmp_path / "new-store"
    assert runner.import_checkpoint(root, downloaded, destination, current) == current
    assert not root.exists()
    assert contents(destination / "objects" / current) == contents(downloaded)
    assert {p.name for p in (destination / "objects").iterdir()} == {current}
    assert runner.resume_checkpoint(root, destination) == current
    assert contents(root) == contents(working)
    assert prepare_weather(root, as_of=NOW)["sha256"] == prepared["sha256"]

    def unexpected(_):
        pytest.fail("The transported cooldown allowed a provider request")

    assert (
        collect_weather(
            root,
            transport=httpx.MockTransport(unexpected),
            clock=lambda: NOW + timedelta(hours=7),
            sleep=lambda _: None,
        )["status"]
        == "deferred"
    )


def test_offer_uses_whole_budget_and_verifies_members(state):
    root, store, digest = state
    offer = runner.offer_checkpoint(root, store, retained_artifact_bytes=0)
    allowance = 400_000_000 - offer["payload_bytes"]
    assert runner.offer_checkpoint(root, store, retained_artifact_bytes=allowance) == offer
    with pytest.raises(ArchiveOnly):
        runner.offer_checkpoint(root, store, retained_artifact_bytes=allowance + 1)
    with pytest.raises(IngestError):
        runner.offer_checkpoint(root, store, retained_artifact_bytes=-1)
    with (store / "objects" / digest / "files/control.sqlite").open("r+b") as stream:
        stream.write(b"Corrupt")
    with pytest.raises(IngestError):
        runner.offer_checkpoint(root, store, retained_artifact_bytes=0)


def test_import_rejects_oversized_manifest_before_copy(state, tmp_path, monkeypatch):
    root, store, digest = state
    download = tmp_path / "download"
    shutil.copytree(store / "objects" / digest, download)
    path = download / "manifest.json"
    manifest = json.loads(path.read_bytes())
    manifest["files"][0]["bytes"] = 400_000_001
    encoded = checkpoint_bundle.canonical(manifest).encode()
    path.write_bytes(encoded)
    root.rename(tmp_path / "held")

    def unexpected(*args, **kwargs):
        pytest.fail("An over-budget import began copying")

    monkeypatch.setattr(checkpoint_bundle, "_copy_file", unexpected)
    destination = tmp_path / "new-store"
    with pytest.raises(ArchiveOnly, match="artifact budget"):
        runner.import_checkpoint(root, download, destination, hashlib.sha256(encoded).hexdigest())
    assert not destination.exists() and not root.exists()


@pytest.mark.parametrize("damage", ["digest", "member", "extra", "root", "existing", "copy"])
def test_invalid_transfer_preserves_download_and_prior_store(state, tmp_path, monkeypatch, damage):
    root, store, digest = state
    download = tmp_path / "download"
    shutil.copytree(store / "objects" / digest, download)
    root.rename(tmp_path / "held")
    destination = tmp_path / "destination"
    original_digest = digest
    if damage == "digest":
        digest = "f" * 64
    elif damage == "member":
        with (download / "files/control.sqlite").open("r+b") as stream:
            stream.write(b"Corrupt")
    elif damage == "extra":
        (download / ".env").write_text("operator file", encoding="utf-8")
    elif damage == "root":
        root = tmp_path / "another-feed-root"
    elif damage == "existing":
        destination.mkdir()
        (destination / "keep.txt").write_text("retain", encoding="utf-8")
    else:

        def interrupted(*args, **kwargs):
            raise OSError("simulated interrupted copy")

        monkeypatch.setattr(checkpoint_bundle, "_copy_file", interrupted)
    before = contents(download)
    with pytest.raises((IngestError, OSError)):
        runner.import_checkpoint(root, download, destination, digest)
    assert not root.exists()
    assert contents(download) == before
    assert destination.exists() == (damage == "existing")
    if damage == "existing":
        assert contents(destination) == {"keep.txt": b"retain"}
    assert [p.name for p in (store / "objects").iterdir()] == [original_digest]


def test_cli_offers_only_bundle_and_imports_without_opening_feed_root(
    state, tmp_path, monkeypatch, capsys
):
    root, store, digest = state
    root.rename(tmp_path / "held")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "runner-offer",
            "runner-offer",
            "--root",
            str(root),
            "--store",
            str(store),
            "--retained-artifact-bytes",
            "0",
        ],
    )
    runner.main()
    offered = json.loads(capsys.readouterr().out)
    assert offered["status"] == "ready" and offered["manifest_sha256"] == digest
    destination = tmp_path / "fresh-store"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "runner-import",
            "runner-import",
            "--root",
            str(root),
            "--store",
            str(destination),
            "--bundle",
            offered["bundle_path"],
            "--expected-sha256",
            digest,
        ],
    )
    runner.main()
    assert json.loads(capsys.readouterr().out) == {"status": "imported", "manifest_sha256": digest}
    assert not root.exists()
    assert runner.resume_checkpoint(root, destination) == digest
