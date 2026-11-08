"""T257 (child of T046): accuracy rows and release checklist from evidence (D92).

Full T046 adds the web accuracy page, browser checks and deployment evidence.
"""

import json
import re
from pathlib import Path

from atlas.models.accuracy import OUTPUT, accuracy_rows, release_checks, render

ROOT = Path(__file__).resolve().parents[1]


def test_accuracy_rows_show_c1_c2_and_m06_with_unavailable_not_zero():
    rows = {row["model"]: row for row in accuracy_rows()}
    assert [rows[m]["core"] for m in ("M07", "M05", "M06")] == ["C1", "C2", "secondary"]
    release = json.loads((ROOT / "models/registry/M05/v1.json").read_text("utf-8"))
    m05 = rows["M05"]
    assert (m05["candidate"], m05["baseline_value"]) == (0.7320467345749282, 0.8082546179167789)
    assert m05["ci95"] == [release["improvement"]["lower95"], release["improvement"]["upper95"]]
    assert m05["test"] == "2020-01-01/2024-12-31" and "hindcast" in m05["status"]
    for blocked in ("M07", "M06"):
        values = [rows[blocked][k] for k in ("candidate", "baseline_value", "improvement", "ci95")]
        assert all(v is None or v == [] for v in values) and 0 not in values
    table = render().split("## Gate checks")[0]
    m06_line = next(line for line in table.splitlines() if line.startswith("| M06 "))
    assert "unavailable" in m06_line and "0.000" not in m06_line


def test_release_is_not_ready_while_any_check_is_not_pass():
    checks = {c["check"]: c["status"] for c in release_checks()}
    assert checks["C3 passes T181 English thresholds"] == "fail"  # reports/rag.md gate
    assert checks["C1 evaluation report and model card"] == "blocked"
    assert "**Release status: not releasable.**" in render()


def test_m05_card_uses_only_numbers_from_its_sources():
    # T258: the C2 model card; a standalone number must appear in a cited source.
    number = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
    card = (ROOT / "reports/models/m05-card.md").read_text("utf-8")
    sources = ["reports/models/m05.md", "models/registry/M05/v1.json", "docs/decisions.md"]
    known = {n for path in sources for n in number.findall((ROOT / path).read_text("utf-8"))}
    assert set(number.findall(card)) - known == set()
    checks = {c["check"]: c["status"] for c in release_checks()}
    assert checks["C2 evaluation report and model card"] == "pass"


def test_committed_checklist_matches_current_evidence():
    assert OUTPUT.read_text("utf-8") == render()
