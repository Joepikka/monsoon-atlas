"""T256 (child of T225): core case studies follow the plan outline with real numbers only."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Plan section 17 case-study outline, in order.
OUTLINE = [
    "Problem and intended use",
    "Data and label provenance",
    "Target definition",
    "Time split",
    "Baselines",
    "Hypothesis and candidate",
    "Leakage audit",
    "Metrics",
    "Failure slices",
    "Computational cost",
    "Deployment decision",
    "Monitoring and retraining",
    "Reproducibility",
    "What changed after review",
    "One positive result, one negative lesson",
]
SOURCES = {
    "m05-case-study.md": [
        "reports/models/m05.md",
        "models/registry/M05/v1.json",
        "docs/decisions.md",
    ],
    "m07-case-study.md": [
        "docs/labels/kerala.md",
        "docs/sources/s32.md",
        "docs/sources/s32-history.md",
        "docs/sources/s34.md",
        "docs/sources/s34-ocr.md",
        "docs/decisions.md",
        "docs/amendments.md",
    ],
    "ask-case-study.md": ["reports/rag.md", "docs/ask.md", "docs/decisions.md"],
}
# A standalone number: not part of an identifier such as T130, Q41, D43 or a hash.
NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")


def numbers(text: str) -> set[str]:
    return {value.rstrip(".,") for value in NUMBER.findall(text)}


@pytest.mark.parametrize("name", sorted(SOURCES))
def test_case_study_follows_plan_outline(name):
    text = (ROOT / "reports/models" / name).read_text("utf-8")
    headings = re.findall(r"(?m)^## (.+)$", text)
    assert [next(h for h in headings if h.startswith(item)) for item in OUTLINE]
    positions = [next(i for i, h in enumerate(headings) if h.startswith(item)) for item in OUTLINE]
    assert positions == sorted(positions)
    assert re.search(r"(?m)^Status: ", text) and "H14" in text
    lesson = text.split("## One positive result, one negative lesson")[1]
    assert "- Positive:" in lesson and "- Negative:" in lesson


@pytest.mark.parametrize("name", sorted(SOURCES))
def test_every_number_appears_in_a_cited_source(name):
    text = (ROOT / "reports/models" / name).read_text("utf-8")
    known = set().union(*(numbers((ROOT / path).read_text("utf-8")) for path in SOURCES[name]))
    assert numbers(text) - known == set()
