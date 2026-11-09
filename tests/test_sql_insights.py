"""T224: SQL insights run on DuckDB 1.x, match the report, carry captions, no blocked source."""

import re

import duckdb
import pytest
import yaml

from atlas.analysis import sql_insights as si

REPORT = si.REPORT.read_text("utf-8")


def blocked_sources() -> set[str]:
    out = set()
    for p in (si.ROOT / "configs/sources").glob("s*.yaml"):
        record = yaml.safe_load(p.read_text("utf-8"))
        if record.get("outcome") == "blocked":
            out.add(record["source_id"])
    return out


def test_ten_queries_with_full_captions():
    paths = si.queries()
    assert len(paths) == 10
    for p in paths:
        h = si.parse_header(p)
        assert all(h.get(k) for k in si.FIELDS), p.name
        assert re.search(r"\d", h["denominator"]), p.name
        assert h["inputs"] in {"committed", "local"}, p.name
        assert re.search(r"\b(S\d\d|M05)\b", h["source"]), p.name


def test_duckdb_is_1x():
    assert duckdb.__version__.startswith("1.")


def test_no_blocked_source_and_no_restricted_millimetres():
    blocked = blocked_sources()
    assert {"S22", "S23", "S28", "S43"} <= blocked
    for p in si.queries():
        text = p.read_text("utf-8")
        assert not blocked & set(re.findall(r"\bS\d\d\b", text)), p.name
        assert not re.search(r"grid_mm|bias_mm", text), p.name


def test_report_lists_every_caption_and_what_is_not_answerable():
    for p in si.queries():
        h = si.parse_header(p)
        for k in si.FIELDS[1:6]:
            assert f"- **{k.capitalize()}:** {h[k]}" in REPORT, (p.name, k)
    assert "## Not answerable" in REPORT
    for _, sources, _ in si.NOT_ANSWERABLE:
        assert sources.split(" ")[0] in REPORT


def test_committed_results_match_the_report():
    sections = si.build("committed")
    assert len(sections) == 6
    for stem, text in sections.items():
        assert text in REPORT, stem


@pytest.mark.skipif(not si.local_ready(), reason="needs data/raw (local only, never in git)")
def test_local_results_match_the_report():
    sections = si.build()
    assert len(sections) == 10
    assert si.report(sections) == REPORT
