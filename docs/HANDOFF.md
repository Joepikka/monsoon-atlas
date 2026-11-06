# Monsoon Atlas: handoff for the next AI agent

Last updated: 6 Nov 2026, T235 prepared snapshots and review fixes passed locally,
branch `p1/gate-core`. Uploaded handoff/ZIP remain historical snapshots.

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
| `docs/amendments.md`, `docs/amendments.yaml` | Amendments v1 plus recorded splits through T235. **They win where they conflict with the plan.** GATE-CORE (A4), human-only steps (A5), P1 order (A8) and child-task dependencies |
| `docs/decisions.md` | Decisions D01 to D66. Every deviation from the plan is recorded here before it is made |
| `AGENTS.md` (imported by `CLAUDE.md`) | Rules for AI agents: hard constraints, environment, how to work on a task, commands |
| `docs/planning/1-handoff.pdf`, `2-project-overview.pdf`, `3-chatgpt-prompt.pdf` | The earlier handoff, overview and the prompt that produced `plan.pdf` |
| `docs/research/kw-live-and-india-data-research.md` | The original KW Live and Indian open-data research |
| `docs/gates/core_data_gate.md` | GATE-CORE report (T222) with decisions D17 and D29 |
| `docs/sources/sNN.md` + `configs/sources/sNN.yaml` | One discovery report and record per checked source |
| `docs/dependency-audit.md` | Licence and wheel audit of every locked package (T007) |
| `docs/reviews/2026-11-05-continuation.md` | Codex review, archive comparison, test evidence and unresolved readiness limits |
| `docs/labels/kerala.md` | T226 evidence audit; full T129 remains pending |

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
| `configs/states/kl.yaml` | Isolated Kerala paths; S32 enabled after T114 checks, other sources disabled |
| `src/atlas/ingest/s32.py`, `schemas/s32.json` | T114 KSEB daily report adapter: observed 07:00 IST, strict layout, unit/percentage quarantine, unknown datum retained; S32 enabled only in Kerala |
| `src/atlas/ingest/s34_ocr.py`, `scripts/s34_ocr_review.py` | T228 local OCR review packets, pinned toolchain/model, two unselected candidates per cell and explicit owner gate; full S34 adapter pending |
| `src/atlas/ingest/s33.py`, `schemas/s33.json` | T116 blocked monthly source: raises SourceUnavailable even if config is force-enabled; no unverified field schema or rows |
| `src/atlas/ingest/s22.py`, `s23.py` | T024/T026 blocked price sources fail before network/file access, even if force-enabled |
| `src/atlas/features/m06.py`, `src/atlas/models/m06.py` | Evidence-bound blocked M06 path; no labels, weights, metrics or predictions |
| `web/`, `scripts/web.ps1` | T038 pinned React/Vite/MapLibre shell; approved immutable JSON loading, dated last-good state, responsive map/list and browser checks; no production data seeded |
| `web/src/map/Layers.tsx`, `web/src/components/SourceBadge.tsx`, `EventTicker.tsx` | T039 per-layer filtering, original clocks/severity, source health, geodesic point radius, area-warning context and pausable dated alert ticker |
| `web/src/components/PlaceLens.tsx`, `web/src/report.ts` | T040 six-tab reports, versioned place selection, immutable share identity and browser print/PDF from the same report; no production places or approvals seeded |
| `worker/`, `scripts/worker.ps1` | T229 child of T042: signed bounded hot-data uploads, canonical source validation and atomic SQLite caps; cloud capability/deployment disabled; actual Miniflare/D1 checks on Ubuntu CI |
| `configs/budgets.yaml` | Request, storage and DuckDB budgets |
| `tests/` | Contracts, fetcher, storage, as-of, discovery/adapters, geography, model gates and state isolation; final continuation results below |

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
| T117 | `5681b09` | S34 KSDMA daily dam reports: **available** 20 Jun 2020 to 4 Nov 2026 (2,296 archive dates), but scanned images require T118 OCR/manual review. Training readiness also requires known datum and verified per-dam daily coverage; archive dates alone do not pass M07's gate. |
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
| T025 | `f1af6cd` | Original S23 discovery: owner key works (current-day snapshot, Karnataka 565 rows, checks pass). Licence and units unresolved at that capture; see 6 Nov retry below. |
| T102 | `e6cb916` | M05 fit (src/atlas/models/m05.py): tune 2017-2018 MAE persistence 0.736, ridge 0.585, LightGBM 0.571 (gain not significant) -> ridge provisional; deterministic, test rows refused, artifacts in data/models (D41) |
| T103 | `bea3eb9` | M05 locked test 2020-2024: ridge beats persistence on all gates (MAE 0.732 vs 0.808, CI lower 0.003, PR-AUC 0.217, Brier skill 0.116, CRPS lower); release v1 candidate_eligible, **owner approval pending**; intervals under-cover (65%) so not published (D42). Report: reports/models/m05.md |
| T103 approval | `7f3780e` | Owner approved M05 v1 (D43): ridge is the champion; outputs labelled hindcast, no intervals |
| T226 (child of T129) | `7c0c8f5` | D44: isolated disabled Kerala config and existing-evidence audit; full T129 pending. D45: ignore local model artifacts without removing them. Acceptance: 7 tests passed. |
| T114 | `812e111` | S32 fetch/parse contract, real attributed CI samples and quarantine checks; D46. D47 fixes empty typed-table validation. |
| T227 (child of T114) | `e017b1e` | All 700 dates, 2024-08-15..2026-07-15, returned validated empty reports. 47 reused, 653 newly captured; zero failed/unattempted. Per-date hashes/counts committed; raw pages local. Acceptance: 7 passed in 1.08s; D48. |
| T228 (child of T118) | 67a47c6 | D49/D50: pinned local OCR tooling and three-page review packet, eight sample cells, six disagreements; all selections null. Machine acceptance: 10 passed in 3.88s. Owner review pending; full T118/S34 adapter remains pending and source disabled. |
| T115 | `e613666` | D51: S33 discovery pulled forward. Nine evidence pages; landing and three published dams URLs are HTTP-200 wrong-address errors. Main Monthly data link is electricity statistics. No reservoir artifact, history, units or file licence verified; source blocked/disabled. Acceptance: 8 passed in 0.11s. |
| T116 | `546ad49` | Disabled S33 adapter raises SourceUnavailable before I/O, including forced-enable attempts. No dataset/field schema invented. Acceptance: 3 passed in 0.42s. |
| T025 retry | `53ad4de` | D52/D53: public browser metadata verifies GODL-India, with three labelled local projections and hashes. Price denominator still unlabelled; S23 stays disabled. Original API captures unchanged. Acceptance: 8 passed in 0.16s. |
| T024 | `fa6589c` | S22 disabled adapter; forced config flags cannot enable network/file access or produce rows. Acceptance: 3 passed in 0.45s; full suite 435 passed, 1 skipped in 103.29s; lint/format pass. No unverified schema invented. |
| T026 | `d2ae46b` | S23 disabled adapter retains the unit gate despite verified GODL. Acceptance: 3 passed in 0.06s; full suite 438 passed, 1 skipped in 91.97s; lint passes. |
| T035 | `882521b` | M06 blocked data gate: actual source/config hashes, planned target/split dates, unknown publication lag and no labels/features/predictions. Acceptance: 4 passed in 0.56s; full suite 442 passed, 1 skipped in 122.47s; lint/format pass. This completes only the prescribed blocked branch. |
| T036 | `aa3ca68` | Blocked M06 fit/predict contract, local no-model record and clean-process status notebook. Acceptance: 3 passed in 1.56s; full suite 445 passed, 1 skipped in 101.12s; lint/format pass. No fitting or evaluation performed. |
| T037 | `5da4702` | Source-bound blocked status and report; no achieved scores, release, champion or predictions (D55). Acceptance: 3 passed in 0.58s; full suite 448 passed, 1 skipped in 128.31s; lint/format pass. M06 remains unavailable. |
| T038 | `4f3c36e` | Pinned Node/React/Vite/MapLibre shell; hash/approval/state checks, original source times/provenance, dated last-good view, responsive map/list and genuine CAP test fixture. Acceptance: 3 passed in 21.18s. Full suite: 451 passed, 1 skipped in 153.66s, including build, 9 unit checks and 18 Chromium checks. Lint/format and dependency policy pass; production npm audit reports 0 advisories. No production data or release approval seeded. |
| T039 | `3dbbd04` | Original source clocks/provenance, provider severity/expiry, source health, per-layer toggles, keyboard geodesic radius and pausable dated alerts (D58). Source projections checked against S01/S09 adapters. Acceptance: 2 passed in 21.13s; full suite 453 passed, 1 skipped in 206.61s; 16 web unit checks and 30 browser checks, including populated axe/overflow checks. Lint/format pass; price/model/source gates unchanged. |
| T040 | `03383a2` | Six tabs, versioned source-backed places, hash-bound historical share links and browser print/PDF from the same report (D59). Original CAP warning/instruction retained; unavailable facilities/scores stay unavailable. Acceptance: 4 passed in 37.80s. Full suite: 457 passed, 1 skipped in 288.83s, including 23 web unit checks and 45 browser checks. Lint/format (147 files), dependency policy and whitespace checks pass. Three generated A4 PDFs checked for original warning, attribution, place version and risk limits. No production places, facilities, scores or approvals seeded. |
| T229 (child of T042) | `d5dc0f2`..`4cdffde` | Local acceptance: 4 passed in 1.61s, including 8 Node logic cases and SQLite cap/rollback checks. Full suite: 461 passed, 1 skipped in 229.96s. Actual Miniflare/D1 Ubuntu CI passed at `4cdffde`, including duplicate concurrency, conflicting cutoffs, original clocks/hash, corruption and storage/write rollback. Lint/format, dependency policy, npm full audit (0 vulnerabilities), amendment parity and whitespace pass. Full T042 is pending H05 and an actual free/no-card capability probe; no remote resource, approval or service is created. |
| T230 (child of T043) | `8565cc9` | Original area-only CAP projection checked against S09 with no supplemental polygon. Nullable coordinates allowed only for official S09 area text with an explicit location limit. List, ticker and report retain it; map makes no marker or fly-to point. Stored canonical hashes are checked before normalization, including ignored fields and older optional-field representations. Acceptance: 2 passed in 14.61s; full suite: 463 passed, 1 skipped in 258.38s, with 26 web unit checks, 48 browser checks and 11 Worker logic checks. Lint/format (151 files), amendment parity and whitespace pass. Actual Worker/D1 Ubuntu and web Windows/Ubuntu CI pass. Full T043's producer, schedule, polling and cloud gate remain pending. |
| T231 (child of T043) | `9dbb233` | Known S09 entries are keyed by actual RSS item versions; changed versions at known URLs re-enter conditional GET. Bare identifier-only skip sets fail before network. Empty valid RSS stays distinct from wrong schema/missing links. Acceptance: 13 passed in 1.10s; full suite: 467 passed, 1 skipped in 482.34s. Lint/format (151 files), dependency policy, amendment parity and whitespace pass. No claim of immutable CAP URLs or guaranteed 15-minute freshness. T043 still needs bounded cache expiry/checkpoints, producer, scheduling and polling. |
| T232 (child of T043) | `acd8168` | Full CAP sender/identifier/sent reference matching, equivalent timezones only, malformed/unmatched/self-reference preservation, Update/Cancel authority and active-warning control filtering (D63). Public rows require Actual/Public lifecycle values; unknown fields and naive dates fail closed. Declared mutated-copy regressions replace the earlier incorrect predecessor test. Acceptance: 31 passed in 1.11s; full suite: 485 passed, 1 skipped in 215.28s. Lint/format (151 files), amendment parity and whitespace pass. |
| T233 (child of T043) | `f48d418` | Signed server-clock admission, atomic elapsed cadence across UTC boundaries/cache loss/duplicate jobs, with shared storage/write guards (D64). Acceptance: 8 passed in 3.13s; full suite: 493 passed, 1 skipped in 194.23s. Worker type checking, 12 logic checks and actual D1 concurrent admission/cap rollback pass on Ubuntu CI. Lint/format (152 files), amendment parity and whitespace pass. No provider collection, cron, cloud resource or activation created. |
| T234 (child of T043) | `2b949c7` | Bounded CAP-only local capture, per-attempt spacing, shared SQLite cadence/cooldown, fair queue, conditional linked-document revalidation, raw hash checks, retained content/check clocks and per-document checkpoints. A hard parent deadline kills/reaps the HTTP-only child; completed evidence survives. Header-only control messages retain actual headers without fake warning rows. Acceptance: 20 passed in 19.55s; full suite: 513 passed, 1 skipped in 247.64s. Web: 30 unit and 48 browser checks pass; build/lint/format (157 files), dependency policy, parity and whitespace pass. Live smoke: 2 actual CAP documents validated in 8.34s, 0 failures, 98 pending, always partial. Independent review's two Important findings fixed with failing-then-passing tests: terminal/interrupted Retry-After and non-reconstructed availability before retrieval. No approval, public snapshot, upload or recurring job created. |
| T235 (child of T043) | `6aa8b24` | Local CAP-only preparation with exact Actual/Public control references, expiry filtering, source-bound area-only records and distinct retrieval/check/preparation clocks. Content-addressed input manifests bind data revisions; prepared-only pointers are serialized, atomic, idempotent and reject older/conflicting cutoffs. Damaged or missing/retargeted control-ledger entries cannot resurrect warnings; header-only Updates/Cancels apply references without fake warning rows. Acceptance: 24 passed in 4.60s; combined S09 checks: 76 passed in 17.31s; full suite: 538 passed, 1 skipped in 216.39s. Worker type checking and 13 logic checks pass, including partial-health preservation and actual Python payload decode/restore. Lint/format (160 files), dependency policy, parity and whitespace pass. Live preparation from the 2 retained CAPs produces 0 current warnings, explicitly partial, with no claim of absence of hazards. Independent review's two Important findings fixed RED→GREEN. No upload, approval, workflow or deployment created. |

