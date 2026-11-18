# Karnataka data-science and ML showcase: plan

Written 13 Nov 2026. A plan only: nothing here is built, fitted or scored yet. It follows
`AGENTS.md` (real data only, honest ML, Rs 0, drive D, Karnataka first). Before the first task
runs, the tasks below must be added to the task list and `docs/amendments.yaml`, and the
deviations listed in section 5 recorded in `docs/decisions.md` (next free number: D211).

**Numbering.** The brief proposed task IDs from T226, but T226 to T267 are already used (checked
by grep over `docs/`, `src/`, `tests/`, `scripts/`, `configs/`; T267 is the highest). This plan
uses **T268 to T289**. Model cards M01 to M20 exist, so new models are **M21** (rain anomaly) and
**M22** (weekly price forecast); M06 keeps its number. Owner steps H01 to H15 exist, so the one new
owner step is **H16**. New source proposals would be S45 onward (S44 is the highest).

## 0. What the showcase should prove

Today: one promoted model (M05 ridge, SPI-3, beats persistence) and 18 of 20 planned models
blocked on labels. The goal is not more model cards; it is a set of finished analyses, each with a
real number and a stated limit, so the Model accuracy page shows results (promoted or
research-only with scores) instead of "blocked".

A research-only result with an honest score is still a result. Several items below are expected to
end research-only (section 4 says which and why). That is fine for interviews: "I tested it, it
did not beat the baseline, here is the interval" is a stronger story than an untested claim.

## 1. Data inventory (what was checked on 13 Nov 2026)

Checked by listing `data/raw/*`, `data/clean/*`, `data/models/`, reading
`configs/sources/s*.yaml` (outcome field of all 44 records), `reports/eda/*/summary.json`,
`reports/models/m05.md`, the three probe responses in `data/raw/S23/probe/`, the first bytes of
`data/clean/S02/ka-districts/2001.json`, `requirements/*.in`, and by importing the libraries in
`.venv`. Nothing was downloaded.

### 1.1 Local now, usable for modelling

| Source | What is on disk | Span and grain | Licence and publishing rule | Use here |
|---|---|---|---|---|
| S08 IMD gridded rain | 54 raw files in `data/raw/S08/` | 1981-01-01 to 2025-12-31, daily, 540 cells of 0.25 degree over Karnataka, 0 missing cell-days (`01_ka_quality`) | Reproduction forbidden: raw local only; publish derived district indices only, cite Pai et al. (2014); no cell, date or mm value published (D129, D158, D166) | M21, segmentation, spatial ML. Hindcast only: files are yearly (D39) |
| S02 ERA5 (Open-Meteo) | `data/clean/S02/ka-districts/2001.json` to `2025.json` | Daily rain, **June to December only**, 2001-2025, one grid point per district; 2026 season to date | CC BY 4.0; about 6 days behind | Monsoon tracker; a live variant of M21 would need a Jan-May backfill (free, about 2 days of API allowance) |
| S17 geoBoundaries | raw files; `web/src/ka-districts.json` | 30 districts, 2021 lines (Ballari includes Vijayanagara) | ODbL | Units, adjacency |
| District adjacency | `reports/eda/10_spatial_statistics/district_neighbours.csv` | Queen weights, 66 shared borders, 1 to 7 neighbours, no islands | Derived | Spatial lag, graph network |
| S16 WorldPop | 16 MB raster in `data/raw/S16/` | 2025, 1 km, 203,344 cells, 70.8 M people | CC BY 4.0 (alpha release, modelled) | Segmentation, hospital siting |
| S18 OSM | `data/clean/S18/hospitals-*.parquet`, Bangalore walk network | 3,581 hospitals | ODbL | Hospital siting |
| S29 KSNDMC (OpenCity) | CSVs in `data/raw/S29/` | **Annual** totals only, 2020-2022, 2024 (district, taluk, hobli); 5,266 station totals for 2023 | Open | Cross-check only; too short for a model |
| S30 BMTC GTFS | raw files | One service date (9 Sep 2026) | Restricted: derived shares only (D191) | Already used (bus access); one segmentation feature for Bangalore only, so not used |
| S44 crime statistics | raw HTML/CSV | Annual, 2023-2024, about 40 police units | Public domain | Too short for a model; not used |
| M05 artefacts | `data/models/m05/`, `models/registry/M05/` | 15,930 district-months of features, saved forecasts 2020-2024 | Derived | Residuals for spatial work |
| MLflow store | `data/models/mlflow.db` (1 MB) | Experiments `Default`, `M05`; 1 run | Local | Tracking for every item |

### 1.2 Free and reachable, but not on disk yet

