# Decisions log

## Continuation review (5 Nov 2026)

- **D53 — Browser metadata evidence for the T025 retry (6 Nov 2026), before
  capture.** D52's public resource and GODL pages render without authentication.
  Permit a narrow exception to D27 for this discovery retry: retain labelled
  browser DOM projections of the resource's licence notice/catalogue description
  and the public licence tabs, plus selected public resource-metadata fields.
  Each projection records its source URL, capture time, observed response status,
  selectors/field paths and transformation; JSON projections also retain the
  original response SHA256. The manifest hashes the projection, never calls it an
  unmodified HTTP response, and keeps its bytes in ignored `data/raw/S23`.
  Projections do not enter the Fetcher's HTTP-cache ledger: a conditional fetch
  must never reuse a filtered projection as the original server response.
  Exclude contacts, user identifiers, cookies, credentials and authentication
  redirects' query strings. This does not permit observation ingestion outside
  the shared Fetcher or bypass a sign-in/challenge. A catalogue navigation reached
  a sign-in page; do not proceed there. GODL verification alone cannot establish
  the price denominator; S23 stays disabled unless that unit is verified too.

- **D52 — Bounded public-catalogue retry while OCR review is pending (6 Nov
  2026).** T025 already lists a browser render as a retry for S23 licence/unit
  verification. Retry that public metadata check now, after T115/T116, without
  accounts, passwords, API keys in forms, terms acceptance or challenge bypass.
  This is independent P1 source discovery; it does not approve S34 OCR or change
  model gates. Only a publisher statement tied to the actual resource can verify
  licence and units. If the browser or page remains unavailable, preserve the
  blocked record and distinguish a local tool failure from publisher evidence.

- **D51 — Verify the remaining M07 source while OCR review is pending (6 Nov
  2026), before implementation.** Pull T115 (S33 monthly-statistics discovery)
  and its T116 adapter into P1 for the D17 core C1 fallback. Replace T115's full
  Karnataka-v1 gate dependency T110 with T113/T226 for this bounded source check;
  T116 keeps T115/T006 and gains T226. This resolves the scheduling prerequisite
  identified in D44 without starting the general Kerala phase. Monthly data may
  support EDA only, never interpolated daily labels or seven-day evaluation.
  The latest instruction to continue is not OCR approval: T118 and S34 values
  remain pending the owner review in D49/D50. If S33 cannot be verified, record
  the blocked outcome and retry condition and keep it disabled; do not invent data.

- **D50 — OCR disagreements stay unresolved (6 Nov 2026), before changing the
  review contract.** Three attempts at one preprocessing recipe failed across the
  mixed layouts. The doubtful assumption was that one recipe could preserve every
  digit. Keep two reproducible OCR candidates per numeric sample: contrast/Lanczos
  and binary/tight-crop/nearest. Record their original crop, settings, word boxes
  and raw text; mark agreement/disagreement and leave selection null. Do not select
  the candidate matching an expected number, edit OCR digits or claim extraction
  accuracy from these development samples. The owner reviews the actual source
  crop and supplies the verified value, as already required by T117/T118. Machine
  acceptance checks provenance and unresolved disagreements, not perfect OCR.
  S34 and the full T118 adapter remain disabled/pending. A later adapter needs
  separately validated layout rules; approving this sample does not approve bulk OCR.

- **D49 — T118 OCR prerequisite split (6 Nov 2026).** Add child **T228** for a
  reproducible, local-only OCR review packet before implementing/using S34 parsed
  values. This separates the required owner review from the multi-layout adapter.
  Pin pypdf 6.21.4, tesserocr 2.12.0 and Pillow 13.0.0 in an optional hash-locked
  OCR group, constrained to core. PyPI provides the Python 3.12 Windows tesserocr
  wheel with bundled Tesseract/Leptonica; use it without an admin installer. Record
  its actual embedded engine version after installation. Use only a commit-pinned
  official tessdata_fast English model with a recorded SHA256 and Apache-2.0
  licence. Dependencies/models/caches and all outputs stay on D. Extract existing
  PDF images through pypdf and preserve source PDF hashes, page numbers, image
  hashes, OCR text/word boxes and engine/settings metadata. OCR output remains an
  unreviewed draft, not observation rows or labels; source S34 stays disabled.
  Restricted source pages, images and OCR text remain under git-ignored data/raw.
  Prepare an offline HTML review packet for the owner, then stop for the manual
  review required by T117/T118. Full T118 remains pending and gains T228 as a
  dependency. T228's machine checks may finish while owner review remains pending;
  neither completion certifies datum, daily coverage or M07 readiness.

