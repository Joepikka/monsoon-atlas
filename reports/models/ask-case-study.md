# Case study: Ask, cited answers over project evidence (core C3)

Status: English evaluation built; the C3 gate is not passed. Numbers come
from [the Ask evaluation report](../rag.md), [docs/ask.md](../../docs/ask.md)
and decisions D87-D90. The owner reviews it under H14.

## Problem and intended use

Answer questions about Monsoon Atlas sources, models and rules with a
citation for every claim, at Rs 0. Ask explains evidence; it gives no
emergency advice, routes or private information.

## Data and label provenance

The corpus is 31 committed project documents: source reports,
model reports, the methods page, decisions and amendments. Raw source data,
news and reviews are excluded. Gold cases are the plan's 50 fixed questions
and 10 numeric templates (60 English cases); expected answers come from the
plan, not from a model.

## Target definition

For each question, a cited chunk must contain the gold fact, every number
must appear in cited evidence, and a numeric answer must equal the gold
value recomputed from its committed file. Unavailable data must be refused.

## Time split

Questions Q01-Q40 are development; Q41-Q50 are a hash-frozen holdout. Each
document is available from its commit time, so an as-of question cannot see
a later edit.

## Baselines

Lexical BM25 retrieval with cited excerpts is the baseline answer path. No
language model is connected (Workers AI waits for H05).

## Hypothesis and candidate

Computed answers for recognised numeric templates should make numeric
questions exact without a model. A multilingual e5 rerank was expected to
fix paraphrase misses; T264 tested it on development questions (D99) and it
did not improve evidence support, so lexical BM25 stays.

## Leakage audit

Ranking choices were judged on development questions only. The methods page
was written from the plan with the question list known, so holdout retrieval
is not an independent test of document coverage.

## Metrics

| Measure | Result | Threshold |
|---|---|---|
| Correctness | 0.89 | 0.85 |
| Evidence support | 0.86 | 0.95 |
| Valid citations | 1.00 | 1.00 |
| Faithfulness | 1.00 | 0.95 |
| Refusal accuracy | 1.00 | 0.95 |
| Numeric cases correct | 10 of 10 | all |

Development retrieval recall before the methods page: 18 of 20 questions had
a gold document in the top five.

## Failure slices

Five fixed questions fail because the gold passage is not retrieved. Three
find the right document but not the section with the gold phrase; two share
too few words with the documents (for example Q02 "charge for access"
against "Rs 0"). Fifteen fixed questions are deferred because their
sources or model cards are outside the Karnataka MVP corpus. No translation
is reviewed, so Kannada, Malayalam and Hindi stay disabled.

## Computational cost

Rs 0: a local SQLite FTS5 index and DuckDB queries, no paid API and no model
calls.

## Deployment decision

Not deployed. The gate fails on evidence support, and the Worker route and
AI binding wait for H05 and H11.

## Monitoring and retraining

Rebuild the index from committed documents after each documentation change
and rerun `python -m atlas.rag.evaluate`. Any invalid citation or wrong
number fails the gate regardless of averages.

## Reproducibility

`configs/rag.yaml` lists the corpus and frozen numeric snapshots; every chunk
records its document hash and commit. The holdout hash is checked in
`tests/rag/test_eval.py`.

## What changed after review

A test showed that one wrong number among 45 cases still cleared the
averages, so the gate now fails on any invalid citation or unsupported
number (D89). Numeric questions moved from search results to computed
answers (D90).

## One positive result, one negative lesson

- Positive: all 10 numeric cases are exact or correctly refused, with the
  queried file cited, and no answer cites a chunk that was not retrieved.
- Negative: neither lexical search nor the e5 rerank bridges these misses;
  evidence support is 0.86 against 0.95, so Ask is not ready to publish.