| Source | Evidence | What is missing | Cost |
|---|---|---|---|
| **S23 mandi price history**, data.gov.in resource `35985678-0d79-46b4-9ed6-6f13308a1d24` ("Variety-wise Daily Market Prices Data of Commodity", GODL) | Probe files: total 83,029,616 rows; Karnataka onion 103,423 rows from 03/01/2014; `Arrival_Date` filter works (14 Karnataka onion rows on 02/01/2019). Fields: `State, District, Market, Commodity, Commodity_Code, Variety, Grade, Arrival_Date, Min_Price, Max_Price, Modal_Price`, all strings | S23 is still `outcome: blocked` in `configs/sources/s23.yaml` (its record describes the older one-day resource). Needs the verify task (T269). Unit is per commodity: **only onion is confirmed as Rs./Quintal** (owner, D201). No arrivals (quantity) field. Page size limit and rate limit unknown | Rs 0; key `DATA_GOV_IN_API_KEY` already in `.env` |
| S07 NASA POWER | Record says daily from 1981, verified at Bengaluru only | 30 district points not fetched | Rs 0; optional temperature feature, not needed for the first pass |
| S03 GloFAS discharge | Simulated, from 1997 at the sampled Cauvery cell | Only samples on disk | Rs 0; not used (simulation, no observed label) |

### 1.3 Not available at Rs 0 with real data: dropped

- **Mandi arrivals (quantities).** Not in the API resource. The AGMARKNET report shows them but
  sits behind a captcha. So no supply feature and no price-quantity analysis.
- **Flood, reservoir and gauge labels** (M01 to M04): still blocked (S27, S28, S43). Not retried.
- **Daily gauge rain.** S29 is annual. No gauge check of ERA5 or IMD below annual totals.
- **Google Open Buildings for all Karnataka** (S19): only sample files are local; the full cell is
  4.8 GB. Not worth the disk for one segmentation feature.
- **NASA FIRMS fire history**: the verified product covers Aug-Nov 2026 only.
- **GPU deep learning** (image models, large sequence models): the MX450 is too small and H10
  (Kaggle/Colab) is not done. Every network below is sized for the 4-core CPU.
- **Anomaly-detection precision** (M16): still 0 of 100 flags adjudicated. No precision claim is
  possible; deterministic data-quality rules are used instead (item 1).

### 1.4 Libraries (checked in `.venv` and `requirements/*.in`)

Locked and importable: scikit-learn 1.9.1, lightgbm 4.7.0, statsmodels 0.15.0, scipy 1.18.1,
optuna 5.0.0, shap 0.54.1, mlflow 3.18.0, matplotlib, plotly (`ml.in`); torch 2.15.0+cpu
(`dl.in`); libpysal, esda, networkx, geopandas (`geo.in`); duckdb 1.5.6.

**No new dependency is needed.** `torch_geometric` is not installed and is not required: a graph
convolution over 30 districts is one normalised-adjacency matrix product in plain torch. Conformal
intervals use the existing `atlas.models.uncertainty.conformal_interval` plus a few lines for the
quantile and adaptive variants (MAPIE, BSD-3, would be a new dependency for no gain). If someone
later wants them: `torch-geometric` (MIT), `mapie` (BSD-3), `spopt` (BSD-3) are all free licences.

Two rules to respect: `ml.in` says classical jobs must never load torch, so network code lives in
its own modules with a lazy import; and CI installs only `core` and `dev`, so every test that needs
scikit-learn, LightGBM or torch must use `pytest.importorskip` (as the M05 tests do) and run locally.

## 2. Portfolio (ranked by interview value against risk)

Shared rules for every model item, reusing what exists:

- Splits from `atlas.models.splits` (`DatasetSplit`, `rolling_origin`), written with
  `write_manifest` and hashed before any fit. Scalers and climatologies from training rows only
  (`TrainOnlyScaler`).
- Comparison by `atlas.models.uncertainty.paired_block_bootstrap` (1000 resamples, seed 42),
  blocks = calendar months for district data, weeks for price data.
- **Promotion rule (unchanged):** the candidate named *before* the locked test is opened is
  promoted only if the lower 95% bound of its improvement over the strongest simple baseline on the
  same rows is above 0, and the owner approves (D38). Otherwise it is published research-only, with
  its scores. The locked test is opened once per model; every other candidate scored at that
  opening is labelled "comparison, not eligible".
- Every fit is an MLflow run in `data/models/mlflow.db` (params, split and dataset hashes, metrics,
  git SHA), using the pattern in `atlas.models.m05.log_mlflow`.

Difficulty: **simple = Sonnet**, **hard = Opus**.

### Item 1. Mandi price data: ingest, cleaning audit and SQL (foundation)

- **Question and user.** "Can ten years of government price reports be trusted, and where not?"
  User: any analyst who must use the data; in business terms a procurement or category analyst.
  Decision: which markets and commodities are reliable enough to plan on.
- **Data and licence.** S23 history resource, Karnataka only, a short list of commodities whose
  unit is confirmed (onion now; tomato, potato, maize, ragi, tur, dry chillies, copra after H16).
  GODL: reuse allowed with attribution.
- **Cleaning (the genuinely messy part).** All fields arrive as strings; dates are DD/MM/YYYY;
  district names are old spellings (`Bellary`, `Chikmagalur`, `Bangalore`) and need a reviewed
  crosswalk to the 30 S17 districts (Vijayanagara markets map to Ballari, stated); variety and
  grade labels vary; duplicate rows; `min <= modal <= max` violations; price jumps of x10 or x100
  (per kg entered as per quintal); market-days with no report; markets that start or stop
  reporting. Rules are deterministic and counted; a row is quarantined with a reason code, never
  silently fixed or deleted, and a missing day is never filled.
- **Features and leakage.** None (no model). The crosswalk is hand-made and versioned.
- **Split / baseline / metric / promotion.** Not a model. Acceptance is reconciliation: clean plus
  quarantined rows equal the API `total` per commodity and year.
