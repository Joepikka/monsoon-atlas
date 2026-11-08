"""T264 (child of T179): pinned e5 passage and query embeddings for the Ask rerank (D99)."""

from __future__ import annotations

import hashlib
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np

from atlas.rag.corpus import ROOT

REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
MODEL_DIR = ROOT / "data/models/e5" / REVISION[:8]
# Published SHA-256 of the large files at REVISION (Hugging Face LFS ids).
HASHES = {
    "model.safetensors": "1a55775f53449dac10a2bcbc312469fac40b96d53198c407081a831f81c98477",
    "tokenizer.json": "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
}


def passage_text(heading: str, text: str) -> str:
    return f"passage: {heading}. {text}"


class Embedder:
    """multilingual-e5-small on CPU, offline, from hash-checked local files only."""

    def __init__(self, folder: Path = MODEL_DIR):
        for name, digest in HASHES.items():
            path = Path(folder) / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise FileNotFoundError(f"{path} is missing or does not match revision {REVISION}")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        import torch
        from sentence_transformers import SentenceTransformer

        torch.set_num_threads(4)
        self.model = SentenceTransformer(str(folder), device="cpu")

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(texts, batch_size=32, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)

    def query(self, question: str) -> np.ndarray:
        return self.encode([f"query: {question}"])[0]


def passage_vectors(index: Path, embedder: Embedder) -> dict[str, np.ndarray]:
    """Vectors for every chunk in `index`, cached beside it and rebuilt when any chunk changes."""
    uri = f"{Path(index).absolute().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        rows = db.execute("SELECT chunk_id, heading, text, sha256 FROM chunks ORDER BY chunk_id")
        rows = rows.fetchall()
    key = hashlib.sha256(
        (REVISION + "".join(f"{c}:{s}" for c, _, _, s in rows)).encode("utf-8")
    ).hexdigest()
    cache = Path(index).with_suffix(".e5.npz")
    if cache.exists():
        with np.load(cache) as stored:
            if str(stored["key"]) == key:
                return dict(zip(stored["ids"].tolist(), stored["vectors"], strict=True))
    vectors = embedder.encode([passage_text(h, t) for _, h, t, _ in rows])
    ids = np.asarray([c for c, _, _, _ in rows])
    np.savez(cache, key=np.asarray(key), ids=ids, vectors=vectors)
    return dict(zip(ids.tolist(), vectors, strict=True))
