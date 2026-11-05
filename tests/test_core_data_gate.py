"""T222 acceptance: the GATE-CORE report lists each A4 check as pass or fail with evidence links,
agrees with the discovery records, and D17 is recorded when a check fails."""

import re
from pathlib import Path

from atlas.config import load_yaml
from atlas.ingest.discovery import Discovery

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs" / "gates" / "core_data_gate.md"
CHECKS = {
    "C1 KWRIS daily history": "s28",
    "C2 Bengaluru ward flood labels": "s43",
    "Ward boundary version": "s40",
}


def results() -> dict[str, str]:
    rows = re.findall(
        r"^\| (.+?) \| \*\*(Pass|Fail)\*\* \| (.+) \|$", GATE.read_text("utf-8"), re.M
    )
    return {name: result for name, result, _ in rows}


def test_every_check_has_a_result():
    assert set(results()) == set(CHECKS)


def test_results_follow_discovery_records():
    for check, source in CHECKS.items():
        d = load_yaml(ROOT / "configs" / "sources" / f"{source}.yaml", Discovery)
        expected = "Pass" if d.outcome == "available" else "Fail"
        assert results()[check] == expected, check


def test_evidence_links_resolve():
    links = re.findall(r"\]\(([^)#]+)\)", GATE.read_text("utf-8"))
    assert links
    for link in links:
        assert (GATE.parent / link).resolve().exists(), link


def test_d17_recorded_when_a_check_fails():
    d17 = next(
        line
        for line in (ROOT / "docs" / "decisions.md").read_text("utf-8").splitlines()
        if line.startswith("| D17 |")
    )
    if "Fail" in results().values():
        assert "reserved" not in d17
        assert "M07" in d17 and "M08" in d17
        assert "H11" in d17  # owner approval is still required