- **D48 — T227 daily census (6 Nov 2026), before implementation.** Use the
  shared Fetcher and S32 parser for all 700 dates, 2024-08-15 through 2026-07-15.
  Reuse hash-checked captures; rate-limit every live HTTP attempt to at least
  3 seconds, including redirects/retries. Check current robots.txt first. Cap a
  run at 1000 HTTP attempts, 1 MiB per response and 256 MiB of fetched artifacts.
  Save an atomic checkpoint after each date. Each date records data/empty/parse
  or fetch failure, with raw hashes where available. Three consecutive failures
  stop further requests and explicitly mark remaining dates unattempted; a failed
  request is never evidence of an empty day. Do not override TLS or sign-in gates.
  The committed census contains provenance/counts only, not raw pages. Its
  acceptance permits explicitly reported failures and must distinguish a complete
  availability census from an incomplete audit. This does not waive M07's datum gate.
  Correction to T114 verification wording: the untouched HTML excerpts retain
  upstream trailing whitespace. Whitespace checks pass for code/docs; the fixture
  warnings are expected and are not removed, preserving their exact excerpt hashes.

- **D46 — T114 S32 adapter policy (6 Nov 2026), recorded before implementation.** Parse the
  captured KSEB report with stdlib HTMLParser; no new dependency. Require the exact
  17-column header and the report's dated 07:00 IST title. Use operator + published
  district code + normalized dam name as an internal ID, preserving the original
  name; do not assert an official ID, alias, geometry or vertical datum. Normalize
  today's level, live storage and live capacity only. Explicit ft suffixes convert
  to metres; unlabelled contradictions are quarantined, not guessed. Reject a row
  if level exceeds its stated MWL (converted units), capacity is not positive, or
  the reported storage percentage differs from 100 * storage/capacity by more than
  0.1 percentage points (rounding tolerance). Missing or rejected core measures
  null the whole core measure group, following D23; retain raw hash and quality
  details. Inflow m3/s and datum remain null with per-field reasons. Previous-year
  columns stay in the raw evidence and are not emitted as backdated observations.
  Date-matched header-only reports return a typed empty table; blank/malformed or
  changed-layout responses fail. Small unchanged title/table excerpts from the
  already captured CC BY-SA KSEB reports are committed as attributed test fixtures,
  with original and excerpt hashes; the discovery raw archive remains local.
  The existing twice-monthly sample is not a daily coverage census. Split that
  follow-up into **T227** (child of T114), recorded in both amendment task lists,
  required before T130: audit every date in the sampled gap at a respectful cadence.
  T114 finishes the adapter contract, not the full backfill or M07 readiness.
- **D47 — Empty typed tables (6 Nov 2026).** T114's real header-only report exposed
  a shared validator bug: its empty missing-flag array inferred Arrow null rather
  than boolean, so the boolean OR failed. Give that array an explicit boolean type;
  keep validation and all other rules intact. A direct T005 regression and the S32
  empty-report test cover it. No rows or zero-valued observations are invented.

- **D44 — T129 bootstrap split, before implementation.** The handoff puts T129 before
  T114/T118, but the plan makes the full T129 depend on those adapters, T046, T116,
  T120, T122 and T124. D29 also returned the full label audit to P3. Add **T226**, a
  child of T129, in P1: isolated, disabled Kerala configuration plus an audit of the
  already captured S32/S34/S35/S36 evidence. Dependencies: T003, T113, T117, T119,
  T121 (all recorded complete). T114 and T118 may follow T226 for the approved D17
  dam fallback. Full T129 remains pending with its original dependencies plus T226;
  no Kerala source, model, dam datum, shelter or label is certified by this bootstrap.
  This resolves the dependency cycle without declaring unfinished P3 work complete.
  The task list and YAML are updated together in the amendments. T130's dependency
  on full T129 and the T115/T116 schedule must be resolved explicitly before T130;
  this bootstrap does not waive either dependency or the datum gate.
- **D45 — Local model artifacts remain outside git.** Continuation review found
  `data/models/` unignored despite T102 and the handoff calling it local-only. Add
  that exact directory to `.gitignore`. Preserve every existing file; do not add
  weights or the MLflow SQLite database to git. Tracked release manifests under
  `models/registry/` remain versioned. This is a one-line review correction, not a
  new model release or retraining run.