T234 independent batch review and rulings: `docs/reviews/2026-11-06-p1-batch.md`.
Both Important findings are fixed; no Critical or Minor findings remain from that
review. Cloud capability, normalized control application, complete coverage and
blocked-source/model gates remain explicitly pending, rather than certified.

T025 retry final validation: `432 passed, 1 skipped, 1 warning in 115.94s`;
lint passes, 128 files pass formatting, dependency policy reports 0 problems
and whitespace checks pass. Independent review found no actionable defect and
confirmed that the projections are absent from the Fetcher cache ledger. The
skip/warning remain the existing S36 PDF-tool absence and MLflow deprecation.

T038 remote web CI passed on Windows and Ubuntu for commit `4f3c36e`:
https://github.com/Joepikka/monsoon-atlas/actions/runs/42201637045 . Both matrix jobs
installed the lock, built, ran unit tests and passed the shell browser checks.

T039 remote web CI also passed both matrix jobs for `3dbbd04`:
https://github.com/Joepikka/monsoon-atlas/actions/runs/42206285593 .

T040 remote web CI passed both matrix jobs for `03383a2`:
https://github.com/Joepikka/monsoon-atlas/actions/runs/42211241573 .

T229 actual Miniflare/workerd/D1 CI passed on Ubuntu for `4cdffde`:
https://github.com/Joepikka/monsoon-atlas/actions/runs/42213687569 . The harness
uses the installed Miniflare 5 options converter and removes comment-only SQL
tails rejected by its pinned workerd. The test suite covers source data age
separately from report age. This is local simulation, not a cloud account probe.

