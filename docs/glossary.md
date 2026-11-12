# Glossary

Plain meanings of the terms this project uses. Terms from plan section 18 that the project does not
use are left out. `tests/test_portfolio.py` checks that each term appears elsewhere in the repository.

| Term | Meaning |
|---|---|
| Data contract | A testable agreement about columns, types, units, meanings and valid values (`schemas/`). |
| Provenance | Where a value came from and which transformations or model versions produced it. |
| Point-in-time (as-of) join | Join only data that was available when the prediction would have been issued. |
| available_at, valid_at | The time the system learned a fact, and the time the fact describes. Features use only rows known at issue time (D37). |
| Forecast vintage | One forecast run, identified by its issue time and model version. |
| Hindcast | A retrospective prediction using historical data. It may not reproduce the information actually available then; every M05 result is one (D39). |
| Leakage | Training or evaluating with information that would not have been available at prediction time. |
| Purge | Remove rows whose target windows overlap a split boundary. |
| Baseline | A simple reference a model must beat. The strongest one on the test rows is used. |
| Persistence | Predict that the latest observed value will continue. |
| Climatology | Predict the long-term average for the same time of year. |
| Champion | The approved model that serves outputs. M05 is the only one, by owner approval (D43). |
| Train, tune, calibration, test | Fit parameters; choose settings; adjust uncertainty; finally score untouched data. The locked test is used once. |
| Ridge | A linear model with a penalty on large coefficients; the M05 champion. |
| LightGBM | An efficient gradient-boosted tree library; tried for M05 and not adopted (D41). |
| MAE | Mean absolute error: the average size of the miss. |
| CRPS | A score for a full predictive distribution; lower is better. |
| Brier skill | Improvement in squared probability error over a baseline. |
| PR-AUC | Area under the precision-recall curve; for rare events it is read against the share of positives (prevalence). |
| Paired block bootstrap | Resample whole blocks of months, keeping model and baseline together, to get a 95% interval for the improvement. |
| Prediction interval | A range for an individual future outcome. The M05 80% intervals do not meet their coverage gate and are hidden. |
| Coverage | The share of outcomes that fall inside a prediction interval. |
| SPI | Standardized precipitation index: rainfall deficit or excess against a fixed reference distribution. SPI-3 uses three months; below -1 counts as drought here. |
| Robust z, MAD | A z-score using the median and the median absolute deviation, so a few outliers do not distort it. M16 uses it; a MAD of 0 gives no z. |
| Anomaly flag | A data-quality signal from a rule, not a real-world incident. |
| Adjudication | A person reviews a flag against independent evidence and labels it. M16 needs 100 before any precision claim. |
| Research-only | A status for a result that does not meet its gate or lacks a measurement. No quality claim is made. |
| Blocked | A status for a model or source whose required data, label, licence or access does not exist, with a recorded retry condition. |
| Data gate | A check, run before modelling, that the data needed for a model exists and can be used. |
| Retry condition | What must change before a blocked task is run again. |
| Frozen, hash-frozen | A file whose SHA-256 is recorded; a test fails if it changes without a decision entry. |
| Derived output | A value computed from a restricted source, such as SPI from IMD rain, that may be published when the raw values may not. |
| Snapshot | An immutable, approved set of records the web app reads. None is approved yet. |
| CAP | Common Alerting Protocol, the format of the Sachet official alerts (S09). |
| H3 | A hexagonal spatial index used for cells. |
| Retrieval, citation, extractive answer | Ask finds passages in project documents, shows them with their source, and does not generate new text. |
| BM25 | A word-matching ranking function used by Ask. |
| Evidence support | The share of fixed Ask questions whose cited passages contain the expected fact; its gate is 0.95. |
