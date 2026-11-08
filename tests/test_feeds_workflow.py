"""T251: the manual hosted relay uses verified selector, archive and offer contracts."""

import hashlib
import importlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import sys
import zipfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import yaml

from atlas.data.budget import GB, ArchiveOnly
from atlas.ingest.base import IngestError
from atlas.ingest.hosted_archive import downloaded_archive, import_archive
from atlas.ingest.runner_checkpoint import (
    bootstrap_checkpoint,
    offer_checkpoint,
    resume_checkpoint,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/feeds.yml"
PINS = {
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python": "6d4fd22b20465ccc0f7354476588e8df7c9ca0e0",
    "actions/download-artifact": "9000827ccba6bdab643e8b6fd33ac0654aef8333",
    "actions/upload-artifact": "cf430e030ddbb5b0abf93d22962f4752f3646cd9",
}
NOW = datetime(2026, 11, 8, 10, tzinfo=UTC)
REPO = "owner/atlas"
SHA = "a" * 40
MANIFEST = "b" * 64
TOKEN = "local-metadata-test-token"
FIELD = re.compile(r"fromJSON\(steps\.(\w+)\.outputs\.json\)\.(\w+)")
DISCOVER, BOOTSTRAP = "${{ !inputs.bootstrap }}", "${{ inputs.bootstrap }}"


def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text("utf-8"))


def relay_steps() -> list[dict]:
    return workflow()["jobs"]["relay"]["steps"]


def action(name: str) -> dict:
    (step,) = [step for step in relay_steps() if step.get("uses", "").startswith(name + "@")]
    return step


@pytest.fixture
def space(monkeypatch, tmp_path):
    usage = shutil.disk_usage(tmp_path)
    monkeypatch.setattr(shutil, "disk_usage", lambda _: usage._replace(free=100 * GB))


