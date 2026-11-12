"""T261 (child of T182): English text Ask page over the hash-checked corpus (D96)."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from atlas.rag.corpus import committed_documents, load_config
from atlas.rag.index import build_index
from atlas.rag.manifest import FIELDS, manifest, public_bytes

ROOT = Path(__file__).resolve().parents[1]
NODE = ROOT / ".tools/node/node-v22.16.0-win-x64/node.exe"
FIXTURE = ROOT / "web/tests/fixtures/ask-corpus.json"
RECALL = r"""
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
const [corpus, dev, module, asOf] = process.argv.slice(1);
const { search } = await import(pathToFileURL(module).href);
const { chunks } = JSON.parse(readFileSync(corpus, 'utf8'));
const rows = readFileSync(dev, 'utf8').trim().split('\n').map(line => JSON.parse(line));
const found = row => search(chunks, row.question, { asOf, state: row.state ?? 'ka' });
console.log(JSON.stringify(rows.map(row => ({ id: row.id, gold: row.gold,
  found: found(row).map(item => item.doc_id) }))));
"""


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    config = load_config()
    index = tmp_path_factory.mktemp("ask") / "index.sqlite"
    documents = committed_documents(config, ROOT)
    build_index(documents, index, limit=config["chunk_tokens"], overlap=config["overlap_tokens"])
    return index


def test_fixture_is_a_canonical_release_of_committed_chunks():
    data = json.loads(FIXTURE.read_text("utf-8"))
    assert public_bytes(data["chunks"]) == FIXTURE.read_bytes()
    for item in data["chunks"]:
        assert tuple(item) == tuple(sorted(FIELDS))
        assert hashlib.sha256(item["text"].encode("utf-8")).hexdigest() == item["sha256"]


def test_cli_writes_corpus_then_pointer_with_matching_hash(corpus, tmp_path):
    env = os.environ | {"PYTHONIOENCODING": "utf-8"}
    command = [sys.executable, "-m", "atlas.rag.manifest", "--index", str(corpus)]
    command += ["--output", str(tmp_path / "load.sql"), "--public", str(tmp_path / "ask")]
    subprocess.run(command, check=True, env=env, capture_output=True)
    pointer = json.loads((tmp_path / "ask/latest.json").read_text("utf-8"))
    release = manifest(corpus)["release"]
    assert pointer == {"schema_version": 1, "release": release, "url": f"/data/ask/{release}.json"}
    published = (tmp_path / f"ask/{release}.json").read_bytes()
    assert hashlib.sha256(published).hexdigest() == release


def test_browser_search_recalls_gold_documents_like_retrieval(corpus, tmp_path):
    if not NODE.exists():
        pytest.skip("Optional pinned Node toolchain is not installed in core-only CI")
    path = tmp_path / "corpus.json"
    path.write_bytes(public_bytes(manifest(corpus)["chunks"]))
    args = [
        str(path),
        str(ROOT / "eval/rag/retrieval_dev.jsonl"),
        str(ROOT / "web/src/ask-search.ts"),
    ]
    result = subprocess.run(
        [str(NODE), "--experimental-strip-types", "--input-type=module", "-e", RECALL, *args]
        + [datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")],
        capture_output=True,
        encoding="utf-8",
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    rows = json.loads(result.stdout)
    for row in rows:
        assert len(row["found"]) <= 5 and all(row["found"].count(d) <= 2 for d in row["found"])
    misses = [row["id"] for row in rows if not set(row["found"]) & set(row["gold"])]
    assert 1 - len(misses) / len(rows) >= 0.85, misses


def test_no_ask_corpus_is_seeded():
    assert not (ROOT / "web/public/data/ask").exists()


def test_ask_page_unit_and_browser_checks(web_check):
    for args in (["run", "build"], ["run", "test"], ["run", "test:e2e", "--", "ask.spec.ts"]):
        web_check(*args)
