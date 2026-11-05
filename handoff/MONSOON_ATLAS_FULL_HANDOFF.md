# Monsoon Atlas: full handoff package

Generated 2026-11-05 17:56 UTC from commit `968e73b` of https://github.com/Joepikka/monsoon-atlas

## How to use this with ChatGPT (or any agent)

1. Upload this file, `docs/plan.pdf` (ChatGPT's original 263-page plan) and, if the tool allows,
   `monsoon-atlas-code.zip` (all code, tests, configs and docs from `main`).
2. Paste the starter prompt from section 12 of the handoff guide below.
3. The agent works in `D:\monsoon-atlas` on Joe's laptop (Windows, everything on drive D),
   one task at a time: acceptance test, commit with the task ID, push, update `docs/HANDOFF.md`.
4. Human-only steps (accounts, terms, passwords, keys, approvals) stay with Joe.

Contents: handoff guide; agent rules; decisions D01-D43; amendments; GATE-CORE report; M05
model report; every source discovery report; state and model configs; file inventory; full
commit history. Raw data (about 3 GB in `data/raw`) and `.env` are not included and never
committed.


---

# 1. Handoff guide (start here)

Source file: `docs/HANDOFF.md`

# Monsoon Atlas: handoff for the next AI agent

Last updated: 5 Nov 2026, after T103 approval (commit `7f3780e`, branch `p1/gate-core`).

This file lets another agent (for example ChatGPT) continue the project without the earlier chat.
Read it fully, then read `AGENTS.md`, then the documents listed in section 2. Keep this file up to
date: add a row to section 7 after every task and refresh sections 8 and 9.

## 1. What the project is

- **Monsoon Atlas** is an open, Rs 0, map-first data and machine-learning site for Indian states.
  It was inspired by KW Live (a Kuwait live map) but must not copy its name, logo, look or text.
- **Owner:** Joe Kanjirathingal (GitHub `Joepikka`), a student in Kerala, building a portfolio
  project. Repository: https://github.com/Joepikka/monsoon-atlas (public, MIT code licence).
- **Who builds:** an AI coding agent does all the building. The owner reviews and does the
  human-only steps (accounts, terms, passwords, keys).
- **State order:** Karnataka (phases P0 to P2), then Kerala (P3), then Delhi (P4), then
  cross-state work (P5).
- **Owner's working rule (5 Nov 2026):** do not ask the owner to approve each next task; make the
  best decision for the project, record it, and keep going. Still stop for human-only steps.

## 2. Source-of-truth documents (all in the repository)

| File | What it is |
|---|---|
| `docs/plan.pdf` | The full plan written by ChatGPT (263 pages, 4 Nov 2026): tasks T001 to T221, model cards M01 to M20, source catalogue S01 onwards, decisions D01 to D16, schemas, leakage rules |
| `docs/amendments.md`, `docs/amendments.yaml` | Amendments v1 (5 Nov 2026). **They win where they conflict with the plan.** Adds T222 to T225, the GATE-CORE check (A4), human-only steps H01 to H14 (A5), and the P1 session order (A8) |
| `docs/decisions.md` | Decisions log D01 to D30. Every deviation from the plan is recorded here before it is made |
| `AGENTS.md` (imported by `CLAUDE.md`) | Rules for AI agents: hard constraints, environment, how to work on a task, commands |
| `docs/planning/1-handoff.pdf`, `2-project-overview.pdf`, `3-chatgpt-prompt.pdf` | The earlier handoff, overview and the prompt that produced `plan.pdf` |
| `docs/research/kw-live-and-india-data-research.md` | The original KW Live and Indian open-data research |
| `docs/gates/core_data_gate.md` | GATE-CORE report (T222) with decisions D17 and D29 |
| `docs/sources/sNN.md` + `configs/sources/sNN.yaml` | One discovery report and record per checked source |
| `docs/dependency-audit.md` | Licence and wheel audit of every locked package (T007) |

Tip: `pdftotext -layout docs/plan.pdf .cache/plan.txt` (Git Bash has pdftotext) gives a
searchable text copy of the plan; each task has a heading like `T057 - Verify access, ...`
and a YAML block `- id: T057`.

## 3. Hard constraints (never break)

1. **Cost Rs 0.** Free tiers and open data only; no paid API, no card on file.
2. **Real data only.** Never invent rows, URLs, endpoints or fields. A source stays disabled until
   its verify task passes; a disabled source raises `SourceUnavailable` and never returns rows.
3. **Honest ML.** Time-based (and where stated, spatial) splits; features available at issue
   time; compare with the strongest simple baseline; promote a model only if the lower 95%
   paired bootstrap CI of the improvement is above 0, otherwise publish it as research-only.
4. **Not an emergency service.** Official alerts, model outputs and inferred items stay visibly
   separate.
5. **Privacy.** No personal data, accounts or subscriber databases.
6. **Licences.** Raw files from sources that reserve rights stay in `data/raw` (git-ignored) and
   are never committed or redistributed. Commit only manifests with SHA256.
7. **Human-only steps** (A5, H01 to H14): the agent never creates accounts, accepts terms, enters
   passwords or types keys. Keys live in `.env` (git-ignored) or GitHub Actions secrets.
8. **Drive D only** (D26): the laptop's drive C is nearly full. Never write caches, models or data
   to C.

## 4. Environment and commands

- Windows 10, 15.7 GB RAM, 4 cores, NVIDIA MX450 (too small for deep learning; train on Kaggle or
  Colab).
- Repository `D:\monsoon-atlas`. Python **3.12.14** lives in `.tools/python` (uv-managed, no
  admin installer); `.venv` is built from it. **DuckDB 1.x only** (2.0.0 corrupted files before).
- Caches: pip, pip-tools and uv in `.cache/`; pytest temp in `.pytest-tmp/`; before any download
  set `TEMP` and `TMP` to `D:\monsoon-atlas\.cache\tmp`.
- Locks: `requirements/{core,dev,geo,ml,dl}.in` compiled to hash-locked `.txt` with pip-tools
  (Windows, Python 3.12; D25). Install with `pip install --require-hashes -r requirements/core.txt`
  and `dev.txt`; raster and polygon work also needs `geo.txt` (installed locally, D35).
- Commands (PowerShell):

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
```

- CI: `.github/workflows/ci.yml` runs the tests on windows-latest and ubuntu-24.04 (actions pinned
  to SHAs, read-only permissions). Tests that need local raw files skip in CI.
- To rebuild the environment from scratch: install uv, `uv python install 3.12.14` into
  `.tools/python`, create `.venv` from that interpreter, then install the two locks above.

## 5. Code map

| Path | Purpose (task) |
|---|---|
| `src/atlas/config.py` | Typed YAML config: `StateConfig`, `SourceConfig` (a source cannot be enabled without `verified_by`; only free sources), budgets (T003) |
| `src/atlas/contracts.py` | Pydantic contracts: `FetchContext`, `RawArtifact`, `Budget`, `ManifestFile`, ID types (T003) |
| `src/atlas/cli.py`, `__main__.py` | Typer CLI skeleton (`python -m atlas --help`; `quota` implemented) (T003, T006) |
| `src/atlas/ingest/http.py` | `Fetcher`: https-only host allowlist, no redirects outside it, retries with Retry-After cap, circuit breaker, request/byte budgets, conditional GET (304 reuses the stored copy), secrets only in requests; `FixtureTransport` for offline tests (T004) |
| `src/atlas/ingest/raw_store.py` | Content-addressed raw store and JSONL ledger under `data/raw/<source>/<date>/<sha256>.<ext>` (T004) |
| `src/atlas/ingest/base.py` | Adapter protocol `fetch(ctx)` and `parse(raw, config)`; error types (T004) |
| `src/atlas/ingest/discovery.py` | Shared discovery contract (D27): `Discovery` record, `EvidenceManifest`, `capture()`, `check()` |
| `src/atlas/ingest/s01.py`, `s02.py`, `s08.py`, `s09.py`, `s15.py`, `s16.py`, `s17.py`, `s18.py` | Source adapters (T010 to T022, T058): `fetch(ctx)` with the shared Fetcher, `parse(raw, config, ...)` to the common envelope plus source columns; `schemas/sNN.json` documents the columns |
| `src/atlas/spatial/places.py`, `crosswalk.py` | Place table, gazetteer with version history, H3 cells, point lookup, area and population crosswalks, metres (T032) |
| `src/atlas/features/base.py`, `src/atlas/models/base.py`, `splits.py` | FeatureSpec and as-of feature building with leakage checks, ModelSpec, evaluators, rolling-origin and spatial splits, hashed split manifests (T033) |
| `src/atlas/models/uncertainty.py`, `evaluate.py`, `registry.py` | Paired block bootstrap, validation-only intervals and thresholds, champion gates, immutable releases with owner approval (T034) |
| `src/atlas/data/validate.py` | Common envelope (`schemas/common.json`) validation, missing-is-not-zero rule, mapping metadata (T005) |
| `src/atlas/data/asof.py` | IST/UTC helpers and DuckDB as-of joins that never use future data (T005) |
| `src/atlas/data/manifest.py`, `store.py`, `budget.py` | Versioned Parquet snapshots, manifests, cache rebuild, 20 GB storage quota (T006) |
| `scripts/audit_dependencies.py` | Licence and Windows-wheel audit (T007) |
| `configs/states/ka.yaml` | Karnataka sources; enabled: S01, S02, S08, S09, S15, S16, S17, S40 |
| `configs/budgets.yaml` | Request, storage and DuckDB budgets |
| `tests/` | 211 tests: contracts, fetcher, storage, as-of, discovery records, gate report, S08 adapter |

## 6. How one task is done (the process every task followed)

1. Pick the next task in the order of section 9. Read its spec in `docs/plan.pdf` (task heading
   and YAML block), check its dependencies, and check the amendments and decisions.
2. **Discovery task** ("Verify access, units and licence"):
   - Explore the source's real pages (generic User-Agent
     `MonsoonAtlas-discovery/0.0.1 (+https://github.com/Joepikka/monsoon-atlas)`, 3 seconds
     between requests, honour robots.txt). Never bypass TLS or sign-ins.
   - Capture evidence with `atlas.ingest.discovery.capture()` into `data/raw` and write
     `tests/fixtures/sNN/manifest.json`. A failed fetch (404, login redirect, TLS error) goes in
     `failed_fetches`, never worked around.
   - Write `configs/sources/sNN.yaml` (outcome available or blocked; access, licence, quota,
     history, units and source-check claims, each citing evidence IDs; field map to the
     canonical fields in plan section 7; dependents; retry condition if blocked).
   - Write `docs/sources/sNN.md` (plain-language report) and `tests/sources/test_sNN_discovery.py`
     (contract passes, status fields, no data committed, local hashes, and checks of the key
     facts against the raw evidence).
3. **Adapter task** ("Implement source contract"): `src/atlas/ingest/sNN.py`, `schemas/sNN.json`,
   `tests/sources/test_sNN.py`. Test a real permitted sample, a malformed copy, an empty response
   and changed columns; a disabled source raises `SourceUnavailable`. Enable the source in the
   state YAML with `verified_by` only after discovery passes.
4. Run the task's acceptance command and the full suite and ruff. A task is done only when they
   pass.
5. Record any deviation in `docs/decisions.md` first.
6. Commit with the task ID (`T058: ...`), ending the message with a co-author line. Push.
7. Update this file and the Obsidian vault (section 11).

## 7. Work log (every task so far)

| Task | Commit | Result |
|---|---|---|
| Planning | — | KW Live researched (4 Nov). ChatGPT wrote `docs/plan.pdf`. Claude reviewed it and wrote amendments v1 (portfolio core first, GATE-CORE, human-only steps, Power BI and SQL extras) |
| T001 | `3e2494b` | Repository, README, MIT licence, planning docs, AGENTS.md and CLAUDE.md |
| T002 | `57d5ce6` | Python 3.12 venv, hash-locked requirements, ruff, first tests |
| T003 | `0110985` | Config models, typed contracts, `ka.yaml`, `budgets.yaml`, CLI skeleton |
| T004 | `a8c5daf` | Fetch boundary (allowlist, retries, budgets, breaker, conditional GET) and raw ledger |
| T005 | `6a2e520` | Common envelope schema, missing-reason rule (D23), as-of joins |
| T006 | `da5d845` | Versioned Parquet manifests, cache rebuild, storage quota (D24) |
| T007 | `5b431b2`, `7dfa7ca` | CI on Windows and Ubuntu, five dependency locks (D25), dependency audit. Project moved fully to drive D (D26). Pushed; PR #1 (P0) merged into `main` at `2875841` |
| T008 | `955d501` | S28 KWRIS (Karnataka reservoirs): **blocked**. Public layer has only the latest reading, no units, all rights reserved; API needs an account |
| T030 | `863f34d` | S40 ward and taluk polygons: **available** for GBA 2025 wards (369, public domain); older BBMP maps unlicensed; no taluk polygons |
| T085 | `7d76b63` | S43 Bengaluru flood labels: **blocked**. No official dated ward-level incidents; the I Change My City complaints log is not ground truth (no rule for negatives) |
| T222 | `71c8d90`, `feffd27` | GATE-CORE: C1 fail, C2 fail, wards pass. D17 approved by the owner: C1 = M07 Kerala dam forecast, C2 = M08 Kerala flood classifier; also try KWRIS (owner emails the helpdesk) |
| T113 | `7a5da80` | S32 KSEB daily dam levels: **available** only from Oct 2023, with a two-year gap |
| T117 | `5681b09` | S34 KSDMA daily dam reports: **available** 20 Jun 2020 to 4 Nov 2026 (2,296 dates), but scanned images, so OCR plus manual review is needed (T118). M07 can train from Jun 2020 |
| T119 | `2ae3917` | S35 Kaggle Kerala 2018 flood datasets: **blocked** (sign-in, no licence, rain tables) |
| T003 fix | `00123ba` | CLI help test pins the child encoding to UTF-8 |
| T121 | `c34fe50` | S36 KSDMA memoranda: **available**, but only district totals; one dated district table (16 Jul 2018); no flood labels before 2018, so M08 can only be a descriptive replay. Discovery contract accepts 304 revalidation (D27); D28 records T117 and T121 in P1 |
| D29 | `3070678` | Core C2 becomes **M05 Karnataka drought outlook** (A4 second fallback), on district or H3 cells; M08 stays as a non-core 2018 replay in P3 |
| T057 | `2cb3c54` | S08 IMD Pune 0.25 degree daily rainfall: **available 1901 to 2025**, GET download, no account. Raw float32 135 x 129, mm, fixed land mask. Disclaimer forbids reproduction without permission, so raw stays local and only derived indices are published. Yearly files only |
| T058 | `63f17d3` | S08 adapter: Karnataka box (540 cells), envelope + `cell_id`, `date_local`, `rain_mm`, `grid_resolution_deg`; `valid_at` = 08:30 IST next day (D30); S08 enabled in `ka.yaml` |
| T009 | `f9dec30` | S01 Open-Meteo forecast: **available** (no key, CC BY 4.0, non-commercial limits). Issue time only via a named model's meta.json; best-match not used. D31: API-host robots.txt is crawler guidance |
| T010 | `cb7f4ca` | S01 adapter: one named model, issue time from meta.json read around the call, settle 10 min (D32); enabled; CC BY fixtures committed so CI runs real-sample tests |
| T011 | `82a82b3` | S02 Open-Meteo ERA5: **available** 1940-01-02 to D-6 (CC BY 4.0, models=era5, IST days). Reanalysis = provenance model; keep the release lag |
| T012 | `ed6842f` | S02 adapter: era5 daily, IST days, valid_at end of day, lag days null not_yet_available; enabled; CC BY fixtures |
| T013 | `f7fea2d` | S09 Sachet CAP alerts: **available**, public domain; feed = latest 100 alerts (~21 h), so history starts with polling; Updates reference replaced alerts; polygons via Polygon URL, else area text |
| T014 | `cd59203` | S09 adapter: CAP to rows, supersede(), WKB polygons, Karnataka filter by sender/area/box (D33); enabled; public-domain fixtures |
| T015 | `f1fadc3` | S15 OpenFreeMap: **available**, no keys; attribution from TileJSON; terms: no bulk tile download, integrator 18+ (owner check before deploy) |
| T016 | `94903c4` | S15 adapter: style + TileJSON to one row (style_url, revision, attribution); no tile downloads; enabled |
| T019 | `56c3b4c` | S17 geoBoundaries: **available**; ADM2 2021 ODbL has 735 districts (not 736), Karnataka 30 (no Vijayanagara); ADM1 2011; no disputed-boundary field (owner check vs India mapping guidance) |
| T020 | `c0a2c6b` | S17 adapter: 30 Karnataka districts, place_id gb-IND-ADM2-<id>, boundary_version with release, parent by point-in-polygon, WKB; enabled |
| T017 | `4a5735e` | S16 WorldPop: **available**, R2025A 1 km counts 2015-2030, CC BY 4.0; alpha release, post-2025 are projections; LZW BigTIFF needs rasterio (geo lock) for T018 |
| T021 | `1545fc5` | S18 Geofabrik: **blocked**, robots.txt disallows *.osm.pbf (D34); 533 MB extract; retry = owner browser download to data/raw/S18, Geofabrik permission, or Overpass source |
| T022 | `a883fa3` | S18 disabled adapter: fetch/parse raise SourceUnavailable, zero rows |
| T018 | `98a6524` | S16 adapter: native 1 km cells in the S17 state polygon, totals conserved (Karnataka 2025: 203,344 cells, ~70.8 M); geo lock installed locally, lazy imports (D35); enabled |
| T031 | `2774b3f` | S40 adapter: 369 GBA 2025 wards, place_id gba2025-c<corp>-w<ward>, parent corporation, WKB; BBMP maps never parsed; enabled |
| T032 | `e9807ef` | Places + gazetteer + crosswalks (src/atlas/spatial): version history, H3 r7/r8 never wards, m2 areas (EPSG:6933), metres, ambiguous search lists choices (D36). Finding: WorldPop gives ~6.0 M in GBA wards (undercount) |
| T033 | `680f65e` | Feature framework (src/atlas/features/base.py, models/base.py, models/splits.py): as-of features with __known_at + assert_as_of, hindcast lag rule, rolling-origin/spatial-block splits with purge, hashed manifests, train-only scaler, strict evaluators (D37) |
| T034 | `e3f07bb` | Release framework (models/uncertainty.py, evaluate.py, registry.py): block bootstrap seed 42, validation-only intervals/thresholds, decide() gates, immutable release JSON + owner approval file, optional MLflow (D38) |
| T023 | `41c763e` | S22 India Data Portal: **blocked** (client-side app, no link or licence in HTML, robots 403, browser unavailable); retry with a browser render; T025 data.gov.in is the other route |
| T101 | `bbe7c25` | M05 target + features pass on IMD 1981-2024 (30 districts, SPI-3 ~N(0,1) on 1981-2010, lag and mutation checks, gate, purged manifest); 2023 missing day handled (D40) |
| T025 | `f1af6cd` | S23 data.gov.in mandi: API works with owner key (current-day snapshot, Karnataka 565 rows, checks pass) but **blocked on licence**: owner to read licence + unit from Catalog Info |
| T102 | `e6cb916` | M05 fit (src/atlas/models/m05.py): tune 2017-2018 MAE persistence 0.736, ridge 0.585, LightGBM 0.571 (gain not significant) -> ridge provisional; deterministic, test rows refused, artifacts in data/models (D41) |
| T103 | `bea3eb9` | M05 locked test 2020-2024: ridge beats persistence on all gates (MAE 0.732 vs 0.808, CI lower 0.003, PR-AUC 0.217, Brier skill 0.116, CRPS lower); release v1 candidate_eligible, **owner approval pending**; intervals under-cover (65%) so not published (D42). Report: reports/models/m05.md |
| T103 approval | `7f3780e` | Owner approved M05 v1 (D43): ridge is the champion; outputs labelled hindcast, no intervals |

## 8. Current state

### Core models (portfolio MVP)

| Slot | Model | Status |
|---|---|---|
| C1 | **M07 Kerala seven-day dam forecast** (D17) | Data: S34 KSDMA daily reports from Jun 2020 (scanned; needs OCR, T118) and S32 KSEB from Oct 2023 (T114 adapter). Model tasks T130 to T132 |
| C2 | **M05 Karnataka drought outlook** (D29): SPI-3 of the issue month and drought probability, per district | T101 is done (`src/atlas/features/m05.py`, `configs/models/m05.yaml`); evaluated as a hindcast (D39). Then T102 (baselines + LightGBM/ridge) and T103 (evaluate and publish) |
| C3 | Ask (question answering, English first) | T179 to T181; uses Cloudflare Workers AI free tier with an extractive fallback (D08) |

Blocked with retry conditions: M01 (Bengaluru ward floods), M02 (KWRIS reservoirs), M03.
M08 is a non-core descriptive 2018 replay (P3).

### Sources checked

| Source | Task | Outcome | Note |
|---|---|---|---|
| S08 IMD gridded rainfall | T057, T058 | available, enabled | raw local only |
| S01 Open-Meteo forecast | T009, T010 | available, enabled | CC BY 4.0; issue time from model meta.json |
| S02 Open-Meteo ERA5 | T011, T012 | available, enabled | reanalysis (provenance model); 6-day lag |
| S09 Sachet CAP alerts | T013, T014 | available, enabled | public domain; poll every 15 min (feed keeps 100) |
| S15 OpenFreeMap basemap | T015, T016 | available, enabled | keep attribution; no bulk tiles; integrator 18+ |
| S16 WorldPop population | T017, T018 | available, enabled | CC BY 4.0; R2025A alpha; needs geo lock |
| S17 geoBoundaries | T019, T020 | available, enabled | 30 Karnataka districts (no Vijayanagara); ODbL |
| S18 Geofabrik OSM | T021, T022 | blocked | robots.txt disallows .osm.pbf (D34) |
| S22 India Data Portal Agmarknet | T023 | blocked | client-side app; retry with a browser render; T025 is the other route |
| S28 KWRIS | T008 | blocked | retry if KWRIS daily history arrives |
| S32 KSEB daily levels | T113 | available (partial history) | adapter T114 |
| S34 KSDMA dam reports | T117 | available (scanned) | OCR T118, adapter |
| S35 Kaggle Kerala floods | T119 | blocked | needs owner Kaggle sign-in (H10) |
| S36 KSDMA memoranda | T121 | available | adapter T122 in P3 |
| S40 ward polygons | T030, T031 | available, enabled | 369 GBA 2025 wards, public domain |
| S43 Bengaluru flood labels | T085 | blocked | not ground truth |

### Pending human-only steps (owner)

- Send the drafted KWRIS helpdesk request to ACIWRM (daily reservoir history). If data arrives
  with units, datum and licence, re-run T008.
- H04: Delhi Open Transit Data registration (needed in P4).
- H10 (optional): Kaggle sign-in only if the owner wants S35 re-checked.
- H11: review at each gate and before any public deployment (licences: S08 and S34 forbid
  reproduction, so only derived outputs may be published).
- Before public deployment also: confirm you are 18+ (OpenFreeMap terms), check boundary maps
  against India's official mapping guidance (geoBoundaries has no disputed-boundary field), and
  label WorldPop counts for Bengaluru as an undercount (about 6.0 million in the GBA wards).
- data.gov.in API key (free, needs an account) for T025 mandi prices: put it in `.env` as
  `DATA_GOV_IN_API_KEY` (name only in code).
- Optional: download `southern-zone-latest.osm.pbf` from Geofabrik in a browser into
  `data/raw/S18/` to unblock S18 (D34).

### Git

- `main` has everything through T103 and the M05 approval (PR #1 P0, PR #2 P1 base layers and
  frameworks, PR #3 M05 and T025; merge `37769bb`). Keep working on branch `p1/gate-core` (or a
  new branch from `main`) and open a PR per batch; auto-merge is enabled on the repository.
- Claude stopped at 89% of its weekly usage on 5 Nov 2026; this file is the full handoff.

## 9. Next tasks, in order

Amendments A8 order, with the D17 and D29 fallbacks:

1. **A8 step 3 is done** (T009 to T022, T031, T032; S18 blocked).
2. **A8 step 4, core sources:** T027 (KWRIS) and T086 stay blocked (skip with a note);
   T011/T012 if not done in step 1.
3. **A8 step 5, frameworks:** done (T033, T034).
4. **T101 is done** (the S08 1981-2024 files are in data/raw; re-fetch with the S08 adapter if missing).
5. **C2 = M05 is evaluated** (T102, T103; report `reports/models/m05.md`, release
   `models/registry/M05/v1.json`). Ridge passed every gate on 2020-2024; status
   `candidate_eligible`, **approved by the owner (D43)**: ridge is the champion.
   Before publishing intervals, recalibrate them (they cover 65%, not 80%).
6. **C1 = M07 (Kerala):** T129 creates `configs/states/kl.yaml` (needed before any Kerala
   source can be enabled), T114 (S32 adapter), T118 (OCR for S34; pin a free OCR such as
   Tesseract and record it in decisions; the owner reviews an OCR sample), T130 to T132. T130
   must re-plan the M07 splits because history starts on 20 Jun 2020.
7. **Prices:** T025 data.gov.in (needs the owner's free API key), then T024/T026 and T035 to T037.
8. Then A8 steps 9 to 13: map and product, hosting, C3 Ask, T225 case studies, T046 MVP
   gate.

## 10. Lessons and pitfalls

- PowerShell on this laptop decodes child output as cp1252; pin `encoding="utf-8"` when a test
  reads subprocess output. Print with `sys.stdout.reconfigure(encoding="utf-8")`.
- `pdftotext` exists only in Git Bash (`/mingw64/bin`). Many government PDFs use Identity-H fonts,
  so the standard library cannot read them; adapters must pin a PDF parser (pypdf) in a lock.
- The fetcher sends conditional requests; a 304 reuses the stored file (even one stored for
  another source with the same URL).
- Indian government sites often have broken TLS chains (BBMP, GBA): record the failure, never
  disable verification.
- Kerala has no state config yet (`configs/states/kl.yaml` arrives in T129), so Kerala sources
  cannot be enabled.
- Full suite takes about 1 minute locally (S08 tests parse a 25 MB file several times).
- IMD Pune speed varies a lot (10 s to 5 minutes per 25 MB year file); run big fetches in the
  background.
- WorldPop GeoTIFFs are BigTIFF (`II+`) with LZW tiles: use rasterio (geo lock).
- Many pages put `&nbsp;` between numbers and units; match the raw HTML, not the rendered text.
- Client-side web apps (India Data Portal) need a browser render; never guess their APIs.
- GitHub sometimes rejects a push with `fatal error in commit_refs`; just retry.
- Geo and ml locks are installed locally; CI installs core and dev only, so tests that need
  rasterio, shapely, h3, scipy or mlflow use `pytest.importorskip` (D35).

## 11. Obsidian vault (owner's second brain)

Vault: `C:\Users\joepi\Documents\Obsidian Vault`. Project note: `Projects/kerala-live-map.md`
(current state and next action). Session log: `Claude/Work log.md` (newest first). Facts:
`Claude/Memory.md`. Never write credentials or raw datasets there.

## 12. Starter prompt for the next agent

> You are continuing Monsoon Atlas in `D:\monsoon-atlas` (GitHub Joepikka/monsoon-atlas, branch
> `p1/gate-core`). Read `docs/HANDOFF.md`, `AGENTS.md`, `docs/amendments.md` and
> `docs/decisions.md`. Use `docs/plan.pdf` for task specs. Take the first task in HANDOFF section
> 9, follow the process in section 6, run its acceptance command, commit with the task ID, push,
> and update HANDOFF sections 7 to 9. Do not ask for approval between tasks; stop only for
> human-only steps H01 to H14.



---

# 2. Rules for AI agents

Source file: `AGENTS.md`

# AGENTS.md: rules for AI coding agents

This repository is built by an AI coding agent following a fixed plan. Read this file before every task.

## Source of truth

1. `docs/plan.pdf`: the full plan (263 pages, 4 Nov 2026). Tasks T001 to T221, model cards M01 to M20, source catalogue S01 onwards, decisions D01 to D16.
2. `docs/amendments.md` and `docs/amendments.yaml`: amendments v1 (5 Nov 2026). **Where they conflict with the plan, the amendments win.** New tasks are T222 to T225.
3. `docs/decisions.md`: the decisions log. Record every deviation from the plan here before you make it.

## Hard constraints (never break)

- **Cost Rs 0.** Free tiers and open data only. No paid API, no paid hosting, no card on file. The Claude API is paid, so Ask uses a free tier (Cloudflare Workers AI) with an extractive fallback.
- **Build order:** Karnataka (P0 to P2), then Kerala (P3), then Delhi (P4), then cross-state work (P5). Follow the session order in amendments A8.
- **Real data only.** Never invent rows, labels, URLs, endpoints or API fields. Unverified sources stay disabled until their verify task passes. A disabled source raises `SourceUnavailable`; it never returns synthetic rows.
- **Honest ML.** Time-based (and, where stated, spatial) splits only. Features must be available at issue time. Always compare with the strongest simple baseline. Promote a model only if the lower 95% paired bootstrap CI of the improvement is above 0. Otherwise publish it as research-only.
- **Not an emergency service.** Official alerts, model outputs and inferred items stay visibly separate. No routing is promised to be safe.
- **No KW Live reuse.** Do not copy the KW Live name, logo, visual identity or website text.
- **Privacy.** No personal data. No accounts or subscriber databases.

## Environment

- Windows 10, 15.7 GB RAM, 4 cores, NVIDIA MX450 (2 GB, too small for deep learning; train on Kaggle or Colab).
- **Python 3.12 only** (never 3.14) in `.venv`. **DuckDB 1.x only** (2.0.0 corrupted files in an earlier project).
- **Everything stays on drive D** (drive C is nearly full; decision D26). The repository is `D:\monsoon-atlas`; Python 3.12.14 is in `.tools/python`; pip, pip-tools and uv caches are in `.cache/`, pytest temp files in `.pytest-tmp/`. Before any command that downloads, set `TEMP` and `TMP` to `D:\monsoon-atlas\.cache\tmp`. Never write caches, models or datasets to drive C.
- DuckDB settings: `memory_limit=4GB`, `threads=4` (amendment A2).

## How to work on a task

1. Pick the next task in the amendments A8 order. Check that its dependencies are done.
2. Do only that task. Keep it within one session (about 3 hours). If it grows, split it into a child task recorded in both the task list and the YAML.
3. Run the task's acceptance command and show its output. A task is done only when the acceptance test passes.
4. Commit with the task ID in the message, for example `T002: Python 3.12 environment, linting and tests`.
5. Record any deviation in `docs/decisions.md`.

## Human-only steps (amendments A5)

The agent never creates accounts, accepts terms, enters passwords or types keys into web forms. When a task needs one of the H01 to H14 steps, stop and ask the owner. Keys live in `.env` (ignored by git) or in GitHub Actions secrets; code reads only the variable names.

## Commands

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
```



---

# 3. Decisions log D01-D43

Source file: `docs/decisions.md`

# Decisions log

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



---

# 4. Plan amendments v1 (win over the plan)

Source file: `docs/amendments.md`

# Monsoon Atlas: plan amendments v1

Date: 5 November 2026. This document amends `Monsoon-Atlas-Complete-Planning-Handover.pdf` (263 pages, 4 Nov 2026), called "the plan" below.

## 0. How to use this document

- **Precedence:** where an amendment conflicts with the plan, the amendment wins. Everywhere else, the plan stays authoritative, including all scientific rules, the Rs 0 rule, source rules, schemas, model cards and the decisions log D01 to D16.
- **T001 change:** copy this file to `docs/amendments.md` next to `docs/plan.pdf`. Copy Appendix Y below to `docs/amendments.yaml`. Keep the numbered list and the YAML in sync, as the plan requires for its own task list.
- **Task IDs:** existing IDs are never renumbered. New tasks use T222 onwards. Reordering is stated as new dependency edges.

## A1. Who builds, and how the timeline is measured

| Plan says | Amended |
|---|---|
| Owner codes 10 focused hours a week plus 25% contingency, giving 115 weeks | **An AI coding agent (Claude Code) does all building.** The owner reviews, approves and does the human-only steps in A5 |
| Hours per task | `hours` now means agent-session effort. The 3-hour cap stays as the size of one session |
| Week-by-week calendar | Replaced by a **session sequence plus external gates**. Calendar time depends only on waits: data availability checks, account approvals (Delhi OTD), prospective forecast-vintage collection and label maturation |

Estimate: 225 tasks, about 225 agent sessions. The portfolio-core MVP (A3) is about 60 sessions. A human review checkpoint (H11) happens at every phase gate. No date in the plan's section 15 table is binding.

## A2. Hardware

- T002 still measures the real machine. The planning default changes from 8 GB to **16 GB RAM**, Windows 10, no local GPU.
- If T002 measures 16 GB or more, set DuckDB `memory_limit=4GB`, `threads=4`. Otherwise keep the plan's values (2 GB, 2 threads).

## A3. Portfolio core (new MVP scope)

The MVP must include the three models that matter most for data and ML job applications. They are built first and documented most deeply.

| Core | Model / feature | Plan tier before | Amended |
|---|---|---|---|
| C1 | **M02 Karnataka reservoir level and storage** (T092 to T094) | v1, P2 | **MVP, P1** |
| C2 | **M01 Bengaluru ward flood occurrence** (T089 to T091) | v1, P2 | **MVP, P1** |
| C3 | **F046 cited RAG Ask, text, English** (T179 to T181) | v1, P5 | **MVP, P1** |
| (secondary) | M06 Kolar tomato price spike (T035 to T037) | MVP | Stays in MVP, but is **not a headline**. It is presented as "the kerala-veg-prices method extended to Karnataka" |

Rules:
- The plan's promotion rule still applies. If a core model does not beat its baseline with the lower 95% CI above 0, it is published as **research-only** with its full report. An honest negative result still counts as a finished core model.
- T182 (voice and the four-language UI) stays outside the MVP. See A7.
- **T046 Karnataka MVP gate** gets these extra acceptance checks: (1) C1 and C2 each have a published evaluation report (champion or research-only) and a model card; (2) C3 passes the T181 evaluation thresholds on the English subset; (3) one case study per core model exists in `reports/models/` (H14 reviews it); (4) the accuracy page (F036) shows C1, C2 and M06.

## A4. Early core-data gate (GATE-CORE)

Problem: the M01 labels (source S43) and the KWRIS daily history are UNVERIFIED. If either is missing, a flagship model has no data, and in the original order this would only become clear in P2.

New order at the start of P1: **T008 (KWRIS) → T030 (ward polygons) → T085 (flood impact labels) → T222 (GATE-CORE report)**, before any other P1 source task.

**T222 GATE-CORE report** writes `docs/gates/core_data_gate.md` with evidence:

| Check | Pass criterion (use the model card's own minimum if it is stricter) | If it fails |
|---|---|---|
| C1 KWRIS daily history | At least 5 reservoirs with daily level or storage for at least 3 monsoon seasons, with known units and datum | **Fallback C1 = M07 Kerala seven-day dam forecast.** Pull T113, T114 and T130 to T132 forward into P1 |
| C2 Bengaluru ward flood labels | At least 100 documented positive ward-days across at least 3 monsoon seasons, plus an explicit coverage rule for negatives | **Fallback C2 = M08 Kerala flood classifier with the 2018 held-out replay.** Pull T119, T129 and T133 to T135 forward. If those labels also fail, C2 = M05 taluk drought outlook (labels from rainfall indices) |
| Ward boundary version | Official ward polygons with a release date | Use taluk or H3 cells for C2 and record it in the decisions log |

The fallback choice is recorded as decision D17 in the decisions log. The owner approves it (H11).

## A5. Human-only steps (in order)

The agent never creates accounts, accepts terms, enters passwords or types keys into web forms. The owner does these steps and puts keys in `.env` locally or in GitHub Actions secrets. The agent only reads the variable names.

| ID | Step (owner) | When | Unblocks |
|---|---|---|---|
| H01 | Approve the final name (check pages.dev subdomain and name conflicts) | Before T001 | T001 |
| H02 | Create a GitHub account (if needed) and the public repository; authenticate `gh` or git on the laptop | Before T001 | T001, T007 |
| H03 | Install Python 3.12 if the installer needs admin rights | Before T002 | T002 |
| H04 | **Submit the Delhi OTD registration on day 1** (approval takes time) | Project start | T148 (P4) |
| H05 | Create a free Cloudflare account (no card); create an API token for Pages, Workers and D1 | Before T042 | T042 to T045, T180 |
| H06 | Create a Hugging Face account and a write token | Before T045 | T045 |
| H07 | Get a data.gov.in API key | Before T025 | T025, T026 |
| H08 | Create a Telegram bot with BotFather and a public channel; give the bot token | Before T083 | T083, T084, T183 |
| H09 | Get a NASA FIRMS MAP_KEY | Before T075 | T075, T076 |
| H10 | Kaggle account, phone verification for GPU, and API token | Before T168 | T168, T174 |
| H11 | Review and approve at each gate: T222, T046, the P2 gate, T166, and before any public deployment (disclaimers, attribution, India mapping guidance) | At gates | Next phase |
| H12 | Get an aisstream key | Before T111 | T111, T112 |
| H13 | **News labels:** the agent may pre-label, but the owner must review at least 20% of every batch (T189 to T208) and every item in the held-out test set. AI-only labels cannot be the ground truth for evaluating an AI extractor | P5 | T209 to T211 |
| H14 | Read every core case study and rewrite the summary in your own words; practise the interview talking points (plan section 17) | After each core model | Portfolio |

## A6. Data analyst deliverables (new)

The plan has notebooks and web dashboards, but no tools that data analyst job posts ask for.

- **T223 Power BI report:** a free Power BI Desktop report generated as PBIP from code, the same approach as `build_pbip.py` in kerala-veg-prices. Pages: reservoir trends, ward rain and flood exposure, prices, and model accuracy. Commit the PBIP, plus PNG and PDF exports for the README. No Power BI Service publishing (it needs a work account).
- **T224 SQL insights report:** 10 business-style questions answered with DuckDB SQL (for example "which reservoirs filled fastest after the heaviest 3-day rain?"), with queries in `sql/insights/` and results in `reports/sql_insights.md`.
- Both depend on T046 and run at the start of P2.

## A7. Languages

- C3 Ask in the MVP is English only.
- v1 language order is changed to **Kannada first** (Karnataka is state 1), then Malayalam, then Hindi.
- The T181 evaluation set adds at least 10 Kannada questions before the Kannada UI is enabled.

## A8. New P1 order (session sequence)

1. P0: T001 to T007 (unchanged)
2. GATE-CORE: T008, T030, T085, **T222**, then H11 approval
3. Weather, alerts and base layers: T009 to T022, T031, T032
4. Core sources: T027 (KWRIS), T086 (flood labels), T011/T012 (ERA5, if not done)
5. Frameworks: T033, T034
6. **C1:** T092, T093, T094 (or the A4 fallback)
7. **C2:** T089, T090, T091 (or the A4 fallback)
8. Prices (secondary): T023 to T026, T035 to T037
9. Map and product: T038, T039, T040, T041
10. Hosting: T042 to T045
11. **C3:** T179, T180, T181 (English only)
12. **T225** core case studies, then **T046** MVP gate (with the A3 extra checks), then H11 approval
13. P2 starts with T223 and T224, then the rest of P2 in the plan's order (without the tasks moved above)

## A9. Unchanged

All of the plan's leakage rules, split protocols, baselines, promotion gates, model cards, source catalogue, schemas, privacy and legal rules, the Rs 0 and no-card policy, the MIT code licence, and the Kerala-then-Delhi phase order.

## Appendix Y: new and changed tasks (YAML)

```yaml
amendments_version: 1
date: 2026-11-05
new_tasks:
  - id: T222
    title: "GATE-CORE: core data availability report"
    phase: P1
    state: KA
    depends_on: [T008, T030, T085]
    files: [docs/gates/core_data_gate.md]
    steps:
      - "Summarise T008/T030/T085 evidence"
      - "Apply A4 pass criteria"
      - "Record D17 fallback decision if any check fails"
    acceptance: >-
      docs/gates/core_data_gate.md lists each A4 check as pass or fail
      with evidence links; D17 recorded when needed
    hours: 2
  - id: T223
    title: "Power BI report (PBIP from code)"
    phase: P2
    state: KA
    depends_on: [T046]
    files: [powerbi/, reports/powerbi/]
    acceptance: "PBIP opens in Power BI Desktop; PNG and PDF exports committed"
    hours: 3
  - id: T224
    title: "SQL insights report"
    phase: P2
    state: KA
    depends_on: [T046]
    files: [sql/insights/, reports/sql_insights.md]
    acceptance: "10 queries run with duckdb and results match reports/sql_insights.md"
    hours: 3
  - id: T225
    title: "Core case studies (C1, C2, C3)"
    phase: P1
    state: KA
    depends_on: [T094, T091, T181]
    files: [reports/models/m02.md, reports/models/m01.md, reports/models/ask.md]
    acceptance: "Each follows the plan section 17 case-study outline with real numbers only"
    hours: 3
moved_tasks:
  - ids: [T092, T093, T094, T089, T090, T091, T179, T180, T181]
    from: [P2, P5]
    to: P1
    before: T046
  - {ids: [T085, T086], from: P2, to: P1, after: T030}
changed_tasks:
  - {id: T001, change: "Also copy docs/amendments.md and docs/amendments.yaml"}
  - {id: T002, change: "Default 16 GB; DuckDB 4 GB/4 threads if measured >= 16 GB"}
  - {id: T046, change: "Add A3 extra acceptance checks; depends on T225"}
  - {id: T181, change: "MVP uses the English subset; add >= 10 Kannada questions before Kannada UI"}
  - {id: T189-T208, change: "Owner reviews >= 20% of each batch and all test items (H13)"}
fallbacks:
  C1: {primary: M02, fallback: M07, pull_forward: [T113, T114, T130, T131, T132]}
  C2:
    primary: M01
    fallback: M08
    pull_forward: [T119, T129, T133, T134, T135]
    second_fallback: M05
    second_pull_forward: [T101, T102, T103]
```



---

# 5. GATE-CORE report (T222, D17, D29)

Source file: `docs/gates/core_data_gate.md`

# GATE-CORE: core data availability report (T222)

Date: 5 Nov 2026. Rules: amendments A4. Inputs: discovery tasks T008 (S28), T030 (S40) and
T085 (S43). Each discovery record cites evidence pages by ID; the pages themselves are kept
locally in `data/raw` with their SHA256 in the committed manifests.

**Result: 2 of 3 checks fail.** The A4 fallbacks are recorded as decision D17.

**Owner decision (H11, 5 Nov 2026): D17 approved, and KWRIS is also tried.** Next tasks: T113
(KSEB daily water level), then T119 (Kerala 2018 flood dataset). In parallel, the owner asks
ACIWRM for KWRIS daily reservoir history.

**Update (5 Nov 2026): decision D29, core C2 is M05.** M08's fallback labels failed in T119 and
T121, so the second A4 fallback applies (see the last section). Next task: T057 (S08 IMD Pune
gridded rainfall).

| Check | Result | Evidence |
|---|---|---|
| C1 KWRIS daily history | **Fail** | [s28.yaml](../../configs/sources/s28.yaml), [s28.md](../sources/s28.md), [manifest](../../tests/fixtures/s28/manifest.json) |
| C2 Bengaluru ward flood labels | **Fail** | [s43.yaml](../../configs/sources/s43.yaml), [s43.md](../sources/s43.md), [manifest](../../tests/fixtures/s43/manifest.json) |
| Ward boundary version | **Pass** | [s40.yaml](../../configs/sources/s40.yaml), [s40.md](../sources/s40.md), [manifest](../../tests/fixtures/s40/manifest.json) |

## C1 KWRIS daily history: fail

Criterion: at least 5 reservoirs with daily level or storage for at least 3 monsoon seasons, with
known units and datum. M02 itself needs daily history from 2017 to 2024.

- The only public reservoir data is a map layer with **one latest row per reservoir** (36
  reservoirs). Filtering it to K.R.Sagara returns a single row (S28 e07, e08).
- 10 of the 36 readings are more than nine months old; one dates from 23 Oct 2021 (e07).
- **No units or datum** are stated for level, storage or flow (e01, e06, e07).
- The footer says "All Rights Reserved"; there is no open licence (e01, e04, e05).
- The Web API needs an account. Its sign-up form asks for name, email, mobile number and
  organisation, and the agent does not create accounts (e02, e03).

Measured against the criterion: 0 reservoirs with daily history, 0 monsoon seasons, units
unknown.

## C2 Bengaluru ward flood labels: fail

Criterion: at least 100 documented positive ward-days across at least 3 monsoon seasons, plus an
explicit coverage rule for negatives. M01 adds: at least 10 events, independently documented
inundation, and audited negatives.

- **No official source** (OpenCity, KSNDMC, Bengaluru Megha Sandesha) publishes dated ward-level
  flood impacts (S43 e02 to e05, e09 to e11). The BBMP and GBA websites failed TLS verification
  and were not checked (S43 `failed_fetches`).
- The flood-prone location maps have no dates (e03, e04): they can be features, not labels.
- The only dated ward-level record is the **I Change My City complaints log** (Janaagraha, a
  civic NGO, CC BY-SA): 136 ward-days in June to November with a "Flooding/Waterlogging"
  complaint across 2019 to 2022 (2019: 52, 2020: 34, 2021: 35, 2022: 15) (e07, e08).

The complaints reach the count, but fail the rest of the criterion:

| Requirement | Complaints log |
|---|---|
| At least 100 positive ward-days | Yes: 136 |
| At least 3 monsoon seasons | Yes: 2019, 2020, 2021 (2022 ends on 31 Jul) |
| Independently documented inundation | **No**: citizen complaints; no authority confirms them |
| Explicit coverage rule for negatives | **No**: a ward-day without a complaint is not a verified dry day |
| Stable reporting | **No**: complaints fell from 7,383 in 2019 to 1,551 in 2022 |

## Ward boundary version: pass

Criterion: official ward polygons with a release date.

- The GBA 2025 final ward map has 369 wards across 5 corporations, notified on 19 Nov 2025. Its
  source is listed as GBA, with licence "Other (Public Domain)" (S40 e02 to e04).
- It uses WGS84 coordinates inside Bengaluru, and the published key `(corporation_id, ward_id)`
  is unique for all 369 wards (e04).
- Caveat: OpenCity does not say whether the KML is GBA's own file or digitised from the notified
  maps (e03).
- Past monsoons used the 198-ward BBMP map, which has no licence: local research only (e06, e07).
- No Karnataka taluk polygons were found (e11), so taluk-level work uses district or H3 views.

## Decision D17 (approved by the owner, H11)

| Check | Proposed fallback (A4) | Tasks pulled into P1 |
|---|---|---|
| C1 | **M07 Kerala seven-day dam forecast** replaces M02 as core C1 | T113, T114 (KSEB daily water level), T130 to T132 |
| C2 | **M08 Kerala flood classifier with the 2018 held-out replay** replaces M01 as core C2. If its labels also fail, C2 becomes M05 (taluk drought outlook) | T119 (Kerala 2018 flood dataset), T129, T133 to T135 |
| Ward boundary | No change | none |

Also proposed:

1. **Verify the fallback data first.** T113 (KSEB daily water level) and T119 (Kerala 2018 flood
   data) are unverified, so run them straight after approval. Only then start the C1 and C2 model
   tasks, so a failing fallback shows up within two sessions.
2. **Keep M01, M02 and M03 in the plan as blocked**, with the retry conditions in s28.yaml and
   s43.yaml. M01's model card allows a fallback product, a rainfall exposure index that is
   explicitly not a probability, and it can still use the GBA 2025 wards.
3. **Do not use the complaints log as ground truth.** Without a coverage rule for negatives, any
   precision or PR-AUC computed on it would be inflated or meaningless. It can be shown as a
   separate, clearly labelled "citizen complaints" layer, if its CC BY-SA terms are followed.

### Options offered at H11 (the owner chose the second)

- **Approve D17 as proposed** (recommended): Kerala models become C1 and C2. This follows A4
  exactly and keeps the honest-ML rules.
- **Approve D17, but also try to unblock KWRIS**: you register a KWRIS account (personal details)
  or email the ACIWRM helpdesk for daily history. If it arrives with units and a licence, re-run
  T008, and M02 can return as a second reservoir model.
- **Use the complaints log for C2 instead of M08**: needs a written coverage rule for negatives
  and is recorded as non-official labels. Not recommended (see C2 above).

## Decision D29: core C2 is M05 (the owner delegated the H11 choice)

M08's labels fail for forecasting. Kaggle needs a sign-in and states no licence (T119,
[s35.md](../sources/s35.md)). The KSDMA memoranda have dated district flood labels for 2018 only,
and few of them, with no independent positives and negatives before 2018 (T121,
[s36.md](../sources/s36.md)). M08's card then allows only a descriptive replay with no accuracy
claim, so the second fallback in A4 applies.

| Change | Tasks |
|---|---|
| **M05 Karnataka taluk drought outlook** becomes core C2: next-month SPI-3 and drought probability, on district or H3 cells (labelled) because no taluk polygons were found | T057 and T058 (S08 IMD Pune gridded rainfall), then T101 to T103, pulled into P1 |
| M08 stays as a non-core descriptive 2018 replay, with no accuracy claim | T122, T129 and T133 to T135 stay in P3 |

Why M05:

1. It can make a forecasting claim: a locked 2020 to 2024 test, compared with strong simple
   baselines (SPI persistence and month climatology).
2. Its rain record starts in 1901, more than the 30 years the card needs.
3. It is a Karnataka model, so it follows the build order (Karnataka first).

Risk: S08 is unverified. T057 runs first, so a failing fallback shows up in one session.



---

# 6. M05 drought model result (T103)

Source file: `reports/models/m05.md`

# M05 Karnataka drought outlook: locked test result (T103)

**Status: candidate_eligible, approved by the owner on 5 Nov 2026 (D43): ridge is the champion.** All gates pass.

**This is a hindcast** (D39): features assume IMD rain up to the previous month was known at
issue time; IMD publishes the gridded files yearly, so live outlooks are not possible from S08.

Test: 1800 district-months, 60 months (2020-2024), 30 districts
(geoBoundaries 2021 lines; no taluk polygons). Baseline: strongest of SPI-3 persistence and month
climatology on the test rows = **persistence**. Candidate: **ridge**.

| Measure | Achieved | Gate |
|---|---|---|
| MAE candidate / baseline | 0.732 / 0.808 (ratio 0.906) | ratio <= 0.95 and lower 95% bound > 0 |
| Improvement (paired block bootstrap, months) | mean 0.076, 95% [0.003, 0.150] | lower bound > 0 |
| Drought PR-AUC (SPI-3 < -1) | 0.217 | > prevalence 0.057 |
| Brier skill vs baseline | 0.116 | > 0 |
| CRPS candidate / baseline | 0.530 / 0.586 | candidate lower |
| 80% interval coverage (spread from 2019) | 0.652 | reported |

All test MAEs: climatology 1.053, lightgbm 0.722, persistence 0.808, ridge 0.732.

Calibration by season (candidate drought probability):

| Season | Rows | Observed drought share | Mean probability |
|---|---|---|---|
| monsoon (Jun-Sep) | 600 | 0.045 | 0.071 |
| rest of year | 1200 | 0.062 | 0.090 |

Gates: mae pass, pr_auc_above_prevalence pass, brier_skill_above_0 pass, crps_below_baseline pass.

## Limits (claims this result does not support)

- SPI is meteorological drought only: not groundwater, crop yield loss or household water.
- 80% intervals cover 65% of test outcomes: too narrow (spread from one
  calibration year, 2019). Do not publish them as 80% intervals until recalibrated.
- Drought probabilities run slightly high in both seasons (see the calibration table).
- District lines are geoBoundaries 2021 (Ballari includes Vijayanagara).
- One IMD day (12 Oct 2023) has gaps outside Karnataka; none in the state (D40).
- A candidate is served only after the owner approves the release (D38); until then the
  baseline is the champion.

Retraining rule: refit quarterly when a new IMD year file is published; any change of target,
unit or boundary version is a new model version with an untouched test period.

Release: `models/registry/M05/v1.json` (git 7efb139bf5c9, dataset
91bb4930a3ff, split manifest e0109096d125).



---

# 7.1 Source report S01

Source file: `docs/sources/s01.md`

# S01 Open-Meteo weather forecast: discovery (T009)

**Outcome: available.** Hourly forecasts for 16 days, free without a key, under CC BY 4.0.
Checked on 5 Nov 2026 (10 evidence files, fetched 12:54 to 12:55 UTC, 3 seconds apart).
Structured record: [`configs/sources/s01.yaml`](../../configs/sources/s01.yaml). Evidence
manifest: [`tests/fixtures/s01/manifest.json`](../../tests/fixtures/s01/manifest.json).

## Access, licence and limits

- `GET https://api.open-meteo.com/v1/forecast` needs no key, account or card (e08, e10).
- Licence: API data are CC BY 4.0 (e04). The free API is for non-commercial use only (e03).
  Monsoon Atlas is non-commercial. Credit Open-Meteo and the model provider.
- Limits of the free API: fewer than 10,000 calls a day, 5,000 an hour, 600 a minute, and
  300,000 a month (e03). One call can carry several coordinates.
- robots.txt: the website allows everything (e01); the API host disallows everything (e02).
  Decision D31 treats the API host file as crawler guidance and follows the API terms instead.

## Units (requested explicitly)

Every call sets `temperature_unit=celsius`, `wind_speed_unit=ms`, `precipitation_unit=mm` and
`timezone=GMT`. The response echoes the units in `hourly_units` (e08). Without the wind parameter
the unit would be km/h (e05).

## Forecast issue time (source-specific check: pass)

The forecast response has no run time (e08, e10). Each model has a metadata file,
`https://api.open-meteo.com/data/<model>/static/meta.json`, the URL the Model Updates page builds
(e06, e07). For ECMWF IFS 0.25 (e09):

| Field | Value |
|---|---|
| `last_run_initialisation_time` | 2026-11-05 00:00 UTC (the issue time) |
| `last_run_availability_time` | 2026-11-05 09:04:15 UTC |
| `data_end_time` | 2026-11-20 03:00 UTC |
| Time step and update interval | 3 hours; every 6 hours |

So T010 must:

1. Request one named model (for example `models=ecmwf_ifs025`), never the default best-match,
   which names no model and so has no known issue time (e10).
2. Read the model metadata before and after the forecast call, and keep the forecast only if
   the run time did not change. Set `issued_at` to the run time and `available_at` to the later
   of the availability time plus 10 minutes (the page's advice, e06) and the fetch time.
3. Store every run, because the API keeps no forecast vintages (D07).

Values in the sample: precipitation 0.0 to 1.9 mm, humidity 36 to 99% (e08). Hours after the
model's data end are null (23 of 384 hours), not zero.

## Adapter (T010)

`src/atlas/ingest/s01.py` follows the three rules above (D32). `fetch` returns the model
metadata and the forecast; `parse(forecast, config, meta=metadata)` writes the envelope plus
`cell_id`, `model`, `temperature_c`, `rain_mm`, `humidity_pct` and `wind_ms`
(`schemas/s01.json`). The two T009 samples are committed as CC BY 4.0 test fixtures.



---

# 7.2 Source report S02

Source file: `docs/sources/s02.md`

# S02 Open-Meteo historical weather / ERA5: discovery (T011)

**Outcome: available.** Daily ERA5 reanalysis from 1940, free without a key, under CC BY 4.0.
Checked on 5 Nov 2026 (7 evidence files, fetched 13:00 to 13:01 UTC, 3 seconds apart).
Structured record: [`configs/sources/s02.yaml`](../../configs/sources/s02.yaml). Evidence
manifest: [`tests/fixtures/s02/manifest.json`](../../tests/fixtures/s02/manifest.json).

## Access, licence and limits

- `GET https://archive-api.open-meteo.com/v1/archive` needs no key, account or card.
- Same licence and limits as S01: CC BY 4.0, free API for non-commercial use, fewer than 10,000
  calls a day (e02, e03). The API host robots.txt disallows crawlers (e01); D31 applies.

## What to request

`models=era5` (0.25 degree, the docs' advice for consistent decades, e04),
`daily=precipitation_sum,temperature_2m_max,temperature_2m_min`, `temperature_unit=celsius`,
`precipitation_unit=mm` and `timezone=Asia/Kolkata`, so a day is an IST day (e05).

## History and release lag (source-specific check: pass)

| Item | Value | Evidence |
|---|---|---|
| Coverage in the docs | ERA5 "1940 to present", "Daily with 5 days delay" | e04 |
| First local day | 1 Jan 1940 has no precipitation (an IST day starts at 18:30 UTC the day before); 2 Jan 1940 is the first full day | e06 |
| Latest day on 5 Nov 2026, 13:01 UTC | 30 Oct 2026 (6 days behind); 31 Oct to 4 Nov are null | e05 |
| July 2024, Bengaluru cell | 264.2 mm in total | e07 |

Rules for T012 and every model that uses S02:

1. ERA5 is a **reanalysis**, which is model output, not an observation: rows get provenance
   `model`.
2. A value for day D did not exist before about D + 6 days. `available_at` is the real fetch
   time; a backtest that uses older rows must apply the lag and be labelled a hindcast (D07).
3. Reanalysis rain can differ a lot from rain gauges at one cell; compare with S08 (IMD gauges)
   before trusting local totals.

## Adapter (T012)

`src/atlas/ingest/s02.py` requests `models=era5` with explicit units and IST days and writes the
envelope plus `cell_id`, `date_local`, `product`, `rain_mm`, `tmax_c` and `tmin_c`
(`schemas/s02.json`). `valid_at` is the end of the IST day; `available_at` is the fetch time;
provenance is `model`. A day with a missing value becomes an all-null row: `not_yet_available`
after the newest complete day (the release lag), otherwise `out_of_coverage`. Two T011 samples
are committed as CC BY 4.0 test fixtures.



---

# 7.3 Source report S08

Source file: `docs/sources/s08.md`

# S08 IMD Pune gridded rainfall: discovery (T057)

**Outcome: available.** Daily 0.25 degree rainfall grids for India from 1901 to 2025 download
without an account. Checked on 5 Nov 2026 (6 evidence files, fetched 12:24 to 12:25 UTC, 3
seconds apart). T057 runs in P1 by decision D29, because S08 is the data for M05, now core C2.
Structured record: [`configs/sources/s08.yaml`](../../configs/sources/s08.yaml). Evidence
manifest: [`tests/fixtures/s08/manifest.json`](../../tests/fixtures/s08/manifest.json).

## Access

- The gridded rainfall page (e03) has a year form that sends the year to `rainfall.php`. The
  same URL answers a plain GET, `rainfall.php?rain=YYYY`, and returns `indYYYY_rfp25.grd`. No
  account, key or card is needed (e04 to e06).
- The page is not linked from the IMD Pune home page (e01). It is the route the plan names
  (imdlib download inventory), on the IMD Pune host.
- robots.txt returns 404 on both hosts, and no quota is published. Downloads are spaced 3 seconds
  apart. One year file is about 25 MB, so the full 1901 to 2025 history is about 3.2 GB.

## Licence: restricted

The site disclaimer says the data "should not be reproduced anywhere without prior permission"
(e02). The gridded page asks for a citation of Pai et al. (2014), MAUSAM 65(1), pp 1 to 18 (e03).
So:

- The year files stay in `data/raw` and are never redistributed.
- Public outputs are derived indices and model results only (SPI, drought probability,
  metrics), with the citation. Raw or area-averaged rainfall values are not published without
  permission. The owner checks this at the H11 review before any public deployment.

## Format (source-specific check: pass)

| Item | Value | Evidence |
|---|---|---|
| File | Raw little-endian float32, no header, one record per day | e03, e04 |
| Grid | 135 x 129 cells; first value 6.5N 66.5E, longitude fastest, south to north | e03 |
| Size | 69,660 bytes x days: 365 days for 1901 and 2025, 366 for 2024 | e04 to e06 |
| Unit | mm; -999.0 outside the land mask | e03 |
| Land mask | The same 4,964 cells in 1901, 2024 and 2025, on every day | e04 to e06 |
| Values | 2024 totals of the nearest cells: about 990 mm at Bengaluru, 6,457 mm near Agumbe, 707 mm at Kalaburagi | e04 |

Days with zero rain at every land cell occur only in December to February. The file has no
separate missing-data flag, so a missing day cannot be told from a dry day. T058 records this
limit.

## History and release lag

- The page text says 1901 to 2024, but the form also offers 2025, and the 2025 file is a full
  year. The page does not say whether 2025 is final, so T058 records it as possibly
  provisional.
- Files are yearly. On 5 Nov 2026 no 2026 file is offered, so the newest data is about 10 to
  22 months older than an issue date in 2026.

## Effect on M05

- **Training and the locked test are covered.** M05 needs the SPI reference 1981 to 2010,
  training 1981 to 2016, tuning 2017 to 2018, calibration 2019 and a locked test 2020 to 2024.
  All of these years are published.
- **Live monthly outlooks are not covered.** The card allows only released rainfall at issue
  time. With yearly files, a live outlook would be a year or more late. T101 must either use a
  near-real-time rainfall source for the latest months, as a separately validated input, or
  publish M05 as a retrospective evaluation only.
- No Karnataka taluk polygons exist (T030), so M05 runs on districts or H3 cells, labelled as
  such.

## Adapter (T058)

`src/atlas/ingest/s08.py` reads a year file into the common envelope plus `cell_id`,
`date_local`, `rain_mm` and `grid_resolution_deg` (`schemas/s08.json`). Neither the page nor
Pai et al. (2014) (e07) states the 24-hour window, so `valid_at` is 08:30 IST on the next day,
the latest possible end (D30). Only land cells in the state cell box become rows: 540 for
Karnataka, so a leap year gives 197,640 rows. Parsing one year takes about 5 seconds.



---

# 7.4 Source report S09

Source file: `docs/sources/s09.md`

# S09 NDMA Sachet CAP alerts: discovery (T013)

**Outcome: available.** Official warnings as CAP 1.2 alerts, public domain, no account. Checked
on 5 Nov 2026 (9 evidence files, fetched 13:05 to 13:06 UTC, 3 seconds apart). Structured record:
[`configs/sources/s09.yaml`](../../configs/sources/s09.yaml). Evidence manifest:
[`tests/fixtures/s09/manifest.json`](../../tests/fixtures/s09/manifest.json).

## Access and licence

- The all-India RSS feed (e02) lists the latest 100 alerts. Each item links its CAP file:
  `FetchXMLFile?identifier=<id>`. Each CAP file names a polygon file in its "Polygon URL"
  parameter: `FetchPolygonXMLFile?identifier=<id>` (e03, e04).
- The feed states `<copyright>public domain</copyright>` (e02).
- No quota is published; robots.txt returns 404.

## History: partial

The feed keeps only the latest 100 alerts, about 21 hours on 5 Nov 2026 (4 Nov 15:55 to 5 Nov
12:35 GMT). No archive is linked, so the project keeps its own history by polling every
15 minutes. The channel `pubDate` is stale (16 Oct 2026); use item dates.

## What the alerts look like

| Evidence | Sender | Type | Event | Area |
|---|---|---|---|---|
| e03 | Karnataka-SNDMC (relaying IMD Bengaluru) | Update | Thunderstorm with Lightning | 5 districts, with LGD district codes |
| e05 | Karnataka-SNDMC | Update | Thunderstorm with Lightning | 4 districts, with LGD codes |
| e06 | Andhra Pradesh SDMA | Alert | Lightning | one mandal, text only |
| e07 | IMD Chennai | Alert | Moderate Rain | 5 districts of Tamil Nadu, with LGD codes |
| e08 | Kerala SDMA (relaying IMD Thiruvananthapuram) | Update | Heavy Rain | "central Kerala", text only |
| e09 | Himachal Pradesh SDMA (relaying FSI) | Update | Pre Fire Alert | Himachal Pradesh, text only |

Alerts have an English info block and often a second one in the state language.

## Source-specific check: pass

1. **Supersession.** An Update names the alert it replaces in `references` as
   `sender,identifier,sent`. T014 marks the referenced alert as superseded; a Cancel (defined in
   CAP 1.2, not seen in the samples) is handled the same way.
2. **Geometry.** The polygon file holds `lat,lon` rings (e04 has 14 rings, each listed twice).
   When there is no polygon, geometry is null and `area_text` is the only location; area text is
   always kept.
3. **No inferred events.** The event is stored as written; rain alerts are never turned into
   lightning alerts or the other way round.

## Adapter (T014)

`src/atlas/ingest/s09.py`: `fetch(ctx, known)` reads the feed and then the CAP and polygon
files of new alerts only; `parse(cap, config, polygon=...)` gives one row per alert in the
state (English info block) with `sender` and `msg_type` added (D33); `supersede(table)` drops
replaced alerts and cancels. Geometry is WKB MultiPolygon in lon, lat order. The CAP, polygon
and feed samples are committed as public-domain test fixtures.



---

# 7.5 Source report S15

Source file: `docs/sources/s15.md`

# S15 OpenFreeMap basemap: discovery (T015)

**Outcome: available.** Free vector basemap with no keys, no registration and no limit on map
views. Checked on 5 Nov 2026 (7 evidence files, fetched 13:12 UTC, 3 seconds apart). Structured
record: [`configs/sources/s15.yaml`](../../configs/sources/s15.yaml). Evidence manifest:
[`tests/fixtures/s15/manifest.json`](../../tests/fixtures/s15/manifest.json).

## How it is used

- The map (T039) loads a style such as `https://tiles.openfreemap.org/styles/liberty` in the
  viewer's browser (MapLibre). The style's vector source is the planet TileJSON, which points at a
  dated revision, `20261101_080013_pt` on 5 Nov 2026 (OpenMapTiles schema 3.16.0) (e05, e06).
- A zoom 6 tile over Karnataka downloaded fine (157 KB, e07).

## Attribution (must stay on every map)

From the TileJSON (e06): OpenFreeMap, © OpenMapTiles, Data from OpenStreetMap. OpenStreetMap data
is ODbL. T016 stores this string with each style revision.

## Terms to respect

- No automated collection beyond small offline downloads: at most 3,000 tiles or 50 MB, at most
  4 parallel requests, a unique User-Agent (e03). The project never bulk-downloads tiles.
- Whoever integrates the public service into a site must be at least 18 (e03). **Owner check
  (H11, before public deployment):** confirm this, or self-host the free planet download instead.
- The tile host's robots.txt returns 403; the website's allows everything (e01).

## Adapter (T016)

`src/atlas/ingest/s15.py`: `fetch` reads the style and the TileJSON its vector source names (no
tiles); `parse(style, config, tilejson=...)` gives one row with `style_url`, `revision` and
`attribution` (`schemas/s15.json`), and fails if the attribution loses OpenStreetMap or
OpenMapTiles. Tests use the local T015 files and skip in CI.



---

# 7.6 Source report S16

Source file: `docs/sources/s16.md`

# S16 WorldPop India population: discovery (T017)

**Outcome: available.** Gridded population counts for India, 1 km, 2015 to 2030, CC BY 4.0.
Checked on 5 Nov 2026 (5 evidence files, fetched 13:26 to 13:27 UTC, 3 seconds apart).
Structured record: [`configs/sources/s16.yaml`](../../configs/sources/s16.yaml). Evidence
manifest: [`tests/fixtures/s16/manifest.json`](../../tests/fixtures/s16/manifest.json).

## Product chosen

R2025A "Individual countries 2015-2030 (1 km resolution)", constrained and UN-adjusted
(`G2_CN_POP_R25A_1km`), India: one GeoTIFF per year on data.worldpop.org (e02, e03). The 2025
file is 16 MB (e05). Other products in the catalogue (100 m, 2000 to 2020) are larger.

| Item | Value | Evidence |
|---|---|---|
| Unit | number of people per pixel (counts, not density) | e03 |
| Grid | 3,504 x 3,451 float32, 0.0083333 degree pixels, top-left 68.19E 35.51N, nodata -99999 | e05 |
| Format | BigTIFF, 512-pixel LZW tiles | e05 |
| Licence | CC BY 4.0; cite DOI 10.5258/SOTON/WP00840 | e03, e04 |

## Warnings

1. R2025A is an **alpha** release that "may change over the coming year" (e03): store the release
   in `raster_id` and re-check yearly.
2. Years after 2025 are **projections**, not estimates.
3. Values are counts, so district totals are **sums** of pixels. T018 must check that the
   clipped sum equals the sum of the kept cells; that needs rasterio (geo lock), because the
   tiles are LZW compressed.

## Adapter (T018)

`src/atlas/ingest/s16.py`: `fetch` follows the catalogue link to the year's GeoTIFF;
`parse(tif, config, boundary=S17 ADM1)` keeps native cells whose centre is in the state polygon
(no resampling, so the total is exactly the sum of kept cells). Karnataka 2025: 203,344 cells and
about 70.8 million people. Needs rasterio from the geo lock (D35); tests skip without it.

**Finding (T032):** WorldPop R2025A puts about 6.0 million people inside the 369 GBA wards in
2025, well below other estimates for Bengaluru, so dense city areas look undercounted. Use it
for weights and relative exposure, not as a city population figure, and say so on any map.



---

# 7.7 Source report S17

Source file: `docs/sources/s17.md`

# S17 geoBoundaries administrative boundaries: discovery (T019)

**Outcome: available.** India district (ADM2) and state (ADM1) polygons, free, open licences.
Checked on 5 Nov 2026 (6 evidence files, fetched 13:17 to 13:19 UTC; 10 seconds apart on
geoboundaries.org, as its robots.txt asks). Structured record:
[`configs/sources/s17.yaml`](../../configs/sources/s17.yaml). Evidence manifest:
[`tests/fixtures/s17/manifest.json`](../../tests/fixtures/s17/manifest.json).

## What is published

| Level | Units | Year represented | Licence | Primary source | Evidence |
|---|---|---|---|---|---|
| ADM2 (districts) | 735 in the file (metadata says 736) | 2021 | ODbL 1.0 | Pathways Data Pvt. Ltd., lgdirectory.gov.in | e03, e06 |
| ADM1 (states) | 36 | 2011 | CC BY 2.5 IN | DataMeet, Election Commission of India | e04, e05 |

Files are fixed to GitHub release commit `9469f09`; the full ADM2 GeoJSON is 48 MB.

## Source-specific check: pass, with three warnings

1. **Counts come from the file**, not the metadata (735, not 736).
2. **Karnataka has 30 districts here.** Vijayanagara (split from Ballari in 2021) is missing, so
   these are older lines; Ballari includes Vijayanagara. Names use old spellings (Bangalore,
   Belgaum, Gulbarga). M05 must label its district view with this boundary version.
3. **No disputed-boundary metadata** exists in the files. ADM1 is a 2011 vintage (Jammu and
   Kashmir as one unit). Any public India map must follow India's official mapping guidance:
   **owner check at H11 before public deployment.**

ADM2 says nothing about wards or taluks. Every ring is closed and every shape ID is unique; full
polygon validity (self-intersection) is checked with shapely in T032 (geo lock).

## Adapter (T020)

`src/atlas/ingest/s17.py`: `fetch` follows the API metadata links to the ADM2 GeoJSON and the
simplified ADM1 GeoJSON; `parse(adm2, config, adm1=...)` keeps the districts whose interior point
lies in the state polygon (30 for Karnataka), with `place_id` `gb-IND-ADM2-<shapeID>`,
`boundary_version` `geoboundaries-IND-ADM2-9469f09`, the state as `parent_id` and WKB geometry
(holes kept). Tests use the local T019 files and skip in CI.



---

# 7.8 Source report S18

Source file: `docs/sources/s18.md`

# S18 Geofabrik OSM extracts: discovery (T021)

**Outcome: blocked** for automated download. Checked on 5 Nov 2026 (4 evidence pages, fetched
13:30 UTC, 3 seconds apart). Structured record:
[`configs/sources/s18.yaml`](../../configs/sources/s18.yaml). Evidence manifest:
[`tests/fixtures/s18/manifest.json`](../../tests/fixtures/s18/manifest.json).

## Why blocked

- `robots.txt` disallows `*.osm.pbf`, `*.shp.zip`, state files and updates for every user agent
  (e01), and no Geofabrik page invites scripted downloads (e02 to e04). Decision D34: the
  pipeline honours this. (D31 covered API hosts whose terms invite programmatic use; Geofabrik's
  download site is not one.)
- Karnataka is inside the Southern Zone extract, which is 533 MB (e03), far above the 50 MB
  evidence budget.

What is known from the pages: data is ODbL 1.0 (e02, e03); extracts are rebuilt daily around
21:00 CET (e04); the Southern Zone page offers the latest file (data to 2026-11-03T21:24:23Z) and
snapshots from 1 Jan 2022 (e03).

## Retry (any one)

1. **Owner step:** download `southern-zone-latest.osm.pbf` in a browser from
   https://download.geofabrik.de/asia/india/southern-zone.html and save it in `data/raw/S18/`.
   A manual download is not a robot. Then re-run T021 on the local file and build T022.
2. Geofabrik states that scripted downloads are allowed.
3. A new source task checks the OpenStreetMap Overpass API (an API with published usage limits)
   for the few Karnataka feature types the map needs.

Until then T022 is a disabled adapter that raises `SourceUnavailable`. Shelter opening status
must never be inferred from OSM, whichever route is used.



---

# 7.9 Source report S22

Source file: `docs/sources/s22.md`

# S22 India Data Portal Agmarknet: discovery (T023)

**Outcome: blocked (not resolved).** Checked on 5 Nov 2026 (4 evidence pages, fetched 16:00 UTC).
Structured record: [`configs/sources/s22.yaml`](../../configs/sources/s22.yaml). Evidence
manifest: [`tests/fixtures/s22/manifest.json`](../../tests/fixtures/s22/manifest.json).

- The Agmarknet page and the documentation site are client-side apps: the served HTML has no
  table, file link, API address or licence (e02, e04). robots.txt returns 403.
- The footer says "All rights reserved" and no dataset licence is visible (e01, e03).
- A browser render was attempted, but the built-in browser was unavailable. No endpoint was
  guessed (plan D14).

**Retry:** render the page in a browser (agent or owner) and record the download link, format
and licence; a sign-in, if needed, is an owner step. **Other route:** T025, data.gov.in mandi
prices (the same Agmarknet data through a free API key, an owner step to obtain the key).



---

# 7.10 Source report S23

Source file: `docs/sources/s23.md`

# S23 data.gov.in mandi prices: discovery (T025)

**Outcome: blocked only on the licence.** Access, schema, pagination and data checks pass. Checked
on 5 Nov 2026 with the owner's free API key (sent only in requests, never stored). Structured
record: [`configs/sources/s23.yaml`](../../configs/sources/s23.yaml). Evidence manifest:
[`tests/fixtures/s23/manifest.json`](../../tests/fixtures/s23/manifest.json).

| Item | Finding | Evidence |
|---|---|---|
| Resource | `9ef84268-d588-465a-a308-a864a43d0070`, read by the owner from the dataset's API tab and echoed by the API (`index_name`) | e01 |
| Publisher | Ministry of Agriculture and Farmers Welfare | e01 |
| Snapshot | Current day only: 17,718 records, all dated 05/11/2026; Karnataka 565 | e01 to e03 |
| Fields | state, district, market, commodity, variety, grade, arrival_date (DD/MM/YYYY), min/max/modal price | e01 |
| Checks | 2 pages of 100 Karnataka rows, all distinct; 0 < min <= modal <= max in all 200 | e02, e03 |
| Units | Not stated in the response (Agmarknet's usual Rs per quintal is unconfirmed) | e01 |
| Licence | Not in the response; the website refuses automated clients (Akamai 403) | e01 |

The API sometimes returns 502 for keyed requests (twice at 16:30 UTC, fine at 17:00 UTC); T026
must retry. History exists only by saving each day's snapshot.

**Retry (owner, 1 minute):** open the dataset's **Catalog Info**, note the licence name and link
(and the price unit if shown), and tell the agent. If it is an open licence such as GODL-India,
re-run T025 to make S23 available.



---

# 7.11 Source report S28

Source file: `docs/sources/s28.md`

# S28 KWRIS reservoirs and rainfall: discovery (T008)

**Outcome: blocked.** Checked on 5 Nov 2026 (evidence fetched at 09:29 UTC). The structured
record is [`configs/sources/s28.yaml`](../../configs/sources/s28.yaml). The evidence manifest is
[`tests/fixtures/s28/manifest.json`](../../tests/fixtures/s28/manifest.json): URL, fetch time,
HTTP status and SHA256 for each page. The pages themselves stay in `data/raw/S28` because the
site reserves all rights.

## What is public

| Item | Finding | Evidence |
|---|---|---|
| Publisher | KWRIS, Water Resources Department, Government of Karnataka (ACIWRM and KSWIC) | e01 |
| Reservoir data without an account | Map layer `reservoir_landing` (GeoServer WFS, published in the home page script): one latest row for each of 36 reservoirs | e01, e07 |
| History | None. The layer keeps one row per reservoir; K.R.Sagara has a single row (05 Nov 2026) | e08 |
| Freshness | 22 rows dated 05 Nov 2026, 4 dated 04 Nov 2026, 9 dated 31 Jan 2026, 1 dated 23 Oct 2021 | e07 |
| Units and datum | Not stated anywhere. Levels range from 29.49 to 2897.2. The field name `TMC_GrossCapacity` suggests TMC, but no unit is given | e01, e06, e07 |
| Web API | `POST /api/data/GetToken` with user ID and password; account needs name, email, mobile number, organisation and reason for joining | e02, e03 |
| Licence | Footer: "All Rights Reserved". No open licence or terms of use. GeoServer "Fees NONE / AccessConstraints NONE" are software defaults | e01, e04, e05 |
| Quota | Not published | e02, e05 |
| Cost | No payment asked anywhere (no card) | e01, e02, e03 |
| Rainfall | Rainfall Analytics page with year selectors from 1971 to 2026; data loads through undocumented page methods; no documented export | e09 |

## Field map (upstream to canonical)

| Canonical | Upstream | Unit status |
|---|---|---|
| reservoir_id | ReservoirID | not applicable |
| date_local | Date (string, for example `05 Nov 2026`) | not applicable |
| level_m | Reservior_Level | unlabelled, not converted |
| storage_mcm | TMC_GrossCapacity | unlabelled, not converted |
| inflow_m3s | Flow_Inflow | unlabelled, not converted |
| outflow_m3s | Flow_OutFlow | unlabelled, not converted |
| capacity_mcm | StorageCapacity_AsPerDesign | unlabelled, not converted |

`Flow_Inflow` is null in 4 rows and 0 in 18 rows. A reported 0 cannot be told apart from a missing
reading, so nulls stay null and no zero is filled in. Inflow is never derived from level.

## Source-specific check

The plan's first feasibility check for S28 (historical span and units) **fails**. So does
GATE-CORE check C1 (at least 5 reservoirs with daily level or storage for at least 3 monsoon
seasons, with known units and datum). The C1 fallback (M07 Kerala seven-day dam forecast) is
decided in T222 and approved by the owner (H11).

## Effect on other tasks

S28 stays `enabled: false` in `configs/states/ka.yaml`. These tasks need S28 history and stay
blocked: T027 (S28 adapter), T092 (M02 labels), T095 (M03 labels) and T167 (GRU reservoir
challenger).

## Retry condition

Re-run T008 when one of these holds:

1. The owner chooses to register a KWRIS account. This is a new human-only step, because the form
   asks for personal details. The Web API terms must then allow research use, and the API must
   return daily reservoir history with units.
2. ACIWRM answers a data request, sent to the helpdesk address published on the site, with daily
   history, units and a licence.
3. The public site starts publishing a reservoir history or export.

## Not done

- No login, no account and no API call (human-only rule, amendments A5).
- The undocumented page methods behind Rainfall Analytics were not called. They are not a
  published interface, and rainfall comes from other sources (S27, S29, IMD, ERA5).



---

# 7.12 Source report S32

Source file: `docs/sources/s32.md`

# S32 KSEB daily water level: discovery (T113)

**Outcome: available, with partial history.** Checked on 5 Nov 2026 (80 evidence pages, fetched
10:35 to 10:40 UTC, 3 seconds apart). T113 was pulled into P1 by decision D17 (core C1 is now
M07 Kerala seven-day dam forecast). Structured record:
[`configs/sources/s32.yaml`](../../configs/sources/s32.yaml). Evidence manifest:
[`tests/fixtures/s32/manifest.json`](../../tests/fixtures/s32/manifest.json). Pages stay in
`data/raw/S32`.

## What KSEB publishes

| Item | Finding | Evidence |
|---|---|---|
| Page | "Daily report: water levels of main reservoirs", 7.00 AM reading | e02 |
| Dams | 16: Idukki, Idamalayar, Kakki (Anathode), Banasurasagar, Sholayar, Madupetty, Anayirankal, Ponmudi, Kuttiyadi (Kakkayam), Pamba, Poringalkuthu, Kundala, Kallarkutty, Lower Periyar, Moozhiyar, Sengulam | e02 |
| Columns | level (metre), live storage (MCM), % storage, same day previous year level and storage, inflow (MU), rainfall (mm), blue/orange/red alert levels, MWL, FRL, spillway crest, live storage at FRL | e02 |
| Past dates | The page's own GET form: `?date=YYYY-MM-DD` | e02, e03 |
| Licence | Terms of Service: CC BY-SA 2.5 India or later | e06 |
| Access | Public; robots.txt disallows nothing; no account, key or card | e01 |

## History

- **Earliest report with dam rows: 26 Oct 2023** (e03). 25 Oct 2023 and 15 Aug 2018 return the
  page header with no rows (e04, e05).
- **Twice-monthly sample** (1st and 15th, Nov 2023 to Nov 2026, 73 dates): rows from
  15 Nov 2023 to 1 Aug 2024, none from 15 Aug 2024 to 15 Jul 2026, rows again from 1 Aug 2026.
  1 Nov 2023 is also empty. Every date with data has all 16 dams.
- The "same day previous year" columns reach one year further back, to Nov 2022 to Aug 2023 and
  Aug to Nov 2025.
- The Historic data page has yearly system statistics only (e07).

So the monsoons with daily data are June to July 2024 and August to September 2026 directly, plus
June to July 2023 and August to September 2025 from the previous-year columns. **There is no
2017 to 2022 daily history**, which M07's model card uses for training.

## Units and data quality

- Units are in the column headers. Some cells override them with an "ft" suffix: Idukki and
  Sholayar alert levels, MWL, FRL and spillway crest are in feet.
- **Inflow is in MU** (million units of energy, GWh), not m3/s, so `inflow_m3s` stays null.
- **No datum** is stated; levels are compared within each dam only.
- **Early reports break the header units:** on 26 Oct 2023 the Idukki and Sholayar levels are in
  feet (2353.98, 2659.6). On 26 Oct and 15 Nov 2023 the % storage is 100 times too large (4921
  for 49.21). From 1 Dec 2023 the sample is consistent. T114 must check every row (level within
  the dam's range in metres; % storage equal to storage divided by storage at FRL) and quarantine
  failures, never rescale them silently.
- The report date comes from the page ("As on 05-Nov-2026 7.00 AM"), never from the fetch time.
  It matched the requested date on all 76 dated pages.

## Field map (upstream to canonical)

| Canonical | Upstream | Unit |
|---|---|---|
| reservoir_id | Name of Dam / Reservoir | none |
| date_local | "As on DD-Mon-YYYY" | Asia/Kolkata, 7.00 AM |
| level_m | Today's Water level (metre) | metre, no datum |
| storage_mcm | Today's Live Storage (MCM) | MCM (live storage) |
| capacity_mcm | Live Storage at FRL (MCM) | MCM |
| inflow_m3s | Inflow MU | energy, not converted: null |

## Effect on M07 (core C1)

The source is usable, but M07's planned splits (train 2017 to 2022, test 2024) cannot come from
S32. T130 must either set new dated splits for Oct 2023 onwards with a gap-aware evaluation, or
find 2017 to 2023 daily history in another source. Next checks: S34 KSDMA dam level reports
(T118) and S33 KSEB monthly statistics (T116). T114 should also confirm the Aug 2024 to Jul 2026
gap day by day.



---

# 7.13 Source report S34

Source file: `docs/sources/s34.md`

# S34 KSDMA dam level reports: discovery (T117)

**Outcome: available, with OCR and manual review.** Daily dam reports from 20 Jun 2020 to
4 Nov 2026 are public, but the archived tables are scanned images. Checked on 5 Nov 2026 (12
evidence files, fetched 10:47 to 10:48 UTC, 3 seconds apart). T117 was pulled into P1 by
decision D28. Structured record: [`configs/sources/s34.yaml`](../../configs/sources/s34.yaml).
Evidence manifest: [`tests/fixtures/s34/manifest.json`](../../tests/fixtures/s34/manifest.json).
Files stay in `data/raw/S34`.

## What KSDMA publishes

| Item | Finding | Evidence |
|---|---|---|
| Today | KSEB and irrigation dam PDFs (05/11/2026, 11.00 AM), with a text layer | e02, e06, e07 |
| Archive | `/archives/`: 2,322 PDF links; 2,296 unique valid dates, 20 Jun 2020 to 4 Nov 2026 | e03, e04 |
| Per year | 2020: 193, 2021: 357, 2022: 357, 2023: 362, 2024: 359, 2025: 363, 2026: 305 | e04 |
| Content | Daily bundle: rainfall, KSEB reservoirs, irrigation reservoirs, sea state; flood report from 2023 | e08 to e12 |
| Format | Archive PDFs are scanned images, one JPEG per page (6 to 9 pages) | e08, e10, e12 |
| Licence | Footer: "All rights reserved"; no open licence | e02 |
| Access | Public; robots.txt disallows only /wp-admin/; no account, key or card | e01 |

## Sample check (columns and dates)

| Report | Table | Dams | Columns |
|---|---|---|---|
| 20/06/2020, 11 am | KSEB | 18 | water level (m; Idukki and Sholayar in ft), colour code, spill (cumecs) |
| 01/08/2023, 11.00 AM | KSEB | 17 | water level (ft or metre per cell), live storage (MCM), % storage, spillway release (m3/sec) |
| 01/08/2023, 11.00 AM | Irrigation, with alert | 12 | water level (metre), storage (MCM), % of gross storage, outflow (m3/sec) |

The date and time in each table title match the archive label. The column sets change between
years, so the adapter needs one parser per layout.

## Data quality

- **Archive labels are unreliable:** 14 labels are malformed or impossible (31/11/2020,
  31/09/2024, 12/06/02023, /07/2026), one is in the year 2121, and some dates have two PDFs.
  The report date is always read from the table title.
- **Feet and metres are mixed** per cell (Idukki, Sholayar); the unit is read from each cell.
- **"Kuttiyadi"** is both a KSEB dam and a different irrigation dam, so IDs include the operator.
- **No datum** is stated.

## Field map (upstream to canonical)

| Canonical | Upstream |
|---|---|
| reservoir_id | operator (KSEB or IRRIGATION) + reservoir name |
| date_local | table title "DD/MM/YYYY - 11.00 AM" (Asia/Kolkata) |
| level_m | Today's Water Level; ft cells converted (1 ft = 0.3048 m) and flagged |
| warning_level_m | Blue, Orange and Red alert levels (today's PDFs); null with a reason in older tables |
| warning_stage | colour code column, or row shading in irrigation tables |

## Effect on M07 (core C1)

S34 is the only source found with daily Kerala dam levels before Oct 2023: 2020 to 2026, about 6
monsoons, for 17 to 18 KSEB dams plus irrigation dams. M07's card trains from 2017, but S34
starts in June 2020, so T130 shifts the training start to 20 Jun 2020. Before any value is used:

1. T118 adds an OCR step. OCR is a new dependency (for example Tesseract, which is free); its
   exact version is pinned and recorded in the decisions log when T118 starts.
2. The owner reviews a sample of the OCR output (plan rule for S34).
3. Values are cross-checked against S32 KSEB levels where the dates overlap (Oct 2023 onwards).



---

# 7.14 Source report S35

Source file: `docs/sources/s35.md`

# S35 Kerala 2018 flood dataset: discovery (T119)

**Outcome: blocked.** No Kaggle dataset gives dated, location-level Kerala flood labels that can be
downloaded without sign-in and has a stated licence. Checked on 5 Nov 2026 (evidence fetched
10:52 to 10:53 UTC). T119 was pulled into P1 by decision D17 (core C2 is now M08). Structured
record: [`configs/sources/s35.yaml`](../../configs/sources/s35.yaml). Evidence manifest:
[`tests/fixtures/s35/manifest.json`](../../tests/fixtures/s35/manifest.json).

## Kaggle datasets found

| Dataset | What the page says | Licence | Evidence |
|---|---|---|---|
| Kerala Floods 2018 (imdevskp) | 2018 casualties, warnings, district-wise warnings, rainfall; from the State Relief Commissioner's memorandum | "Other (specified in description)", but none stated | e01 |
| India Floods Inventory (aditya2803) | 900+ Indian floods, "got this dataset from my Friend" | same, none stated | e02 |
| Monthly Rainfall Index and Flood Probability | Kerala monthly rainfall 1900 to 2018 with a flood flag | Unknown | e03 |
| Kerala_Floods_Dataset | monthly and annual rainfall | Unknown | e04 |
| Kerala_Dataset | rainfall table | Unknown | e05 |

All five require a Kaggle sign-in to download. An anonymous download redirects to the login page,
and Kaggle serves no robots.txt (both recorded as failed fetches). Signing in is an owner step
(H10), so no file or column was seen.

## Why none qualifies

- The plan rejects aggregate rain tables as labels: e03, e04 and e05 are rain tables with a
  monthly or yearly flood flag.
- e02 has no stated origin.
- e01 is the only one with an official source, but it holds district totals for one event, and
  its upstream is the memorandum itself.
- None gives flood labels before 2018. M08's card needs independent positive and negative labels
  before 2018 for any forecasting claim; with 2018 only, M08 is a descriptive replay with no
  predictive accuracy claim.

## Where the labels can come from

The memorandum that e01 cites is public on the KSDMA site (e06): "Additional memorandum, Kerala
Floods 2018", State Relief Commissioner, dated 13-09-2018. It is a 40-page text PDF covering 1 to
30 August 2018, with district tables and a section on flooding from 8 to 22 August. It belongs to
S36 (KSDMA post-disaster assessment), so **T121 runs next**. The plan's S36 rule applies: district
totals only at district resolution, with no invented ward or taluk truth.

## Effect on other tasks

S35 stays disabled. T120 (S35 adapter) and T133 to T135 (M08) depend on T121. If T121 also finds
no dated district labels, decision D17's last fallback applies: C2 becomes M05 (taluk drought
outlook, labels from rainfall indices).



---

# 7.15 Source report S36

Source file: `docs/sources/s36.md`

# S36 KSDMA post-disaster assessment: discovery (T121)

**Outcome: available, as a source of district-level document claims.** It does **not** give the
dated district-day flood labels that M08 needs for a forecasting claim. Checked on 5 Nov 2026
(11 evidence files, fetched 12:06 to 12:07 UTC, 3 seconds apart). T121 runs in P1 by decision
D28. Structured record: [`configs/sources/s36.yaml`](../../configs/sources/s36.yaml). Evidence
manifest: [`tests/fixtures/s36/manifest.json`](../../tests/fixtures/s36/manifest.json).

## Access and licence

- All files are public on sdma.kerala.gov.in and need no account, key or card. robots.txt
  disallows only `/wp-admin/` (e01). The sitemap (e02) lists the three pages used: Disaster
  Memoranda (e03), Floods 2018 (e04) and Event Specific Maps (e05).
- Memorandum 2 (e07) returned 304 Not Modified, so its evidence is the file stored for S35 (same
  URL and SHA256). The discovery contract now accepts 304 as a revalidated stored copy (D27).
- Licence: **restricted**. Every page footer says "All rights reserved", and no open licence is
  linked. The PDFs stay in `data/raw`. Only district facts with a document and page citation are
  published, credited to KSDMA and the State Relief Commissioner.

## What the documents hold

| Evidence | Document | Period | Dated district data |
|---|---|---|---|
| e06 | Memorandum 1, Kerala Floods 2018 (submitted 7-08-2018), 46 pages | 29 May to 31 Jul 2018 | NRSC flooded area in 7 districts "as on 16-7-2018", 55,007 ha (page 9). Fatalities by district, 138 in total (page 14) |
| e07 | Additional Memorandum, Kerala Floods 2018 (13-09-2018), 40 pages | 1 to 30 Aug 2018 | Fatalities in 14 districts, 339 in total (page 20). Narrative dates only, for example flooding in Wayanad, Kannur and Malappuram on 8 and 9 August (page 12). Counts of flood-notified wards per district, no ward list (page 24) |
| e08 | PDNA, Floods and Landslides August 2018 (October 2018), 440 pages | Aug 2018 | Cites a Government Order dated 03/10/2018 that lists notified villages; the order is not linked from these pages (page 319). Gives both 1,259 and 1,260 affected villages (pages 13, 319) |
| e09 | Map "Kerala Flood Inundation (2018)" | 2018 | One map image, no date, "Reference purpose only" |
| e10 | Map "Flood Inundation Map 2013", source NRSC | 2013 | One raster image, year only, no text layer |
| e11 | Memorandum, monsoon calamity (submitted 4-07-2013), 30 pages | 1 to 30 Jun 2013 | District totals for landslide, flood and windfall together (891 villages affected); flooding named only in text for Kuttanad (Alappuzha) and the Kol lands (Thrissur) (page 7) |

The memoranda page also lists memoranda for 2012, 2014, 2019 and 2024 (e03). They were not
downloaded: each is a whole-period total of the same kind as e11.

Problems to handle in T122:

- District names differ between documents, for example Alleppey and Alappuzha, and Kasargode and
  Kasaragode.
- Memorandum 1 writes "One hundred and twenty three (138)" deaths; its table totals 138.
- The PDFs use Identity-H fonts, so a PDF parser is needed (T122 pins one). The tests read the
  pages with pdftotext when it is installed and skip that check otherwise.

## Source-specific check: pass

The plan rule is: use district totals only at district resolution, with no invented ward truth.
`place_id` is a district. Ward figures are only counts per district, so no ward or taluk label is
made. The two maps are images with no published vector layer, so no polygon is digitised from
them.

## Effect on M08 (decided in D29: core C2 is M05)

The M08 card needs "independent positive AND negative labels before 2018" for any forecasting
claim. KSDMA has dated district labels for 2018 only, and few of them: one table (16 Jul 2018)
and narrative dates. Before 2018 there are whole-period totals of mixed hazards (e11) and a
year-only map (e10). Under its card, M08 can only be a **descriptive 2018 replay** with no
predictive accuracy claim.

Decision D17 says that if the M08 labels fail, core C2 becomes M05 (taluk drought outlook).
Decision D29 applies it: M05 is core C2, and M08 stays in P3 as a non-core descriptive 2018
replay. T122 (S36 adapter) stays in P3, because that replay (F045) uses S36.



---

# 7.16 Source report S40

Source file: `docs/sources/s40.md`

# S40 Ward / taluk polygons and crosswalks: discovery (T030)

**Outcome: available** for Bengaluru ward polygons. No Karnataka taluk polygons were found.
Checked on 5 Nov 2026 (evidence fetched 09:36 to 09:38 UTC, 10 seconds apart as `robots.txt`
asks). Structured record: [`configs/sources/s40.yaml`](../../configs/sources/s40.yaml).
Evidence manifest: [`tests/fixtures/s40/manifest.json`](../../tests/fixtures/s40/manifest.json).
The KML files stay in `data/raw/S40` and are not committed.

## Boundary versions found on OpenCity

| Version | Wards | Licence on OpenCity | Source named | Evidence |
|---|---|---|---|---|
| GBA 2025 final (notified 19 Nov 2025) | 369 across 5 corporations | Other (Public Domain) | GBA | e02, e03, e04 |
| GBA 2025 final with renames from 01.12.2025 and population | 369 | Other (Public Domain) | GBA | e02, e05 |
| BBMP 2023 final | 225 | No License Provided | none | e06, e09 |
| BBMP 2022 | 243 | No License Provided | none | e06, e08 |
| BBMP 2015 | 198 | No License Provided | none | e06, e07 |

The GBA 2025 maps are the official ward geography with a release date. The KML resource credit
is "Vivek Mathew" (OpenCity). The page does not say whether the KML is GBA's own file or was
digitised from the notified maps, so T222 should record that caveat. The BBMP maps match the
wards in force during past monsoons (198 wards until 2022), which flood reports from those years
use. With no licence, they are for local research only and never published.

## Checks

- **Coordinates:** all files are OGC KML 2.2, so WGS84 longitude/latitude (EPSG:4326). The
  extents (longitude 77.460 to 77.784, latitude 12.833 to 13.144) lie inside Bengaluru.
- **No guessed IDs:** GBA `ward_id` repeats across corporations; the pair
  `(corporation_id, ward_id)` is unique for all 369 wards. BBMP 2022 `WardNo` is unique (243).
  BBMP 2015 has no ID field; its placemark names run "Ward 1" to "Ward 198".
- **Crosswalks:** the "Constituencies to Wards Mapping" CSV lists old and new wards side by side
  per assembly constituency. It is not a ward-to-ward match, so crosswalks between versions are
  derived from polygon overlap in T031 and labelled as derived.
- **Taluks:** a search for Karnataka taluk boundaries listed no taluk polygon dataset. Taluk-level
  outputs (for example M05) use district or H3 views, labelled as such, until an official taluk
  source is found.

## Field map (upstream to canonical)

| Canonical | Upstream |
|---|---|
| place_id | version prefix + `corporation_id`-`ward_id` (GBA 2025), `WardNo` (2022), placemark name number (2015), `id` (2023) |
| name | `ward_name` / `WardName` / `Ward Name` / `name_en` (Kannada names kept) |
| level | constant `ward` |
| parent_id | `corporation_id` (GBA 2025), `Zone` (2015) |
| version | from the resource title: `bbmp2015`, `bbmp2022`, `bbmp2023`, `gba2025`, `gba2025-12` |
| geometry | KML Polygon or MultiGeometry, stored as WKB in EPSG:4326 |
| valid_from | 2025-11-19 for GBA final; null for BBMP maps (year only) |

## Access and quota

Public downloads, no account, no key, no card. `robots.txt` disallows `/api/` and sets a
10 second crawl delay; the T031 adapter must keep both.

## Adapter (T031)

`src/atlas/ingest/s40.py` parses only the public-domain GBA 2025 final 369-ward KML (e04): one row
per ward with `place_id` `gba2025-c<corporation>-w<ward>`, `boundary_version`
`gba-2025-final-369`, the corporation as parent (Central, East, North, South, West) and WKB
geometry. The unlicensed BBMP maps are never parsed. Tests use the local T030 file and skip in CI.



---

# 7.17 Source report S43

Source file: `docs/sources/s43.md`

# S43 Official shelters and flood impact labels: discovery (T085)

**Outcome: blocked.** No official source publishes dated, ward-level flood impacts or open relief
camps for Bengaluru. Checked on 5 Nov 2026 (evidence fetched 09:46 to 09:48 UTC). Structured
record: [`configs/sources/s43.yaml`](../../configs/sources/s43.yaml). Evidence manifest:
[`tests/fixtures/s43/manifest.json`](../../tests/fixtures/s43/manifest.json). Evidence files stay
in `data/raw/S43`.

## What was checked

| Place | Finding | Evidence |
|---|---|---|
| OpenCity "bengaluru flood" | Flood-prone and low-lying area maps (Source KSRSAC, public domain), underpass audits; no dated incidents | e02, e03 |
| Flood-prone locations KML | 70 named points, only an OBJECTID: no date, ward or depth | e04 |
| OpenCity "inundation" | Hyderabad and Chennai only | e05 |
| OpenCity relief camps / shelters | No datasets | e06 |
| KSNDMC Floods page | One statewide paragraph on four heavy-rain spells in 2022 | e09 |
| KSNDMC Reports | Rainfall reports only | e10 |
| Bengaluru Megha Sandesha | Ward rainfall and temperature, no flood impacts | e11 |
| bbmp.gov.in, gba.karnataka.gov.in | TLS certificate verification failed; not bypassed | failed_fetches |

## The one dated ward-level record: I Change My City complaints

Janaagraha's I Change My City portal (a civic NGO, not a government body) has a complaints log on
OpenCity under CC BY-SA (e07, e08):

- 16,071 complaints, 1 Jan 2019 to 31 Jul 2022, 198 BBMP wards.
- 226 are "Flooding/Waterlogging Of Roads And Footpaths", on 215 ward-days.
- 136 of those ward-days fall in June to November: 2019: 52, 2020: 34, 2021: 35, 2022: 15 (the
  2022 data ends on 31 Jul). They fall on 116 distinct days.
- Dates come in two formats. Read month-first, every row parses and the rows run in time order.

This reaches the GATE-CORE C2 count (at least 100 positive ward-days across at least 3
monsoons), but it does not meet the rest of C2 or the S43 rules:

1. **Not official or independently documented.** A complaint says a citizen saw water on a road.
   No authority confirms the inundation.
2. **No coverage rule for negatives.** A ward-day without a complaint is not a verified dry day.
3. **Reporting bias.** Portal use fell from 7,383 complaints in 2019 to 1,551 in 2022, so later
   years under-report.
4. **Status.** 125 of the 226 flooding complaints are still "Open".
5. **Geometry.** The 198-ward BBMP map that these wards join to has no licence (S40, local only).

## Rules kept

- No OSM shelter tag is treated as an open relief camp; no evacuee records.
- No ward label is made from rainfall. Megha Sandesha ward rainfall is a feature source, not a label.
- No TLS check was bypassed to reach BBMP or GBA.

## Effect on other tasks

S43 stays `enabled: false`. These tasks need flood labels and stay blocked: T086 (S43 adapter),
T089 to T091 (M01 labels, models and evaluation). GATE-CORE C2 has no official label source. T222
records the choice: the A4 fallback (M08 Kerala flood classifier with the 2018 held-out replay),
or, only if the owner approves, the complaints log as non-official labels with a written coverage
rule.

## Retry condition

Re-run T085 when one of these holds:

1. GBA, BBMP, KSNDMC or KSDMA publish dated ward-level flood incident records.
2. The BBMP and GBA websites pass TLS verification.
3. At T222 the owner accepts the complaints log as non-official labels, with a coverage rule,
   recorded in the decisions log.



---

# 8. Karnataka state config (sources and enabled flags)

Source file: `configs/states/ka.yaml`

```yaml
# Karnataka (state 1). Source IDs and verify tasks from docs/plan.pdf sections 6 and 16.
# Every source starts disabled. Enable one only after its verify task passes and
# verified_by points to that evidence. Secrets: env var NAMES only, never values.
state_id: ka
name: Karnataka
storage_tz: UTC
display_tz: Asia/Kolkata
paths:
  raw_root: data/raw/ka
  clean_root: data/clean/ka
  publish_root: data/publish/ka
sources:
  - source_id: S01
    name: "Open-Meteo weather forecast"
    verify_task: T009
    cost: free
    storage_crs: EPSG:4326
    schedule: "every 6 hours"
    enabled: true
    verified_by: configs/sources/s01.yaml
  - source_id: S02
    name: "Open-Meteo historical weather / ERA5"
    verify_task: T011
    cost: free
    storage_crs: EPSG:4326
    schedule: "backfill once; daily delayed updates"
    enabled: true
    verified_by: configs/sources/s02.yaml
  - source_id: S03
    name: "Open-Meteo GloFAS river discharge"
    verify_task: T047
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S04
    name: "Open-Meteo CAMS air-quality estimates"
    verify_task: T049
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S05
    name: "Open-Meteo ensemble"
    verify_task: T051
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S06
    name: "Open-Meteo climate projections"
    verify_task: T053
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S07
    name: "NASA POWER daily point"
    verify_task: T055
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S08
    name: "IMD Pune gridded rainfall 1901-2024"
    verify_task: T057
    cost: free
    schedule: "yearly check"
    enabled: true
    verified_by: configs/sources/s08.yaml
  - source_id: S09
    name: "NDMA Sachet CAP alerts"
    verify_task: T013
    cost: free
    storage_crs: EPSG:4326
    schedule: "every 15 minutes"
    enabled: true
    verified_by: configs/sources/s09.yaml
  - source_id: S10
    name: "adsb.lol live aircraft"
    verify_task: T059
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S11
    name: "OpenSky flight fallback"
    verify_task: T061
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S12
    name: "CelesTrak orbit elements"
    verify_task: T063
    cost: free
    enabled: false
  - source_id: S13
    name: "NASA GIBS satellite imagery"
    verify_task: T065
    cost: free
    enabled: false
  - source_id: S14
    name: "AWS Terrarium terrain"
    verify_task: T067
    cost: free
    enabled: false
  - source_id: S15
    name: "OpenFreeMap basemap"
    verify_task: T015
    cost: free
    schedule: "static, on demand"
    enabled: true
    verified_by: configs/sources/s15.yaml
  - source_id: S16
    name: "WorldPop India population"
    verify_task: T017
    cost: free
    schedule: "once per release"
    enabled: true
    verified_by: configs/sources/s16.yaml
  - source_id: S17
    name: "geoBoundaries administrative boundaries"
    verify_task: T019
    cost: free
    storage_crs: EPSG:4326
    schedule: "yearly check"
    enabled: true
    verified_by: configs/sources/s17.yaml
  - source_id: S18
    name: "Geofabrik OSM extracts"
    verify_task: T021
    cost: free
    storage_crs: EPSG:4326
    schedule: "monthly clipped update"
    enabled: false
  - source_id: S19
    name: "Google Open Buildings"
    verify_task: T069
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S20
    name: "USGS earthquakes"
    verify_task: T071
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S21
    name: "Datameet railway schedules"
    verify_task: T073
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S22
    name: "India Data Portal Agmarknet / existing price data"
    verify_task: T023
    cost: free
    schedule: "backfill; daily if permitted"
    enabled: false
  - source_id: S23
    name: "data.gov.in mandi prices"
    verify_task: T025
    cost: free_with_key
    secret_env: DATA_GOV_IN_API_KEY
    schedule: "daily"
    enabled: false
  - source_id: S25
    name: "NASA FIRMS active fires"
    verify_task: T075
    cost: free_with_key
    storage_crs: EPSG:4326
    secret_env: NASA_FIRMS_MAP_KEY
    schedule: "every 6 hours"
    enabled: false
  - source_id: S27
    name: "KSNDMC gauges"
    verify_task: T077
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S28
    name: "KWRIS reservoirs and rainfall"
    verify_task: T008
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S29
    name: "OpenCity KSNDMC hobli rainfall 2017-2023"
    verify_task: T079
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S30
    name: "BMTC and Namma Metro static GTFS"
    verify_task: T028
    cost: free
    storage_crs: EPSG:4326
    schedule: "weekly"
    enabled: false
  - source_id: S31
    name: "Karnataka RERA projects"
    verify_task: T081
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S39
    name: "Telegram Bot API"
    verify_task: T083
    cost: free_with_key
    secret_env: TELEGRAM_BOT_TOKEN
    schedule: "on official alert change; daily brief"
    enabled: false
  - source_id: S40
    name: "Ward / taluk polygons and crosswalks"
    verify_task: T030
    cost: free
    storage_crs: EPSG:4326
    schedule: "one-off then boundary revision"
    enabled: true
    verified_by: configs/sources/s40.yaml
  - source_id: S43
    name: "Official shelters and flood impact labels"
    verify_task: T085
    cost: free
    storage_crs: EPSG:4326
    enabled: false
  - source_id: S44
    name: "District crime statistics"
    verify_task: T087
    cost: free
    enabled: false
```



---

# 9. M05 model config

Source file: `configs/models/m05.yaml`

```yaml
# M05 Karnataka drought outlook (plan model card M05; core C2 by decision D29). T101.
model_id: M05
task: regression
target: spi3 of the issue month (standardised 3-month rain total, gamma fit per district and calendar month)
classification_target: drought = SPI-3 < -1.0
unit: district            # no verified taluk polygons (T030); S17 geoBoundaries 2021 lines, 30 districts
boundary_version: geoboundaries-IND-ADM2-9469f09
rain_source: S08          # IMD 0.25 degree daily grids, area-weighted (m2) to districts
spi_reference: ["1981-01-01", "2010-12-31"]
features:                 # all from months up to t-1; issue at 00:00 IST on day 1 of month t
  - spi1_lag1
  - spi3_lag1
  - spi6_lag1
  - rain_lag1_mm
  - month_of_year
baselines: [spi3 persistence, month climatology]
splits: src/atlas/features/m05.py splits()  # train 1981-07..2016-09 (purged 92 days), tune 2017-2018, calibrate 2019, test 2020-2024
evidence: hindcast        # D39: S08 is released yearly, so live issue-time rain is not available
data_gate:
  min_years: 30
  taluk_polygons: false   # falls back to districts, labelled as such
```



---

# 10. Repository file inventory

191 tracked files (raw data and secrets are git-ignored).

| File | Bytes |
|---|---|
| `.gitattributes` | 62 |
| `.github/workflows/ci.yml` | 1,546 |
| `.gitignore` | 363 |
| `AGENTS.md` | 3,472 |
| `CLAUDE.md` | 11 |
| `LICENSE` | 1,217 |
| `README.md` | 923 |
| `configs/budgets.yaml` | 1,084 |
| `configs/models/m05.yaml` | 1,109 |
| `configs/sources/s01.yaml` | 4,308 |
| `configs/sources/s02.yaml` | 4,054 |
| `configs/sources/s08.yaml` | 4,925 |
| `configs/sources/s09.yaml` | 5,042 |
| `configs/sources/s15.yaml` | 3,728 |
| `configs/sources/s16.yaml` | 3,946 |
| `configs/sources/s17.yaml` | 4,514 |
| `configs/sources/s18.yaml` | 3,440 |
| `configs/sources/s22.yaml` | 3,286 |
| `configs/sources/s23.yaml` | 4,299 |
| `configs/sources/s28.yaml` | 5,613 |
| `configs/sources/s32.yaml` | 5,616 |
| `configs/sources/s34.yaml` | 5,461 |
| `configs/sources/s35.yaml` | 5,037 |
| `configs/sources/s36.yaml` | 5,900 |
| `configs/sources/s40.yaml` | 5,206 |
| `configs/sources/s43.yaml` | 6,664 |
| `configs/states/ka.yaml` | 5,806 |
| `docs/HANDOFF.md` | 25,045 |
| `docs/amendments.md` | 11,028 |
| `docs/amendments.yaml` | 2,259 |
| `docs/decisions.md` | 18,343 |
| `docs/dependency-audit.md` | 19,963 |
| `docs/gates/core_data_gate.md` | 7,549 |
| `docs/plan.pdf` | 1,816,140 |
| `docs/planning/1-handoff.pdf` | 69,979 |
| `docs/planning/2-project-overview.pdf` | 49,886 |
| `docs/planning/3-chatgpt-prompt.pdf` | 81,468 |
| `docs/research/kw-live-and-india-data-research.md` | 22,590 |
| `docs/sources/s01.md` | 2,869 |
| `docs/sources/s02.md` | 2,473 |
| `docs/sources/s08.md` | 3,935 |
| `docs/sources/s09.md` | 2,904 |
| `docs/sources/s15.md` | 1,807 |
| `docs/sources/s16.md` | 2,111 |
| `docs/sources/s17.md` | 2,176 |
| `docs/sources/s18.md` | 1,655 |
| `docs/sources/s22.md` | 981 |
| `docs/sources/s23.md` | 1,559 |
| `docs/sources/s28.md` | 3,800 |
| `docs/sources/s32.md` | 3,900 |
| `docs/sources/s34.md` | 3,502 |
| `docs/sources/s35.md` | 2,699 |
| `docs/sources/s36.md` | 4,243 |
| `docs/sources/s40.md` | 3,572 |
| `docs/sources/s43.md` | 3,475 |
| `models/registry/M05/v1.approval.json` | 128 |
| `models/registry/M05/v1.evaluation.json` | 1,269 |
| `models/registry/M05/v1.json` | 1,853 |
| `pyproject.toml` | 1,251 |
| `reports/models/m05.md` | 2,415 |
| `requirements/core.in` | 201 |
| `requirements/core.txt` | 40,742 |
| `requirements/dev.in` | 153 |
| `requirements/dev.txt` | 15,139 |
| `requirements/dl.in` | 318 |
| `requirements/dl.txt` | 68,927 |
| `requirements/geo.in` | 318 |
| `requirements/geo.txt` | 119,206 |
| `requirements/ml.in` | 319 |
| `requirements/ml.txt` | 225,097 |
| `schemas/common.json` | 2,958 |
| `schemas/places.json` | 1,330 |
| `schemas/s01.json` | 1,328 |
| `schemas/s02.json` | 1,254 |
| `schemas/s08.json` | 1,007 |
| `schemas/s09.json` | 1,758 |
| `schemas/s15.json` | 684 |
| `schemas/s16.json` | 986 |
| `schemas/s17.json` | 1,118 |
| `schemas/s18.json` | 693 |
| `schemas/s40.json` | 994 |
| `scripts/audit_dependencies.py` | 9,822 |
| `scripts/m05_release.py` | 7,307 |
| `src/atlas/__init__.py` | 94 |
| `src/atlas/__main__.py` | 50 |
| `src/atlas/cli.py` | 3,996 |
| `src/atlas/config.py` | 6,093 |
| `src/atlas/contracts.py` | 5,200 |
| `src/atlas/data/__init__.py` | 0 |
| `src/atlas/data/asof.py` | 3,319 |
| `src/atlas/data/budget.py` | 4,452 |
| `src/atlas/data/manifest.py` | 4,301 |
| `src/atlas/data/store.py` | 5,344 |
| `src/atlas/data/validate.py` | 5,355 |
| `src/atlas/features/__init__.py` | 55 |
| `src/atlas/features/base.py` | 4,184 |
| `src/atlas/features/m05.py` | 10,015 |
| `src/atlas/ingest/__init__.py` | 0 |
| `src/atlas/ingest/base.py` | 1,090 |
| `src/atlas/ingest/discovery.py` | 6,522 |
| `src/atlas/ingest/http.py` | 12,507 |
| `src/atlas/ingest/raw_store.py` | 2,638 |
| `src/atlas/ingest/s01.py` | 8,607 |
| `src/atlas/ingest/s02.py` | 7,451 |
| `src/atlas/ingest/s08.py` | 7,562 |
| `src/atlas/ingest/s09.py` | 10,006 |
| `src/atlas/ingest/s15.py` | 4,741 |
| `src/atlas/ingest/s16.py` | 6,975 |
| `src/atlas/ingest/s17.py` | 8,753 |
| `src/atlas/ingest/s18.py` | 820 |
| `src/atlas/ingest/s40.py` | 5,975 |
| `src/atlas/jsonl.py` | 1,222 |
| `src/atlas/models/__init__.py` | 55 |
| `src/atlas/models/base.py` | 3,119 |
| `src/atlas/models/evaluate.py` | 2,741 |
| `src/atlas/models/m05.py` | 13,163 |
| `src/atlas/models/registry.py` | 4,565 |
| `src/atlas/models/splits.py` | 4,670 |
| `src/atlas/models/uncertainty.py` | 3,301 |
| `src/atlas/spatial/__init__.py` | 85 |
| `src/atlas/spatial/crosswalk.py` | 3,612 |
| `src/atlas/spatial/places.py` | 6,284 |
| `tests/fixtures/README.md` | 3,414 |
| `tests/fixtures/s01/manifest.json` | 5,426 |
| `tests/fixtures/s01_openmeteo_forecast_ecmwf_ifs025_bengaluru_2026-11-05.json` | 14,640 |
| `tests/fixtures/s01_openmeteo_meta_ecmwf_ifs025_2026-11-05.json` | 596 |
| `tests/fixtures/s02/manifest.json` | 4,137 |
| `tests/fixtures/s02_openmeteo_archive_bengaluru_2024-07-01_04.json` | 360 |
| `tests/fixtures/s02_openmeteo_era5_bengaluru_1940-01-01_07.json` | 572 |
| `tests/fixtures/s02_openmeteo_era5_bengaluru_2026-10-20_11-04.json` | 829 |
| `tests/fixtures/s08/manifest.json` | 3,695 |
| `tests/fixtures/s09/manifest.json` | 4,647 |
| `tests/fixtures/s09_sachet_cap_1793871793334006.xml` | 2,682 |
| `tests/fixtures/s09_sachet_cap_1793880856139008.xml` | 2,857 |
| `tests/fixtures/s09_sachet_cap_1793881986295019.xml` | 3,951 |
| `tests/fixtures/s09_sachet_polygon_1793881986295019.xml` | 260,820 |
| `tests/fixtures/s09_sachet_rss_india_2026-11-05.xml` | 83,761 |
| `tests/fixtures/s15/manifest.json` | 3,498 |
| `tests/fixtures/s16/manifest.json` | 2,571 |
| `tests/fixtures/s17/manifest.json` | 3,160 |
| `tests/fixtures/s18/manifest.json` | 2,049 |
| `tests/fixtures/s22/manifest.json` | 2,083 |
| `tests/fixtures/s23/manifest.json` | 1,785 |
| `tests/fixtures/s28/manifest.json` | 5,657 |
| `tests/fixtures/s32/manifest.json` | 42,942 |
| `tests/fixtures/s34/manifest.json` | 7,573 |
| `tests/fixtures/s35/manifest.json` | 3,567 |
| `tests/fixtures/s36/manifest.json` | 5,965 |
| `tests/fixtures/s40/manifest.json` | 6,844 |
| `tests/fixtures/s43/manifest.json` | 6,323 |
| `tests/models/test_leakage.py` | 8,466 |
| `tests/models/test_m05_features.py` | 5,348 |
| `tests/models/test_m05_fit.py` | 5,432 |
| `tests/models/test_m05_gate.py` | 3,544 |
| `tests/models/test_release.py` | 5,673 |
| `tests/sources/conftest.py` | 1,952 |
| `tests/sources/test_s01.py` | 7,928 |
| `tests/sources/test_s01_discovery.py` | 2,604 |
| `tests/sources/test_s02.py` | 6,499 |
| `tests/sources/test_s02_discovery.py` | 2,335 |
| `tests/sources/test_s08.py` | 6,929 |
| `tests/sources/test_s08_discovery.py` | 3,002 |
| `tests/sources/test_s09.py` | 7,470 |
| `tests/sources/test_s09_discovery.py` | 2,597 |
| `tests/sources/test_s15.py` | 5,037 |
| `tests/sources/test_s15_discovery.py` | 1,960 |
| `tests/sources/test_s16.py` | 4,971 |
| `tests/sources/test_s16_discovery.py` | 2,426 |
| `tests/sources/test_s17.py` | 5,260 |
| `tests/sources/test_s17_discovery.py` | 1,994 |
| `tests/sources/test_s18.py` | 1,418 |
| `tests/sources/test_s18_discovery.py` | 1,192 |
| `tests/sources/test_s22_discovery.py` | 1,008 |
| `tests/sources/test_s23_discovery.py` | 1,930 |
| `tests/sources/test_s28_discovery.py` | 987 |
| `tests/sources/test_s32_discovery.py` | 3,780 |
| `tests/sources/test_s34_discovery.py` | 2,273 |
| `tests/sources/test_s35_discovery.py` | 1,951 |
| `tests/sources/test_s36_discovery.py` | 3,470 |
| `tests/sources/test_s40.py` | 4,476 |
| `tests/sources/test_s40_discovery.py` | 2,055 |
| `tests/sources/test_s43_discovery.py` | 2,136 |
| `tests/spatial/test_places.py` | 6,877 |
| `tests/test_asof.py` | 9,370 |
| `tests/test_config.py` | 8,278 |
| `tests/test_core_data_gate.py` | 2,282 |
| `tests/test_discovery.py` | 2,612 |
| `tests/test_environment.py` | 1,491 |
| `tests/test_http.py` | 12,486 |
| `tests/test_locks.py` | 6,042 |
| `tests/test_storage.py` | 10,253 |



---

# 11. Full commit history (oldest first)

```text
3e2494b 2026-11-05 T001: Create repository and planning contract
57d5ce6 2026-11-05 T002: Python 3.12 environment, linting and tests
0110985 2026-11-05 T003: Shared config, typed contracts and CLI
a8c5daf 2026-11-05 T004: Fetch boundary and immutable raw ledger
6a2e520 2026-11-05 T005: Schema registry and available-at-time joins
da5d845 2026-11-05 T006: Versioned Parquet manifests and quota ledger
5b431b2 2026-11-05 T007: Cross-platform CI and dependency audit
7dfa7ca 2026-11-05 T007: Fix pytest basetemp on fresh CI checkouts
2875841 2026-11-05 Merge P0: foundation (T002 to T007) (#1)
955d501 2026-11-05 T008: KWRIS discovery: public snapshot only, no history, blocked
863f34d 2026-11-05 T030: Ward polygons discovery: GBA 2025 official wards available, no taluk polygons
7d76b63 2026-11-05 T085: Flood impact labels discovery: no official ward-level incidents, blocked
71c8d90 2026-11-05 T222: GATE-CORE report: C1 and C2 fail, ward boundary passes; D17 proposed
feffd27 2026-11-05 T222: Record owner approval of D17 (H11), also try KWRIS
7a5da80 2026-11-05 T113: KSEB daily water level discovery: available from Oct 2023, gappy
5681b09 2026-11-05 T117: KSDMA dam level reports discovery: daily archive 2020-2026, scanned
2ae3917 2026-11-05 T119: Kerala 2018 flood dataset discovery: Kaggle blocked, official memorandum next
00123ba 2026-11-05 T003: CLI help test pins the child process encoding to UTF-8
c34fe50 2026-11-05 T121: KSDMA post-disaster assessment discovery: available, no M08 forecast labels
3070678 2026-11-05 T222: Decision D29: core C2 is M05 Karnataka drought outlook
2cb3c54 2026-11-05 T057: IMD Pune gridded rainfall discovery: available, 1901 to 2025
63f17d3 2026-11-05 T058: S08 adapter: IMD year files to the common envelope, Karnataka cells
d834c5a 2026-11-05 Handoff document for the next agent (living, updated after each task)
f9dec30 2026-11-05 T009: Open-Meteo forecast discovery: available, issue time from model metadata
ee1285c 2026-11-05 Handoff: T009 row
cb7f4ca 2026-11-05 T010: S01 adapter: Open-Meteo forecast with issue time from model metadata
740370e 2026-11-05 Handoff: T010 row
82a82b3 2026-11-05 T011: Open-Meteo ERA5 history discovery: available 1940 to D-6
2571ac4 2026-11-05 Handoff: T011 row
ed6842f 2026-11-05 T012: S02 adapter: Open-Meteo ERA5 daily history
80cbdff 2026-11-05 Handoff: T012 row
f7fea2d 2026-11-05 T013: NDMA Sachet CAP alerts discovery: available, public domain feed
73a9331 2026-11-05 Handoff: T013 row
cd59203 2026-11-05 T014: S09 adapter: Sachet CAP alerts with supersession and polygons
ae8a5c9 2026-11-05 Handoff: T014 row
f1fadc3 2026-11-05 T015: OpenFreeMap basemap discovery: available, attribution from TileJSON
a533fc9 2026-11-05 Handoff: T015 row
94903c4 2026-11-05 T016: S15 adapter: OpenFreeMap style revision and attribution
c6a4f0e 2026-11-05 Handoff: T016 row
56c3b4c 2026-11-05 T019: geoBoundaries discovery: available, 735 India districts, 30 for Karnataka
c503e40 2026-11-05 Handoff: T019 row
c0a2c6b 2026-11-05 T020: S17 adapter: geoBoundaries districts with parent state
170553e 2026-11-05 Handoff: T020 row
4a5735e 2026-11-05 T017: WorldPop India population discovery: available, 1 km counts 2015-2030
674b477 2026-11-05 Handoff: T017 row
1545fc5 2026-11-05 T021: Geofabrik OSM extracts discovery: blocked by robots.txt
a883fa3 2026-11-05 T022: S18 disabled adapter: Geofabrik blocked, fails closed
fccd8ec 2026-11-05 Handoff: T021 and T022 rows
98a6524 2026-11-05 T018: S16 adapter: WorldPop counts clipped to the state polygon
bfef005 2026-11-05 Handoff: T018 row
dbaf355 2026-11-05 Handoff: refresh sources, code map and next tasks after T022
2774b3f 2026-11-05 T031: S40 adapter: GBA 2025 wards (369) with parent corporations
7d84f91 2026-11-05 Handoff: T031 row and next task T032
e9807ef 2026-11-05 T032: Place identity, crosswalks and local gazetteer
cbd4f0d 2026-11-05 Handoff: T032 row
680f65e 2026-11-05 T033: Feature and target build framework with leakage checks
dbf9c2c 2026-11-05 Handoff: T033 row
e3f07bb 2026-11-05 T034: Baseline, interval and model release framework
6d57f4c 2026-11-05 Handoff: T034 row
41c763e 2026-11-05 T023: India Data Portal Agmarknet discovery: blocked, client-side app
f024a06 2026-11-05 Handoff: T023 row
4c6c008 2026-11-05 T101 (in progress): M05 target, features, gate and splits; acceptance pending data
a2ec0b8 2026-11-05 Handoff: current state, owner steps, next tasks and lessons after T034/T101 WIP
bbe7c25 2026-11-05 T101: M05 target and features pass on IMD 1981-2024
5ea10db 2026-11-05 Handoff: T101 done
f1af6cd 2026-11-05 T025: data.gov.in mandi prices discovery: works, blocked only on licence
d6732e7 2026-11-05 Handoff: T025 row
e6cb916 2026-11-05 T102: M05 baselines, ridge and bounded LightGBM
7efb139 2026-11-05 Handoff: T102 row
bea3eb9 2026-11-05 T103: M05 locked test: ridge passes all gates, awaiting owner approval
8dc9c8e 2026-11-05 Handoff: T103 row and owner approval step
a62a989 2026-11-05 Handoff: clean M05 next-step note
7f3780e 2026-11-05 T103: Owner approves M05 release v1; ridge is the champion
e23d597 2026-11-05 Handoff: M05 approved
968e73b 2026-11-05 Handoff: final git state after PR #3; Claude stops at 89% weekly usage
```

