"""T255: computed numeric answers match independently recomputed gold (D90)."""

import pytest

from atlas.rag import numeric
from atlas.rag.evaluate import EVAL, numeric_gold, read_jsonl

CASES = {case["id"]: case for case in read_jsonl(EVAL / "snapshot_gold.jsonl")}


@pytest.mark.parametrize("case_id", ["N01", "N02", "N07"])
def test_numeric_templates_match_gold_exactly_with_file_citation(case_id):
    case, gold = CASES[case_id], numeric_gold(CASES[case_id])
    found = numeric.answer(case["question"])
    assert (found["status"], found["value"], found["unit"]) == (
        "answered",
        gold["value"],
        gold["unit"],
    )
    assert found["citations"] == [gold["path"]] and found["mode"] == "computed"


@pytest.mark.parametrize("case_id", ["N03", "N04", "N05", "N06", "N08", "N09", "N10"])
def test_blocked_or_unpublished_numeric_questions_are_not_computed(case_id):
    assert numeric.answer(CASES[case_id]["question"]) is None


@pytest.mark.parametrize(
    "question",
    [
        "What is the most recent ERA5 rainfall value for Mysuru as of 2026-11-04?",
        "What is the most recent ERA5 rainfall value for Bengaluru as of 2026-10-01?",
        "How much better was the M02 reservoir model than persistence?",
        "What does SPI-3 measure?",
    ],
)
def test_unknown_place_model_or_time_stays_unanswered(question):
    assert numeric.answer(question) is None


def test_time_and_place_change_computed_alerts_and_rain():
    alerts = "Which official alerts are active for {} at {}?"
    assert numeric.answer(alerts.format("Bengaluru Urban", "2026-11-05T13:00:00Z"))["value"] == []
    assert numeric.answer(alerts.format("Mysuru", "2026-11-05T14:00:00Z"))["value"] == []
    rain = numeric.answer(
        "What is the most recent ERA5 rainfall value for Bengaluru as of 2026-10-24?"
    )
    assert (rain["value"], rain["date"]) == (37.6, "2026-10-24")
