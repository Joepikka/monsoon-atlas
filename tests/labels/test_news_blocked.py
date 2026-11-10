"""T189 to T208: the twenty news annotation batches are one recorded blocked batch (D155)."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from atlas.config import load_yaml
from atlas.ingest.base import SourceUnavailable
from atlas.ingest.discovery import Discovery
from atlas.ingest.s41 import S41

ROOT = Path(__file__).resolve().parents[2]
RECORD = json.loads((ROOT / "eval/news/blocked.json").read_text("utf-8"))
PAGE = (ROOT / "reports/labels/news.md").read_text("utf-8")
BATCHES = range(1, 21)


def test_s41_is_still_blocked_and_its_adapter_still_raises():
    assert load_yaml(ROOT / "configs/sources/s41.yaml", Discovery).outcome == "blocked"
    with pytest.raises(SourceUnavailable, match="S41 is blocked"):
        S41().fetch(object())
    with pytest.raises(SourceUnavailable, match="S41 is blocked"):
        S41().parse(object(), object())


def test_evidence_hashes_match_the_s41_files_on_disk():
    assert set(RECORD["evidence"]) == {
        "configs/sources/s41.yaml",
        "tests/fixtures/s41/manifest.json",
    }
    for name, sha in RECORD["evidence"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, name


def test_record_counts_are_all_zero_and_requirements_match_the_plan():
    counts = RECORD["counts"]
    assert RECORD["status"] == "blocked" and RECORD["blocking"]["owner_step"] == "H13"
    zero = (
        "articles_selected",
        "records_labelled",
        "records_reviewed_by_owner",
        "batches_completed",
    )
    assert [counts[k] for k in zero] == [0, 0, 0, 0]
    assert (counts["batches"], counts["required_per_batch"], counts["required_total"]) == (
        20,
        50,
        1000,
    )


@pytest.mark.parametrize("batch", BATCHES)
def test_batch_is_recorded_blocked_and_no_file_exists(batch):
    task = RECORD["tasks"][batch - 1]
    assert task == {
        "task": f"T{188 + batch}",
        "batch": batch,
        "planned_file": f"eval/news/batch_{batch:02d}.jsonl",
    }
    assert not (ROOT / task["planned_file"]).exists()
    assert not (ROOT / f"reports/labels/news_{batch:02d}.md").exists()
    assert not list((ROOT / "eval/news").glob("batch_*.jsonl"))


def test_page_numbers_equal_the_record():
    counts = RECORD["counts"]
    rows = dict(re.findall(r"^\| ([A-Za-z ]+) \| (\d+) \|$", PAGE, re.M))
    assert {k: int(v) for k, v in rows.items()} == {
        "Batches": counts["batches"],
        "Required per batch": counts["required_per_batch"],
        "Required in total": counts["required_total"],
        "Articles selected": counts["articles_selected"],
        "Records labelled": counts["records_labelled"],
        "Records reviewed by the owner": counts["records_reviewed_by_owner"],
        "Batches completed": counts["batches_completed"],
    }
    assert "none is done" in PAGE and "S41" in PAGE and "H13" in PAGE