T230 actual area-only alert D1 round trip and all web viewports passed at `8565cc9`:
https://github.com/Joepikka/monsoon-atlas/actions/runs/42215181966 (Worker),
https://github.com/Joepikka/monsoon-atlas/actions/runs/42215181974 (Windows/Ubuntu web).

T233 actual D1 admission concurrency and shared capacity guards passed at `f48d418`:
https://github.com/Joepikka/monsoon-atlas/actions/runs/42243904334 .

T234 at `c186d5e` passed core CI on Windows/Ubuntu, real Worker/D1 Ubuntu CI,
and web checks on Windows/Ubuntu:
https://github.com/Joepikka/monsoon-atlas/actions/runs/42250185879 ,
https://github.com/Joepikka/monsoon-atlas/actions/runs/42250185714 ,
https://github.com/Joepikka/monsoon-atlas/actions/runs/42250185614 .
The tested batch is draft PR #5: https://github.com/Joepikka/monsoon-atlas/pull/5 .
T235 at `08fd4d0` passed core CI on Windows/Ubuntu, actual partial-health D1
persistence on Ubuntu, and web checks on Windows/Ubuntu:
https://github.com/Joepikka/monsoon-atlas/actions/runs/42256005921 ,
https://github.com/Joepikka/monsoon-atlas/actions/runs/42256005957 ,
https://github.com/Joepikka/monsoon-atlas/actions/runs/42256006061 .
The local integration test also validates Python-produced payloads with the
actual Worker decoder/restore. T236's local bounded runner is in progress.

