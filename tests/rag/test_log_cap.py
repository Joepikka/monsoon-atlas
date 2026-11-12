"""T265 (child of T179): append-only logs limited in Ask results (D100)."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from atlas.rag.corpus import Document, load_config
from atlas.rag.index import build_index
from atlas.rag.retrieve import retrieve

NOW = datetime(2026, 11, 8, 12, tzinfo=UTC)
BASE = Document(
    doc_id="log",
    path="log.md",
    kind="project",
    states=("ka",),
    licence="project-mit",
    language="en",
    text="",
    sha256="0" * 64,
    available_at="2026-11-01T00:00:00Z",
    commit="f" * 40,
)
LOG_TEXT = "# Log\n\n" + "\n\n".join(
    f"## Entry {n}\n\nmonsoon drought outlook rainfall note {n} monsoon drought" for n in range(6)
)


@pytest.fixture
def index(tmp_path):
    documents = [
        replace(BASE, doc_id="log", path="log.md", text=LOG_TEXT),
        replace(BASE, doc_id="a", path="a.md", text="# A\n\nmonsoon drought outlook for districts"),
        replace(BASE, doc_id="b", path="b.md", text="# B\n\nrainfall outlook and drought months"),
    ]
    path = tmp_path / "index.sqlite"
    build_index(documents, path)
    return path


def logs_in(found):
    return sum(row["doc_id"] == "log" for row in found)


def test_l0_keeps_two_per_document_and_l1_l2_keep_one_per_log(index):
    question = "monsoon drought outlook rainfall"
    assert logs_in(retrieve(question, as_of=NOW, index=index)) == 2
    for rule in ("L1", "L2"):
        found = retrieve(question, as_of=NOW, index=index, logs=("log",), log_rule=rule)
        assert logs_in(found) == 1
        assert {"a", "b"} <= {row["doc_id"] for row in found}
    # L1 without any listed log changes nothing.
    assert logs_in(retrieve(question, as_of=NOW, index=index, log_rule="L1")) == 2


def test_l2_ranks_the_log_below_an_equal_specific_match(index):
    question = "monsoon drought outlook rainfall"
    first = retrieve(question, as_of=NOW, index=index, logs=("log",), log_rule="L1")[0]
    halved = retrieve(question, as_of=NOW, index=index, logs=("log",), log_rule="L2")
    assert first["doc_id"] == "log" and halved[0]["doc_id"] != "log"
    # Halving happens before the candidate cut, so a non-log just past it can still win.
    for rule, expected in (("L1", True), ("L2", False)):
        top = retrieve(question, as_of=NOW, index=index, logs=("log",), log_rule=rule, candidates=1)
        assert (top[0]["doc_id"] == "log") is expected
    with pytest.raises(ValueError, match="only with method R0"):
        retrieve(question, as_of=NOW, index=index, logs=("log",), log_rule="L2", method="R1")


def test_unknown_rule_and_config_logs():
    with pytest.raises(ValueError, match="log rule"):
        retrieve("rain", as_of=NOW, log_rule="L9")
    config = load_config()
    ids = {entry["doc_id"] for entry in config["documents"]}
    assert set(config["log_documents"]) == {"project/decisions", "project/amendments"} <= ids
    assert config["log_rule"] in ("L0", "L1", "L2")


def test_committed_log_selection_follows_d100():
    import re
    from pathlib import Path

    from atlas.rag.evaluate import LOG_NAMES

    root = Path(__file__).resolve().parents[2]
    text = (root / "reports/rag-logs.md").read_text("utf-8")
    rows = re.findall(r"^\| (L\d) \| [^|]+ \| ([\d.]+) \| ([\d.]+) \|$", text, re.M)
    assert sorted(rule for rule, _, _ in rows) == ["L0", "L1", "L2"]
    key = [(-float(s), -float(r), rule) for rule, s, r in rows]
    assert key == sorted(key)  # support, then recall, then the simpler rule
    rule = load_config()["log_rule"]
    assert rule == rows[0][0] and f"**Chosen: {rule}.**" in text
    assert "Holdout cases (Q41-Q50) are not run here." in text
    assert LOG_NAMES[rule] in (root / "reports/rag.md").read_text("utf-8")