- **Artefacts.** `notebooks/12_ka_mandi_quality.ipynb`, `reports/eda/12_ka_mandi_quality/`
  (summary.json, coverage heatmap market x month, rule-violation table), six DuckDB queries
  `sql/insights/q13` to `q18` (window functions for rolling medians, gaps-and-islands for
  reporting gaps, percentile price bands, market ranking, year-on-year change, a join to the
  district crosswalk), a "Data quality" section on the findings page, Power BI page "Market data".
- **Libraries.** duckdb, pandas, httpx (locked).
- **CPU time.** Backfill is network-bound: onion is 103,423 rows; at an unknown page limit this is
  100 to 1,000 requests per commodity, so minutes to about an hour each at a polite rate. Cleaning
  and SQL: seconds.
- **Difficulty.** Verify and adapter: hard (Opus), because unit and licence evidence decide whether
  the source may be enabled. Cleaning notebook and SQL: simple (Sonnet).
- **Interview story.** "The first week went on the data, not the model: 100,000 rows, strings for
  numbers, three spellings of one district. I wrote counted rules, quarantined instead of deleting,
  and reconciled to the publisher's totals." Shows SQL, data cleaning and judgement.

### Item 2. M06 price-spike early warning (imbalanced classification)

- **Question and user.** "Will this market's price jump by a quarter within about two weeks?"
  User: a farmer-producer group or small trader deciding to hold or sell; a canteen or retailer
  deciding to buy ahead. Not trading advice; the page says so.
- **Data and licence.** Item 1's clean table. Start with onion (unit confirmed); the plan's Kolar
  tomato target follows when H16 confirms tomato.
- **Target (from `configs/models/m06.yaml`, unchanged).** Unit market x commodity-variety-grade x
  issue day; positive when any modal price in the next 16 days is at least 1.25 times the median of
  the prior 28 observed days, with at least 20 prior and 8 future observations; otherwise the label
  is missing, not negative.
- **Features and leakage risk.** Lagged price levels and returns, rolling volatility, distance from
  the seasonal median (training years only), same-commodity prices in other Karnataka markets,
  calendar and festival-free season terms, district rain anomaly from S08/S02. Risks: (1) the
  publication time of a report is unknown, so features use reports dated up to t-2 and the result
  is labelled a hindcast until T269 measures the delay; (2) overlapping 16-day label windows, so a
  16-day purge between splits and bootstrap blocks of whole weeks; (3) the seasonal median must be
  fitted on training years only; (4) markets that appear only in the test period are scored
  separately.
- **Split.** The planned one: train 2021-2023, tune Jan-Jun 2024, calibrate Jul-Dec 2024, locked
  test Jan 2025 to May 2026. History back to 2014 allows a longer train; that change is decided and
  recorded before the gate is written, not after seeing scores.
- **Strongest simple baseline.** The better, on the tune rows, of (a) the base rate per calendar
  month and (b) a one-line rule: "price already 10% above its 28-day median".
- **Metric.** PR-AUC (spikes are rare, so ROC-AUC flatters), Brier skill, calibration by decile,
  precision at the alert budget a user could act on (top 5% of market-days).
- **Promotion.** Lower 95% bound of the Brier-score improvement over the baseline above 0 and
  PR-AUC above prevalence, as M05's gates.
- **Candidates.** Logistic regression with class weights (provisional candidate), LightGBM with
  `scale_pos_weight` (replaces it only with a significant gain on tune, as D41). No SMOTE: resampled
  rows would be invented rows. Probabilities calibrated on the calibration window (isotonic or
  Platt, chosen there).
- **Artefacts.** `reports/models/m06.md` rewritten from "blocked" to a result, model card, case
  study, `models/registry/M06/v1.json`, Accuracy-page row, Power BI page "Price spike".
- **Libraries.** scikit-learn, lightgbm, optuna (locked).
- **CPU time.** Features under 2 minutes; 30 Optuna trials about 10 to 20 minutes.
- **Difficulty.** Hard (Opus): label windows and timing are where leakage hides.
- **Interview story.** "5% positives. I refused accuracy as a metric, refused SMOTE, used PR-AUC
  and calibration, and compared against a one-line rule a trader already uses."

### Item 3. M21 monthly district rain-anomaly forecast against climatology

- **Question and user.** "Will next month be wetter or drier than normal in this district?" User:
  a district agriculture officer or an input dealer planning stock; an insurer sizing exposure.
- **Data and licence.** S08 monthly district rain 1981-2025 (the table `atlas.features.m05`
  already builds). Derived indices only are published. Hindcast (D39).
- **Target.** Standardised anomaly of month t rain per district (z-score against the 1981-2010
  mean and spread for that district and calendar month; dry-season months with near-zero spread are
  excluded by a stated rule, not scored as zero). Secondary: tercile class (below, near, above).
- **Features and leakage risk.** Anomalies at lags 1 to 12, SPI-1/3/6 at t-1, month terms, the
  state-mean anomaly at t-1. Optional later: ENSO and Indian Ocean Dipole indices from NOAA (public
  domain), which would be a new source S45 with its own verify task; **not assumed here and no URL
  is recorded until that task checks one.** Risks: reference statistics from 1981-2010 only; one
  month's rain is not known on day 1 of the next month in real life (hindcast label).
