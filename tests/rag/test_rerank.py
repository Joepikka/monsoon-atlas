"""T264 (child of T179): e5 rerank methods keep the retrieval rules (D99)."""

from dataclasses import replace
from datetime import UTC, datetime

import numpy as np
import pytest

from atlas.rag.corpus import Document
from atlas.rag.embed import Embedder
from atlas.rag.index import build_index
from atlas.rag.retrieve import _order, retrieve

NOW = datetime(2026, 11, 8, 12, tzinfo=UTC)
BASE = Document(
    doc_id="a",
    path="a.md",
    kind="project",
    states=("ka",),
    licence="project-mit",
    language="en",
    text="",
    sha256="0" * 64,
    available_at="2026-11-01T00:00:00Z",
    commit="f" * 40,
)


class FakeEmbedder:
    """Puts the question near the vector stored for `target`."""

    def __init__(self, vectors, target):
        self.vector = vectors[target]

    def query(self, question):
        return self.vector


def test_order_rules():
    cosine = {"a": 0.1, "b": 0.9, "c": 0.5, "d": 0.95}
    assert _order("R1", ["a", "b", "c"], cosine, 50) == ["b", "c", "a"]
    fused = _order("R2", ["a", "b", "c"], cosine, 50)
    assert set(fused) == {"a", "b", "c"} and fused[0] == "b"  # rank 2 and 1 beats 1 and 3
    assert "d" in _order("R3", ["a", "b", "c"], cosine, 50)  # dense-only chunk joins
    assert _order("R1", ["x", "y"], {"x": 0.5, "y": 0.5}, 50) == ["x", "y"]  # ties by ID


def test_rerank_keeps_as_of_state_and_per_document_rules(tmp_path):
    documents = [
        replace(
            BASE,
            doc_id="a",
            path="a.md",
            text="# A\n\n## One\n\nrain gauge\n\n## Two\n\nrain map\n\n## Three\n\nrain day",
        ),
        replace(
            BASE,
            doc_id="late",
            path="late.md",
            text="# Late\n\nrain later",
            available_at="2026-11-09T00:00:00Z",
        ),
        replace(BASE, doc_id="kl", path="kl.md", text="# KL\n\nrain kerala", states=("kl",)),
        replace(BASE, doc_id="b", path="b.md", text="# B\n\nmonsoon drought outlook"),
    ]
    index = tmp_path / "index.sqlite"
    build_index(documents, index)
    import sqlite3

    with sqlite3.connect(index) as db:
        ids = [row[0] for row in db.execute("SELECT chunk_id FROM chunks ORDER BY chunk_id")]
    rng = np.random.default_rng(0)
    vectors = {
        key: v / np.linalg.norm(v)
        for key, v in zip(ids, rng.normal(size=(len(ids), 8)), strict=True)
    }
    late = next(key for key in ids if key.startswith("late"))
    kerala = next(key for key in ids if key.startswith("kl"))
    for method in ("R1", "R2", "R3"):
        for target in (late, kerala):
            found = retrieve(
                "rain",
                as_of=NOW,
                index=index,
                method=method,
                embedder=FakeEmbedder(vectors, target),
                vectors=vectors,
            )
            keys = [row["chunk_id"] for row in found]
            assert late not in keys and kerala not in keys
            assert sum(row["doc_id"] == "a" for row in found) <= 2
    dense = retrieve(
        "rain",
        as_of=NOW,
        index=index,
        method="R3",
        embedder=FakeEmbedder(vectors, next(k for k in ids if k.startswith("b"))),
        vectors=vectors,
    )
    assert any(row["doc_id"] == "b" for row in dense)  # no shared word, found by e5
    with pytest.raises(ValueError, match="Unknown retrieval method"):
        retrieve("rain", as_of=NOW, index=index, method="R9")


def test_embedder_refuses_unpinned_files(tmp_path):
    (tmp_path / "model.safetensors").write_bytes(b"not the pinned weights")
    with pytest.raises(FileNotFoundError, match="does not match revision"):
        Embedder(tmp_path)
