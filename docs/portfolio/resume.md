# Resume lines

Every metric here is either a measured value with its source file listed under the line, or a
bracketed placeholder from plan section 17 (`[N]`, `[X]%`, `[metric]`, `[baseline]`, `[L,U]`,
`[dates / independent events]`, `[coverage]%`, `[latency]`). `tests/test_portfolio.py` recomputes
each count and each M05 number from the repository, so a line cannot drift from its source.

Do not substitute a target threshold, a prior project's 0.33 PR-AUC, available data volume or a
proposed feature for an achieved result. A negative finding that can be reproduced is a valid line.

## Usable now

- **Data engineering:** "Documented access, licence and history for 44 public data sources for
  Karnataka, Kerala and Delhi (3 states) in versioned, tested source records: 26 available and 18
  blocked, where a blocked source raises an error and never returns synthetic rows."
  - Source: [configs/sources/](../../configs/sources/s01.yaml) (44 records, count by `outcome`),
    [configs/states/](../../configs/states/ka.yaml) (3 state configs), [AGENTS.md](../../AGENTS.md)
- **Data science:** "Evaluated 1 of 20 planned models to a release decision: a ridge drought outlook
  beat a persistence baseline on a locked 2020 to 2024 time-split hindcast (MAE 0.732 against
  0.808; paired block bootstrap improvement 0.076, 95% CI 0.003 to 0.150), and recorded the other
  19 models as blocked or research-only with the gate that failed."
  - Source: [models/registry/M05/v1.json](../../models/registry/M05/v1.json),
    [reports/models/m05.md](../../reports/models/m05.md), [models/registry/](../../models/registry/m01.json)
    (status of each model). Time split only; no spatial holdout was run.
- **Honest ML:** "Reported two negative findings with numbers: an anomaly rule that gives no
  z-score for 6,644,980 of 8,875,440 Karnataka cell-days and has 0 of 100 flags adjudicated, so its
  precision is not measured; and a retrieval evaluation whose evidence support fell from 0.86 on
  8 Nov 2026 to 0.80 on 11 Nov 2026 against a 0.95 gate as the indexed corpus grew."
  - Source: [reports/models/m16.md](../../reports/models/m16.md),
    [reports/rag.md](../../reports/rag.md), [docs/decisions.md](../../docs/decisions.md) (D147)
- **LLM and product:** "Built extractive cited retrieval with no language model over 31 project
  documents on a Rs 0 budget; it is research-only because its evidence support is below its gate."
  - Source: [configs/rag.yaml](../../configs/rag.yaml) (31 documents),
    [reports/rag.md](../../reports/rag.md), [docs/ask.md](../../docs/ask.md)

## Placeholder lines: not usable until measured

These are the plan's lines. Keep the brackets until a frozen report supplies the value. None of them
is an achievement today.

- **Data engineering:** "Built a versioned pipeline integrating [N] licensed public datasets across 3
  Indian states, processing [N] records/day with [X]% valid coverage and point-in-time replay."
  - Not usable: no feed log or `data/` exists in the repository, so records per day and valid
    coverage are not measured, and the replay is not mounted (D163, D162).
- **Data science:** "Evaluated [N] forecasting/classification models using time and spatial
  holdouts; improved [metric] by [X]% over [baseline], 95% CI [L,U], on [dates / independent events]."
  - Not usable: only one model has a result, and no spatial holdout was run. Use the measured line above.
- **ML engineering:** "Deployed daily batch forecasts with calibrated 80% intervals, model/data
  lineage and rollback; measured [coverage]% coverage and [latency] inference time."
  - Not usable: nothing is deployed, no model serves forecasts, and the M05 intervals do not pass
    their coverage gate and are hidden. Inference time is not measured.
- **LLM and product:** "Implemented multilingual cited retrieval with [N] reviewed evaluation cases,
  [X]% supported claims and quota-safe fallback on a Rs 0 hosting budget."
  - Not usable: only English is evaluated, Kannada, Malayalam and Hindi drafts are unreviewed,
    evidence support is below its gate, and the quota fallback waits for owner step H05.