- **Split.** Train 1982-2014, tune 2015-2017, calibrate 2018-2019, locked test 2020-2025 (72
  months, 2,160 district-months), 31-day purge. Caveat to print: M05 has already been tested on
  2020-2024 with related inputs, so design choices here are fixed on the tune years only.
- **Strongest simple baseline.** The best on test rows of climatology (anomaly 0), persistence of
  last month's anomaly, and the same month last year. Expect climatology to be the hard one.
- **Candidates.** Per-district SARIMA or ETS (statsmodels), ridge (provisional candidate),
  LightGBM; plus the spatial and network challengers of items 7 and 8, all frozen before the test
  is opened.
- **Metric.** MAE of the anomaly; ranked probability skill score for terciles; CRPS with intervals.
- **Promotion.** The standard rule. Honest prior: one-month rain anomalies are close to
  unpredictable from local history, so the likely outcome is research-only, published with its
  interval.
- **Artefacts.** `notebooks/13_ka_rain_anomaly.ipynb`, `reports/models/m21.md`, card, findings-page
  chart (skill by calendar month), Accuracy-page row, Power BI page "Forecast lab".
- **Libraries.** statsmodels, scikit-learn, lightgbm.
- **CPU time.** Dataset seconds; SARIMA refit once a year per district about 5 to 10 minutes; ridge
  and LightGBM under 5 minutes.
- **Difficulty.** Simple (Sonnet) for baselines and ridge; the split and gate file hard (Opus).
- **Interview story.** "The baseline is 'assume normal'. Most of the work was proving whether
  anything beats it, month by month, with a block bootstrap so correlated districts do not fake
  significance."

### Item 4. District segmentation (unsupervised)

- **Question and user.** "Which districts are alike, so one programme design can serve a group?"
  User: a state planner or an NGO choosing pilot districts; in business terms, market segmentation.
- **Data and licence.** Only committed or local derived numbers: rain climatology and seasonality
  share, year-to-year variability, Sen trend (D196), drought-month frequency from SPI-3
  (training-period years), population and density (S16), hospital access (D195), 2026 monsoon
  percent of normal (D202). About 10 to 12 features for 30 districts.
- **Cleaning.** Scale choice (robust scaling; log for population), collinearity check, Bangalore as
  an outlier handled openly (with and without).
- **Method.** PCA for the picture; k-means, Gaussian mixture and Ward clustering compared; a
  spatially constrained Ward (scikit-learn `AgglomerativeClustering` with the queen connectivity)
  to get contiguous regions.
- **Validation instead of a split.** Silhouette and gap statistic for k; stability as the adjusted
  Rand index over 1,000 bootstrap and leave-one-feature-out runs; comparison with the familiar
  coastal / Malnad / north interior / south interior grouping as an external sanity check.
- **Baseline / promotion.** Not a predictive model, so no promotion. Published as "descriptive
  typology" only if the median bootstrap ARI is at least 0.6; otherwise published as "no stable
  clusters found", which is also a result.
- **Honest limit.** n = 30. This is a typology, not a discovery. A second pass clusters market
  price-seasonality profiles from item 1 (hundreds of series), which has enough rows to be robust.
- **Artefacts.** `notebooks/14_ka_segments.ipynb`, `reports/eda/14_ka_segments/`, a map measure on
  the Overview 3D map, a findings section, Power BI page "Segments".
- **Libraries.** scikit-learn, libpysal. **CPU time.** Under 2 minutes. **Difficulty.** Simple
  (Sonnet).
- **Interview story.** "With 30 rows the risk is seeing patterns in noise, so I reported stability,
  not just a pretty map."

### Item 5. Uncertainty: conformal and quantile intervals

- **Question and user.** "How wrong could this forecast be?" User: anyone who acts on items 2, 3
  or 9; a planner needs the 10th percentile, not the mean.
- **Why here.** M05's 80% intervals covered 65%, then 72.8% after recalibration (T262), and stay
  hidden; no further rule may be tried on 2020-2024. New targets give a clean second attempt.
- **Method.** (a) split conformal on calibration residuals (existing function); (b) conformalised
  quantile regression with LightGBM's quantile objective, so width varies with the situation;
  (c) adaptive conformal for time series (the miscoverage level is nudged after each miss), a few
  lines of numpy. Chosen on the calibration window, applied once to the test.
- **Leakage risk.** Calibration rows must come after training and before test; the adaptive
  variant may only use outcomes already observed at issue time.
- **Metric and gate.** Coverage of the 80% interval between 75% and 85% (the existing gate), mean
  width, coverage by season and by district so a good average cannot hide a bad group.
- **Promotion.** Intervals are shown on the site only if the gate passes on the locked test.
- **Artefacts.** A section in `m21.md`, `m22.md`; reliability chart on the findings page.
- **CPU time.** Under 5 minutes. **Difficulty.** Hard (Opus). **Libraries.** lightgbm, numpy.
- **Interview story.** "My first intervals failed their own check and I hid them. Then I fixed the
  method on a fresh target instead of tuning on the test years."

### Item 6. Explainability: SHAP and permutation importance

- **Question and user.** "Why did the model raise this alert?" User: the same decision-maker, and
  a reviewer deciding whether to trust the model.
