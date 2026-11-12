"""T255: computed numeric Ask answers from frozen snapshots with DuckDB (D90)."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime

import duckdb

from atlas.rag.corpus import ROOT, load_config

# Only explicit templates are answered; anything else falls back to cited search results.
TEMPLATES = {
    "daily_rain": re.compile(
        r"\brain(?:fall)?\b.*?\bfor (?P<place>[A-Za-z][A-Za-z ]*?)\s*(?:\([^)]*\))?\s*"
        r"as of (?P<as_of>\d{4}-\d{2}-\d{2})\b",
        re.IGNORECASE,
    ),
    "alerts": re.compile(
        r"\balerts?\b.*?\bactive for (?P<place>[A-Za-z][A-Za-z ]*?) at "
        r"(?P<as_of>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)",
        re.IGNORECASE,
    ),
    "model_release": re.compile(
        r"\bhow much better\b.*?\b(?P<model>M\d{2})\b.*?\bpersistence\b", re.IGNORECASE
    ),
}


def _connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(config={"memory_limit": "4GB", "threads": 4})  # amendment A2


def _snapshot(kind: str, **match: str) -> dict | None:
    for item in load_config().get("snapshots", []):
        if item["kind"] != kind:
            continue
        if "place" in match and match["place"].lower() not in item.get("places", []):
            continue
        if "model" in match and item["source_id"] != match["model"]:
            continue
        return item
    return None


def answer(question: str) -> dict | None:
    """Return a computed, cited answer for a recognised template, else None."""
    for kind, pattern in TEMPLATES.items():
        found = pattern.search(question)
        if not found:
            continue
        fields = {k: v.strip() for k, v in found.groupdict().items()}
        if kind == "alerts":
            item = _snapshot(kind)
        else:
            item = _snapshot(kind, **{k: v for k, v in fields.items() if k != "as_of"})
        if item is None:
            return None
        path = str(ROOT / item["path"])
        with _connect() as db:
            if kind == "daily_rain":
                row = db.execute(
                    "WITH d AS (SELECT unnest(daily.time) AS day, "
                    "unnest(daily.precipitation_sum) AS rain, "
                    "daily_units.precipitation_sum AS unit FROM read_json_auto(?)) "
                    "SELECT day, rain, unit FROM d WHERE rain IS NOT NULL AND day <= ? "
                    "ORDER BY day DESC LIMIT 1",
                    [path, date.fromisoformat(fields["as_of"])],
                ).fetchone()
                if row is None:
                    return None
                day, value, unit = row
                text = f"{value:g} {unit} on {day.isoformat()} ({item['source_id']})"
                extra = {"date": day.isoformat()}
            elif kind == "alerts":
                moment = datetime.fromisoformat(fields["as_of"].replace("Z", "+00:00"))
                moment = moment.astimezone(UTC).replace(tzinfo=None)  # DuckDB reads Z as UTC
                rows = db.execute(
                    "SELECT id FROM read_json_auto(?) WHERE valid_at <= ? AND ? < expires_at "
                    "AND available_at <= ? AND (contains(lower(warning_text), ?) "
                    "OR contains(lower(area_text), ?)) ORDER BY id",
                    [
                        path,
                        moment,
                        moment,
                        moment,
                        fields["place"].lower(),
                        fields["place"].lower(),
                    ],
                ).fetchall()
                value, unit, extra = [r[0] for r in rows], item["unit"], {}
                text = f"{len(value)} active official alert(s): " + (", ".join(value) or "none")
            else:
                value = dict(
                    zip(
                        ("mean", "lower95", "upper95"),
                        db.execute(
                            "SELECT improvement.mean, improvement.lower95, improvement.upper95 "
                            "FROM read_json_auto(?)",
                            [path],
                        ).fetchone(),
                        strict=True,
                    )
                )
                unit, extra = item["unit"], {}
                text = (
                    f"{fields['model']} improved on persistence by {value['mean']:.3f} "
                    f"({unit}; 95% CI {value['lower95']:.3f} to {value['upper95']:.3f})"
                )
        return {
            "mode": "computed",
            "status": "answered",
            "answer": text,
            "value": value,
            "unit": unit,
            "citations": [item["path"]],
            **extra,
        }
    return None
