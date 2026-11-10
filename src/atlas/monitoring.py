"""T219 (D163): drift, feed, quota and rollback checks as pure functions that return alerts.

Alerts go to an owner-run log (`deliver`) and the job summary of an owner-dispatched workflow. This
module sends nothing to any person or channel and imports no network or messaging library.
Prediction history is append-only: a rollback moves the manifest pointer and nothing else, and a
corrected label is a new ledger revision, never an edit of the old line.
"""

from __future__ import annotations

import bisect
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

from atlas import jsonl
from atlas.config import Budgets
from atlas.data.budget import QuotaLedger, StorageQuota
from atlas.data.budget import check as check_budgets
from atlas.data.manifest import ManifestStore
from atlas.data.store import verify_files

ROOT = Path(__file__).resolve().parents[2]
PSI_LIMIT = 0.2  # plan T219: review when PSI is above this in two consecutive windows
MAE_FACTOR = 1.2  # plan T219: review when residual MAE exceeds this times the frozen baseline MAE
MAE_DAYS = 14  # labelled days in the residual window
STALE_FACTOR = 2.0  # D163: a feed is stale after two stated cadences without a success
MISSING_LIMIT = 0.10  # D163: owner-tunable; the plan states no missingness limit


@dataclass(frozen=True)
class Alert:
    kind: str
    subject: str
    evidence: dict = field(default_factory=dict)
    action: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


# --- feeds ------------------------------------------------------------------------------------

_CADENCE = re.compile(r"^(?:every (\d+) (minute|hour)s?|(hourly)|(daily)|(weekly)|(monthly))\b")


def cadence_hours(schedule: str | None) -> float | None:
    """Hours between runs when the source record states a recurring cadence, else None."""
    m = _CADENCE.match(schedule or "")
    if not m:
        return None  # one-off, annual or on-demand: no recurring cadence is stated
    if m.group(1):
        return int(m.group(1)) / (60 if m.group(2) == "minute" else 1)
    return {"hourly": 1.0, "daily": 24.0, "weekly": 168.0, "monthly": 720.0}[m.group(0).split()[0]]


def feed_age_alert(
    source_id: str, schedule: str | None, last_success: datetime | None, now: datetime
) -> Alert | None:
    cadence = cadence_hours(schedule)
    if cadence is None:
        return None
    age = None if last_success is None else (now - last_success).total_seconds() / 3600
    if age is not None and age <= STALE_FACTOR * cadence:
        return None
    evidence = {"cadence_hours": cadence, "age_hours": None if age is None else round(age, 2)}
    return Alert("feed_stale", source_id, evidence, "stop dependent models; check the feed log")


def missingness_alert(
    source_id: str, missing: int, expected: int, limit: float = MISSING_LIMIT
) -> Alert | None:
    """missing_fraction = missing / expected; an empty expectation is itself a failure."""
    if expected <= 0:
        evidence = {"missing_fraction": None, "reason": "no expected records"}
        return Alert("feed_missingness", source_id, evidence, "check the source")
    fraction = missing / expected
    if fraction <= limit:
        return None
    evidence = {"missing_fraction": round(fraction, 4), "missing": missing, "expected": expected}
    return Alert("feed_missingness", source_id, evidence | {"limit": limit}, "check the source")


def schema_alert(
    source_id: str, expected: Mapping[str, str], observed: Mapping[str, str]
) -> Alert | None:
    added = sorted(set(observed) - set(expected))
    removed = sorted(set(expected) - set(observed))
    retyped = sorted(k for k in set(expected) & set(observed) if expected[k] != observed[k])
    if not (added or removed or retyped):
        return None
    evidence = {"added": added, "removed": removed, "retyped": retyped}
    return Alert("feed_schema_change", source_id, evidence, "hold the adapter; review the change")


def model_sources(root: Path = ROOT) -> dict[str, list[str]]:
    """Source IDs each model reads, from configs/models/*.yaml (M16 lists only those it uses)."""
    out = {}
    for path in sorted((root / "configs/models").glob("m*.yaml")):
        cfg = yaml.safe_load(path.read_text("utf-8"))
        sources = cfg.get("sources", [cfg["rain_source"]] if "rain_source" in cfg else [])
        if isinstance(sources, dict):
            sources = [k for k, v in sources.items() if str(v).startswith("used")]
        out[cfg.get("model_id", path.stem.upper())] = list(sources)
    return out