@pytest.fixture
def hosted(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    return importlib.import_module("atlas.ingest.hosted_checkpoint")


def run(**changes) -> dict:
    return {
        "id": 92,
        "workflow_id": 42,
        "run_number": 1,
        "head_branch": "main",
        "head_sha": SHA,
        "event": "workflow_dispatch",
        "status": "in_progress",
        "conclusion": None,
        "run_attempt": 1,
        "repository": {"id": 7, "full_name": REPO},
        "head_repository": {"id": 7},
        **changes,
    }


def artifact(run_id: int, **changes) -> dict:
    return {
        "id": 901,
        "name": f"ka-feed-checkpoint-{MANIFEST}",
        "size_in_bytes": 1200,
        "expired": False,
        "created_at": "2026-11-08T08:00:00Z",
        "expires_at": "2026-11-15T08:00:00Z",
        "digest": "sha256:" + "c" * 64,
        "workflow_run": {
            "id": run_id,
            "repository_id": 7,
            "head_repository_id": 7,
            "head_branch": "main",
            "head_sha": SHA,
        },
        **changes,
    }


def select(hosted, *, bootstrap: bool, active=None, artifacts=None) -> tuple[dict, list]:
    active = run(**({} if bootstrap else {"run_number": 11})) | (active or {})
    prior = run(id=91, run_number=10, status="completed", conclusion="success")
    artifacts = ([] if bootstrap else [artifact(91)]) if artifacts is None else artifacts
    requested = []

    def handle(request):
        assert request.method == "GET" and request.url.host == "api.github.com"
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        path = request.url.path.removeprefix(f"/repos/{REPO}/actions")
        requested.append(path)
        replies = {
            "/runs/92": active,
            "/runs/91": prior,
            "/workflows/42/runs": {"total_count": 2, "workflow_runs": [active, prior]},
            "/artifacts": {"total_count": len(artifacts), "artifacts": artifacts},
        }
        return httpx.Response(200, json=replies[path])

    trust = hosted.TrustedRun(REPO, 7, 42, 92, SHA)
    result = hosted.select_checkpoint(
        trust, None, bootstrap=bootstrap, now=NOW, transport=httpx.MockTransport(handle)
    )
    return result, requested


def upload_zip(bundle: Path, directory: Path) -> Path:
    # upload-artifact v7 roots one directory path at that directory and stores its files.
    directory.mkdir()
    archive = directory / "artifact"  # the download action's name without Content-Disposition
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as writer:
        for member in sorted(bundle.rglob("*")):
            if member.is_file():
                writer.write(member, member.relative_to(bundle).as_posix())
    return archive


def identity(archive: Path) -> dict:
    data = archive.read_bytes()
    return {"archive_sha256": hashlib.sha256(data).hexdigest(), "archive_bytes": len(data)}


def test_relay_is_manual_serial_bounded_and_read_only():
    flow = workflow()
    text = WORKFLOW.read_text("utf-8")
    triggers = flow[True]  # PyYAML reads the bare `on` key as a boolean.
    assert set(triggers) == {"workflow_dispatch"}
    assert triggers["workflow_dispatch"]["inputs"] == {
        "bootstrap": {
            "description": triggers["workflow_dispatch"]["inputs"]["bootstrap"]["description"],
            "type": "boolean",
            "default": False,
        }
    }
    assert flow["permissions"] == {"contents": "read", "actions": "read"}
    assert flow["concurrency"] == {"group": "ka-feeds", "cancel-in-progress": False}
    job = flow["jobs"]["relay"]
    assert (job["runs-on"], job["timeout-minutes"]) == ("ubuntu-24.04", 3)
    assert job["env"]["MODE"] == "${{ inputs.bootstrap && '--bootstrap' || '--discover' }}"
    assert "secrets." not in text and "atlas.ingest.runner_cycle" not in text
    for step in job["steps"]:
        if "uses" in step:
            name, pin = step["uses"].split("@")
            assert PINS[name] == pin


def test_artifact_transport_is_pinned_raw_and_cannot_overwrite():
    download = action("actions/download-artifact")
    assert download["if"] == DISCOVER
    assert download["with"] | {"path": None} == {
        "artifact-ids": "${{ fromJSON(steps.select.outputs.json).artifact_id }}",
        "run-id": "${{ fromJSON(steps.select.outputs.json).run_id }}",
        "repository": "${{ github.repository }}",
        "github-token": "${{ github.token }}",
        "path": None,
        "skip-decompress": True,
        "digest-mismatch": "error",
    }
    upload = action("actions/upload-artifact")
    assert "if" not in upload
    assert upload["with"]["name"].startswith("ka-feed-checkpoint-${{ fromJSON(steps.offer")
    assert upload["with"]["path"] == "${{ fromJSON(steps.offer.outputs.json).bundle_path }}"
    for key, value in {
        "if-no-files-found": "error",
        "overwrite": False,
        "include-hidden-files": False,
    }.items():
        assert upload["with"][key] == value


def test_workflow_uses_only_real_outputs_and_cli_options(hosted, space, tmp_path):
    outputs = {
        DISCOVER: select(hosted, bootstrap=False)[0],
        BOOTSTRAP: select(hosted, bootstrap=True)[0],
    }
    root, store = tmp_path / "feeds", tmp_path / "store"
    bootstrap_checkpoint(root, store)
    offer = offer_checkpoint(root, store, retained_artifact_bytes=0)
    for step in relay_steps():
        modes = [step["if"]] if "if" in step else [DISCOVER, BOOTSTRAP]
        for source, field in FIELD.findall(json.dumps(step)):
            for mode in modes:
                assert field in (outputs[mode] if source == "select" else offer), (step, field)
        commands = re.findall(r"python -m (atlas\.[\w.]+)((?:\\\n|.)*)", step.get("run", ""))
        for module, command in commands:
            code = Path(importlib.util.find_spec(module).origin).read_text("utf-8")
            options = re.findall(r"(?<![\w-])(--[a-z][\w-]*|runner-[a-z]+)", command)
            assert options and all(f'"{option}"' in code for option in options), command
    source = Path(hosted.__file__).read_text("utf-8")
    assert '"--bootstrap"' in source and '"--discover"' in source


def test_bootstrap_and_relay_hops_import_identical_checkpoints(space, tmp_path):
    root, store = tmp_path / "feeds", tmp_path / "store"
    digest = bootstrap_checkpoint(root, store)
    with closing(sqlite3.connect(root / "control.sqlite")) as db:
        tables = {name for (name,) in db.execute("SELECT name FROM sqlite_master")}
    assert {"local_admission", "cap_documents"} <= tables
    held = root.rename(tmp_path / "held")
    first = offer_checkpoint(root, store, retained_artifact_bytes=0)
    assert first["manifest_sha256"] == digest and first["retention_days"] == 7
    for hop in range(2):
        offer = offer_checkpoint(root, store, retained_artifact_bytes=1000 * hop)
        assert {key: offer[key] for key in ("manifest_sha256", "payload_bytes")} == {
            key: first[key] for key in ("manifest_sha256", "payload_bytes")
        }
        archive = upload_zip(Path(offer["bundle_path"]), tmp_path / f"download-{hop}")
        before = archive.read_bytes()
        store = tmp_path / f"store-{hop}"
        found = downloaded_archive(archive.parent)
        assert import_archive(root, found, store, expected_sha256=digest, **identity(archive)) == (
            digest
        )
        assert archive.read_bytes() == before and not root.exists()
    assert resume_checkpoint(root, store) == digest
    assert (root / "control.sqlite").read_bytes() == (held / "control.sqlite").read_bytes()


def test_archive_cli_imports_from_download_directory(space, tmp_path, monkeypatch, capsys):
    module = importlib.import_module("atlas.ingest.hosted_archive")
    root, store = tmp_path / "feeds", tmp_path / "store"
    digest = bootstrap_checkpoint(root, store)
    offer = offer_checkpoint(root, store, retained_artifact_bytes=0)
    archive = upload_zip(Path(offer["bundle_path"]), tmp_path / "dl")
    root.rename(tmp_path / "held")
    checks = identity(archive)
    arguments = ["--root", str(root), "--download-dir", str(archive.parent)]
    arguments += ["--store", str(tmp_path / "next"), "--expected-sha256", digest]
    arguments += ["--archive-sha256", checks["archive_sha256"]]
    arguments += ["--archive-bytes", str(checks["archive_bytes"])]
    monkeypatch.setattr(sys, "argv", ["runner-import-zip", "--child", *arguments])
    module.main()
    assert json.loads(capsys.readouterr().out) == {"status": "imported", "manifest_sha256": digest}

    def bounded(command, *, timeout):
        assert command[3:] == ["--child", *arguments] and timeout == 60
        return {"status": "deadline"}

    monkeypatch.setattr(module, "run_bounded", bounded)
    monkeypatch.setattr(sys, "argv", ["runner-import-zip", *arguments])
    with pytest.raises(SystemExit, match="1"):
        module.main()


@pytest.mark.parametrize("existing", ["root", "store"])
def test_bootstrap_never_replaces_existing_state(space, tmp_path, existing):
    root, store = tmp_path / "feeds", tmp_path / "store"
    target, other = (root, store) if existing == "root" else (store, root)
    target.mkdir()
    (target / "retained.txt").write_bytes(b"retained")
    with pytest.raises(IngestError, match="already exists"):
        bootstrap_checkpoint(root, store)
    assert (target / "retained.txt").read_bytes() == b"retained"
    assert sorted(path.name for path in target.iterdir()) == ["retained.txt"]
    assert not other.exists()


@pytest.mark.parametrize("layout", ["missing", "empty", "two", "directory", "hardlink"])
def test_download_directory_must_hold_one_regular_file(tmp_path, layout):
    directory = tmp_path / "download"
    if layout != "missing":
        directory.mkdir()
    if layout == "two":
        (directory / "artifact").write_bytes(b"1")
        (directory / "other").write_bytes(b"2")
    elif layout == "directory":
        (directory / "artifact").mkdir()
    elif layout == "hardlink":
        (tmp_path / "outside").write_bytes(b"1")
        os.link(tmp_path / "outside", directory / "artifact")
    with pytest.raises((IngestError, OSError)):
        downloaded_archive(directory)


def test_manual_bootstrap_measures_inventory_without_predecessor(hosted):
    retained = [{"id": 5, "size_in_bytes": 300, "expired": True}, artifact(80, id=6)]
    result, requested = select(hosted, bootstrap=True, artifacts=retained)
    assert result == {
        "status": "bootstrap",
        "repository": REPO,
        "run_id": 92,
        "retained_artifact_bytes": 1500,
        "available_artifact_bytes": 399_998_500,
        "retention_days": 7,
    }
    assert requested == ["/runs/92", "/artifacts"]


@pytest.mark.parametrize(
    "active",
    [
        {"event": "schedule"},
        {"event": "push"},
        {"status": "completed", "conclusion": "success"},
        {"run_attempt": 2},
        {"head_sha": "f" * 40},
    ],
)
def test_bootstrap_requires_active_manual_first_attempt(hosted, active):
    with pytest.raises(IngestError, match="trusted active run"):
        select(hosted, bootstrap=True, active=active)


def test_bootstrap_refuses_existing_checkpoint_and_over_budget_inventory(hosted):
    with pytest.raises(IngestError, match="already has a checkpoint"):
        select(hosted, bootstrap=True, artifacts=[artifact(92)])
    full = [{"id": 5, "size_in_bytes": 400_000_001, "expired": True}]
    with pytest.raises(ArchiveOnly):
        select(hosted, bootstrap=True, artifacts=full)
    with pytest.raises(IngestError, match="Invalid pinned"):
        hosted.select_checkpoint(
            hosted.TrustedRun(REPO, 7, 42, 92, SHA), MANIFEST, bootstrap=True, now=NOW
        )


def test_selector_cli_accepts_bootstrap_status(hosted, monkeypatch, capsys):
    def bounded(command, *, timeout):
        assert command[-1] == "--bootstrap" and TOKEN not in repr(command)
        return {"status": "bootstrap", "retained_artifact_bytes": 0}

    monkeypatch.setattr(hosted, "run_bounded", bounded)
    arguments = ["--repository", REPO, "--repository-id", "7", "--workflow-id", "42"]
    arguments += ["--run-id", "92", "--head-sha", SHA, "--bootstrap"]
    monkeypatch.setattr(sys, "argv", ["runner-select", *arguments])
    hosted.main()
    assert json.loads(capsys.readouterr().out)["status"] == "bootstrap"
