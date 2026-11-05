"""Source discovery records (plan P1 "Verify access, units and licence" tasks).

A discovery task ends with two committed files:
  configs/sources/sNN.yaml          what was found; every claim cites evidence IDs
  tests/fixtures/sNN/manifest.json  one entry per fetched evidence page: URL, time, status, SHA256

The evidence bytes stay in the local raw store (data/raw, git-ignored), because most sources have
no redistribution licence. "blocked" is a valid discovery result; it never produces data rows.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field

from atlas.contracts import (
    Budget,
    FetchContext,
    SafeUrl,
    Sha256,
    SourceId,
    StateId,
    Strict,
    UtcDatetime,
)
from atlas.ingest.http import Fetcher
from atlas.ingest.raw_store import RawStore

Ids = list[str]


class Evidence(Strict):
    id: str = Field(pattern=r"^e\d{2}$")
    url: SafeUrl
    fetched_at: UtcDatetime
    status: int
    media_type: str
    sha256: Sha256
    bytes: int = Field(gt=0)
    raw_path: str
    shows: str = Field(min_length=10)


class EvidenceManifest(Strict):
    source_id: SourceId
    evidence: list[Evidence] = Field(min_length=1)


class Claim(Strict):
    """A finding, with the evidence that supports it."""

    status: str = Field(min_length=1)
    detail: str = Field(min_length=10)
    evidence: Ids = Field(min_length=1)


class FieldMapping(Strict):
    canonical: str
    upstream: str | None
    unit_status: Literal["labelled", "unlabelled", "not_applicable", "absent"]
    detail: str = Field(min_length=10)
    evidence: Ids = Field(min_length=1)


class Discovery(Strict):
    source_id: SourceId
    state: StateId
    name: str
    verify_task: str = Field(pattern=r"^T\d{3}$")
    discovered_at: UtcDatetime
    outcome: Literal["available", "blocked"]
    landing_url: SafeUrl
    publisher: str
    no_card: bool
    account_required: bool
    access: Claim
    licence: Claim
    provider_quota: Claim
    history: Claim
    earliest_date: str | None
    latest_date: str | None
    units: Claim
    source_check: Claim
    field_map: list[FieldMapping] = Field(min_length=1)
    dependents: list[str]
    retry_condition: str | None


LICENCE = {"open", "restricted", "unverified"}
HISTORY = {"available", "partial", "not_public"}


def capture(
    source_id: str,
    state: str,
    pages: Mapping[str, tuple[str, str]],
    raw_root: Path,
    allowed_hosts: set[str],
    *,
    fetcher: Fetcher | None = None,
    delay_s: float = 0.0,
) -> EvidenceManifest:
    """Fetch evidence pages {id: (url, what it shows)} into the raw store.
    `delay_s` honours a source's robots.txt Crawl-Delay between requests."""
    store = RawStore(raw_root)
    fetcher = fetcher or Fetcher(store, allowed_hosts)
    now = datetime.now(UTC)
    ctx = FetchContext(
        source_id=source_id,
        state=state,
        run_id=f"discovery-{now:%Y%m%dT%H%M%SZ}",
        requested_at=now,
        budget=Budget(max_requests=len(pages) * 4, max_bytes=50 * 1024**2),
        raw_root=raw_root,
    )
    out = []
    for i, (eid, (url, shows)) in enumerate(pages.items()):
        if i and delay_s:
            time.sleep(delay_s)
        art = fetcher.fetch_bytes(ctx, url, mapping_version="discovery")
        out.append(
            Evidence(
                id=eid,
                url=art.source_url,
                fetched_at=art.fetched_at,
                status=art.response_status,
                media_type=art.media_type,
                sha256=art.sha256,
                bytes=Path(art.path).stat().st_size,
                raw_path=Path(art.path).relative_to(raw_root).as_posix(),
                shows=shows,
            )
        )
    return EvidenceManifest(source_id=source_id, evidence=out)


def load_manifest(path: Path) -> EvidenceManifest:
    return EvidenceManifest.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_manifest(manifest: EvidenceManifest, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n"
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def check(d: Discovery, manifest: EvidenceManifest, *, source_enabled: bool) -> list[str]:
    """Discovery contract: explicit statuses, every claim cited, blocked stays disabled."""
    problems = []
    known = {e.id for e in manifest.evidence}
    if manifest.source_id != d.source_id:
        problems.append(f"manifest is for {manifest.source_id}, not {d.source_id}")
    claims = {n: getattr(d, n) for n in ("access", "licence", "provider_quota", "history", "units")}
    claims["source_check"] = d.source_check
    cited = [(n, c.evidence) for n, c in claims.items()]
    cited += [(f"field_map.{f.canonical}", f.evidence) for f in d.field_map]
    for name, ids in cited:
        for eid in ids:
            if eid not in known:
                problems.append(f"{name} cites {eid}, which is not in the evidence manifest")
    for e in manifest.evidence:
        if e.status != 200:
            problems.append(f"{e.id}: evidence must be a stored 200 response, got {e.status}")
    if d.licence.status not in LICENCE:
        problems.append(f"licence status must be one of {sorted(LICENCE)}")
    if d.history.status not in HISTORY:
        problems.append(f"history status must be one of {sorted(HISTORY)}")
    if d.outcome == "blocked":
        if not d.retry_condition:
            problems.append("a blocked source needs a retry condition")
        if not d.dependents:
            problems.append("a blocked source must list the dependents it disables")
        if source_enabled:
            problems.append(f"{d.source_id} is blocked but enabled in the state config")
    elif d.licence.status == "unverified" or d.history.status == "not_public":
        problems.append("an available source needs a known licence and published history")
    return problems
