# Ask corpus and retrieval (T252)

Ask is the citation-first explanation layer (core C3). This step builds its
English Karnataka corpus and a local lexical index. It does not generate
answers, call a cloud model or download an embedding model.

## Corpus

`configs/rag.yaml` lists every document that may enter the index. Only
committed, project-owned documents are allowed: the README, agent rules,
decisions, amendments, gate report, feed and web notes, source discovery
reports and model reports. Raw source data, news, reviews, research about
other products and credentials are never indexed. A listed file with
uncommitted changes stops the build, so the index always matches a commit.

Each chunk records its document and section IDs, heading, state, language,
licence, SHA-256 and the commit time of its document as `available_at`.
Chunks hold at most 300 tokens with a 50-token overlap. A table row is never
split; it becomes one "column: value" line. Until the pinned e5 tokenizer is
installed, words and punctuation count as tokens (D87).

```powershell
.\.venv\Scripts\python -m atlas.rag.index
.\.venv\Scripts\python -m atlas.rag.retrieve "What does SPI-3 measure?"
```

The index is written to `data/rag/index.sqlite` (ignored by Git) and replaced
only after a complete build.

## Retrieval

Retrieval filters by `as_of`, state and language before ranking, so a
document committed after `as_of` is not returned. Each question word becomes
a quoted SQLite FTS5 term, so question text cannot change the query. BM25
ranks the top 50 candidates (headings weigh twice as much as text). The
result keeps at most five chunks, at most two per document, drops near
duplicates and stays within 3000 tokens.

On the 20 development questions in `eval/rag/retrieval_dev.jsonl`, a gold
document appears in the top five for 18 (90%). The two misses (Q02 "charge
for access", Q28 "what must a model beat") use words that the documents do
not contain. The planned e5 embedding rerank addresses paraphrase; it needs
the deep-learning lock and a model download. Plan questions Q41-Q50 stay
untouched for the held-out evaluation (T181).
