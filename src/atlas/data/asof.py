"""Point-in-time ("as-of") joins and local-time conversion (plan section 4, T005).

A feature row issued at time t may only use observations whose available_at <= t. Among those,
the latest valid time wins, and for one valid time the latest revision known by t wins. A
revision published after t can therefore never enter a prediction issued at t.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import duckdb
import pyarrow as pa

from atlas.config import DISPLAY_TZ


def local_midnight_utc(day: date, tz: str = DISPLAY_TZ) -> datetime:
    """00:00 local time on `day`, in UTC. 2024-07-02 IST midnight -> 2024-07-01T18:30Z."""
    return datetime.combine(day, time(0), tzinfo=ZoneInfo(tz)).astimezone(UTC)


def local_to_utc(value: datetime, tz: str = DISPLAY_TZ) -> datetime:
    """Interpret a naive provider timestamp as local time and convert it to UTC."""
    if value.tzinfo is not None:
        raise ValueError("expected a naive local timestamp")
    return value.replace(tzinfo=ZoneInfo(tz)).astimezone(UTC)


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def asof_join(
    spine: pa.Table,
    obs: pa.Table,
    *,
    by: str,
    values: Sequence[str],
    issue_col: str = "issue_at",
    allow_future_valid: bool = False,
) -> pa.Table:
    """Attach to each spine row the observation known at its issue time.

    Output = spine columns + `values` + obs_valid_at, obs_available_at, obs_snapshot_id and
    missing_reason. Unmatched rows keep null values with missing_reason='not_yet_available';
    nulls are never filled. Forecast-style observations (valid_at after issue) are excluded
    unless allow_future_valid=True.
    """
    spine = spine.append_column("_row", pa.array(range(spine.num_rows), pa.int64()))
    issue = f"s.{_q(issue_col)}"
    future = "" if allow_future_valid else f"AND (o.valid_at IS NULL OR o.valid_at <= {issue})"
    picked = ", ".join(f"c.{_q(v)}" for v in values)
    con = duckdb.connect()
    try:
        con.execute("SET TimeZone = 'UTC'")
        con.register("spine", spine)
        con.register("obs", obs)
        sql = f"""
            WITH cand AS (
                SELECT s._row, o.*,
                       row_number() OVER (
                           PARTITION BY s._row
                           ORDER BY o.valid_at DESC NULLS LAST, o.available_at DESC,
                                    o.snapshot_id DESC
                       ) AS _rn
                FROM spine s
                JOIN obs o ON o.{_q(by)} = s.{_q(by)} AND o.available_at <= {issue} {future}
            )
            SELECT s.* EXCLUDE (_row), {picked},
                   c.valid_at AS obs_valid_at,
                   c.available_at AS obs_available_at,
                   c.snapshot_id AS obs_snapshot_id,
                   CASE WHEN c._row IS NULL THEN 'not_yet_available'
                        ELSE c.missing_reason END AS missing_reason
            FROM spine s
            LEFT JOIN cand c ON c._row = s._row AND c._rn = 1
            ORDER BY s._row
        """
        return con.execute(sql).to_arrow_table()
    finally:
        con.close()