T116 final validation: `430 passed, 1 skipped, 1 warning in 115.83s`; lint passes,
128 files pass formatting, dependency policy reports 0 problems and whitespace
checks pass. Independent review found no actionable defect. The skip/warning
remain the existing S36 PDF-tool absence and MLflow deprecation.

T115 final validation: `427 passed, 1 skipped, 1 warning in 98.82s`; lint passes,
126 files pass formatting, dependency policy reports 0 problems, and amendment
Markdown/YAML parity passes. Review identified evidence descriptions that named
intended page content; those now describe the observed error, covered by a
regression test. The skip/warning remain the existing S36 PDF-tool absence and
MLflow deprecation. No raw page content was committed.

T228 final validation: `419 passed, 1 skipped, 1 warning in 106.21s`; lint passes,
124 files pass format, dependency policy reports 0 problems, `pip check` passes,
amendment Markdown/YAML parity passes, and all 13 local HTML/image links resolve.
The skip/warning are the existing S36 PDF-tool absence and MLflow deprecation.
Independent code review found no actionable defect. This verifies machine
preparation only; it is not an OCR accuracy claim or owner approval.

T227 final validation: `407 passed, 1 skipped, 1 warning in 108.98s`; adapter/history
acceptance is covered by the full suite. Ruff lint passes, 120 files pass format,
dependency policy reports 0 problems, and whitespace checks pass for this diff.
The skip/warning remain the S36 PDF tool absence and upstream MLflow deprecation.

