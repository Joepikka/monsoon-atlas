# Case-study template

Copy this file to `reports/models/<id>-case-study.md` for one model. It follows plan section 17 and
the outline `tests/test_case_studies.py` checks. The three existing case studies are
[M05](../../reports/models/m05-case-study.md), [M07](../../reports/models/m07-case-study.md) and
[Ask](../../reports/models/ask-case-study.md); the owner rewrites each summary in their own words (H14).

## Rules

1. Every number must cite a committed file: a model report in `reports/models/`, a registry record in
   `models/registry/`, a source record in `configs/sources/`, or a decision in `docs/decisions.md`.
   A number with no committed source is deleted, not rounded or estimated.
2. A blocked model's case study states the gate that failed, quoting its registry reason and retry
   condition. It has no accuracy, baseline score, improvement or interval, and it says "no model was
   fitted". Missing is never written as 0.
3. A research-only model says "research-only" in the first line, gives counts only, and states what
   was not measured.
4. Name hindcast or live in the first paragraph. A hindcast is never described as a forecast that
   was available at the time (D39, D07).
5. Name the strongest simple baseline and its score on the same rows. A model is promoted only if
   the lower 95% paired bootstrap bound of its improvement is above 0 (D38); otherwise say research-only.
6. No marketing words, no unmeasured achievement, no target threshold written as a result.
7. Include one positive result and one negative lesson, with real numbers or the stated absence of them.
8. Re-check every number against its source after any change to the report, the registry or the
   corpus; scores that cannot be reproduced are reported as such (D147).

## Template

Replace each angle-bracket instruction. Keep the headings and their order.

```markdown
# Case study: <model ID and name> (<core ID if any>)

Status: <champion | research-only | blocked, with the decision ID>. Every number below comes from
<linked reports, registry files and decision IDs>. The owner reviews this text and rewrites the
summary in their own words (H14).

## Problem and intended use
<The decision the model supports, and what it must not be used for.>

## Data and label provenance
<Source IDs, licence status, coverage, missing data and how labels were made. Link the source records.>

## Target definition
<Target, unit, horizon and boundary version.>

## Time split
<Train, tune, calibration and locked test periods, and the purge. A blocked model: "no split".>

## Baselines
<The simple baselines and the strongest one on the test rows.>

## Hypothesis and candidate
<What was expected to beat the baseline and why. Candidates tried, including those that lost.>

## Leakage audit
<How each feature is known at issue time; the test that fails on future data; vintage limits.>

## Metrics
<Baseline and candidate scores, paired block bootstrap improvement with 95% CI, calibration and
interval coverage. A blocked model: the gate that failed and its retry condition.>

## Failure slices
<Seasons, places or events where it does worse. Note any slice with too few rows.>

## Computational cost
<Training and inference time and memory on the stated hardware, or "not measured".>

## Deployment decision
<Champion, research-only or blocked; who decided and when; what is shown to users.>

## Monitoring and retraining
<Drift and score checks, the retraining rule, and what quarantines the model.>

## Reproducibility
<Commands, dataset and split hashes, git commit, and the raw data that is not committed.>

## What changed after review
<Changes made after the owner or a test review, with decision IDs.>

## One positive result, one negative lesson
- Positive: <one result with its numbers and source, or "none">
- Negative: <one lesson with its numbers and source>
```
