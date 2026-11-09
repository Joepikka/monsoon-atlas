"""Common envelope validation and contract versioning (plan section 7, T005).

Every normalized source table carries the envelope in schemas/common.json plus its own measure
columns. A null measure is never zero: it must carry a missing_reason, and a row with a
missing_reason must have null measures.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from functools import cache
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas"
SUPPORTED_SCHEMA_VERSIONS = frozenset({1})
MAPPING_KEY = b"atlas.mapping"
TS = pa.timestamp("us", tz="UTC")
_TYPES = {
    "string": pa.string(),
    "int64": pa.int64(),
    "bool": pa.bool_(),
    "timestamp": TS,
    "list<string>": pa.list_(pa.string()),
}


class SchemaError(ValueError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


@cache
def common_spec() -> dict:
    return json.loads((SCHEMA_DIR / "common.json").read_text(encoding="utf-8"))


def envelope_schema() -> pa.Schema:
    return pa.schema(
        [pa.field(f["name"], _TYPES[f["type"]], f["nullable"]) for f in common_spec()["fields"]]
    )


def validate_table(table: pa.Table, *, measures: Sequence[str] = ()) -> pa.Table:
    """Return the table unchanged if it satisfies the envelope contract, else raise SchemaError."""
    spec, problems = common_spec(), []
    for field in envelope_schema():
        if field.name not in table.column_names:
            problems.append(f"missing envelope column {field.name}")
        elif table.schema.field(field.name).type != field.type:
            got = table.schema.field(field.name).type
            problems.append(f"{field.name}: type {got}, expected {field.type}")
        elif not field.nullable and table[field.name].null_count:
            problems.append(f"{field.name}: nulls in a required column")
    for m in measures:
        if m not in table.column_names:
            problems.append(f"missing measure column {m}")
    if problems:
        raise SchemaError(problems)

    enums = spec["enums"]
    for col in ("state", "provenance", "missing_reason"):
        allowed = pa.array(enums[col])
        bad = pc.drop_null(pc.filter(table[col], pc.invert(pc.is_in(table[col], allowed))))
        if len(bad):
            problems.append(f"{col}: invalid values {sorted(set(bad.to_pylist()))}")
    flags = pc.list_flatten(table["quality_flags"])
    bad_flags = set(flags.to_pylist()) - set(enums["quality_flags"])
    if bad_flags:
        problems.append(f"quality_flags: invalid values {sorted(bad_flags)}")

    versions = set(table["schema_version"].to_pylist()) - SUPPORTED_SCHEMA_VERSIONS
    if versions:
        problems.append(f"schema_version {sorted(versions)} not supported by this reader")

    has_reason = pc.is_valid(table["missing_reason"])
    flagged_missing = pa.array(
        ["missing" in flags for flags in table["quality_flags"].to_pylist()], type=pa.bool_()
    )
    for m in measures:
        null = pc.is_null(table[m])
        if pc.any(pc.and_(null, pc.invert(has_reason))).as_py():
            problems.append(f"{m}: null without missing_reason")
        if pc.any(pc.and_(pc.or_(has_reason, flagged_missing), pc.invert(null))).as_py():
            problems.append(f"{m}: value present on a row marked missing (missing is not 0)")

    early = pc.less(table["available_at"], table["fetched_at"])
    not_reconstructed = pc.not_equal(table["provenance"], "reconstructed")
    if pc.any(pc.and_(early, not_reconstructed)).as_py():
        problems.append("available_at before fetched_at requires provenance=reconstructed")

    try:
        dedupe_snapshots(table)
    except SchemaError as exc:
        problems.extend(exc.problems)
    if problems:
        raise SchemaError(problems)
    return table


def dedupe_snapshots(table: pa.Table) -> pa.Table:
    """Drop exact duplicate rows of the same (record_id, snapshot_id). A published snapshot is
    immutable, so the same key with different content is an error, not a revision."""
    keys = list(zip(table["record_id"].to_pylist(), table["snapshot_id"].to_pylist(), strict=True))
    if len(set(keys)) == len(keys):  # no repeated key: nothing to compare (large tables, S30)
        return table
    rows = table.to_pylist()
    seen: dict[tuple[str, str], dict] = {}
    keep = []
    for i, row in enumerate(rows):
        key = (row["record_id"], row["snapshot_id"])
        if key not in seen:
            seen[key] = row
            keep.append(i)
        elif seen[key] != row:
            raise SchemaError([f"snapshot {key} appears with different content"])
    return table.take(keep) if len(keep) != len(rows) else table


def with_mapping(table: pa.Table, provider_to_canonical: dict[str, str], mapping_version: str):
    """Record which provider field became which canonical column, in the Arrow schema metadata
    (survives Parquet round trips)."""
    meta = dict(table.schema.metadata or {})
    meta[MAPPING_KEY] = json.dumps(
        {"mapping_version": mapping_version, "provider_to_canonical": provider_to_canonical}
    ).encode()
    return table.replace_schema_metadata(meta)


def read_mapping(table: pa.Table) -> dict:
    raw = (table.schema.metadata or {}).get(MAPPING_KEY)
    if raw is None:
        raise SchemaError(["no provider mapping metadata"])
    return json.loads(raw)
