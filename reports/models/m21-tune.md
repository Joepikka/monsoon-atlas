# M21 classical models on the tune years (T281)

**Tune only (2015-2017). Calibrate (2018-2019) and the locked test (2020-2025) are not scored. T281 named no candidate**; T283 (below) adds networks and names it, and T284 opens the test once. Hindcast (D39).

Every choice was made inside train (1982-01 to 2014-11): SARIMA order by AIC per district, ridge alpha by mean MAE over ten yearly rolling origins (31-day purge), LightGBM by a seeded random search of 30 configs with early stopping on an inner validation slice (2012-01 to 2014-11), then refitted on all train rows. Tune was scored once.

897 district-months in 36 months. MAE of the anomaly (lower is better). Improvement = climatology loss minus model loss, paired block bootstrap by month (1,000 resamples, seed 42), 95% interval. RPS is the tercile ranked probability score (climatology: 1/3 each); RPSS = 1 - RPS / RPS of climatology. CRPS: the model's forecast plus its out-of-sample train residuals; climatology uses the train anomalies of the same district and calendar month.

| Model | Tune MAE | MAE improvement over climatology (95% interval) | RPS | RPSS | CRPS | CRPS improvement (95% interval) | Train seconds |
|---|---|---|---|---|---|---|---|
| Climatology (anomaly 0) | 0.907 | - | 0.233 | 0 | 0.656 | - | - |
| Train median of district and month | 0.900 | +0.007 [-0.045, +0.062] | - | - | - | - | - |
| Persistence (t-1) | 1.114 | -0.207 [-0.384, -0.039] | - | - | - | - | - |
| Same month last year (t-12) | 1.351 | -0.445 [-0.647, -0.257] | - | - | - | - | - |
| SARIMA per district | 0.911 | -0.004 [-0.016, +0.007] | 0.235 | -0.010 | 0.659 | -0.003 [-0.021, +0.015] | 12.6 |
| Ridge (pooled) | 0.914 | -0.007 [-0.030, +0.013] | 0.241 | -0.034 | 0.674 | -0.018 [-0.065, +0.031] | 3.2 |
| LightGBM (pooled) | 0.878 | +0.029 [-0.029, +0.086] | 0.234 | -0.002 | 0.658 | -0.002 [-0.048, +0.039] | 2.8 |

## Reading

On MAE, nothing beats climatology on tune: no lower 95% bound is above 0.
The train median of the district and calendar month is a stronger point baseline than anomaly 0, because monthly rain is skewed (the median anomaly is below 0); a model that only learns this shift is not skill. MAE improvement over that median (95% interval): SARIMA per district -0.011 [-0.073, +0.047]; Ridge (pooled) -0.014 [-0.079, +0.048]; LightGBM (pooled) +0.022 [-0.026, +0.062].

## Choices made on train

- SARIMA orders chosen: {'(0, 0, 0)': 21, '(1, 0, 1)': 3, '(0, 0, 1)': 1, '(2, 0, 0)': 3, '(1, 0, 0)x(1, 0, 0, 12)': 2} (districts per order).
- Ridge alpha: 10000.
- LightGBM: learning_rate 0.1, num_leaves 31, max_depth 8, min_child_samples 50, feature_fraction 1.0, lambda_l2 0.0, objective regression_l1, num_boost_round 21, inner_valid_mae 0.769.

## Runs

MLflow experiment M21 in `data/models/mlflow.db` (local), git 68133a16c1c4 (the commit before T281; the T281 code is in the T281 commit). Run IDs: sarima `12579710acde4baebbf8db2d1abcc2a2`, ridge `1d0a69ec859a41d1a910965cd86d8c7f`, lightgbm `99b78376d18f452db770586a53caf693`. Dataset sha256 7035ecaa7a2b6743, split sha256 a4092dd453c691ad.

## Limits

- Hindcast only; S08 is released yearly. The tune years are 36 months, so intervals are wide.
- SARIMA forecasts are one step ahead with train parameters held fixed; the filter reads anomalies up to month t-1, the same information as the lag features. ETS was not fitted: dry months leave gaps that SARIMA's state-space filter handles and ETS does not.
- Probabilistic scores use pooled residuals (anomalies are already standardised per district and month).
- Tercile edges in anomaly units are midpoints between the 1982-2010 classes in train; 1981 has no row (lags need a year).

# M21 networks on the tune years (T283)

**Tune only. Calibrate and the locked test are not scored.** Plain torch on CPU, 5 seeds each (seeds [0, 1, 2, 3, 4]). Each seed: fit on inner train (to 2011-11), early stopping on the inner validation slice of train (2012-01 to 2014-11, patience 15, at most 150 epochs), refit on all train rows for the early-stopped number of epochs, tune scored once. Sizes, dropout 0.1, weight decay 0.0001 and learning rate 0.003 were fixed in advance; L1 loss.

- MLP: the ridge features (12 anomaly lags, SPI-1/3/6, state anomaly at t-1, month sin and cos), two hidden layers of 32.
- GCN-GRU: per month, the 30 districts' anomaly, observed flag, SPI-1/3/6 and month sin and cos; two graph convolutions relu(A H W) of width 16 with A the row-normalised queen adjacency plus self loops; a GRU of width 32 over the past 12 months; a linear head per district.
- Ablation: the same GCN-GRU with A = identity (no neighbour information).

