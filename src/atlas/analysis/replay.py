"""T142: 2018 Kerala flood replay records and their as-known / reconstructed mode (D127).

A record is "as_known" only when a real publication date (`known_from`) exists and falls on or
before the end of the replay window; in the as-known view it appears only from that date. Every
other record (gridded analyses, later fetches) is "reconstructed" and never shown as known at the
time. No forecast vintage is held for 2018, so the replay carries none.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date

import pyarrow as pa

LABEL = (
    "Descriptive replay of the 2018 Kerala floods, not a forecast. No historical forecast "
    "vintage is held, so none is shown; reconstructed records are later analyses."
)
MODES = ("as_known", "reconstructed")


def mode(known_from: date | None, window_end: date) -> str:
    return "as_known" if known_from is not None and known_from <= window_end else "reconstructed"


def as_known(records: Iterable[Mapping], cursor: date) -> list[Mapping]:
    """Records a reader could have seen on `cursor`: as-known ones published by then."""
    return [
        r
        for r in records
        if r["mode"] == "as_known" and date.fromisoformat(r["known_from"]) <= cursor
    ]


def validate(replay: Mapping) -> None:
    """The contract Replay.tsx also enforces: labels, modes and no forecast vintages."""
    end = date.fromisoformat(replay["window"]["end"])
    if replay["label"] != LABEL or replay["forecast_vintages"]:
        raise ValueError("replay must carry the label and no forecast vintage")
    for r in replay["records"]:
        if not r.get("source") or not r.get("vintage"):
            raise ValueError(f"{r['id']}: record without source or vintage")
        known = date.fromisoformat(r["known_from"]) if r["known_from"] else None
        if r["mode"] not in MODES or r["mode"] != mode(known, end):
            raise ValueError(f"{r['id']}: mode does not follow its publication date")


def daily_box_mean(table: pa.Table) -> dict[date, tuple[float, int]]:
    """S08 rows -> {day: (mean rain over cells with a value, cells with a value)}."""
    sums: dict[date, list[float]] = defaultdict(lambda: [0.0, 0])
    for d, v in zip(
        table.column("date_local").to_pylist(), table.column("rain_mm").to_pylist(), strict=True
    ):
        if v is not None:
            sums[d][0] += v
            sums[d][1] += 1
    return {d: (s / n, n) for d, (s, n) in sorted(sums.items())}
