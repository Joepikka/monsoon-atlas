"""T108: market-price audit helpers with exact denominators.

The Karnataka price feeds (S22, S23) are blocked, so there are no price rows. Every measure
therefore reports its counts and, when a denominator is zero, a "not computable" status with the
reason; a share is None, never 0% and never filled. The unit audit reads the committed
discovery record of each source and changes nothing.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path

import yaml


def load_record(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def audit_rows(record: Mapping) -> list[dict]:
    """One row per discovery field_map entry: canonical field, upstream name, unit status."""
    return [
        {
            "source": record["source_id"],
            "canonical": f["canonical"],
            "upstream": f["upstream"] or "",
            "unit_status": f["unit_status"],
            "detail": f["detail"],
            "evidence": " ".join(f["evidence"]),
        }
        for f in record["field_map"]
    ]


def source_status(record: Mapping) -> dict:
    return {
        "source": record["source_id"],
        "discovered_at": record["discovered_at"],
        "outcome": record["outcome"],
        "licence": record["licence"]["status"],
        "history": record["history"]["status"],
        "earliest_date": record["earliest_date"],
        "latest_date": record["latest_date"],
        "units": record["units"]["status"],
        "retry_condition": " ".join(record["retry_condition"].split()),
    }


def measure(name: str, count: int, total: int, reason: str) -> dict:
    """count out of total; a zero total is not computable (share None), never 0%."""
    ok = total > 0
    return {
        "measure": name,
        "count": count,
        "n": total,
        "share": count / total if ok else None,
        "status": "computed" if ok else f"not computable: {reason}",
    }


def month_counts(dates: Iterable[date]) -> dict:
    """Price rows per calendar month (1-12) and the total they sum to."""
    by_month = Counter(d.month for d in dates)
    n = sum(by_month.values())
    return {"n": n, "by_month": {m: by_month.get(m, 0) for m in range(1, 13)} if n else None}


def label_summary(labels: Iterable[bool | None], reason: str) -> list[dict]:
    """Future-label coverage and spike prevalence; None = label unknown (never filled)."""
    labels = list(labels)
    labelled = [x for x in labels if x is not None]
    return [
        measure("future_label_coverage", len(labelled), len(labels), reason),
        measure("spike_prevalence", sum(labelled), len(labelled), reason),
    ]
