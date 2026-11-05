"""Storage quota and usage ledger (plan T006, section 6 "Storage arithmetic").

Storage status is measured from real bytes on disk, never from assumed compression:
  ok            below warn_at (80%)
  warn          at or above warn_at: keep ingesting, record it, reduce future capture cadence
  archive_only  at or above stop_at (95%): new ingestion is refused
Nothing is ever deleted to get back under quota; existing snapshots always survive.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from atlas import jsonl
from atlas.config import Budgets, StorageBudget

Status = Literal["ok", "warn", "archive_only"]
GB = 1024**3


class ArchiveOnly(RuntimeError):
    """Storage reached the stop threshold; new ingestion is paused, history is kept."""


def bytes_used(roots: Iterable[Path]) -> int:
    total = 0
    for root in roots:
        if Path(root).exists():
            total += sum(p.stat().st_size for p in Path(root).rglob("*") if p.is_file())
    return total


@dataclass(frozen=True)
class StorageQuota:
    roots: tuple[Path, ...]
    budget_bytes: int
    warn_at: float
    stop_at: float

    @classmethod
    def from_budget(cls, roots: Iterable[Path], budget: StorageBudget) -> StorageQuota:
        return cls(
            roots=tuple(Path(r) for r in roots),
            budget_bytes=int(budget.archive_budget_gb * GB),
            warn_at=budget.warn_at_fraction,
            stop_at=budget.stop_at_fraction,
        )

    def used(self) -> int:
        return bytes_used(self.roots)

    def status(self, extra_bytes: int = 0) -> Status:
        fraction = (self.used() + extra_bytes) / self.budget_bytes
        if fraction >= self.stop_at:
            return "archive_only"
        return "warn" if fraction >= self.warn_at else "ok"

    def ensure_can_ingest(self, incoming_bytes: int = 0) -> Status:
        """Raise ArchiveOnly if this write would reach the stop threshold. Never deletes."""
        status = self.status(incoming_bytes)
        if status == "archive_only":
            raise ArchiveOnly(
                f"storage at or above {self.stop_at:.0%} of {self.budget_bytes / GB:.1f} GB; "
                "new ingestion paused (archive-only). Existing snapshots are kept."
            )
        return status


class QuotaLedger:
    """Append-only JSONL usage ledger: one line per recorded use of a free-tier service."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def record(self, service: str, metric: str, amount: float, at: datetime | None = None) -> None:
        at = at or datetime.now(UTC)
        if at.utcoffset() is None or at.utcoffset().total_seconds() != 0:
            raise ValueError("ledger timestamps must be UTC")
        jsonl.append(
            self.path,
            {"at": at.isoformat(), "service": service, "metric": metric, "amount": amount},
        )

    def totals(self, day: date) -> dict[tuple[str, str], float]:
        out: dict[tuple[str, str], float] = {}
        for e in jsonl.read(self.path):
            if datetime.fromisoformat(e["at"]).date() == day:
                key = (e["service"], e["metric"])
                out[key] = out.get(key, 0) + e["amount"]
        return out


def daily_caps(budgets: Budgets) -> dict[tuple[str, str], float]:
    """Per-day caps from budgets.yaml that the ledger can be checked against."""
    caps: dict[tuple[str, str], float] = {}
    for service, model in budgets:
        for metric, value in model:
            if metric.endswith("_per_day"):
                caps[(service, metric.removesuffix("_per_day"))] = value
    return caps


def check(budgets: Budgets, ledger: QuotaLedger, quota: StorageQuota, day: date) -> dict:
    used = ledger.totals(day)
    services = []
    for (service, metric), cap in sorted(daily_caps(budgets).items()):
        amount = used.get((service, metric), 0)
        services.append(
            {"service": service, "metric": metric, "used": amount, "cap": cap, "over": amount > cap}
        )
    return {
        "storage_status": quota.status(),
        "storage_used_bytes": quota.used(),
        "storage_budget_bytes": quota.budget_bytes,
        "services": services,
    }
