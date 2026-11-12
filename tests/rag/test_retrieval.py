"""T252: committed-document Ask corpus, chunking and as-of lexical retrieval (D87)."""

import json
import os
import sqlite3
import subprocess
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from atlas.rag.corpus import (
    CorpusError,
    Document,
    chunk,
    committed_documents,
    load_config,
    tokens,
)
from atlas.rag.index import build_index
from atlas.rag.retrieve import retrieve

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 8, 12, tzinfo=UTC)


def document(doc_id, text, *, available_at="2026-11-01T00:00:00Z", **changes):
    base = Document(
        doc_id=doc_id,
        path=f"{doc_id}.md",
        kind="project",
        states=("ka",),
        licence="project-mit",
        language="en",
        text=text,
        sha256="0" * 64,
        available_at=available_at,
        commit="f" * 40,
    )
    return replace(base, **changes)


def git(root, *args, date="2026-11-01T00:00:00+00:00"):
    env = {
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(root),
    }
    subprocess.run(["git", "-C", str(root), *args], check=True, env=os.environ | env)


def test_chunks_respect_window_overlap_headings_and_whole_table_rows():
    prose = " ".join(f"word{i}." for i in range(700))
    table = "\n".join(
        ["| Measure | Achieved | Gate |", "|---|---|---|"]
        + [f"| metric {i} | {i}.5 mm | pass |" for i in range(40)]
    )
    doc = document("d", f"# Title\n\n## Long prose\n\n{prose}\n\n## Results\n\n{table}\n")
    chunks = chunk(doc, limit=300, overlap=50)
    assert all(item.tokens <= 300 for item in chunks)
    prose_chunks = [item for item in chunks if item.section == "long-prose"]
    assert len(prose_chunks) >= 5
    for left, right in zip(prose_chunks, prose_chunks[1:], strict=False):
        start = left.text.split().index(right.text.split()[0])
        carried = left.text.split()[start:]
        assert right.text.split()[: len(carried)] == carried  # whole words overlap
        assert 40 <= tokens(" ".join(carried)) <= 50
    assert {item.heading for item in prose_chunks} == {"Title - Long prose"}
    rows = [line for item in chunks if item.section == "results" for line in item.text.split("\n")]
    for i in range(40):
        assert f"Measure: metric {i}; Achieved: {i}.5 mm; Gate: pass" in rows
    assert len({item.chunk_id for item in chunks}) == len(chunks)
    assert tokens("SPI-3 < -1") == 6


def test_committed_documents_use_commit_time_and_refuse_dirty_or_unlisted(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "a.md").write_text("# A\n\nCommitted text.\n", encoding="utf-8")
    git(tmp_path, "add", "a.md")
    git(tmp_path, "commit", "-q", "-m", "a", date="2026-10-01T05:30:00+05:30")
    config = {
        "licences": ["project-mit"],
        "documents": [{"doc_id": "a", "path": "a.md", "kind": "project", "states": ["ka"]}],
    }
    (found,) = committed_documents(config, tmp_path)
    assert found.available_at == "2026-10-01T00:00:00Z" and "Committed text." in found.text
    (tmp_path / "a.md").write_text("# A\n\nUncommitted claim.\n", encoding="utf-8")
    with pytest.raises(CorpusError, match="uncommitted"):
        committed_documents(config, tmp_path)
    git(tmp_path, "checkout", "--", "a.md")
    bad = {"licences": ["project-mit"], "documents": [{**config["documents"][0], "licence": "x"}]}
    with pytest.raises(CorpusError, match="licence"):
        committed_documents(bad, tmp_path)
    missing = {"licences": ["project-mit"], "documents": [{**config["documents"][0]}]}
    missing["documents"][0]["path"] = "b.md"
    with pytest.raises(CorpusError):
        committed_documents(missing, tmp_path)
    outside = {"licences": ["project-mit"], "documents": [{**config["documents"][0]}]}
    outside["documents"][0]["path"] = "../a.md"
    with pytest.raises(CorpusError, match="inside"):
        committed_documents(outside, tmp_path)


