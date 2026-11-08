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

## Answer contract (T253)

`worker/src/ask.ts` holds the answer rules the Worker will use. The system
prompt is fixed; retrieved chunks enter only as a JSON evidence string within
the 3000-token input cap, so retrieved text cannot add rules. Generation runs
only when a model function is supplied and the 100 answers/day, 6
requests/minute and 8000 neurons/day caps allow it. A generated reply is kept
only if it is valid JSON, cites retrieved chunks, stays within 350 tokens and
every number in it appears in the cited text. Every other case returns up to
five quoted excerpts (all retrieved chunks, D90) labelled as search results, with citations, or
`insufficient_evidence` when nothing was retrieved. No AI binding or
account exists yet: Workers AI waits for H05 and the free/no-card probe.

## Evaluation (T254)

`eval/rag/questions.jsonl` keeps the plan's 50 fixed questions (Q41-Q50 held
out and hash-frozen) and `eval/rag/snapshot_gold.jsonl` the 10 numeric cases:
60 English gold cases. 35 fixed questions resolve to a support phrase in an
indexed document; 15 are deferred with reasons. Numeric gold is recomputed
from committed files. `python -m atlas.rag.evaluate` rebuilds the index,
scores the current extractive path and writes [the report](../reports/rag.md).
Any invalid citation or wrong or unsupported number fails the gate, whatever
the averages. Since T255, recognised numeric templates are computed by
DuckDB from the frozen snapshots listed in `configs/rag.yaml` and cite the
queried file; all 10 numeric cases pass. The gate still fails on evidence
support (0.83 against 0.95): six questions use words the gold passage lacks,
which needs the e5 rerank. Translations are not
reviewed, so only English is evaluated.

## Ask route (T260)

`POST /api/v1/ask` takes JSON `query`, `language` (en, kn, ml or hi),
`place_id` (`in:<ka|kl|dl>...`), `as_of` (UTC to the second, not in the
future) and one to five distinct `chunk_ids`, which the browser picks from
its own search. Any other field, including client-supplied evidence, is
refused. The Worker reads those IDs from the current trusted release in D1
(`ask_chunks`, `ask_current`), rechecks each chunk's SHA-256 and drops
chunks committed after `as_of`, expired, or not for the place's state (the
same rules as retrieval). An unknown ID is a 400; a hash mismatch or a
missing release is a 503 fallback with no quote. The reply carries
`release`, `as_of`, `answer`, `citations`, `status` and `mode`. Generation
is off, so every answer is the extractive one above; other languages get
the same quoted English excerpts.

`python -m atlas.rag.manifest` turns the committed index into a release:
its ID is the SHA-256 of the canonical chunk list, and
`data/rag/ask-release.sql` (git-ignored) inserts the new rows, then moves
the pointer, then deletes old rows, one statement per line, so a partial
load never changes what is served. Loading it into the remote D1 database
(`wrangler d1 execute --remote --file`) is a deploy step that waits for H05.
The 8 Nov 2026 index exports 333 chunks from 31 documents.
