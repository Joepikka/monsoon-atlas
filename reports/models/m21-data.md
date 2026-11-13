# M21 monthly district rain-anomaly forecast: dataset, split and baselines (T280)

**No model is fitted and the locked test (2020-2025) is not scored.** This is the data step for
plan item 3 (`docs/plans/karnataka-ml-showcase.md`). It is a hindcast (D39): features assume IMD
rain up to the previous month was known at issue time; 2025 is provisional (D98).

## What was built

- `src/atlas/models/m21_data.py` builds the dataset from the M05 monthly district table
  (S08 1981-2025, 30 districts). Run: `.venv\Scripts\python -m atlas.models.m21_data`.
- Target: anomaly of month t rain per district, z = (rain - mean) / sd, with mean and sd per
  district and calendar month from 1981-2010 only. Secondary target: tercile class against the
  1981-2010 33rd and 67th percentiles.
- Dry-month rule: a district and calendar month whose 1981-2010 sd of monthly rain is below
  10 mm has no anomaly. Those rows are left out, not scored as zero: 61 of 360 district-months
  (January 28, February 27, December 6).
- Features (months up to t-1 only): anomalies at lags 1 to 12, SPI-1, SPI-3 and SPI-6 at t-1
  (from M05), the state-mean anomaly at t-1 and the calendar month.
- Dataset: 13,156 rows (target months 1982-01 to 2025-12; the 24 December 2014 rows sit in the
  purge gap), kept locally in `data/models/m21/m21_dataset.parquet` (git-ignored; no mm values).
- Split manifest `models/gates/m21_splits.json` and data gate `models/gates/m21.json` with the
  dataset, split and source hashes. The gate status is ok (45 years of rain).

| Split | Target months | Rows |
|---|---|---|
| Train | 1982-01 to 2014-11 (31-day purge before tune) | 9,843 |
| Tune | 2015-01 to 2017-12 | 897 |
| Calibrate | 2018-01 to 2019-12 | 598 |
| Locked test | 2020-01 to 2025-12 (not scored) | 1,794 |

## Baselines on the tune years (2015-2017)

897 district-months in 36 months. MAE of the anomaly (lower is better). Improvement is the
climatology MAE minus the baseline MAE, with a paired block bootstrap by month (1,000 resamples,
seed 42).

| Baseline | Tune MAE | Improvement over climatology (95% interval) |
|---|---|---|
| Climatology (anomaly 0) | 0.907 | - |
| Persistence (anomaly of t-1) | 1.114 | -0.207 [-0.384, -0.039] |
| Same month last year (t-12) | 1.351 | -0.445 [-0.647, -0.257] |

Climatology is the strongest simple baseline on tune, as the plan expected. On train
(1982-2014, 9,843 rows) the MAEs are 0.756, 1.007 and 1.016. The baseline that a candidate must
beat at T284 is the strongest of the three on the test rows.

## Limits

- Hindcast only; S08 is released yearly, so this is not a live forecast.
- Persistence falls back to 0 when month t-1 is a dry district-month (1,408 of 13,156 rows,
  1,188 of them March targets).
- M05 was already tested on 2020-2024 with related inputs, so design choices for M21 are fixed on
  the tune years only.
- District lines are geoBoundaries 2021 (Ballari includes Vijayanagara).