Mean over seeds, seed sd in brackets. MAE improvement: climatology minus model, paired block bootstrap by month on the seed-mean errors. Lower bounds per seed: lowest and highest over the seeds.

| Model | Tune MAE (sd) | MAE range | MAE improvement over climatology (95% interval) | Lower bounds per seed | RPSS (sd) | CRPS (sd) | Parameters | Seconds per seed |
|---|---|---|---|---|---|---|---|---|
| MLP (tabular features) | 0.902 (0.007) | 0.895-0.914 | +0.005 [-0.044, +0.057] | -0.054 to -0.034 | -0.034 (0.014) | 0.673 (0.006) | 1697 | 2.8 |
| GCN-GRU (queen adjacency) | 0.907 (0.009) | 0.897-0.920 | +0.000 [-0.059, +0.065] | -0.086 to -0.049 | -0.041 (0.018) | 0.673 (0.008) | 5233 | 21.9 |
| GCN-GRU, identity ablation | 0.891 (0.002) | 0.888-0.893 | +0.015 [-0.034, +0.069] | -0.041 to -0.022 | -0.022 (0.004) | 0.664 (0.002) | 5233 | 27.0 |

## Reading

- Against the best classical model (LightGBM (pooled)), MAE improvement (95% interval): MLP (tabular features) -0.025 [-0.062, +0.013]; GCN-GRU (queen adjacency) -0.029 [-0.064, +0.007].
- Ablation, identity minus adjacency (positive means the neighbours help): -0.015 [-0.033, +0.002].

## Candidate

Rule (written into the gate before the networks were scored): Fixed before the networks were scored on tune. Eligible: SARIMA, ridge, LightGBM, MLP and GCN-GRU (the identity-matrix GCN-GRU is an ablation, not eligible). The default candidate is the classical model with the lowest tune MAE. A network replaces it only if the sd of its tune MAE over the five seeds is at most 0.01 and the lower 95% bound of its MAE improvement over that classical model (seed-mean errors, paired block bootstrap by month) is above 0; among such networks the lowest mean tune MAE wins. If the candidate's lower 95% bound of MAE improvement over climatology is not above 0, it is still named for the single test opening in T284 and is expected to be research-only.

**Named candidate: lightgbm.** lowest classical tune MAE; no network beat it with a lower 95% bound above 0; tune MAE 0.878, lower 95% bound vs climatology -0.029, so expected research-only.

## Runs

MLflow experiment M21, 15 runs (one per network and seed, with the inner-validation loss curve), git e904e3697829 (the commit before T283).

# M21 spatial lags and spatial checks (T282)

**Comparison only: never the candidate, and the test is not opened.** Spatial lags are the mean over a district's queen neighbours of the anomaly, SPI-1 and SPI-3 of month t-1 (a neighbour's month t value is never a feature). LightGBM is refitted with the T281 procedure with and without them; tune 2015-2017 scored once. Notebook `notebooks/15_ka_spatial_ml.ipynb`, outputs in `reports/eda/15_ka_spatial_ml/`.

**The spatial lag does not help on tune**: MAE improvement of the lags over plain LightGBM +0.008 [-0.020, +0.037] (paired block bootstrap by month, 95% interval).

| Model | Tune MAE | MAE improvement over climatology (95% interval) |
|---|---|---|
| LightGBM, T281 features (refit) | 0.878 | +0.029 [-0.029, +0.086] |
| LightGBM + spatial lags | 0.870 | +0.037 [-0.014, +0.092] |

## Moran's I of tune residuals

27 of 36 tune months have every district scored (999 permutations, BH at q = 0.05). Median I 0.52 before and 0.50 after the lags; significant months 25 and 26. Intra-month correlation of residuals 0.49, so a month of 30 districts carries about 2.0 independent values: every interval here resamples whole months.

## Cross-validation inside train (2005-01 to 2014-11 inside train, 2966 district-months)

Improvement over climatology (MAE, 95% interval); overstatement = this scheme minus leave-one-region-out with rolling origins (the honest one).

| Scheme | Folds | Without lags | With lags | Overstatement without / with |
|---|---|---|---|---|
| random 5-fold over district-months | 5 | +0.039 [+0.020, +0.061] | +0.044 [+0.023, +0.066] | +0.077 / +0.080 |
| leave one region out, all months | 5 | +0.024 [+0.004, +0.045] | +0.025 [+0.007, +0.046] | +0.062 / +0.061 |
| yearly rolling origins, all districts | 10 | -0.034 [-0.065, -0.002] | -0.034 [-0.063, -0.002] | +0.004 / +0.001 |
| leave one region out with yearly rolling origins | 50 | -0.038 [-0.066, -0.008] | -0.036 [-0.063, -0.006] | +0.000 / +0.000 |

## M05 spatial challenger (research-only)

v1 ridge (alpha 0.1) with and without neighbour SPI-1 and SPI-3 at t-1, D97 rolling origins, 2000-01 to 2019-12 (7200 district-months; 2020-2024 was the v1 test and is not re-scored). MAE 0.611 without and 0.611 with the lags; improvement -0.000 [-0.001, +0.001]. Median Moran's I of residuals 0.49 without and 0.49 with. Not promotable: it waits for the 2026-2027 test defined for M05 v2.

MLflow: M21 run `c556aea57e78425982e8e5ade5db116e`, M05 run `7f373cc52f114891be8c5bead53bb72f`.