T114 verification (6 Nov 2026): 34 adapter checks pass (also run with coverage:
89% of the adapter); source/isolation/as-of checks: 69 passed. Full suite:
`400 passed, 1 skipped, 1 warning in 169.45s`. Ruff lint passes; format check:
117 files formatted. Dependency policy: 0 problems. Amendment Markdown/YAML
parity passes. Code/doc whitespace checks pass; unchanged upstream HTML fixtures
retain trailing spaces (D48). The skip and warning are the same S36
`pdftotext` absence and MLflow deprecation described below. Independent read-only
review found no actionable defect. All 77 captured S32 report pages replayed:
50 empty; other pages contain 224 valid, 154 quarantined and 54 incomplete rows.

T226 final verification (Python 3.12.14 in `D:\monsoon-atlas\.venv`):

```text
python -m pytest tests/test_kl_data.py -q
7 passed in 0.62s
python -m pytest -q -ra
365 passed, 1 skipped, 1 warning in 110.57s
python -m ruff check .
All checks passed!
python -m ruff format --check .
115 files already formatted
python scripts/audit_dependencies.py --policy
policy: 0 problem(s)
```

The skipped S36 PDF-text evidence check requires `pdftotext` on PATH; T122 pins a
PDF parser. The warning is MLflow's SQLAlchemy `noload` deprecation. Amendment
Markdown/YAML parity and `git diff --check` passed. Independent read-only review
found no actionable issues in T226; it did not certify future adapters or rerun M05.

## 8. Current state

### Core models (portfolio MVP)

