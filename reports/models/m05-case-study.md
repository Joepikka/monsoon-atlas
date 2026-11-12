# Case study: M05 Karnataka drought outlook (core C2)

Status: approved hindcast champion (D43). Every number below comes from
[the evaluation report](m05.md), the release `models/registry/M05/v1.json` or
decisions D39-D43. The owner reviews this text and rewrites the summary in
their own words (H14).

## Problem and intended use

Estimate next-month meteorological drought for each Karnataka district: the
SPI-3 value of the issue month and the probability that SPI-3 falls below
-1. It supports drought monitoring on the map. It is not a groundwater,
crop-yield or household-water forecast.

## Data and label provenance

IMD Pune 0.25 degree daily gridded rainfall (S08) for 1981-2024, read from
the yearly files. The licence forbids reproduction, so raw files stay local
and only derived indices are published. District rain is the area-weighted
mean of grid cells over 30 geoBoundaries 2021 districts (Ballari includes
Vijayanagara). One IMD day (12 Oct 2023) has missing land cells, none in
Karnataka (D40); a missing day is never filled with zero.

## Target definition

SPI-3 from a gamma fit with a zero-rain share per district and calendar
month on the 1981-2010 reference period; drought means SPI-3 below -1.0
(D39).

## Time split

```text
1981-07 ........ 2016-09 | purge | 2017-01 .. 2018-12 | 2019 | 2020-01 ........ 2024-12
train                      92 days  tune                 calibrate  locked test
```

Training ends 92 days before the first later month because SPI-3 targets
span three months (D39). There is no spatial holdout: all 30 districts are
forecast in every split.

## Baselines

SPI-3 persistence and month climatology. On the test rows the strongest
baseline is persistence (MAE 0.808; climatology 1.053).

## Hypothesis and candidate

Recent SPI at one, three and six months, last month's rain and season terms
should beat persistence. Ridge regression was the provisional candidate;
LightGBM could replace it only with a significant gain on the tune years.
On 2017-2018 (720 rows) MAE was persistence 0.736, ridge 0.585 and LightGBM
0.571, but LightGBM's gain over ridge had a lower bound of -0.013, so ridge
stayed (D41).

## Leakage audit

Features for issue month t use IMD rain to the end of month t-1, as if known
at issue. IMD publishes the files yearly, so this timing was not really
available: every result is a hindcast (D39). Scalers and climatology use
training rows only; test rows were scored once.

## Metrics with paired confidence interval

Locked test 2020-2024: 1800 district-months, 60 months, 30 districts.

| Measure | Ridge | Persistence | Gate |
|---|---|---|---|
| MAE | 0.732 | 0.808 | ratio 0.906 <= 0.95, pass |
| Improvement (paired block bootstrap by month) | 0.076, 95% CI 0.003 to 0.150 | | lower bound > 0, pass |
| Drought PR-AUC | 0.217 | prevalence 0.057 | pass |
| Brier skill | 0.116 | | > 0, pass |
| CRPS | 0.530 | 0.586 | lower, pass |
| 80% interval coverage | 0.652 | | reported |

## Failure slices

Drought probabilities run high in both seasons: in the monsoon (600 rows)
observed drought share 0.045 against mean probability 0.071; in the rest of
the year (1200 rows) 0.062 against 0.090. The 80% intervals cover 65% of
outcomes because their spread comes from one calibration year, 2019.

## Computational cost

Training runs on the 4-core laptop CPU at Rs 0. Wall-clock times were not
recorded for T102/T103, so no runtime is claimed.

## Deployment decision

Release v1 passed every gate (`candidate_eligible`). The owner approved it
on 5 Nov 2026 (D43): ridge is the champion. Outputs are labelled hindcast,
and the intervals are withheld until they are recalibrated (D42).

## Monitoring and retraining

Refit when a new IMD year file is published. A change of target, unit or
boundary version is a new model version with an untouched test period.

## Reproducibility

Git `7efb139bf5c9`, dataset `91bb4930a3ff`, split manifest `e0109096d125`,
release `models/registry/M05/v1.json` with its per-file source hashes.

## What changed after review

The owner's approval made ridge the champion without editing the release
file. Review kept the under-covering intervals off the map and kept the
hindcast label on every output.

## One positive result, one negative lesson

- Positive: a simple ridge model beat persistence on five untouched years,
  MAE 0.732 against 0.808, with the improvement's lower bound above zero.
- Negative: the 80% intervals covered only 65%; one calibration year was too
  little to size uncertainty, so intervals stay unpublished.
