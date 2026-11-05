"""Immutable model releases (T034).

Each release is one JSON file, `<root>/<model_id>/<version>.json`, written once and never
overwritten. It records the dataset hash, git SHA, split cutoffs, baseline and candidate scores,
the bootstrap interval, the decision and the approval status. Only an `approve` record by the
owner turns an eligible candidate into the champion; otherwise the baseline is served.
MLflow (ml lock) is optional local tracking that mirrors the same fields.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field

from atlas.contracts import ModelId, Sha256, Strict, UtcDatetime


class Release(Strict):
    model_id: ModelId
    version: str = Field(pattern=r"^v\d+$")
    created_at: UtcDatetime
    dataset_sha256: Sha256
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    cutoffs: dict[str, str] = Field(min_length=1)  # role -> "start/end" ISO dates
    baseline: str = Field(min_length=1)
    baseline_scores: dict[str, float]
    candidate: str | None = None
    candidate_scores: dict[str, float] | None = None
    improvement: dict[str, float] | None = None  # mean, lower95, upper95, n_rows, n_blocks
    status: Literal["candidate_eligible", "baseline_only", "research_only"]
    reason: str = Field(min_length=1)
    approval: Literal["pending", "approved", "rejected"] = "pending"


def git_sha(repo: Path) -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def write_release(release: Release, root: Path) -> Path:
    path = root / release.model_id / f"{release.version}.json"
    if path.exists():
        raise FileExistsError(f"{path} exists; releases are immutable, use a new version")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(release.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def approve(
    root: Path, model_id: str, version: str, decision: Literal["approved", "rejected"], by: str
) -> Path:
    """Owner approval is a separate immutable file; the release file itself never changes."""
    release = Release.model_validate_json((root / model_id / f"{version}.json").read_text("utf-8"))
    if decision == "approved" and release.status != "candidate_eligible":
        raise ValueError(
            f"{model_id} {version} is {release.status}; only eligible candidates can be approved"
        )
    path = root / model_id / f"{version}.approval.json"
    if path.exists():
        raise FileExistsError(f"{path} exists")
    body = {"decision": decision, "by": by, "at": datetime.now(UTC).isoformat()}
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def champion(root: Path, model_id: str) -> str:
    """The served model: the newest approved eligible candidate, else the newest baseline."""
    folder = root / model_id
    releases = sorted(
        (
            Release.model_validate_json(p.read_text("utf-8"))
            for p in folder.glob("v*.json")
            if ".approval" not in p.name
        ),
        key=lambda r: int(r.version[1:]),
    )
    if not releases:
        raise LookupError(f"no releases for {model_id}")
    for r in reversed(releases):
        approval = folder / f"{r.version}.approval.json"
        if r.status == "candidate_eligible" and approval.exists():
            if json.loads(approval.read_text("utf-8"))["decision"] == "approved":
                return r.candidate
    return releases[-1].baseline


def log_to_mlflow(release: Release, tracking_uri: str) -> str:
    """Mirror a release into a local MLflow store (for example sqlite:///D:/.../mlflow.db)."""
    import mlflow  # ml lock

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(release.model_id)
    with mlflow.start_run(run_name=release.version) as run:
        mlflow.log_params(
            {
                "dataset_sha256": release.dataset_sha256,
                "git_sha": release.git_sha,
                **release.cutoffs,
            }
        )
        mlflow.log_metrics({f"baseline_{k}": v for k, v in release.baseline_scores.items()})
        if release.candidate_scores:
            mlflow.log_metrics({f"candidate_{k}": v for k, v in release.candidate_scores.items()})
        mlflow.set_tags({"status": release.status, "approval": release.approval})
        return run.info.run_id