- **Method.** TreeSHAP on the LightGBM models of items 2, 3 and 9; permutation importance on the
  locked test rows (after the test has been opened, for explanation only, never for selection);
  for ridge, standardised coefficients beside SHAP as an agreement check; stability of the top
  features across rolling-origin folds; two worked local explanations (one true alert, one false).
- **Risk.** Correlated lag features share credit, so features are grouped (all price lags, all rain
  terms) before ranking, and the text says importance is not causation.
- **Artefacts.** `reports/models/explain.md`, beeswarm and grouped-bar PNGs, a "Why" panel on the
  Accuracy page fed from a small JSON.
- **CPU time.** Under 10 minutes. **Difficulty.** Simple (Sonnet). **Libraries.** shap,
  scikit-learn.
- **Interview story.** "I show a false alarm explained as carefully as a hit."

### Item 7. Spatial ML: spatial lags, spatial cross-validation and residual maps

- **Question and user.** "Does knowing the neighbours help, and are our error bars honest when
  districts move together?" User: the modeller and the reviewer; for a business, the same question
  as regional sales that rise and fall together.
- **Starting point.** Moran's I of M05 residuals is significant in 57 of 60 test months (median
  0.55), queen adjacency in `reports/eda/10_spatial_statistics/`.
- **Method.** For M21: add neighbour-mean anomaly and SPI at t-1 (spatial lag of *past* values
  only); compare with and without on the tune years; report Moran's I of residuals before and
  after; leave-one-region-out cross-validation with `atlas.models.splits.spatial_blocks` to measure
  how well the model transfers to unseen districts; effective sample size per month.
- **Leakage risk.** A neighbour's value for the same month is not known at issue time and must
  never be a feature. Spatial block folds must also respect time order.
- **Honest prior.** The residual clustering is mostly weather shared in the *same* month, which no
  lagged feature can know. Expect little or no gain in point accuracy. The useful outputs are the
  honest ones: tests that treat a month as one block, and a map of where the model is weakest.
- **M05 itself.** A spatial challenger to M05 cannot be promoted now: 2020-2024 has been used and
  the finding that motivates it came from those residuals. It is scored on rolling origins before
  2020 only, published research-only, and waits for the 2026-2027 test already defined for v2.
- **Artefacts.** Section in `m21.md`, `notebooks/15_ka_spatial_ml.ipynb`, residual map layer.
- **CPU time.** Under 10 minutes. **Difficulty.** Hard (Opus). **Libraries.** libpysal, esda,
  lightgbm.
- **Interview story.** "I found my errors were spatially correlated, asked whether that was
  exploitable or only a warning about my confidence intervals, and tested both."

### Item 8. Neural network 1: graph network over the district adjacency

- **Question.** Same as items 3 and 7, with a model that shares information along borders.
- **Model.** A small GCN-GRU in plain torch: per-district input of the last 12 months of anomalies
  and SPI, one or two graph-convolution layers using the row-normalised queen matrix, a GRU over
  time, a linear head. About 5,000 to 20,000 parameters for 30 nodes x about 400 training months.
- **Honesty controls.** Five seeds, report mean and spread; early stopping on the tune years only;
  an ablation with the identity matrix instead of the adjacency (if that scores the same, the graph
  adds nothing); a plain MLP on the same inputs; compared against ridge and LightGBM on identical
  rows. Dropout and weight decay fixed on tune.
- **Split, baseline, metric, promotion.** M21's. It is a pre-registered comparison at M21's single
  test opening, eligible for promotion only if it was the named candidate, which it should not be
  unless it wins on the tune years by a significant margin.
- **Honest prior.** About 12,000 training rows of noisy monthly data: ridge will probably match or
  beat it. The deliverable is a fair, reproducible comparison, most likely research-only.
- **Artefacts.** `src/atlas/models/nn_graph.py` (lazy torch import), `reports/models/m21.md`
  section, MLflow runs with loss curves.
- **CPU time.** About 1 to 3 minutes per seed. **Difficulty.** Hard (Opus). **Libraries.** torch
  (locked, CPU). No torch-geometric.
- **Interview story.** "I built a graph network from scratch in 60 lines, then showed with an
  ablation whether the graph mattered. On small data the linear model held; I can explain why."

### Item 9. M22 weekly price forecast, with neural network 2 (global sequence model)

- **Question and user.** "What will the modal price be over the next four weeks, with a range?"
  User: a buyer for a kitchen chain or a farmer-producer group timing sales. Decision: buy or sell
  now or wait. Not a price guarantee.
- **Data and licence.** Item 1's table, aggregated to market x commodity weekly median modal price;
  a week with fewer than 3 reports is missing, not interpolated. Series kept only if coverage in
  the training window passes a stated threshold.
- **Features and leakage risk.** Log-price lags, seasonal terms, cross-market means at lag 1, rain
  anomaly at lag 1. Target is the log change from the last observed week to weeks t+1 .. t+4. Same
  publication-delay caution as item 2.
- **Split.** Train 2014-2021, tune 2022, calibrate 2023, locked test 2024 to mid-2026, 4-week
  purge; rolling weekly origins inside the test.
- **Strongest simple baseline.** The best on test rows of last value (random walk), seasonal naive
  (same week last year scaled) and a 4-week moving average. For prices, last value is very hard to
  beat; say so up front.
