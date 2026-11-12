"""T227: resumable KSEB date census. Run with the repository Python; no credentials.

Writes provenance/counts only. Raw HTML stays in the immutable local store.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.robotparser import RobotFileParser

from atlas.config import load_state
from atlas.contracts import Budget, FetchContext, RawArtifact
from atlas.ingest.base import IngestError
from atlas.ingest.http import USER_AGENT, Fetcher
from atlas.ingest.raw_store import RawStore
from atlas.ingest.s32 import HOSTS, MAPPING_VERSION, S32, URL

ROOT = Path(__file__).resolve().parents[1]


def dates(start: date, end: date):
    if start > end:
        raise ValueError("start must not be after end")
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)


def pacer(seconds: float, *, clock=time.monotonic, sleep=time.sleep):
    """An httpx request hook, applied to redirects and retries as well as first calls."""
    previous = None

    def pace(_request):
        nonlocal previous
        now = clock()
        if previous is not None:
            sleep(max(0.0, seconds - (now - previous)))
        previous = clock()

    return pace


def checkpoint(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def public_artifact(raw: RawArtifact, root: Path) -> dict:
    return raw.model_dump(mode="json") | {
        "path": raw.path.resolve().relative_to(root.resolve()).as_posix()
    }


def audit(start, end, output, config, fetcher, ctx, *, blocked=None, robots=None):
    if not config.enabled or config.source_id != "S32":
        raise ValueError("the verified S32 source must be enabled")
    # One ledger read, not one growing whole-ledger scan per date. Fetcher still owns writes.
    cache = {}
    for entry in fetcher.store.entries():
        raw = entry["artifact"]
        if raw["response_status"] in (200, 304):
            cache[raw["source_url"]] = raw
    result = {
        "source_id": "S32",
        "task": "T227",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "audited_at": datetime.now(UTC).isoformat(),
        "complete": False,
        "meaning": "data means rows in a report; valid/quarantined/incomplete counts are separate",
        "robots": robots,
        "days": [],
    }
    failures, fetched_bytes = 0, 0
    stop_reason = blocked
    requested = list(dates(start, end))
    for day in requested:
        url = f"{URL}?date={day.isoformat()}"
        row = {
            "date": day.isoformat(),
            "url": url,
            "outcome": "not_attempted",
            "rows": None,
            "valid": None,
            "quarantined": None,
            "incomplete": None,
            "artifact": None,
            "error": stop_reason,
            "reused": False,
        }
        if stop_reason is None:
            raw = None
            try:
                if url in cache:
                    raw = RawArtifact.model_validate(cache[url])
                    row["reused"] = True
                else:
                    raw = S32(config, day=day, fetcher=fetcher).fetch(ctx)[0]
                    fetched_bytes += raw.path.stat().st_size
                row["artifact"] = public_artifact(raw, ctx.raw_root)
                table = S32(config, day=day).parse(raw, config)
                reasons = Counter(table["missing_reason"].to_pylist())
                row.update(
                    outcome="data" if table.num_rows else "empty",
                    rows=table.num_rows,
                    valid=reasons[None],
                    quarantined=reasons["quality_rejected"],
                    incomplete=reasons["not_reported"],
                    error=None,
                )
                failures = 0
            except (IngestError, OSError, ValueError) as exc:
                failures += 1
                row.update(outcome="failed", error=f"{type(exc).__name__}: {exc}"[:300])
                if failures >= 3:
                    stop_reason = "Stopped after three consecutive failures: " + row["error"]
            if fetched_bytes >= 256 * 1024**2:
                stop_reason = "256 MiB run download budget reached"
        result["days"].append(row)
        checkpoint(output, result)
        if len(result["days"]) % 10 == 0 and stop_reason is None:
            counts = Counter(r["outcome"] for r in result["days"])
            print(f"{len(result['days'])}/{len(requested)} dates: {dict(counts)}", flush=True)
    result["complete"] = all(r["outcome"] in {"data", "empty"} for r in result["days"])
    result["summary"] = dict(Counter(r["outcome"] for r in result["days"]))
    result["stopped_reason"] = stop_reason
    checkpoint(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2024, 8, 15))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 7, 15))
    parser.add_argument("--output", type=Path, default=ROOT / "data/manifests/S32/history.json")
    args = parser.parse_args()
    if shutil.disk_usage(ROOT).free < 20 * 1024**3:
        raise SystemExit("At least 20 GiB free on the repository drive is required")
    config = load_state(ROOT / "configs/states/kl.yaml").source("S32")
    raw_root = ROOT / "data/raw"
    ctx = FetchContext(
        source_id="S32",
        state="kl",
        run_id=f"s32-history-{time.time_ns()}",
        requested_at=datetime.now(UTC),
        raw_root=raw_root,
        budget=Budget(max_requests=1000, max_bytes=1024**2),
    )
    fetcher = Fetcher(RawStore(raw_root), HOSTS)
    fetcher.client.event_hooks["request"] = [pacer(3.0)]
    blocked, robots_record = None, None
    try:
        raw = fetcher.fetch_bytes(
            ctx, "https://kseb.in/robots.txt", mapping_version=MAPPING_VERSION
        )
        rules = RobotFileParser()
        rules.parse(raw.path.read_text("utf-8").splitlines())
        allowed = rules.can_fetch(USER_AGENT, URL)
        robots_record = {"artifact": public_artifact(raw, raw_root), "allowed": allowed}
        if not allowed:
            blocked = "Current robots.txt does not allow the report path"
    except (IngestError, OSError, ValueError) as exc:
        blocked = f"robots.txt verification failed: {type(exc).__name__}: {exc}"[:300]
    try:
        result = audit(
            args.start,
            args.end,
            args.output,
            config,
            fetcher,
            ctx,
            blocked=blocked,
            robots=robots_record,
        )
    finally:
        fetcher.client.close()
    print(
        json.dumps(
            {
                "complete": result["complete"],
                "summary": result["summary"],
                "stopped_reason": result["stopped_reason"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
