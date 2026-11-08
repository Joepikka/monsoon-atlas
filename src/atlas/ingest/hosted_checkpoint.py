"""T248: verify one pinned GitHub checkpoint using read-only metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from atlas.config import load_budgets
from atlas.data.budget import ArchiveOnly
from atlas.ingest.base import IngestError
from atlas.ingest.checkpoint_bundle import HASH, ROOT
from atlas.ingest.schedule import run_bounded

API = "https://api.github.com"
API_VERSION = "2026-03-10"
PAGE_SIZE = 100
MAX_PAGES = 10
MAX_REPLY = 1024**2
DEADLINE_S = 30


@dataclass(frozen=True)
class TrustedRun:
    repository: str
    repository_id: int
    workflow_id: int
    run_id: int
    head_sha: str
    branch: str = "main"


def _integer(value: object, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise IngestError("Invalid GitHub metadata integer")
    return value


def _metadata(client: httpx.Client, path: str, params: dict | None = None) -> dict:
    with client.stream("GET", path, params=params) as response:
        if response.status_code != 200:
            raise IngestError(f"GitHub metadata request returned HTTP {response.status_code}")
        if response.headers.get("content-encoding", "identity").lower() != "identity":
            raise IngestError("GitHub metadata has an unsupported encoding")
        body = bytearray()
        for chunk in response.iter_bytes(chunk_size=64 * 1024):
            body.extend(chunk)
            if len(body) > MAX_REPLY:
                raise IngestError("GitHub metadata exceeds its byte bound")
    value = json.loads(body.decode("utf-8"))
    if not isinstance(value, dict):
        raise IngestError("GitHub metadata must be an object")
    return value


def _verify_run(value: dict, trust: TrustedRun) -> None:
    if (
        _integer(value["id"], minimum=1) != trust.run_id
        or _integer(value["workflow_id"], minimum=1) != trust.workflow_id
        or _integer(value["repository"]["id"], minimum=1) != trust.repository_id
        or _integer(value["head_repository"]["id"], minimum=1) != trust.repository_id
        or value["repository"]["full_name"].lower() != trust.repository.lower()
        or value["head_branch"] != trust.branch
        or value["head_sha"] != trust.head_sha
        or value["event"] not in {"schedule", "workflow_dispatch"}
        or value["status"] != "completed"
        or value["conclusion"] != "success"
        or type(value["run_attempt"]) is not int
        or value["run_attempt"] != 1
    ):
        raise IngestError("GitHub run does not match the trusted completed run")


def _inventory(client: httpx.Client, path: str, trust: TrustedRun, name: str) -> tuple[dict, int]:
    seen = set()
    expected = selected = None
    retained = 0
    for page in range(1, MAX_PAGES + 1):
        payload = _metadata(client, path, {"per_page": PAGE_SIZE, "page": page})
        count = _integer(payload["total_count"])
        rows = payload["artifacts"]
        if expected is None:
            expected = count
        if (
            count != expected
            or count > MAX_PAGES * PAGE_SIZE
            or not isinstance(rows, list)
            or len(rows) != min(PAGE_SIZE, count - len(seen))
        ):
            raise IngestError(
                "GitHub artifact inventory is incomplete, changed or exceeds its bound"
            )
        for item in rows:
            identifier = _integer(item["id"], minimum=1)
            if identifier in seen:
                raise IngestError("GitHub artifact inventory repeats an ID")
            seen.add(identifier)
            retained += _integer(item["size_in_bytes"])
            if item.get("name") != name:
                continue
            run = item.get("workflow_run")
            if not isinstance(run, dict) or run.get("id") != trust.run_id:
                continue
            if selected is not None:
                raise IngestError("GitHub run has ambiguous checkpoint artifacts")
            selected = item
        if len(seen) == count:
            if selected is None:
                raise IngestError("Pinned GitHub run has no matching checkpoint artifact")
            return selected, retained
    raise IngestError("GitHub artifact inventory exceeds its page bound")


def select_checkpoint(
    trust: TrustedRun,
    manifest_sha256: str,
    *,
    now: datetime | None = None,
    transport: httpx.BaseTransport | None = None,
) -> dict:
    """Return pinned identity and complete listed repository usage, without downloading."""
    now = datetime.now(UTC) if now is None else now
    if (
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}", trust.repository)
        or trust.repository.split("/")[-1] in {".", ".."}
        or not re.fullmatch(r"[0-9a-f]{40}", trust.head_sha)
        or not re.fullmatch(HASH, manifest_sha256)
        or not 1 <= len(trust.branch) <= 255
        or now.utcoffset() != timedelta(0)
    ):
        raise IngestError("Invalid pinned checkpoint identity")
    for identifier in (trust.repository_id, trust.workflow_id, trust.run_id):
        _integer(identifier, minimum=1)
    budget = load_budgets(ROOT / "configs/budgets.yaml").github_actions
    cap = budget.artifacts_mb * 1_000_000
    headers = {
        "Accept": "application/vnd.github+json",
        "Accept-Encoding": "identity",
        "X-GitHub-Api-Version": API_VERSION,
    }
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    path = f"/repos/{trust.repository}/actions"
    try:
        with httpx.Client(
            base_url=API,
            headers=headers,
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(5, connect=2),
        ) as client:
            _verify_run(_metadata(client, f"{path}/runs/{trust.run_id}"), trust)
            artifact, retained = _inventory(
                client, f"{path}/artifacts", trust, f"ka-feed-checkpoint-{manifest_sha256}"
            )
        run = artifact["workflow_run"]
        digest = artifact["digest"]
        created = datetime.fromisoformat(artifact["created_at"])
        expires = datetime.fromisoformat(artifact["expires_at"])
        if (
            _integer(run["id"], minimum=1) != trust.run_id
            or _integer(run["repository_id"], minimum=1) != trust.repository_id
            or _integer(run["head_repository_id"], minimum=1) != trust.repository_id
            or run["head_branch"] != trust.branch
            or run["head_sha"] != trust.head_sha
            or artifact["expired"] is not False
            or not isinstance(digest, str)
            or not re.fullmatch(f"sha256:{HASH}", digest)
            or created.utcoffset() != timedelta(0)
            or expires.utcoffset() != timedelta(0)
            or not created
            <= now
            < expires
            <= created + timedelta(days=budget.artifact_retention_days)
        ):
            raise IngestError("GitHub checkpoint artifact failed identity or retention checks")
        size = _integer(artifact["size_in_bytes"], minimum=1)
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError, OverflowError):
        raise IngestError("Malformed GitHub checkpoint metadata") from None
    if retained > cap:
        raise ArchiveOnly("Listed GitHub artifacts exceed the configured storage budget")
    return {
        "status": "selected",
        "repository": trust.repository,
        "run_id": trust.run_id,
        "artifact_id": artifact["id"],
        "manifest_sha256": manifest_sha256,
        "archive_sha256": digest.removeprefix("sha256:"),
        "artifact_bytes": size,
        "retained_artifact_bytes": retained,
        "available_artifact_bytes": cap - retained,
        "retention_days": budget.artifact_retention_days,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--repository-id", required=True, type=int)
    parser.add_argument("--workflow-id", required=True, type=int)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.child:
            trust = TrustedRun(
                args.repository,
                args.repository_id,
                args.workflow_id,
                args.run_id,
                args.head_sha,
                args.branch,
            )
            result = select_checkpoint(trust, args.manifest_sha256)
        else:
            result = run_bounded(
                [sys.executable, "-m", "atlas.ingest.hosted_checkpoint", "--child", *sys.argv[1:]],
                timeout=DEADLINE_S,
            )
    except (IngestError, ArchiveOnly, OSError, ValueError, httpx.HTTPError) as error:
        reason = (
            str(error) if isinstance(error, (ArchiveOnly, IngestError)) else type(error).__name__
        )
        result = {"status": "failed", "reason": reason}
    print(json.dumps(result))
    if not args.child and result["status"] != "selected":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