- **Candidates.** ETS per series; LightGBM global model (provisional candidate) with quantile
  objective; **network: a global GRU (or a small temporal convolution network) trained across all
  series** with a market and commodity embedding, about 20,000 to 50,000 parameters. This is the
  item where a network has a fair chance: hundreds of series x about 600 weeks, far more rows than
  the district data.
- **Metric.** MASE against the seasonal naive (scale-free across commodities), sMAPE, pinball loss
  for the 10/50/90 quantiles, interval coverage (item 5).
- **Promotion.** Standard rule on MASE with week blocks; the network is promoted only if it was
  named the candidate on tune evidence.
- **Artefacts.** `reports/models/m22.md`, card, `src/atlas/models/nn_seq.py`, a "Price outlook"
  chart per market on the findings page (hindcast label), Power BI page.
- **CPU time.** LightGBM about 10 minutes with tuning; GRU about 5 to 15 minutes per seed, five
  seeds, so up to about an hour, run once in the background.
- **Difficulty.** Hard (Opus). **Libraries.** statsmodels, lightgbm, torch.
- **Interview story.** "Random walk is the benchmark that humbles price models. I report MASE
  against it, and whether the network earned its complexity over gradient boosting."

### Item 10. Hypothesis testing: does a rain shock move prices? (event study)

- **Question and user.** "After an unusually wet or dry month in a growing district, do onion or
  tomato prices rise, and for how long?" User: a policy analyst deciding whether a rain alert
  should trigger a price watch; a business analyst asked "did X cause Y?".
- **Data.** Item 1 prices plus S08 district rain. The design already exists and is waiting for
  rows: `atlas.analysis.event_study` and `notebooks/06_rain_price.ipynb` (market and week fixed
  effects, event-time dummies with reference week -1, cluster-robust standard errors by market,
  pre-trend check, placebo on shifted dates; the label stays "association only" unless both checks
  pass, D126).
- **Extra tests.** Monsoon against non-monsoon volatility (Levene or a permutation test);
  Kruskal-Wallis across market tiers; Benjamini-Hochberg across commodities; effect sizes with
  intervals, not only p-values; a power note on the smallest effect the data could detect.
- **Leakage.** Not a forecast. The risk is the forking-paths kind: the event definition (for
  example district rain above the 90th percentile of its month) is written down before the
  estimate is run.
- **Artefacts.** `reports/eda/06_rain_price/summary.json` filled with real estimates, findings
  section with the event-time plot, Power BI visual.
- **CPU time.** Under 5 minutes. **Difficulty.** Hard (Opus) for design review; the notebook
  re-run is simple. **Libraries.** statsmodels, scipy.
- **Interview story.** "I pre-registered the event, checked pre-trends and a placebo, and called
  it association when the checks did not pass."

### Item 11. Prescriptive analytics: where would ten new hospitals help most?

- **Question and user.** "If the state adds ten hospitals, which locations cut the number of
  people more than 10 km from care the most?" User: a health planner; the same shape as store or
  warehouse siting for a business analyst.
- **Data and licence.** All local: S16 population cells, S18 hospitals, S17 districts; the distance
  code in `atlas.analysis.access` (D195).
- **Method.** Greedy maximal-coverage selection over candidate cells (provably within 63% of the
  optimum), reported against two simple baselines: the ten most populous uncovered cells, and one
  per worst district. Sensitivity to the 10 km threshold (5, 10, 15 km) and to dropping 10% of OSM
  hospitals at random (data-completeness check).
- **Not a model.** No split or promotion. Limits repeated from D195: straight-line distance, OSM
  thinner in rural areas, modelled population. Output is "illustrative siting under stated
  assumptions", never a recommendation of record.
- **Artefacts.** `notebooks/16_ka_hospital_siting.ipynb`, `reports/eda/16_ka_hospital_siting/`,
  a map layer of the ten cells and people gained, a findings section, Power BI visual.
- **CPU time.** About 2 to 5 minutes with the KD-tree. **Difficulty.** Simple (Sonnet).
  **Libraries.** scipy, numpy.
- **Interview story.** "I moved from describing a gap (11.5% beyond 10 km) to a decision: these ten
  sites cover N more people, and here is how sensitive that is to bad data."

### Item 12. Experiment tracking and one results table

- **Question and user.** "Which run produced the number on the site?" User: the reviewer, and the
  owner in an interview.
- **Method.** Every fit in items 2, 3, 8 and 9 logs to `data/models/mlflow.db`. One script
  exports a leaderboard (model, candidate, baseline, metric, improvement and its interval, status,
  run ID, git SHA) to the JSON the Accuracy page reads and to a Power BI CSV, through the same row
  functions so the two cannot disagree (the D199 pattern). A test fails if a published number has
  no matching run.
- **Artefacts.** `scripts/leaderboard.py`, Accuracy-page rows for M06, M21, M22 with status
  "promoted" or "research-only (scored)", Power BI page "Model lab".
- **CPU time.** Seconds. **Difficulty.** Simple (Sonnet). **Libraries.** mlflow.
- **Interview story.** "Any number on the site traces to a run, a commit, a dataset hash and a
  split hash."

### Coverage check

