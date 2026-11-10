# News annotation batches T189 to T208

**Status: blocked. No batch exists. No news article has been selected or labelled.**

The plan asks for twenty batches of 50 real, permitted news articles (1,000 records) labelled by
event class, public place, event date and evidence span. None can start, so no `batch_NN.jsonl`,
per-batch report or per-batch test is written: an empty batch file would look like a finished
batch with no rows. This page and [`eval/news/blocked.json`](../../eval/news/blocked.json) are
the single record for all twenty tasks (D155).

| Count | Value |
|---|---|
| Batches | 20 |
| Required per batch | 50 |
| Required in total | 1000 |
| Articles selected | 0 |
| Records labelled | 0 |
| Records reviewed by the owner | 0 |
| Batches completed | 0 |

## Why

- **S41 is blocked** ([discovery](../../docs/sources/s41.md), T125; disabled contract T126). Every
  publisher checked limits RSS use to personal reading, and no permission to store a headline,
  link and timestamp is on record. There are 0 permitted articles and no frozen temporal split to
  select from. The hashes of the S41 record and evidence manifest are in the blocked record, so a
  change to S41 makes its test fail.
- **Owner step H13 has not happened.** The agent may pre-label, but the owner must review at
  least 20% of every batch and every held-out test item. Labels made only by an AI cannot be the
  ground truth for judging an AI extractor. No review exists.

## Carry-over

All 1000 records are carried into future bounded tasks; none is done. Nothing is invented to fill
a batch.

## Retry

Written publisher permission is on record and S41 is re-run (T125). Then articles are selected from
a frozen temporal split, the agent pre-labels them, and the owner reviews at least 20% of each
batch and all test items (H13). Model M18 (T209 to T211) stays blocked until its data gate of 1000
permitted annotated texts is met.
