"""T250 verifies the selected ZIP and its separately trusted manifest."""

import hashlib
import importlib
import shutil
import stat
import warnings
import zipfile
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from atlas.data.budget import GB, ArchiveOnly
from atlas.ingest.base import IngestError
from atlas.ingest.runner_checkpoint import commit_checkpoint, resume_checkpoint
from atlas.ingest.s01_collect import collect_weather
from atlas.ingest.s01_prepare import prepare_weather
from atlas.ingest.schedule import defer, open_control

FIXTURES = Path(__file__).resolve().parent / "fixtures"
NOW = datetime(2026, 11, 5, 14, tzinfo=UTC)


@pytest.fixture
def state(tmp_path, monkeypatch):
    module = importlib.import_module("atlas.ingest.hosted_archive")
    usage = shutil.disk_usage(tmp_path)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: usage._replace(free=100 * GB))
    root, store = tmp_path / "feeds", tmp_path / "old-store"
    with closing(open_control(root / "control.sqlite")):
        pass
    digest = commit_checkpoint(root, store, expected_head=None)
    return module, root, store, digest


def zip_bundle(bundle, path, *, directories=False):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member in sorted(bundle.rglob("*")):
            if member.is_file() or directories:
                archive.write(member, member.relative_to(bundle).as_posix())


def deliver(module, root, archive, store, digest, **changes):
    data = archive.read_bytes()
    checks = {
        "expected_sha256": digest,
        "archive_sha256": hashlib.sha256(data).hexdigest(),
        "archive_bytes": len(data),
    }
    return module.import_archive(root, archive, store, **(checks | changes))


def weather(request):
    filename = (
        "s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json"
        if request.url.path.endswith("meta.json")
        else "s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json"
    )
    return httpx.Response(
        200,
        content=(FIXTURES / filename).read_bytes(),
        headers={"content-type": "application/json"},
    )


def test_verified_archive_recovers_weather_bytes_and_cooldown(state, tmp_path):
    module, root, original, prior = state
    assert (
        collect_weather(
            root, transport=httpx.MockTransport(weather), clock=lambda: NOW, sleep=lambda _: None
        )["status"]
        == "captured"
    )
    prepared = prepare_weather(root, as_of=NOW)
    with closing(open_control(root / "control.sqlite")) as db:
        defer(db, "S01", (NOW + timedelta(hours=8)).timestamp())
    digest = commit_checkpoint(root, original, expected_head=prior)
    archive = tmp_path / "downloaded.zip"
    zip_bundle(original / "objects" / digest, archive, directories=True)
    before = archive.read_bytes()
    held = root.rename(tmp_path / "held")
    store = tmp_path / "next-store"
    assert deliver(module, root, archive, store, digest) == digest
    assert not root.exists() and archive.read_bytes() == before
    assert resume_checkpoint(root, store) == digest
    assert (root / "control.sqlite").read_bytes() == (held / "control.sqlite").read_bytes()
    assert prepare_weather(root, as_of=NOW)["sha256"] == prepared["sha256"]

    def unexpected(_):
        pytest.fail("Restored cooldown allowed a provider request")

    assert (
        collect_weather(
            root,
            transport=httpx.MockTransport(unexpected),
            sleep=lambda _: None,
            clock=lambda: NOW + timedelta(hours=7),
        )["status"]
        == "deferred"
    )


@pytest.mark.parametrize("damage", ["hash", "size", "manifest", "bad-zip", "central-bound"])
def test_archive_identity_or_metadata_failure_leaves_no_store(state, tmp_path, monkeypatch, damage):
    module, root, original, digest = state
    archive = tmp_path / "downloaded.zip"
    zip_bundle(original / "objects" / digest, archive)
    options = {}
    if damage == "hash":
        options["archive_sha256"] = "f" * 64
    elif damage == "size":
        options["archive_bytes"] = archive.stat().st_size + 1
    elif damage == "manifest":
        options["expected_sha256"] = "f" * 64
    elif damage == "bad-zip":
        archive.write_bytes(archive.read_bytes()[:-20])
    else:
        monkeypatch.setattr(module, "MAX_CENTRAL_BYTES", 1)
    root.rename(tmp_path / "held")
    store = tmp_path / "next-store"
    before = archive.read_bytes()
    reason = {
        "hash": "selected digest",
        "size": "selected size",
        "manifest": "member failed digest",
        "bad-zip": "central|malformed",
        "central-bound": "central directory exceeds",
    }[damage]
    with pytest.raises(IngestError, match=reason):
        deliver(module, root, archive, store, digest, **options)
    assert not store.exists() and not root.exists()
    assert archive.read_bytes() == before


@pytest.mark.parametrize(
    "damage", ["extra", "traversal", "windows", "alias", "duplicate", "link", "missing", "bytes"]
)
def test_zip_inventory_and_member_checks_prevent_import(state, tmp_path, damage):
    module, root, original, digest = state
    bundle = original / "objects" / digest
    archive = tmp_path / "downloaded.zip"
    name = "files/control.sqlite"
    data = (bundle / name).read_bytes()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as writer:
        writer.write(bundle / "manifest.json", "manifest.json")
        if damage not in {"missing", "link", "bytes"}:
            writer.writestr(name, data)
        extra = {
            "extra": ".env",
            "traversal": "../outside.txt",
            "windows": "files|control.sqlite",
            "alias": "files/CONTROL.sqlite",
            "duplicate": name,
        }.get(damage)
        if extra:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                writer.writestr(extra, b"unexpected")
        if damage == "link":
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            writer.writestr(info, data)
        if damage == "bytes":
            writer.writestr(name, b"X" + data[1:])
    if damage == "windows":
        archive.write_bytes(
            archive.read_bytes().replace(b"files|control.sqlite", b"files\\control.sqlite")
        )
    root.rename(tmp_path / "held")
    store = tmp_path / "next-store"
    with pytest.raises(IngestError):
        deliver(module, root, archive, store, digest)
    assert not (tmp_path / "outside.txt").exists()
    assert not store.exists() and not root.exists()


def test_expansion_budget_refuses_before_extracting(state, tmp_path, monkeypatch):
    module, root, original, digest = state
    archive = tmp_path / "downloaded.zip"
    zip_bundle(original / "objects" / digest, archive)
    limit = archive.stat().st_size

    def budget(size, retained):
        assert retained == 0
        if size > limit:
            raise ArchiveOnly("test expansion budget")

    def unexpected(*args, **kwargs):
        pytest.fail("An over-budget ZIP began extracting")

    monkeypatch.setattr(module, "_artifact_budget", budget)
    monkeypatch.setattr(module, "_extract", unexpected)
    root.rename(tmp_path / "held")
    store = tmp_path / "next-store"
    with pytest.raises(ArchiveOnly, match="expansion budget"):
        deliver(module, root, archive, store, digest)
    assert not store.exists() and not root.exists()


def test_existing_store_is_never_replaced(state, tmp_path):
    module, root, original, digest = state
    archive = tmp_path / "downloaded.zip"
    zip_bundle(original / "objects" / digest, archive)
    root.rename(tmp_path / "held")
    before = (original / "catalog.sqlite").read_bytes()
    with pytest.raises(IngestError):
        deliver(module, root, archive, original, digest)
    assert (original / "catalog.sqlite").read_bytes() == before
    assert not root.exists()
