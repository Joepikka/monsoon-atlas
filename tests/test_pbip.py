"""T223: the Power BI project is generated, deterministic and honest about blocked sources."""

import csv
import filecmp
import importlib.util
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_pbip", ROOT / "powerbi" / "build_pbip.py")
bp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bp)

PROJECT = ROOT / "powerbi"
FOLDER = re.search(
    r'DataFolder = "(.*?)"',
    (PROJECT / "MonsoonAtlas.SemanticModel/definition/expressions.tmdl").read_text("utf-8"),
).group(1)


def blocked_sources() -> set[str]:
    out = set()
    for p in (ROOT / "configs/sources").glob("s*.yaml"):
        record = yaml.safe_load(p.read_text("utf-8"))
        if record.get("outcome") == "blocked":
            out.add(record["source_id"])
    return out


def files(base: Path) -> set[str]:
    return {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()}


def test_generator_is_deterministic_and_matches_committed(tmp_path):
    for run in ("a", "b"):
        bp.build(tmp_path / run, FOLDER)
        bp.write_data(tmp_path / run / "data")
    assert files(tmp_path / "a") == files(tmp_path / "b")
    assert all(
        filecmp.cmp(tmp_path / "a" / f, tmp_path / "b" / f, shallow=False)
        for f in files(tmp_path / "a")
    )
    for f in files(tmp_path / "a"):
        rel = Path(f)
        committed = bp.DATA / rel.relative_to("data") if rel.parts[0] == "data" else PROJECT / rel
        assert filecmp.cmp(tmp_path / "a" / f, committed, shallow=False), f


def test_every_project_json_parses():
    paths = [
        p
        for p in PROJECT.rglob("*")
        if p.is_file() and p.suffix in {".json", ".pbip", ".pbir", ".pbism"}
    ]
    assert len(paths) > 15
    for p in paths:
        json.loads(p.read_text("utf-8"))


def test_four_pages_in_order():
    pages = json.loads(
        (PROJECT / "MonsoonAtlas.Report/definition/pages/pages.json").read_text("utf-8")
    )
    assert pages["pageOrder"] == ["reservoirs", "rain", "prices", "accuracy"]


def visuals():
    base = PROJECT / "MonsoonAtlas.Report/definition/pages"
    for p in sorted(base.glob("*/visuals/*/visual.json")):
        yield p.parts[-4], json.loads(p.read_text("utf-8"))


def test_every_data_visual_reads_an_existing_nonempty_csv():
    seen = set()
    for page, v in visuals():
        for role in v["visual"].get("query", {}).get("queryState", {}).values():
            for item in role["projections"]:
                field = next(iter(item["field"].values()))
                seen.add((page, field["Expression"]["SourceRef"]["Entity"], field["Property"]))
    assert seen
    for page, entity, prop in seen:
        csv_name, _, cols, measures = bp.TABLES[entity]
        assert prop in {c for c, _ in cols} | {m for m, *_ in measures}, (page, entity, prop)
        with (bp.DATA / csv_name).open(encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        assert [c for c, _ in cols] == rows[0] and len(rows) > 1, csv_name


def test_no_blocked_source_or_restricted_value_as_data():
    blocked = blocked_sources()
    assert {"S22", "S23", "S28", "S43"} <= blocked
    for table, (csv_name, source, cols, _) in bp.TABLES.items():
        assert source not in blocked, table
        assert not {c for c, _ in cols} & {"grid_mm", "bias_mm", "ratio"}, table
        assert (bp.DATA / csv_name).exists()


def test_blocked_pages_carry_their_reason_and_no_data():
    blocked = blocked_sources()
    for key, (ids, reason) in bp.BLOCKED.items():
        assert set(ids.split()) <= blocked, key
        assert reason.startswith(("blocked", "M07"))
    for page, expected in (
        ("reservoirs", "S28"),
        ("rain", "S43"),
        ("prices", "S22"),
        ("accuracy", "M07"),
    ):
        text = " ".join(json.dumps(v) for p, v in visuals() if p == page)
        assert "Blocked:" in text and expected in text, page
    assert not [1 for p, v in visuals() if p == "prices" and v["visual"].get("query")]


def test_accuracy_matches_registry_and_report():
    gain = list(csv.DictReader((bp.DATA / "model_gain.csv").open(encoding="utf-8")))
    ka = (ROOT / "docs/releases/ka.md").read_text("utf-8")
    assert [r["promoted"] for r in gain] == ["yes", "yes"]
    assert "| M05 | C2 |" in ka and "0.732" in ka and "0.808" in ka
    assert gain[0]["mae_ridge"] == "0.732" and gain[0]["mae_baseline"] == "0.808"


def test_reservoir_rows_are_the_published_s32_sample():
    rows = list(csv.DictReader((bp.DATA / "reservoir_change.csv").open(encoding="utf-8")))
    assert len(rows) == 16 and {r["window"] for r in rows} == {
        w for w, _ in bp.RESERVOIR_WINDOWS.values()
    }
    assert all(
        abs(float(r["end_pct"]) - float(r["start_pct"]) - float(r["change_points"])) < 0.06
        for r in rows
    )


def test_no_service_publishing_or_credentials():
    text = " ".join(
        p.read_text("utf-8")
        for p in PROJECT.rglob("*")
        if p.is_file() and p.suffix not in {".csv", ".pyc"}
    )
    assert not re.search(r"powerbi\.com|api\.powerbi|tenant|token", text, re.I)


def test_district_rain_is_gauge_only():
    assert (bp.DATA / "district_rain.csv").read_text("utf-8").splitlines()[
        0
    ] == "district,year,gauge_mm"