| Slot | Model | Status |
|---|---|---|
| C1 | **M07 Kerala seven-day dam forecast** (D17) | T226/T114/T227 done. S32's public reports contain no rows throughout the checked 700-day gap; S34 needs T118 OCR/review. Both sources report unknown datum; model readiness still blocked pending T130's gate. |
| C2 | **M05 Karnataka drought outlook** (D29): SPI-3 of the issue month and drought probability, per district | T101-T103 done; ridge approved in D43. Hindcast only (D39); do not publish the under-covering intervals (D42). |
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
| S23 data.gov.in mandi prices | T025 | blocked on price denominator; GODL verified | Key was already used in discovery; no new key or licence confirmation needed |
| S28 KWRIS | T008 | blocked | retry if KWRIS daily history arrives |
| S32 KSEB daily levels | T113, T114, T227 | available, enabled in KL (partial history) | Strict quarantine; datum unknown; all 700 gap dates return validated empty reports |
| S33 KSEB monthly statistics | T115, T116 | blocked, disabled adapter complete | Published archive pages return wrong-address errors; no verified reservoir file |
| S34 KSDMA dam reports | T117 | available (scanned) | OCR T118, adapter |
| S35 Kaggle Kerala floods | T119 | blocked | needs owner Kaggle sign-in (H10) |
| S36 KSDMA memoranda | T121 | available | adapter T122 in P3 |
| S40 ward polygons | T030, T031 | available, enabled | 369 GBA 2025 wards, public domain |
| S43 Bengaluru flood labels | T085 | blocked | not ground truth |

### Pending human-only steps (owner)

- **H05/H06:** the owner reports both accounts signed in and showed a signed-in
  Cloudflare dashboard in regular Chrome on 6 Nov. Google rejected login in the
  automation-controlled browser; use regular Chrome for account setup. Tokens
  are not configured locally. Account access does not certify a free/no-card
  capability probe or authorize public deployment. Do not create accounts,
  accept terms or enter keys on the owner's behalf.
  The owner explicitly deferred tokens on 6 Nov: "I'll do this later; continue
  local work." Do not repeat the token question; proceed with independent local
  preparation. The concrete owner guide is `docs/account-setup.md`.

- **Current next action: review the S34 OCR sample** at
  `D:\monsoon-atlas\data\raw\S34\ocr-review\index.html`. Compare the eight original
  cell crops with both OCR readings and confirm/correct values and units. Six cells
  disagree. No candidate is selected, including the two that agree. T117/T118
  requires this owner review before values are used; it does not approve bulk OCR.

- Send the drafted KWRIS helpdesk request to ACIWRM (daily reservoir history). If data arrives
  with units, datum and licence, re-run T008.
- H04: Delhi Open Transit Data registration (needed in P4).
- H10 (optional): Kaggle sign-in only if the owner wants S35 re-checked.
- H11: review at each gate and before any public deployment (licences: S08 and S34 forbid
  reproduction, so only derived outputs may be published).
- Before public deployment also: confirm you are 18+ (OpenFreeMap terms), check boundary maps
  against India's official mapping guidance (geoBoundaries has no disputed-boundary field), and
  label WorldPop counts for Bengaluru as an undercount (about 6.0 million in the GBA wards).
- T025 already accessed data.gov.in with the owner's key, and the browser retry verified
  GODL. Remaining blocker: a publisher statement establishing the API price denominator;
  see `docs/sources/s23.md`. Do not request another key or repeat licence confirmation.
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
6. **C1 = M07 (Kerala): T226/T114/T227 and T228 machine preparation are done.**
   First obtain the required owner review of the S34 packet (section 8). Then
   continue full T118: validate per-layout cell extraction, dates, units and dam
   identity; retain quarantine and never infer alert colours from English OCR.
   T228 sample approval does not approve bulk extraction; S34 remains disabled.
   Before T130, explicitly resolve its full-T129 dependency for the M07-only fallback.
   T115/T116 scheduling is resolved by D51; full T129 remains P3 and pending (D44).
   T130 must verify known datum, >=3 years daily coverage across >=8 dams and new dated
   splits against the actual parsed history. The Jun 2020 archive start is not a gate pass.
   Independent follow-up D51: T115/T116 are done (S33 blocked, disabled adapter
   tested). This supplies a source-availability status, not observations for M07.
7. **Prices:** T025's GODL licence is verified; the price denominator remains unverified.
   Capture a publisher unit statement tied to the actual resource before enabling ingestion
   in T026 or T035 to T037. T024/T026 disabled adapters are complete. The S23 API key was
   already supplied; do not request it again without cause.
   T035-T037's prescribed blocked branch is complete; `reports/models/m06.md`
   records why there is no trained price model. Continue independent P1 work (D54).
