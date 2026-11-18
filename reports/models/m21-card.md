# Model card: M21 Karnataka monthly rain-anomaly forecast

Fields follow the M05 card. Results come from [the evaluation report](m21.md), the release `models/registry/M21/v1.json` and the gate `models/gates/m21.json`.

| Card field | This release (v1, test opened once) |
|---|---|
| Scope | Karnataka; regression of the monthly rain anomaly with tercile probabilities. Not an emergency decision system. Hindcast only (D39). |
| Target, horizon and unit | Month t district rain as a z-score against the 1981-2010 mean and sd of that district and calendar month (unitless), issued at 00:00 IST on day 1 of t. Dry district-months (1981-2010 sd below 10 mm) are not scored. |
| Features and lag evidence | S08 anomaly lags 1-12, SPI-1/3/6 and the state-mean anomaly at t-1, calendar month. No month-t value. IMD releases yearly files, so the issue-time availability is assumed (D39). |
| Train, tune, calibration and test | Choices on train 1982-01 to 2014-11 and tune 2015-2017; refit on 1982-01 to 2017-11; calibrate 2018-2019 (intervals); locked test 2020-2025, opened once on 2026-11-18; 31-day purges. |
| Units of analysis | 30 geoBoundaries 2021 districts (Ballari includes Vijayanagara). |
| Baselines | Climatology (anomaly 0), persistence (t-1) and same month last year; climatology is strongest on the test rows (MAE 1.059). Train median per district and month reported too. |
| Candidates | LightGBM named by a written rule on tune (D217). Scored as comparisons, not eligible: SARIMA per district, ridge, LightGBM with spatial lags, MLP, GCN-GRU and its identity ablation. |
| Achieved metrics (test) | MAE 1.088 vs 1.059; improvement -0.029, 95% CI -0.061 to +0.003; RPSS +0.082; CRPS 0.770 vs 0.789 for climatology. |
| Uncertainty | Split-conformal 80% intervals (seasonal offsets from 2018-2019 residuals, fixed before the test): coverage 0.754, mean width 2.706; inside the 75-85% gate, may be shown. |
| Data licence | IMD rain may not be reproduced; only derived indices and model outputs are published (D129, D158). Cite Pai et al. (2014). |
| Limits | Meteorological anomaly only; no ocean indices; 72 test months with districts that move together; 2025 provisional (D98). |
| Status | research_only: lower 95% bound of the MAE improvement over climatology is -0.061, not above 0; published research-only with its scores. |
| Retraining | Any change of target, features, unit or boundary is a new version with an untouched test period (2026 onwards). |
