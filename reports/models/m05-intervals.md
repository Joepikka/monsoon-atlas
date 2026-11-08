# M05 80% interval recalibration (T262)

**Result: intervals stay hidden.** Test coverage 0.728 against the 75%-85% gate (v1 intervals: 0.652).

The point forecasts are the approved v1 ridge and do not change. The rule was fixed in D97
before any interval was computed. It is a hindcast, like every M05 result (D39).

## Choosing the rule on 2010-2019

Residuals come from ridge refits at origins 2000, 2005, 2010 and 2015, each predicting the
next five years out of sample. Each year from 2010 to 2019 is covered using residuals from
the years before it. The rule with mean coverage closest to 80% wins.

| Rule | Mean coverage 2010-2019 | Mean width (SPI) |
|---|---|---|
| last 5 years, by season | 0.803 | 1.910 |
| last 10 years, by season | 0.804 | 1.925 |
| last 5 years, pooled | 0.805 | 1.914 |
| last 10 years, pooled | 0.812 | 1.938 |
| last 1 year, pooled | 0.771 | 1.918 |
| last 1 year, by season | 0.750 | 1.872 |

Chosen: **last 5 years, by season**, calibrated on 2015 to 2019.

## One check on 2020-2024

| Measure | Value |
|---|---|
| Rows | 1800 |
| 80% interval coverage | 0.728 |
| Mean width (SPI) | 1.971 |
| Coverage, monsoon (Jun-Sep) | 0.643 |
| Coverage, rest of year | 0.771 |
| Persistence with the same rule: coverage / width | 0.772 / 2.312 |

Offsets added to the forecast (10th and 90th residual percentiles, SPI):

- monsoon (Jun-Sep): -0.891 to 0.846
- rest of year: -1.010 to 1.079

## Limits

- The 2020-2024 test was already used once for the v1 intervals (65% coverage). The rule was chosen on 2010-2019 only; this is the second use of the test years, for intervals only.
- Residuals of nearby districts in the same month move together, so coverage varies from
  year to year more than independent rows would suggest; conformal guarantees assume
  exchangeable rows, which time series only approximate.
- Refit residuals stand in for the champion's own pre-test errors, because the champion was
  trained on everything before 2016-10.

Record: `models/registry/M05/v1.intervals.json`; script: `scripts/m05_intervals.py`.