8. **A8 step 9:** T038/T039/T040 checks pass. T041's walking-network study is
   blocked by S18 (T021/T022); no catchments or coverage results are invented.
   `scripts/web.ps1 run dev` serves the local
   map at http://127.0.0.1:5173. There is no approved public snapshot or deployment.
   T229's local T042 implementation and real Ubuntu runtime CI pass. Full T042
   stays pending H05. T230 preserves text-only S09 alerts through the browser
   and hot transport; local and web/Worker CI checks pass. T231 replaces permanent
   known identifiers with RSS item fingerprints; T232 fixes complete CAP
   supersession identity and public lifecycle selection. T233's durable source
   admission passes locally and in actual D1. T234's local bounded collector and
   independent review fixes pass. T235 normalization/prepared snapshots and its
   review fixes also pass locally. Next implement the bounded refresh runner,
   remaining source preparation, schedule and active-page poller. Research in
   `.cache/t043-research/findings.md` verifies that a full cold CAP+polygon sweep
   already needs 200 seconds of spacing alone; use bounded CAP-only admission,
   persisted ETag/checkpoints and a hard subprocess deadline, with partial/dating
   limits. Never infer complete Karnataka coverage from CAP-only text filtering.
   Run a single local capture with `scripts/feeds.ps1 --max-documents 30`; its
   evidence and control database remain under `.cache/feeds`. Do not reset that
   database to bypass admission/cooldown, or publish its partial results as a
   complete warning feed. `scripts/feeds.ps1 prepare` makes immutable local
   prepared-only envelopes, without upload or approval. `docs/feeds.md` describes
   the scope; `docs/reviews/2026-11-06-t235.md` records the latest review fixes.
   Continue
   independent local hosting preparation and then C3 Ask preparation,
   T225 case studies and T046;
   unresolved human/data gates must remain pending rather than blocking independent work.

## 10. Lessons and pitfalls

- PowerShell on this laptop decodes child output as cp1252; pin `encoding="utf-8"` when a test
  reads subprocess output. Print with `sys.stdout.reconfigure(encoding="utf-8")`.
- `pdftotext` exists only in Git Bash (`/mingw64/bin`). Many government PDFs use Identity-H fonts,
  so the standard library cannot read them; adapters must pin a PDF parser (pypdf) in a lock.
- The fetcher sends conditional requests; a 304 reuses the stored file (even one stored for
  another source with the same URL).
- Indian government sites often have broken TLS chains (BBMP, GBA): record the failure, never
  disable verification.
- Kerala's config enables S32 only (T114); other sources remain disabled. Discovery
  availability alone does not certify adapters, full T129 or M07 readiness.
- Full suite took 117.61 seconds before this continuation (358 passed, 1 skipped);
  S08/model tests parse real local rainfall data. MLflow emits an upstream deprecation warning.
- IMD Pune speed varies a lot (10 s to 5 minutes per 25 MB year file); run big fetches in the
  background.
- WorldPop GeoTIFFs are BigTIFF (`II+`) with LZW tiles: use rasterio (geo lock).
- Many pages put `&nbsp;` between numbers and units; match the raw HTML, not the rendered text.
- Client-side web apps (India Data Portal) need a browser render; never guess their APIs.
- GitHub sometimes rejects a push with `fatal error in commit_refs`; just retry.
- Geo and ml locks are installed locally; CI installs core and dev only, so tests that need
  rasterio, shapely, h3, scipy or mlflow use `pytest.importorskip` (D35).

## 11. Obsidian vault (owner's second brain)

Historical vault location: `C:\Users\joepi\Documents\Obsidian Vault`. D26 keeps current
project writes on D; this continuation updates the repository handoff only.
Project note: `Projects/kerala-live-map.md`
(current state and next action). Session log: `Claude/Work log.md` (newest first). Facts:
`Claude/Memory.md`. Never write credentials or raw datasets there.

## 12. Starter prompt for the next agent

> You are continuing Monsoon Atlas in `D:\monsoon-atlas` (GitHub Joepikka/monsoon-atlas, branch
> `p1/gate-core`). Read `docs/HANDOFF.md`, `AGENTS.md`, `docs/amendments.md` and
> `docs/decisions.md`. Use `docs/plan.pdf` for task specs. Take the first task in HANDOFF section
> 9, follow the process in section 6, run its acceptance command, commit with the task ID, push,
> and update HANDOFF sections 7 to 9. Do not ask for approval between tasks; stop only for
> human-only steps H01 to H14.
