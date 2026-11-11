"""T224: ten business-style questions answered with DuckDB SQL over data we actually hold.

Queries live in `sql/insights/qNN_<slug>.sql`; each starts with a comment header (question, source,
unit, range, denominator, caveat, inputs) that becomes the caption in `reports/sql_insights.md`.
Inputs are DuckDB views: `committed` ones read files tracked in git (they run in CI), `local` ones
are built by the existing adapters from `data/raw` (never committed). Restricted sources (S08 IMD)
enter only as an index (per-district mean grid/gauge ratio), never as millimetres (D129, D131). No
query reads a blocked source (D105); those questions are listed under "Not answerable".

Run from the repository root: .venv/Scripts/python -m atlas.analysis.sql_insights
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb

from atlas.config import load_state
from atlas.contracts import RawArtifact

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
SQL_DIR = ROOT / "sql" / "insights"
REPORT = ROOT / "reports" / "sql_insights.md"
FIELDS = ("question", "source", "unit", "range", "denominator", "caveat", "inputs")
# (question from the spec or its spirit, blocking sources, why it cannot be answered)
NOT_ANSWERABLE = [
    (
        "Which reservoirs filled fastest after the heaviest 3-day rain?",
        "S28 (KWRIS daily reservoir levels), S43",
        "No daily reservoir history: S28 is blocked (D105) and the S32 KSEB reports we hold are "
        "sampled about every 15 days, so a 3-day rain window cannot be paired with a fill rate.",
    ),
    (
        "How many of the rain-flood events were followed by a price spike in the nearest market?",
        "S22, S23 (market prices), flood labels",
        "S22 and S23 are blocked, so there are no price rows, and flood labels are blocked.",
    ),
]


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("SET memory_limit='4GB'")
    con.execute("SET threads=4")
    return con


def artifact(source: str, eid: str, mapping: str) -> RawArtifact:
    manifest = json.loads((ROOT / f"tests/fixtures/{source}/manifest.json").read_text("utf-8"))
    e = next(x for x in manifest["evidence"] if x["id"] == eid)
    return RawArtifact(
        sha256=e["sha256"],
        path=RAW / e["raw_path"],
        fetched_at=e["fetched_at"],
        media_type=e["media_type"],
        response_status=e["status"],
        source_url=e["url"],
        schema_mapping_version=mapping,
    )


def committed_views(con: duckdb.DuckDBPyConnection) -> None:
    eda = (ROOT / "reports/eda").as_posix()
    con.execute(
        f"""CREATE VIEW s29_gauge AS
        SELECT district, year::INTEGER AS year, gauge_mm, status
        FROM read_csv('{eda}/02_ka_rain/district_year_comparison.csv', header=true)"""
    )
    # S08 enters only as the index grid / gauge, as a per-district mean over several years (D169).
    con.execute(
        f"""CREATE VIEW s08_ratio_by_district AS
        SELECT district, years_compared::INTEGER AS years_compared,
               grid_wetter_years::INTEGER AS grid_wetter_years,
               grid_drier_years::INTEGER AS grid_drier_years, mean_ratio
        FROM read_csv('{eda}/02_ka_rain/district_ratio_summary.csv', header=true)"""
    )
    con.execute(
        f"""CREATE VIEW s29_stations_2023 AS
        SELECT district, stations::INTEGER AS stations, with_value::INTEGER AS with_value
        FROM read_csv('{eda}/02_ka_rain/station_coverage_2023.csv', header=true)"""
    )
    con.execute(
        f"""CREATE VIEW s06_model_change AS
        SELECT point, model, base_mm, future_mm, change_pct
        FROM read_csv('{eda}/07_climate/s06_model_change.csv', header=true)"""
    )
    m05 = (ROOT / "models/registry/M05").as_posix()
    con.execute(f"CREATE VIEW m05_eval AS SELECT * FROM read_json('{m05}/v1.evaluation.json')")
    con.execute(f"CREATE VIEW m05_2025 AS SELECT * FROM read_json('{m05}/v1.monitor-2025.json')")


def local_ready() -> bool:
    return all((RAW / d).is_dir() for d in ("S21", "S32", "S44"))


def local_views(con: duckdb.DuckDBPyConnection) -> None:
    """Parse the pinned raw files with the existing adapters (needs data/raw; local only)."""
    from datetime import date
    from urllib.parse import parse_qs, urlsplit

    import pyarrow as pa

    from atlas.ingest.s21 import S21
    from atlas.ingest.s32 import S32
    from atlas.ingest.s44 import S44

    ka, kl = (load_state(ROOT / f"configs/states/{s}.yaml") for s in ("ka", "kl"))
    crime = pa.concat_tables(
        [
            S44("ka").parse(artifact("s44", eid, "s44-v1"), ka.source("S44"), year=y)
            for eid, y in (("e05", 2023), ("e04", 2024))
        ]
    )
    con.register(
        "s44_arrow",
        crime.select(["district_id", "unit_kind", "year", "offence_category"] + ["count"]),
    )
    con.execute("CREATE VIEW s44_crime AS SELECT * FROM s44_arrow")

    manifest = json.loads((ROOT / "tests/fixtures/s32/manifest.json").read_text("utf-8"))
    tables = []
    for e in manifest["evidence"]:
        if "dashboard/view/waterlevel" not in e["url"] or e["media_type"] != "text/html":
            continue
        q = parse_qs(urlsplit(e["url"]).query).get("date")
        t = S32(kl.source("S32"), day=date.fromisoformat(q[0]) if q else None).parse(
            artifact("s32", e["id"], "s32-v1"), kl.source("S32")
        )
        tables.append(
            t.select(
                ["reservoir_name", "district_code", "date_local"]
                + ["level_m", "storage_mcm", "capacity_mcm"]
            )
        )
    con.register("s32_arrow", pa.concat_tables(tables))
    con.execute("CREATE VIEW s32_reservoir AS SELECT * FROM s32_arrow")

    stops = S21("ka", "Karnataka").parse(
        artifact("s21", "e08", "s21-v1"),
        ka.source("S21"),
        stations=artifact("s21", "e06", "s21-v1"),
    )
    con.register(
        "s21_arrow", stops.select(["station_id", "train_id", "stop_sequence", "departure_text"])
    )
    con.execute("CREATE VIEW s21_stops AS SELECT * FROM s21_arrow")


def parse_header(path: Path) -> dict[str, str]:
    """`-- key: value` lines at the top of a query; `--   more` continues the previous value."""
    out: dict[str, str] = {}
    key = None
    for line in path.read_text("utf-8").splitlines():
        if not line.startswith("--"):
            break
        m = re.match(r"-- (\w+): (.*)", line)
        if m:
            key = m[1]
            out[key] = m[2].strip()
        elif key and line.startswith("--  "):
            out[key] += " " + line[2:].strip()
    return out


def queries() -> list[Path]:
    return sorted(SQL_DIR.glob("q[0-9][0-9]_*.sql"))


def run(con: duckdb.DuckDBPyConnection, path: Path) -> tuple[list[str], list[tuple]]:
    cur = con.execute(path.read_text("utf-8"))
    return [d[0] for d in cur.description], cur.fetchall()


def cell(v) -> str:
    return "n/a" if v is None else str(v)


def section(path: Path, cols: list[str], rows: list[tuple]) -> str:
    h = parse_header(path)
    lines = [f"## {path.stem[:3].upper()}. {h['question']}", ""]
    lines += [f"- **{k.capitalize()}:** {h[k]}" for k in FIELDS[1:6]]
    lines += ["", f"Query: `sql/insights/{path.name}`", ""]
    lines += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def build(only: str | None = None) -> dict[str, str]:
    """Query stem -> report section. `only='committed'` skips the local-only queries."""
    con = connect()
    committed_views(con)
    if only != "committed":
        local_views(con)
    out = {}
    for p in queries():
        if only == "committed" and parse_header(p)["inputs"] != "committed":
            continue
        out[p.stem] = section(p, *run(con, p))
    return out


def report(sections: dict[str, str]) -> str:
    head = [
        "# SQL insights report (T224)",
        "",
        "Ten questions answered with DuckDB SQL over the data we hold. Every table below is "
        "regenerated by `.venv/Scripts/python -m atlas.analysis.sql_insights`; `inputs: local` "
        "queries need `data/raw` (not in git), `inputs: committed` ones run in CI. Counts are "
        "exact; nothing is imputed. The S08 IMD grid appears only as an index (grid / gauge "
        "ratio), never as millimetres, and H11 item 3 still decides its publication (D105, "
        "D129). Registered crime cases are not crime incidence. S32 results (Q08, Q09) derive "
        "from KSEB pages under CC BY-SA 2.5 India: credit KSEB, share alike. Substitutions for "
        "the spec's example questions: D131.",
        "",
    ]
    tail = ["## Not answerable", ""]
    tail += [f"- **{q}** Blocked by {src}. {why}" for q, src, why in NOT_ANSWERABLE]
    return "\n".join(head) + "\n" + "\n".join(sections.values()) + "\n" + "\n".join(tail) + "\n"


def main() -> None:
    REPORT.write_text(report(build()), "utf-8", newline="\n")
    print("wrote", REPORT)


if __name__ == "__main__":
    main()