Plan decisions D01 to D16 come from `docs/plan.pdf` section 3. Decisions from D17 on are made while building. Each deviation from the plan is recorded here before it is made.

## From the plan (4 Nov 2026)

| ID | Decision | Alternative rejected | Reason |
|---|---|---|---|
| D01 | Shared state-configured monorepo | Three independent apps | Reuse contracts, UI and model evaluation; state adapters hold the differences |
| D02 | Static public product plus an optional small Worker | Always-on FastAPI/PostGIS service | Precomputed predictions and a file API fit no-card free hosting |
| D03 | Parquet is the truth; DuckDB 1.x is a rebuildable cache | DuckDB as the only raw archive | Immutable files survive cache corruption; single writer only |
| D04 | Public Hugging Face data subsets; full local archive | Cloudflare R2 by default | R2 requires billing activation |
| D05 | Admin places plus H3 analysis cells | Treat H3 cells as wards | Public identities need real boundaries; hex cells support analytical joins |
| D06 | LightGBM or linear champions only after tests | Neural model for every target | Small data and free compute favour baselines; three bounded neural experiments |
| D07 | Collect real forecast vintages going forward | Use future observed weather in historical forecast tests | Prevents leakage; reanalysis-only experiments are labelled hindcasts |
| D08 | Cloudflare Workers AI with an extractive fallback | Paid Claude API; assumed Gemini quota | Documented free cap; fail closed if availability changes |
| D09 | Immutable published snapshots plus a capacity stop | Promise of an infinite free archive | Free quotas are finite |
| D10 | Local watches; public Telegram channels | Personal accounts or a DM database | No personal data collection |
| D11 | Official warnings displayed; risk layers are research | Emergency routing or flood authority | Risk scores cannot guarantee road or shelter safety |
| D12 | Exact candidate pins plus a compatibility gate | Claim untested environments are verified | Locks and Windows wheels are tested during execution |
| D13 | Dated split protocols and failed-model reports | One inflated global accuracy number | Evidence per state, horizon and event |
| D14 | Source URLs only from real pages | Guessed resource IDs or endpoints | Canonical schemas are our design, not claims about upstream fields |
| D15 | Minimal CSS and an accessible linked list | Copying a reference site's look | Original muted teal and sand design |
| D16 | No dependency on blocked services | Depend on NCRB, WRIS, groundwater or GDELT | Core pipeline stays independent; optional discovery tasks may record blockers |

## Made during the build