@pytest.fixture
def small_index(tmp_path):
    documents = [
        document("old", "# Reservoir note\n\nThe reservoir datum is unknown."),
        document(
            "new",
            "# Reservoir update\n\nThe reservoir datum was verified later.",
            available_at="2026-11-10T00:00:00Z",
        ),
        document(
            "expired",
            "# Reservoir expired\n\nThe reservoir notice expired.",
            expires_at="2026-11-05T00:00:00Z",
        ),
        document("kerala", "# Reservoir Kerala\n\nThe reservoir is in Kerala.", states=("kl",)),
        document("hindi", "# Reservoir\n\nReservoir text in another language.", language="hi"),
        document("copy", "# Reservoir note\n\nThe reservoir datum is unknown.", states=("all",)),
    ]
    output = tmp_path / "index.sqlite"
    assert build_index(documents, output)["chunks"] == 6
    return output


def test_as_of_state_language_expiry_and_duplicate_filters(small_index):
    found = [row["doc_id"] for row in retrieve("reservoir datum", as_of=NOW, index=small_index)]
    assert len(found) == 1 and found[0] in {"old", "copy"}  # identical text kept once
    later = retrieve("reservoir datum", as_of=datetime(2026, 11, 11, tzinfo=UTC), index=small_index)
    assert sorted(row["doc_id"] for row in later) == sorted(["new", found[0]])
    early = retrieve("reservoir", as_of=datetime(2026, 11, 4, tzinfo=UTC), index=small_index)
    assert "expired" in {row["doc_id"] for row in early}
    kerala = retrieve("reservoir Kerala", as_of=NOW, state="kl", index=small_index)
    assert {row["doc_id"] for row in kerala} >= {"kerala"} and "old" not in {
        row["doc_id"] for row in kerala
    }
    hindi = retrieve("reservoir", as_of=NOW, language="hi", index=small_index)
    assert {row["doc_id"] for row in hindi} == {"hindi"}
    with pytest.raises(ValueError):
        retrieve("x" * 501, as_of=NOW, index=small_index)
    with pytest.raises(ValueError):
        retrieve("reservoir", as_of=datetime(2026, 11, 8), index=small_index)


@pytest.mark.parametrize(
    "question",
    ['reservoir" OR text NEAR(a b)', "reservoir* AND (datum)", "-- ; DROP TABLE chunks", '"""'],
)
def test_question_text_cannot_inject_query_syntax(small_index, question):
    retrieve(question, as_of=NOW, index=small_index)
    with closing(sqlite3.connect(small_index)) as db:
        assert db.execute("SELECT COUNT(*) FROM chunks").fetchone() == (6,)


def test_build_replaces_index_only_after_success(tmp_path):
    output = tmp_path / "index.sqlite"
    build_index([document("a", "# A\n\nfirst")], output)
    before = output.read_bytes()
    with pytest.raises(sqlite3.IntegrityError):
        build_index([document("a", "# A"), document("a", "# A again")], output)
    assert output.read_bytes() == before
    assert sorted(path.name for path in tmp_path.iterdir()) == ["index.sqlite"]


def test_project_corpus_recalls_gold_documents_for_dev_questions(tmp_path):
    config = load_config()
    documents = committed_documents(config, ROOT)
    assert {doc.licence for doc in documents} == {"project-mit"}
    assert not any(
        doc.path.startswith(("data/", "docs/reviews", "docs/research")) for doc in documents
    )
    output = tmp_path / "index.sqlite"
    build_index(documents, output, limit=config["chunk_tokens"], overlap=config["overlap_tokens"])
    questions = [
        json.loads(line)
        for line in (ROOT / "eval/rag/retrieval_dev.jsonl").read_text("utf-8").splitlines()
    ]
    assert not {item["id"] for item in questions} & {f"Q{n}" for n in range(41, 51)}
    hits = []
    for item in questions:
        found = retrieve(
            item["question"], as_of=datetime.now(UTC), state=item.get("state", "ka"), index=output
        )
        assert len({row["chunk_id"] for row in found}) == len(found) <= config["top_k"]
        assert all(sum(r["doc_id"] == row["doc_id"] for r in found) <= 2 for row in found)
        assert sum(row["tokens"] for row in found) <= config["max_context_tokens"]
        hits.append(bool({row["doc_id"] for row in found} & set(item["gold"])))
    misses = [item["id"] for item, hit in zip(questions, hits, strict=True) if not hit]
    assert sum(hits) / len(hits) >= 0.85, misses