| Skill asked for | Items |
|---|---|
| Cleaning genuinely messy data | 1 |
| EDA | 1, 4, 10 |
| SQL | 1 (q13 to q18) |
| Hypothesis testing | 10 (and existing D196) |
| Time-series forecasting | 3, 9 |
| Imbalanced classification | 2 |
| Unsupervised learning | 4 |
| Explainability | 6 |
| Uncertainty | 5 |
| Spatial ML | 7, 8 |
| Neural networks (two, CPU) | 8 (graph), 9 (sequence) |
| Experiment tracking | 12 |
| Business decision use case | every item; 11 is prescriptive |

## 3. Sequenced tasks (each one session of about 3 hours or less)

Four tracks. **Track B and Track C need no owner step and no download; they can start today and
run in parallel with Track A.** Inside a track, order matters.

### Track A: prices (needs S23 verified; H16 widens it beyond onion)

| ID | Task | Depends on | Acceptance check |
|---|---|---|---|
| T268 | Register this plan: task rows in the task list and `docs/amendments.yaml`, decision D210 (deviations in section 5), `configs/models/m21.yaml` and `m22.yaml` as planned definitions with `enabled: false` | none | `docs/amendments.yaml` still parses and the full `pytest -q` suite passes (no test reads that file today); no model status changes |
| T269 | S23 verify re-run for resource `35985678-...`: record evidence in `tests/fixtures/s23/manifest.json`, measure page-size limit and safe request rate, count Karnataka rows per commodity and year, map units (onion from D201; others stay disabled until H16), compare its latest day with the daily resource to estimate publication delay | T268 | `configs/sources/s23.yaml` validates; outcome `available` for confirmed commodities only; `pytest -q tests/test_discovery.py tests/sources tests/models/test_m06_features.py` (the blocked-branch M06 and price-EDA tests are updated in the same task) |
| H16 (owner, about 10 minutes) | On the AGMARKNET report page, read the "Price Unit" for tomato, potato, maize, ragi, tur, dry chillies, copra and tell the agent | none | Units recorded with date in `docs/sources/s23.md` |
| T270 | History adapter and resumable Karnataka backfill for confirmed commodities into `data/raw/S23/` (ledger) and `data/clean/S23/*.parquet` | T269 | Row count per commodity-year equals the API `total`; re-run downloads nothing |
| T271 | Cleaning rules, district and market crosswalk, quarantine with reason codes; notebook 12 and `reports/eda/12_ka_mandi_quality/` | T270 | clean + quarantined = raw; summary.json lists every rule count; unit tests on real fixture rows |
| T272 | SQL insights q13 to q18 and price EDA (seasonality, volatility, coverage); findings section and Power BI CSVs | T271 | `python -m atlas.analysis.sql_insights` runs all queries; sync test for findings bundle passes |
| T273 | M06 labels, features, split manifest and data gate; no fit. Mutation test: changing a future row never changes an earlier feature | T271 | Gate JSON written with dataset and split hashes; leakage tests pass |
| T274 | M06 baselines, logistic, LightGBM on train/tune; calibration on its window; candidate named in the gate file; MLflow runs | T273 | Tune-set table in the report; candidate recorded before any test read |
| T275 | M06 locked test once; report, card, registry record; owner approval asked if eligible | T274 | `reports/models/m06.md` shows achieved numbers and gates; registry status is `candidate_eligible` or `research_only` |
| T276 | M22 weekly dataset, split manifest, baselines, ETS and LightGBM quantile on train/tune | T271 | Gate JSON; tune-set MASE table |
| T277 | M22 global GRU/TCN in `nn_seq.py`, five seeds, tune only; candidate named | T276 | Loss curves in MLflow; seed spread reported; test not read |
| T278 | M22 locked test once with intervals (item 5); report and card | T277 | `reports/models/m22.md` with MASE, pinball, coverage against the 75-85% gate |
| T279 | Rain-shock event study with real rows (notebook 06, pre-written event definition) | T271 | `06_rain_price/summary.json` has estimates, pre-trend and placebo results, and the label |

### Track B: rain (all data local; start now)

| ID | Task | Depends on | Acceptance check |
|---|---|---|---|
| T280 | M21 dataset from the M05 monthly table, target rule for dry months, split manifest, data gate, baselines (climatology, persistence, last year) | T268 | Gate JSON with hashes; baseline table on tune years; leakage tests |
| T281 | M21 SARIMA/ETS, ridge, LightGBM on train/tune; MLflow | T280 | Tune table with bootstrap intervals |
| T282 | Spatial lag features, leave-one-region-out check, Moran's I of tune residuals before and after (item 7); M05 spatial challenger on pre-2020 rolling origins, research-only | T281 | Notebook 15 runs end to end; report states whether the lag helps |
| T283 | GCN-GRU and MLP in `nn_graph.py`, five seeds, identity-matrix ablation, tune only | T281 | Ablation table; candidate for M21 named in the gate file |
| T284 | M21 locked test once for the named candidate, all others scored as comparisons; conformal intervals (item 5); report and card | T282, T283 | `reports/models/m21.md` with gates; intervals shown only if coverage is 75-85% |

### Track C: independent, local, no model gate (start now, any order)

