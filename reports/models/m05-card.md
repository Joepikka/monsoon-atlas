# Model card: M05 Karnataka drought outlook

Fields follow the plan's M05 card. Results come from [the evaluation
report](m05.md), the release `models/registry/M05/v1.json` and decisions
D39-D43.

| Card field | This release (v1, approved 5 Nov 2026) |
|---|---|
| Scope | Karnataka; regression plus drought probability. Not an emergency decision system. Hindcast only (D39). |
| Target, horizon and unit | District SPI-3 of the issue month (standardized trailing three-month rainfall, unitless) and the probability that SPI-3 < -1.0. Reference gamma fit on 1981-2010 only. |
| Features and lag evidence | S08 SPI-1, SPI-3 and SPI-6 and rain to the end of the previous month, plus season terms. No future rainfall. IMD releases files yearly, so the issue-time availability assumed here was not real (D39). No temperature feature. |
| Train, tune, calibration and test | Train 1981-07-01 to 2016-09-30, tune 2017-2018, calibrate 2019, locked test 2020-2024; 92-day purge (D39). Rolling-origin results are not reported in this release. |
| Units of analysis | 30 geoBoundaries 2021 districts, labelled as districts. Taluk polygons were not found (S40), as the card's feasibility gate allows. |
| Baselines | SPI-3 persistence and month climatology; persistence is stronger on the test rows. |
| Candidates | Ridge (chosen) and LightGBM; LightGBM's tune gain over ridge was not significant (lower bound -0.013, D41). |
| Achieved metrics (test) | MAE 0.732 vs 0.808 (ratio 0.906); improvement 0.076, 95% CI 0.003 to 0.150; drought PR-AUC 0.217 vs prevalence 0.057; Brier skill 0.116; CRPS 0.530 vs 0.586. All release gates pass. |
| Monitoring (2025, provisional) | MAE 0.625 vs 0.744 for persistence (ratio 0.841): flag holds (T263, D98, `reports/models/m05-2025.md`). 80% intervals covered 0.869 that year; they stay hidden. |
| Calibration | Probabilities run high: monsoon observed 0.045 vs mean 0.071; rest of year 0.062 vs 0.090. |
| Uncertainty | 80% intervals cover 0.652 of test outcomes (v1) and 0.728 after recalibration on pre-test years (T262, D97, `reports/models/m05-intervals.md`); below the 75-85% gate, so they are not published. |
| Data licence | IMD rain may not be reproduced; only derived SPI and model outputs may be published. |
| Limits | Meteorological drought only: not groundwater, crop yield or household water. Ballari includes Vijayanagara. |
| Status | Champion by owner approval (D43); served outputs say hindcast. |
| Retraining | Refit when a new IMD year file is published; a change of target, unit or boundary is a new version with an untouched test period. |
