"""T248 GitHub metadata fixtures use documented REST fields only."""

import importlib
import json
import sys
from datetime import UTC, datetime

import httpx
import pytest

from atlas.data.budget import ArchiveOnly
from atlas.ingest.base import IngestError

NOW = datetime(2026, 11, 8, 10, tzinfo=UTC)
REPO = "owner/atlas"
SHA = "a" * 40
MANIFEST = "b" * 64
ARCHIVE = "c" * 64
TOKEN = "local-metadata-test-token"


@pytest.fixture
def hosted(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    return importlib.import_module("atlas.ingest.hosted_checkpoint")


def run_info(**changes):
    return {
        "id": 91,
        "workflow_id": 42,
        "head_branch": "main",
        "head_sha": SHA,
        "event": "schedule",
        "status": "completed",
        "conclusion": "success",
        "run_attempt": 1,
        "repository": {"id": 7, "full_name": REPO},
        "head_repository": {"id": 7},
        **changes,
    }


def artifact(**changes):
    return {
        "id": 901,
        "name": f"ka-feed-checkpoint-{MANIFEST}",
        "size_in_bytes": 1200,
        "expired": False,
        "created_at": "2026-11-08T08:00:00Z",
        "expires_at": "2026-11-15T08:00:00Z",
        "digest": f"sha256:{ARCHIVE}",
        "workflow_run": {
            "id": 91,
            "repository_id": 7,
            "head_repository_id": 7,
            "head_branch": "main",
            "head_sha": SHA,
        },
        **changes,
    }


def call(hosted, run=None, pages=None, *, calls=None):
    pages = pages if pages is not None else [(1, [artifact()])]
    calls = [] if calls is None else calls

    def handle(request):
        assert request.method == "GET"
        assert request.url.host == "api.github.com" and request.url.scheme == "https"
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        assert request.headers["accept-encoding"] == "identity"
        assert request.headers["x-github-api-version"] == "2026-03-10"
        calls.append(request.url.path)
        if request.url.path == f"/repos/{REPO}/actions/runs/91":
            return httpx.Response(200, json=run_info() if run is None else run)
        assert request.url.path == f"/repos/{REPO}/actions/artifacts"
        assert request.url.params["per_page"] == "100"
        count, artifacts = pages[int(request.url.params["page"]) - 1]
        return httpx.Response(200, json={"total_count": count, "artifacts": artifacts})

    trust = hosted.TrustedRun(REPO, 7, 42, 91, SHA)
    return hosted.select_checkpoint(trust, MANIFEST, now=NOW, transport=httpx.MockTransport(handle))


def test_pinned_run_and_paginated_repository_usage(hosted):
    unrelated = [{"id": i, "size_in_bytes": 25, "expired": i % 2 == 0} for i in range(1, 101)]
    calls = []
    result = call(hosted, pages=[(101, unrelated), (101, [artifact()])], calls=calls)
    assert result == {
        "status": "selected",
        "repository": REPO,
        "run_id": 91,
        "artifact_id": 901,
        "manifest_sha256": MANIFEST,
        "archive_sha256": ARCHIVE,
        "artifact_bytes": 1200,
        "retained_artifact_bytes": 3700,
        "available_artifact_bytes": 399_996_300,
        "retention_days": 7,
    }
    assert len(calls) == 3


@pytest.mark.parametrize(
    "change",
    [
        {"id": 90},
        {"workflow_id": 43},
        {"head_branch": "fork"},
        {"head_sha": "f" * 40},
        {"event": "pull_request"},
        {"status": "in_progress"},
        {"conclusion": "failure"},
        {"run_attempt": 2},
        {"repository": {"id": 8, "full_name": REPO}},
        {"head_repository": {"id": 8}},
    ],
)
def test_ineligible_run_stops_before_artifact_inventory(hosted, change):
    calls = []
    with pytest.raises(IngestError, match="run"):
        call(hosted, run=run_info(**change), calls=calls)
    assert calls == [f"/repos/{REPO}/actions/runs/91"]


@pytest.mark.parametrize(
    "change",
    [
        {"name": "older-checkpoint"},
        {"expired": True},
        {"expired": 0},
        {"digest": "sha256:broken"},
        {"digest": None},
        {"size_in_bytes": 0},
        {
            "workflow_run": {
                "id": 92,
                "repository_id": 7,
                "head_repository_id": 7,
                "head_branch": "main",
                "head_sha": SHA,
            }
        },
        {"expires_at": "2026-11-08T09:00:00Z"},
        {"expires_at": "2026-11-16T08:00:00Z"},
        {"created_at": "2026-11-08T11:00:00Z"},
    ],
)
def test_untrusted_artifact_metadata_has_no_fallback(hosted, change):
    with pytest.raises(IngestError):
        call(hosted, pages=[(1, [artifact(**change)])])


@pytest.mark.parametrize(
    "problem", ["short", "count", "duplicate", "ambiguous", "oversized", "negative"]
)
def test_invalid_inventory_fails_closed(hosted, problem):
    rows = [{"id": i, "size_in_bytes": 1} for i in range(1, 101)]
    pages = {
        "short": [(2, [artifact()])],
        "count": [(101, rows), (102, [artifact()])],
        "duplicate": [(101, rows), (101, [artifact(id=1)])],
        "ambiguous": [(2, [artifact(), artifact(id=902)])],
        "oversized": [(1001, rows)],
        "negative": [(2, [artifact(), {"id": 999, "size_in_bytes": -1}])],
    }[problem]
    with pytest.raises(IngestError):
        call(hosted, pages=pages)


def test_storage_cap_counts_even_listed_expired_artifacts(hosted):
    retained = {"id": 999, "size_in_bytes": 400_000_000 - 1200, "expired": True}
    assert call(hosted, pages=[(2, [artifact(), retained])])["available_artifact_bytes"] == 0
    retained["size_in_bytes"] += 1
    with pytest.raises(ArchiveOnly):
        call(hosted, pages=[(2, [artifact(), retained])])


@pytest.mark.parametrize("status", [302, 403, 429, 503, 200])
def test_http_redirect_errors_and_oversized_metadata_stop_once(hosted, status):
    attempts = []

    def respond(request):
        attempts.append(request.url.host)
        return httpx.Response(
            status, headers={"Location": "https://example.invalid/"}, content=b"x" * (1024**2 + 1)
        )

    with pytest.raises(IngestError):
        hosted.select_checkpoint(
            hosted.TrustedRun(REPO, 7, 42, 91, SHA),
            MANIFEST,
            now=NOW,
            transport=httpx.MockTransport(respond),
        )
    assert attempts == ["api.github.com"]


def test_parent_is_bounded_and_never_passes_token_in_arguments(hosted, monkeypatch, capsys):
    def deadline(command, *, timeout):
        assert command[:4] == [sys.executable, "-m", "atlas.ingest.hosted_checkpoint", "--child"]
        assert TOKEN not in repr(command)
        assert timeout == 30
        return {"status": "deadline"}

    monkeypatch.setattr(hosted, "run_bounded", deadline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "runner-select",
            "--repository",
            REPO,
            "--repository-id",
            "7",
            "--workflow-id",
            "42",
            "--run-id",
            "91",
            "--head-sha",
            SHA,
            "--manifest-sha256",
            MANIFEST,
        ],
    )
    with pytest.raises(SystemExit, match="1"):
        hosted.main()
    assert json.loads(capsys.readouterr().out)["status"] == "deadline"