def stopped_models(stale_sources: Sequence[str], deps: Mapping[str, Sequence[str]]) -> list[Alert]:
    """A stale feed stops every model that reads it."""
    return [
        Alert(
            "model_stopped",
            model,
            {"stale_sources": sorted(set(sources) & set(stale_sources))},
            "serve the baseline or nothing until the feed recovers",
        )
        for model, sources in sorted(deps.items())
        if set(sources) & set(stale_sources)
    ]


# --- model drift ------------------------------------------------------------------------------


def bin_edges(train: Sequence[float], bins: int = 10) -> list[float]:
    """Fixed interior quantile edges from the training window (ties collapse)."""
    ordered = sorted(train)
    return sorted({ordered[len(ordered) * i // bins] for i in range(1, bins)})


def psi(edges: Sequence[float], train: Sequence[float], window: Sequence[float]) -> float:
    def share(values: Sequence[float]) -> list[float]:
        counts = [0] * (len(edges) + 1)
        for v in values:
            counts[bisect.bisect_right(edges, v)] += 1
        return [max(c / len(values), 1e-4) for c in counts]

    return sum((a - e) * math.log(a / e) for e, a in zip(share(train), share(window), strict=True))


def psi_alert(
    model: str, feature: str, train: Sequence[float], windows: Sequence[Sequence[float]]
) -> Alert | None:
    """Review when PSI against the training bins is above 0.2 in the latest two windows."""
    if len(windows) < 2:
        return None
    edges = bin_edges(train)
    values = [psi(edges, train, w) for w in windows[-2:]]
    if not all(v > PSI_LIMIT for v in values):
        return None
    evidence = {"feature": feature, "psi": [round(v, 4) for v in values], "limit": PSI_LIMIT}
    return Alert("model_psi", model, evidence, "open a review; do not retrain automatically")


def frozen_baseline_mae(model_id: str = "M05", root: Path = ROOT) -> float:
    release = json.loads((root / f"models/registry/{model_id}/v1.json").read_text("utf-8"))
    return release["baseline_scores"]["mae"]


def mae_alert(model: str, observed_mae: float, baseline_mae: float) -> Alert | None:
    if observed_mae <= MAE_FACTOR * baseline_mae:
        return None
    evidence = {"mae": observed_mae, "baseline_mae": baseline_mae, "factor": MAE_FACTOR}
    return Alert("model_residual", model, evidence, "open a review; the baseline stays served")


def residual_alert(
    model: str, abs_errors: Mapping[date, float], baseline_mae: float
) -> Alert | None:
    """MAE over the latest 14 labelled days against 1.2 x the frozen baseline MAE."""
    if len(abs_errors) < MAE_DAYS:
        return None  # fewer than 14 labelled days: not assessable yet
    days = sorted(abs_errors)[-MAE_DAYS:]
    return mae_alert(model, sum(abs_errors[d] for d in days) / MAE_DAYS, baseline_mae)


# --- budgets ----------------------------------------------------------------------------------


def storage_alerts(
    budgets: Budgets, ledger: QuotaLedger, quota: StorageQuota, day: date
) -> list[Alert]:
    """Storage warns at 80% and is archive-only at 95% (D24); a service over its cap alerts."""
    report = check_budgets(budgets, ledger, quota, day)
    alerts = []
    if report["storage_status"] != "ok":
        used, cap = report["storage_used_bytes"], report["storage_budget_bytes"]
        action = (
            "reduce capture cadence"
            if report["storage_status"] == "warn"
            else "ingestion paused; nothing is deleted"
        )
        evidence = {"used_bytes": used, "budget_bytes": cap, "fraction": round(used / cap, 4)}
        alerts.append(Alert(f"storage_{report['storage_status']}", "storage", evidence, action))
    alerts += [
        Alert(
            "quota_over",
            f"{s['service']}.{s['metric']}",
            {"used": s["used"], "cap": s["cap"]},
            "pause calls until the next UTC day",
        )
        for s in report["services"]
        if s["over"]
    ]
    return alerts


# --- delivery ---------------------------------------------------------------------------------


def deliver(alerts: Sequence[Alert], log: Path, at: datetime | None = None) -> int:
    """Append alerts to the owner-run log. The only destination; nothing is sent to anyone."""
    at = at or datetime.now(UTC)
    for alert in alerts:
        jsonl.append(log, {"at": at.isoformat(), **alert.as_dict()})
    return len(alerts)


# --- rollback and corrections -----------------------------------------------------------------


def rollback_if_corrupt(store: ManifestStore) -> dict | None:
    """Verify the current release; if its files are corrupt, point `current` at the prior release.

    Prediction history, the ledger, old manifests and data files are not touched. Refuses when the
    prior release is also unverifiable. Returns None when the current release verifies.
    """
    current = store.current()
    if current is None:
        raise ValueError("no release is published")
    try:
        verify_files(current, store.data_root)
        return None
    except (ValueError, OSError) as exc:
        problem = str(exc)
    history = store.history()
    if not history:
        raise ValueError("current release is corrupt and there is no prior release")
    verify_files(store.load(history[0]), store.data_root)  # never roll back onto a bad release
    store.rollback()
    return {
        "from": current.release_id,
        "to": history[0],
        "problem": problem,
        "data_revision": store.current().data_revision,
    }


def append_correction(
    ledger: Path, prediction_id: str, label: float | str, reason: str, at: datetime
) -> int:
    """Add a corrected label as a new revision (1, 2, ...); the original line is never edited."""
    revision = 1 + sum(
        e.get("kind") == "label_correction" and e["prediction_id"] == prediction_id
        for e in jsonl.read(ledger)
    )
    jsonl.append(
        ledger,
        {
            "kind": "label_correction",
            "prediction_id": prediction_id,
            "revision": revision,
            "label": label,
            "reason": reason,
            "at": at.isoformat(),
        },
    )
    return revision


def current_label(ledger: Path, prediction_id: str):
    """The latest revision of a label: the newest correction, else the original label."""
    entries = [e for e in jsonl.read(ledger) if e.get("prediction_id") == prediction_id]
    corrections = [e for e in entries if e["kind"] == "label_correction"]
    if corrections:
        return max(corrections, key=lambda e: e["revision"])["label"]
    return next((e["label"] for e in entries if e["kind"] == "label"), None)


def write_report_revision(report_dir: Path, name: str, payload: dict) -> Path:
    """Write `<name>.r<N>.json` with the next revision number; earlier reports are retained."""
    report_dir.mkdir(parents=True, exist_ok=True)
    revisions = [
        int(m.group(1))
        for p in report_dir.glob(f"{name}.r*.json")
        if (m := re.fullmatch(rf"{re.escape(name)}\.r(\d+)\.json", p.name))
    ]
    path = report_dir / f"{name}.r{max(revisions, default=0) + 1}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", "utf-8", newline="\n")
    return path


# --- committed-state report (the monitor workflow) ---------------------------------------------


def committed_report(root: Path = ROOT, now: datetime | None = None) -> list[dict]:
    """Checks that need only the repository. Live feed logs and data/ are not in a checkout, so
    those rows say unavailable instead of passing."""
    now = now or datetime.now(UTC)
    monitor = json.loads((root / "models/registry/M05/v1.monitor-2025.json").read_text("utf-8"))
    baseline = frozen_baseline_mae("M05", root)
    alert = mae_alert("M05", monitor["mae"]["ridge"], baseline)
    rows = [
        {
            "check": "M05 2025 MAE against 1.2 x frozen baseline",
            "status": "alert" if alert else "ok",
            "detail": f"MAE {monitor['mae']['ridge']:.3f}, limit {MAE_FACTOR * baseline:.3f} "
            f"(frozen persistence MAE {baseline:.3f}; 12 months, a hindcast monitor, not 14 days)",
        },
        {
            "check": "Feed age and missingness",
            "status": "unavailable",
            "detail": "no feed success log in a clean checkout",
        },
        {
            "check": "Model PSI",
            "status": "unavailable",
            "detail": "no live issue-time predictions exist",
        },
    ]
    data = root / "data"
    if (data / "clean").exists():
        from atlas.config import load_budgets

        b = load_budgets(root / "configs/budgets.yaml")
        quota = StorageQuota.from_budget([data / "clean", data / "manifests"], b.storage)
        found = storage_alerts(b, QuotaLedger(data / "quota/ledger.jsonl"), quota, now.date())
        rows.append(
            {
                "check": "Storage and free-tier budgets",
                "status": "alert" if found else "ok",
                "detail": "; ".join(a.kind for a in found) or "within 80% and daily caps",
            }
        )
    else:
        rows.append(
            {
                "check": "Storage and free-tier budgets",
                "status": "unavailable",
                "detail": "no data/ directory in a clean checkout",
            }
        )
    return rows


def summary_markdown(rows: Sequence[dict]) -> str:
    lines = [
        "## Monsoon Atlas monitor (owner-run, committed state)",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    lines += [f"| {r['check']} | {r['status']} | {r['detail']} |" for r in rows]
    return "\n".join(lines) + "\n"


def main() -> int:
    rows = committed_report()
    print(summary_markdown(rows))
    return 1 if any(r["status"] == "alert" for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