| ID | Task | Depends on | Acceptance check |
|---|---|---|---|
| T285 | District segmentation (item 4): notebook 14, stability, map measure | T268 | summary.json has k, silhouette, bootstrap ARI and the publish decision |
| T286 | Hospital siting (item 11): notebook 16, baselines, sensitivity | T268 | Greedy gain is at least each baseline's; summary.json reproducible from input hashes |

### Track D: wrap-up (after the tracks that feed it)

| ID | Task | Depends on | Acceptance check |
|---|---|---|---|
| T287 | Explainability report (item 6) for whichever of M06, M21, M22 exist | T275 and/or T284, T278 | `reports/models/explain.md`; grouped importances; two local explanations |
| T288 | Leaderboard export, Accuracy-page rows, findings sections, Power BI pages "Market data", "Price spike", "Forecast lab", "Segments", "Model lab" (item 12) | T287 | Sync tests pass; every published number has an MLflow run ID; PBIR JSON validates |
| T289 | Case studies for M06, M21, M22 from the template, plus a one-page "interview map" in `docs/portfolio/` (skill, item, number, limit); owner rewrites summaries (H14) | T288 | `release_checks()` lists the new case studies; owner review pending is shown, not hidden |

Suggested order if one agent works alone: T268, then T285 and T286 (two quick visible wins),
T280 to T284 (first new scored model), then Track A as soon as T269 passes, then Track D.
Rough total: 22 sessions.

## 4. Risks, and what makes an item research-only

| Risk | Effect | What the plan does |
|---|---|---|
| S23 verify fails (unit evidence judged too weak, API throttles, history has long gaps for Karnataka) | Items 1, 2, 9, 10 cannot start | Tracks B and C still deliver items 3 to 8, 11, 12. S23 stays disabled; nothing is scraped from the captcha page |
| Only onion has a confirmed unit | Smaller M06 and M22 | Run on onion alone; widen after H16. A unit is never assumed from the size of the numbers |
| Publication time of mandi reports unknown | Any "issue-time" claim is unsafe | Features stop at t-2 and results are labelled hindcast; T269 measures the delay by comparing the two resources; live use waits for that |
| Price history is not revised-as-published (later corrections may be in the data) | Mild optimism in price models | Stated as a limit; from T270 on, daily snapshots keep vintages for a future prospective check |
| Climatology or random walk is not beaten | M21, M22 not promoted | Published research-only with scores and intervals. This is the expected outcome for M21 |
| Small data for networks (30 districts) | Network loses to ridge or wins by seed luck | Five seeds, identity ablation, same rows, block bootstrap; a win must show on tune before the test is opened |
| Test-set reuse | Inflated results | One opening per model; candidates frozen in the gate file first; M05 challengers are not scored on 2020-2024 at all |
| Multiple candidates at one opening | A lucky comparison looks like a winner | Only the pre-named candidate can be promoted; the others are labelled comparisons |
| n = 30 clustering | Unstable segments | Publish only if bootstrap ARI is at least 0.6; otherwise report "no stable clusters" |
| S08 licence | A chart could expose restricted values | Only district indices, anomalies and scores are published; the existing bundle tests (no mm, no cell, no date) are extended to new bundles |
| OSM completeness (item 11) | Siting result biased towards areas with unmapped hospitals | Sensitivity run; wording "illustrative" |
| Training on CPU with the `dl` lock | Contradicts the comment in `dl.in` ("export/inference checks only") | Recorded as a deviation (section 5); models are tiny, no GPU claim is made |
| CI has no ML libraries | New tests silently skipped in CI | Tests use `importorskip`; acceptance commands are run locally and their output pasted in the task record |
| Scope creep | 22 sessions is already large | Items 8 and 9's network and item 10 are the first to cut; items 1 to 4 and 11 alone already change the "blocked everywhere" picture |

An item is **research-only instead of promoted** when any of these holds: the lower 95% bound of
the improvement is 0 or below; the candidate was not named before the test was opened; the test
period was touched during design; fewer than 24 test months (or 52 test weeks) are available; a
feature's issue-time availability is assumed rather than measured (hindcast models can be approved
as hindcasts, as M05 was, but never served as live forecasts); or the owner has not approved the
release (D38). Descriptive items (1, 4, 10, 11) are never "promoted"; they are published as
analyses with their limits.

## 5. Deviations to record before starting (for D211)

1. New models M21 and M22 and tasks T268 to T289 are outside the 4 Nov plan and amendments v1.
2. M06 starts with onion in all Karnataka markets, not Kolar tomato, until H16 confirms tomato's
   unit; its training window may start before 2021 (decided in T273, before any fit).
3. Small networks are trained locally on CPU with the `dl` lock; `dl.in` describes that lock as
   for export and inference checks.
4. S23 is enabled per commodity, on a second resource of the same catalogue, not on the resource
   the original record describes.
5. A proposed owner step H16 (read price units on AGMARKNET) is added.

## 6. Not checked in this plan

- The data.gov.in page-size limit, rate limit and total Karnataka row count (T269 measures them).
- Whether price history for the planned M06 split years (2021 to mid-2026) is complete for onion;
  only the first rows (2014) and one 2019 day were probed.
- Whether NOAA climate-index files are reachable and under what terms (possible S45; not used
  unless verified).
- Actual CPU timings: every time above is an estimate from data size, not a measurement.