| ID | Date | Decision | Reason |
|---|---|---|---|
| D17 | 2026-11-05 (**approved by the owner at H11 on 2026-11-05**, with the option "also try KWRIS") | GATE-CORE fallbacks (amendments A4). C1 fails, so core C1 becomes **M07 Kerala seven-day dam forecast**; pull T113, T114 and T130 to T132 into P1. C2 fails, so core C2 becomes **M08 Kerala flood classifier with the 2018 held-out replay**; pull T119, T129 and T133 to T135 into P1, and if its labels also fail, C2 becomes M05. Ward boundary passes (GBA 2025, 369 wards): no change. T113 and T119 run first, so a failing fallback shows up early. M01, M02 and M03 stay blocked with their retry conditions. The I Change My City complaints log is not used as ground truth. KWRIS is also tried: the owner sends a data request to the ACIWRM helpdesk or registers a KWRIS account (owner-only steps); if daily history arrives with units, datum and a licence, T008 is re-run and M02 can return as a second reservoir model | `docs/gates/core_data_gate.md`: KWRIS publishes only the latest reading per reservoir, with no units or licence (T008); no official dated ward-level flood labels exist, and the citizen complaints log has no coverage rule for negatives (T085) |
| D18 | 2026-11-05 | Adopt plan amendments v1 (`docs/amendments.md`); they win where they conflict with the plan | AI agent builds; portfolio core first; early data gate |
| D19 | 2026-11-05 | Project name: Monsoon Atlas (owner approved, H01). Free subdomain `monsoon-atlas.pages.dev` had no DNS record and the GitHub name `Joepikka/monsoon-atlas` was free on this date | Original name, no paid domain |
| D20 | 2026-11-05 | Repository at `D:\monsoon-atlas` | Drive C has 15 GB free, below the plan's 20 GB storage preflight |
| D21 | 2026-11-05 | Add `CLAUDE.md` that imports `AGENTS.md` | Claude Code reads `CLAUDE.md`, not `AGENTS.md` |
| D22 | 2026-11-05 | T002 uses the uv-managed CPython 3.12.14 already on the laptop (`%APPDATA%\uv\python\cpython-3.12.14-windows-x86_64-none`) to create `.venv` with stdlib `venv`, instead of installing official 3.12.10. `py -3.12` does not resolve it, so the venv is created from that interpreter's path | Same 3.12 minor with newer security patches; no admin installer needed. All other T002 steps (pip-tools hash locks, `--require-hashes` installs, section 5 pins) are as planned |
| D23 | 2026-11-05 | Add a nullable `missing_reason` enum column to the common envelope (`schemas/common.json`); a null measure requires a reason, and a row with a reason must have null measures | T005 requires a missing-reason enum and "missing != 0", but the section 7 envelope has no column to carry it |
| D24 | 2026-11-05 | Storage quota counts `data/clean` and `data/manifests` against a 20 GB archive budget: warn at 80%, archive-only (new ingestion refused) at 95%. `ManifestFile` gains a required `rows` count | Plan section 6 storage arithmetic and T006; T006 wording ("archive-only status at 80%") conflicts with section 6 ("80% warn, 95% archive-only"); section 6 is followed. Row counts let a rebuild prove it matches the manifest |
| D25 | 2026-11-05 | T007 locks five groups (`core`, `dev`, `geo`, `ml`, `dl`), each compiled against `core.txt`. Parser packages for ingest adapters (bs4, lxml, pypdf, openpyxl, gtfs-realtime-bindings, sgp4, huggingface-hub) are not locked yet; each adapter task adds the exact pins it needs. Text files use LF line endings (`.gitattributes`). Locks are resolved on Windows with Python 3.12; a Linux training lock (Kaggle or Colab, with CUDA wheels) is made by the first task that trains there | Section 5 names these parsers but no adapter needs them yet; adding them later keeps each lock tested by real use. LF keeps hashes and diffs identical on Windows and Ubuntu CI |
| D26 | 2026-11-05 | Everything the project writes stays on drive D. Python 3.12.14 is installed in `.tools/python` (supersedes the interpreter path in D22) and `.venv` is rebuilt from it. pip, pip-tools and uv caches and temp files live in `.cache/`, pytest temp files in `.pytest-tmp/` (both git-ignored); `.venv/pip.ini` and `[tool.pip-tools]` in `pyproject.toml` set them. Commands that download set `TEMP` and `TMP` to `D:\monsoon-atlas\.cache\tmp`. The dev lock now pins pip and setuptools (`allow-unsafe`) | The first `dl` lock compile filled drive C (15 GB pip-tools cache; "No space left on device"). The cache was moved to D and removed from C at the owner's request. A fresh environment (CI included) needs pinned setuptools to install with `--require-hashes` |
| D27 | 2026-11-05 | Source discovery tasks share one contract, `atlas.ingest.discovery`: a `configs/sources/sNN.yaml` record where every claim cites evidence IDs, and a `tests/fixtures/sNN/manifest.json` with each evidence page's URL, fetch time, status and SHA256. Evidence pages are fetched through the T004 fetcher into `data/raw` and are not committed. Evidence must be a stored 200 response, or a 304 when the fetcher revalidates a copy it already holds (same URL and SHA256; added in T121) | The plan gives each discovery task its own files but no shared format. One contract keeps about 40 discovery tasks consistent, and keeping the pages local respects sources that reserve all rights (S28 does) |
| D28 | 2026-11-05 | T117 (S34 dam reports) and T121 (S36 KSDMA post-disaster assessment) run in P1, before the T110 Karnataka handoff gate they depend on in the plan | They are the M07 history and M08 label sources for the D17 fallbacks, so a failing fallback must show up before P2. Both are read-only discovery tasks and change nothing in Karnataka work |
| D29 | 2026-11-05 (the owner delegated this H11 choice to the agent: "think yourself the best of the best decision and exicute that desicion") | Core C2 becomes **M05 Karnataka taluk drought outlook**, the second fallback in amendments A4 and D17. M08's labels fail for forecasting: T121 found dated district flood labels for 2018 only, and no independent positives and negatives before 2018. M05 runs on district or H3 cells, labelled as such, because no Karnataka taluk polygons were found (T030). Pull T057 and T058 (S08 IMD Pune gridded rainfall) and T101 to T103 into P1; T057 runs first, so a failing fallback shows up early. M08 stays in P3 as a non-core descriptive 2018 replay with no accuracy claim, so T129 and T133 to T135 go back to P3; T122 (S36 adapter) stays in P3 for that replay | M05 can make a forecasting claim: a locked 2020 to 2024 test against strong simple baselines (SPI persistence and month climatology). Its rainfall record starts in 1901, more than the 30 years the card needs. It is a Karnataka model, so it also follows the build order. `docs/sources/s36.md`, `docs/gates/core_data_gate.md` |
| D30 | 2026-11-05 | S08 adapter (T058): `valid_at` is 08:30 IST (03:00 UTC) on the day after `date_local`, the latest possible end of the daily window, because neither the IMD page nor Pai et al. (2014) states it. `available_at` is the fetch time (release dates are not published). Rows are kept only for land cells inside a state cell box (Karnataka 11.5-18.5N, 74-78.75E, 540 cells); T101 assigns cells to districts. A negative or non-finite value becomes null with `quality_rejected`. S08 is enabled in `ka.yaml` | A later end time can only delay a feature, never leak a future day into it. The box keeps a year at about 198,000 rows instead of 1.8 million for all India. `configs/sources/s08.yaml` (e03, e07) |
| D31 | 2026-11-05 | robots.txt on an API host (Open-Meteo `api.open-meteo.com` disallows all) is read as guidance for web crawlers. Calls to a documented public API follow that provider's published API terms and rate limits instead; robots.txt on website hosts is still honoured for discovery pages | Open-Meteo's terms invite free non-commercial API use within stated limits; the API host file stops search engines indexing API URLs. Revisit if a provider says otherwise. `configs/sources/s01.yaml` (e02, e03) |
| D32 | 2026-11-05 | S01 adapter (T010): always one named model (default `ecmwf_ifs025`, never best-match); `issued_at` is the model's `last_run_initialisation_time`, read before and after the forecast call (a changed run is rejected); `available_at` is the later of availability + 10 minutes and the fetch time. An hour with any measure missing becomes an all-null row with `out_of_coverage`, because the envelope has one `missing_reason` per row. Open-Meteo rows carry `redistribution_allowed = true` (CC BY 4.0, credit Open-Meteo and ECMWF), and its unmodified responses may be committed as test fixtures | T009 found no run time in the response. Losing a few partial hours at the forecast end is safer than mixing real and missing values in one row |
| D33 | 2026-11-05 | S09 adapter (T014): add `sender` and `msg_type` to the plan's S09 fields, because supersession needs them; `supersede()` drops alerts referenced by a later Update or Cancel and the Cancel messages. The English info block is used. Geometry is WKB MultiPolygon written with the standard library (shapely is only in the geo lock). An alert belongs to Karnataka if its sender or area text names the state or a polygon vertex falls in the state box; T032 replaces this with district matching. `fetch` skips identifiers already stored | CAP 1.2 needs msgType and sender to resolve references; a box test over-includes border areas, which is safe for display |
| D34 | 2026-11-05 | Geofabrik (S18, T021): the pipeline does not download `.osm.pbf` or `.shp.zip` files, because Geofabrik's robots.txt disallows them for all user agents and its pages do not invite scripted downloads. S18 is blocked; T022 is a disabled adapter. Retry: an owner browser download into `data/raw/S18`, Geofabrik permission, or a separate Overpass API source | D31 applies only to API hosts whose terms invite programmatic use. The project rule is to honour robots.txt elsewhere |
| D35 | 2026-11-05 | The hash-locked geo group (`requirements/geo.txt`: rasterio, shapely, pyproj, geopandas, h3) is now installed in the local `.venv`. Adapters import geo packages inside the function that needs them, so the core install (and CI, which installs core and dev only) can still import every module; their tests use `pytest.importorskip`. S16 clips WorldPop by keeping native cells whose centre lies in the S17 ADM1 state polygon, with provenance `model` | Raster and polygon work (T018, T032) needs them; a lazy import keeps CI light. Keeping native cells conserves counts exactly, as the T017 source check requires |
| D36 | 2026-11-05 | Places (T032): official places keep their namespaced source IDs and a `boundary_version`; the gazetteer keeps every version (history), and version changes are linked by area crosswalks. H3 resolution 7 and 8 cells are kind `h3`, IDs `h3:<res>:<index>`, and the gazetteer rejects H3 rows that look like wards. Areas are in m2 in EPSG:6933; distances are geodesic metres. Name search is local only (no query storage, no Nominatim, no autocomplete); several matches return a selection list. Analysis falls back to districts because no taluk polygons are verified | Plan T032 steps; Nominatim is optional in the plan and not needed for district and ward names |
| D37 | 2026-11-05 | Feature framework (T033): a feature window ends `lag_days` before the issue time and uses only rows known then, either by `available_at` (live) or by `valid_at + publication_lag_days` (hindcasts rebuilt from later fetches, labelled as such per D07). Each feature carries `<name>__known_at`, and `assert_as_of` fails if it is after the issue time. Splits purge horizon + publication lag; manifests store dates and a SHA256; scalers fit on training dates only; evaluators refuse empty tests, missing labels or predictions, one-class tests and unknown forecast vintages | Plan T033; the hindcast rule is needed because every historical row in this project is fetched in 2026, long after it was first published |
| D38 | 2026-11-05 | Release framework (T034): the paired block bootstrap (1000 resamples, seed 42) resamples whole blocks; a candidate is only `candidate_eligible` with enough rows and blocks, both test scores present, the model's own loss threshold met and a lower 95% bound above 0; a missing score makes the release `research_only`, never 0. Releases are immutable JSON files under `models/releases/<model>/` (written once); an eligible candidate becomes champion only after a separate owner approval file. MLflow (ml lock) is an optional local mirror | Plan section 11 and T034; owner approval keeps 'no silent challenger promotion' true by construction |
| D39 | 2026-11-05 | M05 (T101) is evaluated as a **hindcast**: features for issue month t use IMD rain up to the end of month t-1, as if it were known at issue. S08 files are released yearly, so this timing was not really available; every M05 result must be labelled a hindcast (plan D07). District rain is the mean of 0.25 degree cells weighted by overlap area in m2; SPI uses a gamma fit with a zero-rain share per district and calendar month on 1981-2010; drought is SPI-3 < -1.0. The training window ends 2016-09-30, 92 days before the first test month, because SPI-3 targets span 3 months | Honest labelling beats a live claim the data cannot support; the purge stops shared target months between train and test |
| D40 | 2026-11-05 | S08: -999 on a land cell for one day is a **missing day**, not a mask change (the IMD 2023 file has 79 land cells at -999 on 12 Oct 2023, none in the Karnataka box). The adapter stores it as null with `not_reported` and the `missing` flag; a sea cell that gains a value still fails. M05 drops a cell from a district's monthly mean for any month in which that cell has a missing day | Found by the T101 run on 1981-2024; zero-filling a gap would understate rain |
| D41 | 2026-11-05 | M05 fit (T102): baselines SPI-3 persistence and train-only month climatology; ridge (alpha on tune) is the provisional candidate; LightGBM (30 seeded configurations from the section 11 space, early stopping on tune) replaces it only if its paired block bootstrap lower 95% bound on tune is above 0. Hyperparameters are sampled with numpy seed 42 instead of Optuna. No notebook: results are in `data/models/m05/m05_fit.json` (git-ignored) and the local MLflow store `data/models/mlflow.db`. First run (tune 2017-2018, 720 rows): MAE persistence 0.736, ridge 0.585, LightGBM 0.571; LightGBM gain over ridge lower bound -0.013, so ridge stays | Plan T102 and section 11; fewer dependencies; the decision rule matches 'promote LightGBM only with skill' |
| D42 | 2026-11-05 | M05 release v1 (T103): evaluated once on the locked 2020-2024 test against the stronger baseline on the test rows (persistence). Drought probabilities come from a Gaussian with the spread of 2019 residuals. Result: ridge passes all gates (MAE 0.732 vs 0.808, bootstrap lower bound 0.003; PR-AUC 0.217 vs prevalence 0.057; Brier skill 0.116; CRPS 0.530 vs 0.586), so status `candidate_eligible` with approval `pending`: persistence serves until the owner approves. Known limits: 80% intervals cover only 65% and probabilities run high, so intervals are not published; it is a hindcast (D39) | Plan T103 gates; the owner approval step keeps promotion explicit |
| D43 | 2026-11-05 (**owner approval in chat: "Approve M05"**) | M05 release v1 is approved: `models/registry/M05/v1.approval.json` makes ridge the champion drought model; the release file itself stays unchanged. Published M05 outputs must say hindcast (D39) and must not show the 80% intervals until they are recalibrated (D42) | Owner decision at H11 after reading `reports/models/m05.md` |
