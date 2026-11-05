"""Feature specs and as-of feature building (T033).

A feature for a unit issued at time t aggregates one source field over a window that ends
`lag_days` before t, using only rows known at t:

- rule "available_at": rows with available_at <= t (live data, the default);
- rule "valid_plus_lag": rows with valid_at + publication_lag_days <= t, for hindcasts that
  rebuild history from data fetched later (for example ERA5's ~6-day lag, T011). Such features
  must be labelled hindcasts (plan D07).

Every feature column comes with `<name>__known_at`, the latest time an input row became known;
`assert_as_of` fails if any of those is after the issue time.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import duckdb
import pyarrow as pa
from pydantic import Field

from atlas.contracts import SourceId, Strict

AGGREGATIONS = {"sum": "sum", "mean": "avg", "max": "max", "min": "min", "count": "count"}


class LeakageError(ValueError):
    """A feature used information that was not known at its issue time."""


class FeatureSpec(Strict):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    source: SourceId
    field: str = Field(min_length=1)
    lag_days: int = Field(ge=0)
    window_days: int = Field(ge=1)
    aggregation: Literal["sum", "mean", "max", "min", "count"]
    available_rule: Literal["available_at", "valid_plus_lag"] = "available_at"
    publication_lag_days: int = Field(default=0, ge=0)


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def build_features(
    spine: pa.Table, obs: pa.Table, specs: Sequence[FeatureSpec], *, unit: str = "unit_id"
) -> pa.Table:
    """spine(unit, issue_at) + one column per spec and its __known_at column.

    `obs` has unit, source_id, valid_at, available_at and the spec fields. A window with no
    known rows gives null, never zero.
    """
    names = [s.name for s in specs]
    if len(set(names)) != len(names):
        raise ValueError("feature names must be unique")
    spine = spine.append_column("_row", pa.array(range(spine.num_rows), pa.int64()))
    parts = []
    for s in specs:
        known = (
            "o.available_at <= s.issue_at"
            if s.available_rule == "available_at"
            else f"o.valid_at + INTERVAL {s.publication_lag_days} DAY <= s.issue_at"
        )
        end = f"s.issue_at - INTERVAL {s.lag_days} DAY"
        start = f"s.issue_at - INTERVAL {s.lag_days + s.window_days} DAY"
        value = f"o.{_q(s.field)}"
        parts.append(
            f"""(SELECT {AGGREGATIONS[s.aggregation]}({value}) FROM obs o
                 WHERE o.{_q(unit)} = s.{_q(unit)} AND o.source_id = '{s.source}'
                   AND o.valid_at > {start} AND o.valid_at <= {end} AND {known}
                   AND {value} IS NOT NULL) AS {_q(s.name)},
                (SELECT max(CASE WHEN '{s.available_rule}' = 'available_at' THEN o.available_at
                                 ELSE o.valid_at + INTERVAL {s.publication_lag_days} DAY END)
                 FROM obs o
                 WHERE o.{_q(unit)} = s.{_q(unit)} AND o.source_id = '{s.source}'
                   AND o.valid_at > {start} AND o.valid_at <= {end} AND {known}
                   AND {value} IS NOT NULL) AS {_q(s.name + "__known_at")}"""
        )
    con = duckdb.connect()
    try:
        con.execute("SET TimeZone = 'UTC'")
        con.register("spine", spine)
        con.register("obs", obs)
        sql = f"SELECT s.* EXCLUDE (_row), {', '.join(parts)} FROM spine s ORDER BY s._row"
        return con.execute(sql).to_arrow_table()
    finally:
        con.close()


def assert_as_of(features: pa.Table, names: Sequence[str]) -> None:
    """Raise LeakageError if any feature used a row known after its issue time."""
    issue = features["issue_at"].to_pylist()
    for name in names:
        known = features[f"{name}__known_at"].to_pylist()
        late = [
            i for i, (k, t) in enumerate(zip(known, issue, strict=True)) if k is not None and k > t
        ]
        if late:
            raise LeakageError(
                f"{name}: {len(late)} rows use data known after issue (row {late[0]})"
            )
