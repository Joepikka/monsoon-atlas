# Monsoon Atlas: handoff for the next AI agent

Last updated: 9 Nov 2026, T088 S44 crime statistics adapter (P2),
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
- **Owner's rule (9 Nov 2026):** "do not stop or ask me anything ... continue the project till the
  project is fully completed". Work through the plan continuously; a human-only step is recorded
  as blocked (owner list in section 8) and skipped, never done by the agent.

## 2. Source-of-truth documents (all in the repository)

| File | What it is |
|---|---|
| `docs/plan.pdf` | The full plan written by ChatGPT (263 pages, 4 Nov 2026): tasks T001 to T221, model cards M01 to M20, source catalogue S01 onwards, decisions D01 to D16, schemas, leakage rules |
| `docs/amendments.md`, `docs/amendments.yaml` | Amendments v1 plus recorded splits through T267. **They win where they conflict with the plan.** GATE-CORE (A4), human-only steps (A5), P1 order (A8) and child-task dependencies |
| `docs/decisions.md` | Decisions D01 to D114. Every deviation from the plan is recorded here before it is made |
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
| `src/atlas/ingest/s01.py`, `s02.py`, `s03.py`, `s04.py`, `s05.py`, `s06.py`, `s07.py`, `s08.py`, `s10.py`, `s12.py`, `s13.py`, `s14.py`, `s19.py`, `s20.py`, `s21.py`, `s29.py`, `s44.py`, `s09.py`, `s15.py`, `s16.py`, `s17.py`, `s18.py` | Source adapters (T010 to T022, T048 to T088 even; T062, T076, T078, T082, T084, T086 disabled): `fetch(ctx)` with the shared Fetcher, `parse(raw, config, ...)` to the common envelope plus source columns; `schemas/sNN.json` documents the columns |
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
| `src/atlas/rag/`, `configs/rag.yaml`, `docs/ask.md` | T252 Ask corpus (committed project documents only), chunking, local FTS5 index in ignored `data/rag/` and as-of filtered BM25 retrieval; T260 `manifest.py` exports the trusted D1 Ask release (`data/rag/ask-release.sql`) |
| `.github/workflows/feeds.yml` | T251 manual-only hosted checkpoint relay (no schedule, no hosted capture) |
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
| T236 (child of T043) | `0b8fa6a` | One local S09 capture/preparation child under a 150-second parent deadline, without nested launchers. Shared provider admission/backoff stays intact. Retained evidence can be prepared after not-due/deferred/failed collection, preserving actual source validation clocks and partial health. Acceptance: 7 passed in 10.31s; full suite: 545 passed, 1 skipped in 302.34s. Lint/format (162 files), dependency policy, parity and working-diff whitespace pass. A real bounded CLI smoke captured 2 CAPs and prepared a partial result in 7.02s, 0 failed captures and 99 pending documents. The child-kill test preserves completed capture, then recovers preparation with no additional provider call. No weather implementation, upload, scheduling or public release is claimed. |
| T237 (child of T043) | `c848989` | Paired local S01 capture for verified Bengaluru query (12.97,77.59), returned ECMWF grid point (13.0,77.5). Immutable receipts bind metadata-before/forecast/metadata-after artifacts; stable initialization, settling at retrieval, quality-passed future temperature and monotonic model/head checks precede advancement. Shared source-specific pacing/cooldown enforces S01 five-second spacing, five attempts per six-hour admission (20/day cap) and S09 one-second spacing. Both producers stop before network when disabled. Acceptance: 15 passed in 14.13s; joint refresh/weather checks: 24 passed in 21.72s; full suite: 563 passed, 1 skipped in 255.16s. Lint/format (164 files), policy, parity and whitespace pass. Live capture succeeded with 3 actual requests; repeat was not-due with 0 requests. Joint review's two Important findings fixed RED→GREEN: recoverable CAP capture I/O still prepares retained data, and bad previous weather heads cannot lose new completed receipts. Raw capture only, partial single-point coverage; no weather projection, upload or activation. |
| T238 (child of T043) | `4d46546` | Offline partial weather preparation from immutable validated metadata/forecast/metadata receipts. Exact hashes, model/point/settling and cutoff checks precede selection; per-model/run/content cohorts preserve first retrieval and complete-pair availability, while source health uses the latest actual validation. Shared immutable writing retains CAP continuity, byte/quota caps and atomic monotonic/idempotent prepared-only heads. Acceptance: 43 passed in 22.95s; serial combined source/capture checks: 147 passed in 55.89s; full final suite: 606 passed, 1 skipped, 1 existing MLflow warning in 278.69s. Ruff/format (168 files), policy, amendment parity and whitespace pass; actual Worker decode/restore round-trip ran locally. Independent task review: spec PASS, quality APPROVED, no Critical/Important findings. Retained-live no-network smoke produced one real 20.6 degC forecast for 19:00Z at (13,77.5), with original retrieval/completion clocks; same-cutoff replay preserved exact bytes. No upload, approval, activation or statewide coverage. |
| T235 review fixes (D70) | `6ea389c` | Preserve the selected CAP info headline with description/event fallbacks and unchanged normalized schema. Refuse disabled S09 before retained-input reads, including header-only and no-display evidence. Prepared v2 keeps exact v1 history. CAP acceptance 31 passed, actual Worker round-trip passed, full final suite 613 passed with 1 skip and the existing warning. Both Important branch-review findings were addressed in a separate scoped review. |
| T239 (child of T043) | `05ff03f` | The local sender verifies prepared source identity, cutoff, payload and input hashes, then signs exact gzip bytes for an explicit loopback Worker origin. It checks a bounded acknowledgement and preserves preparation on repeat or failure. Acceptance 63 passed in 28.37s. Full rerun 676 passed, 1 skipped and the existing MLflow warning in 745.35s. Lint, format, dependency policy, amendment parity and whitespace passed. Actual PowerShell and Worker-code smoke returned stored then unchanged with equal Worker IDs and unchanged preparation. Task and incremental integration review passed. |
| T240 (child of T043) | `47fee40`, `77b0c16` | The approved normal Karnataka view checks S09 every 15 minutes and S01 every six hours while visible. One bounded request, elapsed deadline and per-source high-water checks preserve honest dates and coverage. Map, list and ticker use the source overlay with dated daily fallback. Place Lens, frozen links and print use the approved daily release. D73 preserves older stored IDs and verifies their normalized GET projection separately. Mounted acceptance 9 passed in 20.6s after review fixes. Full pre-fix browser run 57 passed, final web units 42 passed, Worker 13 passed and build/typechecks passed. Scoped review cleared the legacy compatibility finding. |
| T241 (child of T043) | `2f44faf`, `cdefdb8` | Seal quiescent S09/S01 state and restore verified bytes to the original absent path. The bundle retains raw evidence, prepared history, SQLite admission and cooldown. D75 binds CAP capture clocks to ledger events and preserves valid cross-day revalidation. Acceptance 27 passed in 24.45s, plus 53 S09 regression checks. The real local export matched 27 files by path, size and SHA-256. |
| T242 (child of T043) | `0f1775a` | A signed claim to the explicit loopback Worker precedes one S01 or S09 capture. Wrong or unavailable acknowledgements fail closed. The collector retains its own cadence and cooldown. Acceptance 22 passed in 2.89s, with 139 combined transport, cadence and collector tests. |
| T243 (child of T043) | `9032843`, `7a51610` | A dedicated local store retains immutable checkpoint generations and a SQLite head. Expected-head comparison rejects stale saves. Recovery verifies the current bundle and the original absent root. D78 preserves retained objects after catalogue loss and includes pending SQLite pages in quota checks. Acceptance 13 passed in 5.72s and 79 combined regressions passed. |
| T244 (child of T043) | D79/A27 | `runner-cycle` composes verified restore, one signed capture and expected-head save in a 150-second child. It keeps the working root on refusal or timeout and saves valid local control after handled capture failure. Acceptance 11 passed in 17.78s. |
| T245 (child of T043) | D80/A28 | `runner-cycle --upload-local` prepares successful capture, saves a verified generation and signs its immutable bytes. A lost acknowledgement can retry the same prepared head on `not_due`. Acceptance 14 passed in 20.18s. |
| T246 (child of T043) | D81/A29 | The runner reuses an intact prepared head across cutoffs when inputs and projection match. Actual source checks, expiration and forecast selection can change the output. |
| T247 (child of T043) | D82/A30 | Offer the verified current bundle for artifact transport and import it with an independent digest into a fresh store. The offer checks the configured retained-byte budget. Acceptance 10 passed in 5.57s. |
| T248 (child of T043) | D83/A31 | Read-only `runner-select` verifies explicitly pinned run and artifact metadata and counts the complete bounded repository inventory. Acceptance 34 passed in 0.93s. |
| T249 (child of T043) | D84/A32 | `runner-select --discover` verifies the active run and immediate predecessor by run number. It checks commit ancestry and one checkpoint, and stops on gaps or failures. Acceptance 54 passed in 0.97s. |
| T250 (child of T043) | D85/A33 | `runner-import-zip` binds the raw ZIP to selected size and digest, then extracts only verified manifest members before installing the local catalogue. Acceptance 16 passed in 5.49s. |
| T251 (child of T043) | D86/A34 | Manual-only `.github/workflows/feeds.yml` relays the checkpoint: immediate predecessor or explicit manual bootstrap, pinned raw download by artifact ID, single-file download-directory import, offer and upload. Acceptance 20 passed in 2.00s; 127 related tests passed. No schedule, hosted capture or live dispatch yet. |
| T252 (child of T179) | D87/A35 | English Ask corpus: 30 committed project documents from `configs/rag.yaml`, 292 heading-scoped chunks (300 tokens, 50 overlap, whole table rows) with commit-time `available_at`, licence and hashes; SQLite FTS5 BM25 with as-of/state/language/expiry filters, quoted terms and two chunks per document. Acceptance 9 passed in 7.22s; dev recall 18/20 (misses Q02, Q28 are paraphrases). No embeddings or generation yet. |
| T253 (child of T180) | D88/A36 | Pure Worker answer contract `worker/src/ask.ts`: fixed system prompt, JSON-quoted evidence under 3000 tokens, 100/day, 6/min and 8000-neuron caps, generated JSON kept only with retrieved citations and supported numbers, otherwise cited extractive excerpts. Acceptance 4 passed (Node 5/5, `tsc` clean). No route, AI binding or account. |
| T254 (child of T181) | D89/A37 | 60 English gold cases: plan Q01-Q50 (Q41-Q50 hash-frozen holdout; 35 resolve to support phrases in indexed documents, 15 deferred with reasons) and N01-N10 (S02, S09 and M05 gold recomputed from committed files; 7 require refusal). New `docs/methods.md` corpus page. Scorer fails any invalid citation or wrong/unsupported number. Acceptance 13 passed. Current extractive Ask: correctness 0.80, evidence 0.83, citations 1.00, refusal 1.00; gate not passed (`reports/rag.md`). Translations unreviewed. |
| T255 (child of T180) | D90/A38 | Recognised numeric templates (latest rain, active alerts, model improvement) answered by DuckDB over frozen committed snapshots in `configs/rag.yaml`, independent of the gold code, citing the queried file; fallback shows all five retrieved chunks. Acceptance 30 passed (15 numeric, 13 eval + retrieval). Numeric 10/10; overall correctness 0.87, evidence support 0.83: C3 gate still not passed (paraphrase misses need e5). |
| T256 (child of T225) | D91/A39 | Core case studies in plan section 17 order: `reports/models/m05-case-study.md` (approved hindcast champion), `m07-case-study.md` (blocked at data gate; no model) and `ask-case-study.md` (gate not passed). A test checks the outline order and that every number appears in a cited committed source. Acceptance 6 passed. H14 owner review pending. |
| T257 (child of T046) | D92/A40 | `python -m atlas.models.accuracy` builds C1 (M07), C2 (M05) and M06 accuracy rows from committed records (unavailable, never zero) and writes `docs/releases/ka.md`, the T046/A3 checklist with evidence. Status: not releasable (C1 blocked, C2 model card missing, C3 gate failed, T045/T041/H05/H11 pending). Acceptance 3 passed. |
| T258 (child of T046) | D93/A41 | `reports/models/m05-card.md` fills the plan's M05 card fields with release results and deviations (district units, no temperature feature, hindcast); every number is checked against sources. C2 check now passes; release still not releasable. Acceptance 4 passed. Full suite at T255: 896 passed, 1 load-sensitive failure (`test_killed_child_keeps_completed_checkpoint_and_raw_evidence`, 5 s child deadline) that passes alone. |
| T259 (child of T046) | D94/A42 | `?page=accuracy` web page (F036) loads only an approved, hash-checked accuracy release; blocked models show "Unavailable", never 0; header links to it. Fixture generated from committed records. Acceptance 3 passed; vitest 45 and all 69 browser checks pass (12 new). No release served. |
| T260 (child of T180) | D95/A43 | `POST /api/v1/ask` reads client-chosen chunk IDs (max 5) only from the current trusted D1 release (`ask_chunks`, `ask_current`), rechecks SHA-256, as-of, state and expiry, refuses unknown IDs and client evidence, and returns the cited extractive answer. `python -m atlas.rag.manifest` exports 333 chunks as release `9957c42d…` with a pointer-swap load file. Acceptance 8 passed; Worker node tests 22 passed; real workerd/D1 runtime check passed locally. Generation, quota counters and the remote D1 load wait for H05. |
| T261 (child of T182) | D96/A44 | `?page=ask` English text Ask page: loads the hash-checked public corpus (`/data/ask/latest.json` names `<release>.json`, bytes hash to the release ID), BM25 search in the browser (`web/src/ask-search.ts`, dev recall 90%), sends the top five chunk IDs to `/api/v1/ask`, shows the matching Worker answer or labelled local results, with citation cards (path, commit time, evidence age). Header link "Ask". Acceptance 5 passed; 12 new browser checks. No corpus published (H05). Voice and other languages stay outside the MVP. |
| T262 (child of T103) | D97/A45 | M05 80% interval recalibration with the rule fixed before any run: out-of-sample ridge residuals from rolling origins 2000/2005/2010/2015, six rules ranked on 2010-2019 only; "last 5 years, by season" (80.3% there). One check on 2020-2024: coverage 0.728 (monsoon 0.643), below the 75-85% gate, so intervals stay hidden. Point forecasts unchanged. Record `models/registry/M05/v1.intervals.json`, report `reports/models/m05-intervals.md`. Acceptance 4 passed. The test years are now used twice for intervals; any further interval rule needs untouched data (IMD 2025 or later). |
| T263 (child of T103) | D98/A46 | M05 2025 monitoring check, rules fixed before scoring. IMD 2025 file re-fetched 8 Nov: identical to 5 Nov (b4fa5ffb...), never used by M05, finality not stated (provisional). 1981-2024 rows still hash to the v1 dataset. On 360 district-months: ridge MAE 0.625 vs persistence 0.744 (ratio 0.841), improvement 0.119 [0.019, 0.226] over 12 months: flag **holds**. 80% intervals (D97 rule, champion 2020-2024 residuals) covered 0.869: too wide that year; still hidden. Record `models/registry/M05/v1.monitor-2025.json`, report `reports/models/m05-2025.md`, card row added. Acceptance 3 passed. |
| T264 (child of T179) | D99/A47 | Owner approved the full dl lock (torch 2.15.0 CPU, transformers 5.22.1, sentence-transformers 6.2.0; installed in `.venv`) and `intfloat/multilingual-e5-small` rev 614241f6 (MIT; `model.safetensors`, `tokenizer.json` hash-checked) in ignored `data/models/e5/614241f6/`. `atlas.rag.embed` + R0-R3 methods in `retrieve.py`; `evaluate --select` ranks them on dev only. All reach 0.852 dev evidence support; R0 BM25 has best dev recall (0.85 vs 0.80), so R0 stays (`rerank_method: R0`). C3 report once: evidence support 0.86 (30/35), gate fails on Q02, Q23, Q26, Q33, Q43. Three of those retrieve the right document but the wrong section. Acceptance 4 passed. |
| T265 (child of T179) | D100/A48 | Limit the two append-only logs (`project/decisions`, `project/amendments`, 154 of 333 chunks) in Ask results. Rules fixed first: L0 as before, L1 one result per log, L2 also halves their BM25. Dev only: L0 and L1 tie (0.852 support, 0.85 recall), L2 0.80 recall, so L0 stays (`log_rule: L0`, `log_documents` in `configs/rag.yaml`). C3 report once: same as T264 (0.86; Q02, Q23, Q26, Q33, Q43). Known ceiling: section fixes alone max 33/35 = 0.943 < 0.95. Acceptance 4 passed. |
| T266 (child of T046) | D101/A49 | Owner approved ("Yes, record it"): C3 Ask is research-only under A3 (evidence support 0.86 < 0.95; T264 and T265 gave no gain). Checklist shows the C3 check as `research-only` (never `pass`); the Ask page shows a research-only note; the Ask case study's deployment decision says so. Owner decides at H11 whether research-only C3 meets T046 extra check (2). Review fix 848c3d5: L2 halves log scores in SQL before the top-50 cut. Acceptance 18 passed. |
| T267 (child of T130) | D103/A50 | Owner approved downloading KSEB's 18 dam O&M manuals (about 101 MB, kseb.in, robots allows all) as S32 evidence e81-e98 in ignored `data/raw/S32/`. Stated datum (above MSL) only for the Idukki reservoir (e81 p223, Survey of India benchmarks), Sengulam (e83), Kakki-Anathode (e96), Pamba (e97); 13 manuals give elevations with no named datum. 4 < 8 dams, so T130's datum gate is not met. Table in `docs/labels/kerala.md`; S32 units claim updated. Also D102: owner-delegated agent review of the S34 OCR sample. Acceptance 3 passed. |
| D104/D105 | owner | C1 deferred to the owner at the end of the project (no KSEB email); P2 starts locally while T046 stays open. T223/T224 deferred to the end of P2 (their data is blocked; IMD-derived values wait for H11 item 3). |
| T047 | D105 | S03 Open-Meteo GloFAS river discharge: available, no key, CC BY 4.0 (free API non-commercial). Simulated m³/s; sea point and 1984-1996 at the Cauvery cell stay null; values from 2 Jan 1997 with no gaps; GloFAS licence link 404 recorded. Acceptance 6 passed. |
| T048 | D105 | S03 adapter `src/atlas/ingest/s03.py`: named `models=seamless_v4` (same values as default; unknown name HTTP 400), IST days, nulls kept with reasons, negatives rejected, provenance model; real CC BY 4.0 fixtures; S03 enabled. Acceptance 11 passed. |
| T049 | D105 | S04 Open-Meteo CAMS air quality: available, no key, CC BY 4.0 (free API non-commercial). Hourly CAMS global PM2.5/PM10/NO2 in μg/m³ at 0.4°; issue time from `data/cams_global/static/meta.json` (stable before/after); Bengaluru history from 4 Aug 2022, no gaps, no negatives; `cams_europe` HTTP 400 for Karnataka and the Copernicus licence link 404 recorded. Acceptance 7 passed. |
| T050 | D105 | S04 adapter `src/atlas/ingest/s04.py`: named `domains=cams_global`, metadata read around the call (run change rejects), valid times UTC, `data_end_time` exclusive (later hours null, out_of_coverage), negatives rejected, provenance model, product cams_global; real CC BY 4.0 fixtures; S04 enabled every 6 hours. Acceptance 12 passed; full suite 974 passed (13 min). |
| T051 | D105 | S05 Open-Meteo ensemble: available, no key, CC BY 4.0 (free API non-commercial). Member counts read per product at Bengaluru (IFS 0.25 51, GEFS 0.25 31, ICON-EPS 40, GEM 21). IFS metadata run time covers only hours before `data_end_time` (later hours match an earlier run); six member rain values -0.1 mm; API keeps ~4.5 days of past values (old start_date HTTP 400). Acceptance 7 passed; tests/sources 423 passed. |
| T052 | D105 | S05 adapter `src/atlas/ingest/s05.py`: named `models=ecmwf_ifs025_ensemble`, metadata read around the call, one row per cell/hour/member with the member set read from each response; hours before the run or at/after its exclusive `data_end_time` stay all-null with null `issued_at` (flags missing, stale); negative rain rejected; real CC BY 4.0 fixtures; S05 enabled daily. Acceptance 14 passed; full suite 995 passed. |
| T053 | D105 | S06 Open-Meteo climate projections: available, no key, CC BY 4.0 (Open-Meteo and CMIP6). 7 HighResMIP models, daily 1 Jan 1950 to 31 Dec 2050 at Bengaluru (EC_Earth3P_HR ends 2049; 2051 HTTP 400). No scenario parameter (docs: "as close to RCP8.5 as possible"), so scenario null; default bias-corrected onto ERA5-Land, raw differs; long ranges count as many calls. Acceptance 7 passed; tests/sources 444 passed. |
| T054 | D105 | S06 adapter `src/atlas/ingest/s06.py`: chosen HighResMIP models within 1950-2050 (unknown model/date refused before any request), one row per cell/GMT day/model, `scenario` always null, `bias_corrected` flag (default ERA5-Land or raw), no issue time, missing model-days null, negative rain rejected, response must hold exactly the requested models; one request per fetch (callers split weighted long ranges); real CC BY 4.0 fixtures; S06 enabled. Acceptance 14 passed; full suite 1016 passed. |
| T055 | D106 | S07 NASA POWER daily point: available, no key; AWS registry (linked from POWER) says no use restrictions, CC BY 4.0, cite POWER. robots.txt disallows /api/ but docs invite scripted use: D106 applies D31. Fill -999 (8 Nov 2026; shortwave before 1984 and after 31 Aug 2026); shortwave MJ/m^2/day with AG, kW-hr/m^2/day with RE; header names products per request; meteorology MERRA2 to GEOSIT between 1 and 8 Oct 2026. Acceptance 8 passed; tests/sources 466 passed. |
| T056 | D106, D107 | S07 adapter `src/atlas/ingest/s07.py`: PRECTOTCORR, T2M, ALLSKY_SFC_SW_DWN per point, community=AG, UTC days, 3 s between calls; fetch splits ranges until each response names one meteorology and one solar product; parse refuses mixed/unknown products, other units, non-UTC; -999 to null with reasons; own `solar_missing_reason` so solar lag keeps rain and temperature; products and API version per row; real fixtures; S07 enabled. Acceptance 16 passed; full suite 1040 passed. |
| T059 | D105 | S10 adsb.lol live aircraft: available, no key, ODbL 1.0; terms: free, key by feeding may be required later, contact for production. /v2/point radius <= 250 nm. Units from linked readsb reference (ft, kt, s); API `now` is milliseconds (checked against fetch time). Live only (daily archive on GitHub not used). Rules for T060: hide positions older than 300 s, no prediction, no owner enrichment, drop LADD/PIA (dbFlags). Acceptance 7 passed; tests/sources 489 passed. |
| T060 | D108 | S10 adapter `src/atlas/ingest/s10.py`: /v2/point route, `now` checked as ms near fetch time; one row per aircraft (hex, now - seen_pos or lastPosition, lat/lon, ft to m, kt to m/s, on_ground, position_type); provenance inferred; drops positions >300 s old at fetch, position-less and LADD/PIA aircraft; never stores callsign/registration/type; fixture is real e10 with flight/r/t removed; S10 enabled. Acceptance 13 passed; full suite 1060 passed. |
| T061 | A5 | S11 OpenSky: **blocked**. OpenSky's API repo says using the API means agreeing to its terms; terms page, home page and robots.txt return 403 to the scripted client (no user-agent change or other route). Owner step: read https://opensky-network.org/about/terms-of-use and decide. Docs record research/non-commercial use, citation of the OpenSky paper, anonymous 400 credits/day, units. One anonymous probe returned 200 before the clause was read (body not stored). Acceptance 6 passed; tests/sources 508 passed. |
| T062 | A5 | S11 disabled contract `src/atlas/ingest/s11.py`: fetch and parse raise SourceUnavailable before any I/O even if force-enabled; `schemas/s11.json` has no fields. Acceptance 3 passed; tests/sources 511 passed. |
| T063 | D109 | S12 CelesTrak: available, no key, licence **restricted** (none published). robots.txt disallows gp*.php but the usage policy addresses M2M software: D109 applies D31; once per 2-hour update; stop on any non-200. TLE checksums/epochs pass, but TLE lacks 6-digit catalog numbers (stations: 19 OMM vs 15 TLE; crewed Soyuz/Dragon missing), so OMM JSON. Acceptance 7 passed. |
| T064 | D109 | S12 adapter `src/atlas/ingest/s12.py`: OMM JSON per GROUP, one row per object (norad_id, epoch_at, name, mean elements; tle lines null), stale flag after 7 days, provenance official, redistribution false. Fetcher gains opt-in `retry_delays=()`; adapter refuses a retrying Fetcher. Raw sample is local only (tests skip in CI). S12 enabled. Acceptance 12 passed; full suite 1089 passed. |
| T065 | D105 | S13 NASA GIBS: available, no key, NASA open data (cite). NOAA-20 VIIRS true colour from 2018 in five ranges with gaps; Suomi NPP stopped 2 Nov 2026. Capabilities default (today) tile over Bengaluru is all black before the pass; 8 Nov shows imagery with cloud; gap date 404. Acceptance 7 passed. |
| T066 | D105 | S13 adapter `src/atlas/ingest/s13.py`: capabilities, then probe state tile for up to 3 newest listed dates until not blank; one row (layer_id, imagery_date, tile_template, bounds, crs); fixtures: NOAA-20 layer block + two real tiles; pillow needed (tests skip in CI). S13 enabled. Acceptance 9 passed. |
| T067 | D105 | S14 AWS Terrarium: available, no key, attribution required (India from USGS SRTM/GMTED2010 and NOAA ETOPO1, public domain). Formula decodes Bengaluru z10 to 767-960 m, Arabian Sea z8 to -2,488 m (bathymetry). Two GitHub 504s recorded. Acceptance 6 passed. |
| T068 | D105 | S14 adapter `src/atlas/ingest/s14.py`: on-demand tiles, decode every pixel, reject non-256x256-RGB or outside -11000..8900 m, one metadata row per tile (key, z/x/y, encoding, crs, min_m, max_m); two real tiles committed; pillow needed (skip in CI). S14 enabled. Acceptance 7 passed; full suite 1118 passed. |
| T069 | D105 | S19 Open Buildings v3: available, dual CC BY 4.0/ODbL (CC BY used). Karnataka in S2 cell 3bb, 4,834 MB gzipped; discovery read cell 3b3 (3.9 MB): six columns, confidence 0.65-0.97, no repeated plus codes, no owner/address/use data. Acceptance 7 passed. |
| T070 | D105 | S19 adapter `src/atlas/ingest/s19.py`: shard URLs from the index; new `Fetcher.fetch_large` + `RawStore.put_stream` stream large files to disk; `parse_batches` clips by box, dedupes plus codes, WKT to WKB, bounded tables. Fixture: first 300 real rows of 3b3. State run (4.8 GB) left to F020/T105. S19 enabled. Acceptance 11 passed. |
| T071 | D110 | S20 USGS: FDSN query + GeoJSON feeds, no key. No starttime = last 30 days only. South India box since 1959: 95 reviewed events (28 Karnataka), 16 without magnitude. Feed: automatic vs reviewed, merged ids. www.usgs.gov licence pages return 202 to scripts, browser unavailable: licence **restricted** until read (H11). Acceptance 6 passed. |
| T072 | D110 | S20 adapter `src/atlas/ingest/s20.py`: day feed hourly or dated query; rows per earthquake in box (event_id, origin_at, lat, lon, depth_km, magnitude, mag_type, review_status, updated_at); record_id = id+updated; null magnitude not_reported; other types/deleted dropped; redistribution false; tests read local raw (skip in CI). S20 enabled. Acceptance 14 passed; full suite 1154 passed (2 Ask tests needed decisions.md committed; rerun 69 passed). |
| T073 | D111 | S21 Datameet railways: CC0 (README), last change 8 Aug 2016, commit e0c538a1 pinned. 8,990 stations (301 Karnataka, 293 no geometry), 5,208 trains, 417,080 stops; "None" first arrivals/last departures; no stop sequence (file order; ids rise for 5,199 trains). schedules.json 82 MB streamed. Acceptance 5 passed. |
| T074 | D111 | S21 adapter `src/atlas/ingest/s21.py`: pinned-commit stations + streamed schedules; stops at state stations (station_id, train_id, stop_sequence, arrival/departure text, journey_day, lat/lon); None to null; imputed flag when ids disagree; provenance reconstructed; real CC0 subset fixtures. S21 enabled. Acceptance 12 passed. |
| T075 | A5 | S25 NASA FIRMS: **blocked** on owner step H09 (MAP_KEY). Data open (NASA full and open sharing; acknowledge FIRMS/LANCE/ESDIS), within 3 hours; download pages are script shells and robots closes /dist/; browser pane unavailable. VIIRS units recorded. Acceptance 6 passed. |
| T076 | A5 | S25 disabled contract `src/atlas/ingest/s25.py` (no I/O even if force-enabled; empty schema). Acceptance 3 passed. |
| T077 | D112 | S27 KSNDMC: **blocked**. HTTPS refused (ksndmc.org), www name unresolved, Varunamitra unreachable. Over plain HTTP (read once under D112) only an ASP.NET template with three undocumented TRG endpoints (no station list, units, licence). Acceptance 5 passed. |
| T078 | D112 | S27 disabled contract `src/atlas/ingest/s27.py`. Acceptance 3 passed. |
| T079 | D113 | S29 OpenCity KSNDMC: available, "Other (Public Domain)", crawl delay 10 s. **Annual only**: district/taluk/hobli CSVs 2020-2025 (layouts differ; 2025 lacks the D/T/H marker) and 2023 station totals (5,266); no daily series, so D113. Acceptance 6 passed. |
| T080 | D113 | S29 adapter `src/atlas/ingest/s29.py`: per-layout parse (2020 annual columns, 2021/2022/2024, 2023 stations); rows by level and name path with rain/normal/departure; coverage null; duplicates flagged; 2025 refused. Real public-domain subsets. S29 enabled. Acceptance 9 passed; full suite 1205 passed. |
| T081 | A5 | S31 Karnataka RERA: **blocked**. Public list, no CAPTCHA, 10,106 applications (9,065 registered) embedded in page script with project and promoter names (individuals included); copyright policy: reproduction only after emailed permission (owner). No location/status in the list. Acceptance 6 passed. |
| T082 | A5 | S31 disabled contract `src/atlas/ingest/s31.py`. Acceptance 3 passed. |
| T083 | A5 | S39 Telegram Bot API: **blocked** on owner step H08 (bot token, public channel, developer terms). Limits and retry_after recorded. Acceptance 5 passed. |
| T084 | A5 | S39 disabled contract. Acceptance 3 passed. |
| T086 | A5 | S43 disabled contract `src/atlas/ingest/s43.py` (T085 blocked earlier). Acceptance 3 passed. |
| T087 | D114 | S44 crime statistics: OpenCity republishes KSP annual tables 2022-2025, "Other (Public Domain)": counts per police unit (no names/locations); units are not districts (commissionerates split, range rows are empty headings, railways/coastal/CID no area); IPC to BNS from July 2024. Acceptance 6 passed; range text corrected in 7266f6e. |
| T088 | D114 | S44 adapter `src/atlas/ingest/s44.py`: 2024 offence heads and 2023 IPC/SLL/total; one count per published unit and column with unit_kind; headings skipped; blanks null; no crosswalk guessed. Real public-domain tables. S44 enabled. Acceptance 7 passed. |
| T089-T091 | `b866b27`, `4dd5bff`, `24fee33` | M01 Bengaluru ward flood occurrence: **blocked** (S43 has no dated ward-level inundation records or audited negatives). Shared helper `src/atlas/models/blocked.py` (M06 pattern): data gate with evidence hashes, no-model manifest, status record. Plan fallback `atlas.features.m01.exposure_index`: S01 forecast rain over the next 24 h per ward cell, labelled "not a flood probability", null unless all 24 hours exist. Report `reports/models/m01.md`. |
| T092-T094 | `f8668aa`, `35baa67`, `7b90eea` | M02 Karnataka reservoir level: **blocked** (S28 KWRIS has no verified daily history); 2028 prospective splits kept in `configs/models/m02.yaml`. |
| T095-T097 | `7ed227d`, `a1b1f16`, `637c7cd` | M03 reservoir inflow: **blocked** (no reported daily inflow; never inferred from levels). |
| T098-T100 | `26c8092`, `9d04a25`, `3d3c0ef` | M04 rain-gauge gap filling: **blocked** (S27 blocked; S29 annual totals only). Model tests 45 passed; full suite 1280 passed in 638.55s, ruff clean. |
| T028 | `6f955cd` (D115) | S30 GTFS: neither BMTC nor BMRCL publishes GTFS (Mobility Database, OpenCity, BMRCL site); uses Vonter's unofficial ODbL feeds pinned at ee945dc (BMTC) and f402c4c (BMRCL); licence restricted, raw local only. Acceptance 8 passed. |
| T029 | `582947a` | S30 adapter: stop times for one local service date (calendar + calendar_dates), seconds from noon minus 12 h never wrapped, BMRCL timepoint 0 flagged imputed; `dedupe_snapshots` fast path for large tables. S30 enabled. Acceptance 16 passed. |
| T104 | `835b6ed` (D116) | `atlas.transit.schedule`: service day D and D-1 for 24:00+ trips, shape-only interpolation between consecutive stops, pauses on gaps/missing shapes, labelled scheduled-not-live; S21 historical reference only. `web/src/map/ScheduledTransit.tsx` built, not mounted until H11. Acceptance 9 passed. |
| T105 | `d775c51` (D117) | `atlas.spatial.context` + `web/src/map/ContextLayers.tsx`: FIRMS/RERA disabled with retry reasons; hotspot = thermal anomaly only; RERA public fields only; S19 clipped to a versioned boundary; crime district-year totals listed, not mapped. Acceptance 7 passed. |
| T106 | `ec74182`, `721e945` (D118) | Feed-quality notebook `notebooks/01_ka_quality.ipynb`: S08 KA box complete 1981-2025, S10 lag ECDF, S01 run lag; prices and one-day feeds stated as limits. Byte-identical re-run. Acceptance 3 passed. |
| T107 | `da9dadf` (D119) | Rainfall notebook: annual district gauge (S29) vs grid (S08) 2020-2024 via committed crosswalk; 117 of 123 district-years compared (Ballari/Vijayanagara 2021+ excluded); median grid-to-gauge ratio 1.04 (grid wetter in 65% of compared district-years). Acceptance 5 passed. (Sonnet subagent) |
| T108 | `581cdb5` (D120) | Price notebook is a unit and availability audit: S22/S23 blocked, zero rows, measures n = 0 "not computable". Acceptance 9 passed. (Sonnet subagent) |
| T109 | `9df5092` (D121) | Spatial statistics on M05 ridge residuals: queen adjacency (66 borders), Moran's I 0.09-0.84, 57 of 60 test months significant after BH; training-only variogram 2000-2019. M04 blocked: no comparison. Acceptance 10 passed. (Opus subagent) |
| T110 | `732113d` (D122) | Karnataka v1 gate `docs/releases/ka-v1.md`: 33 KA sources (23 enabled, 10 blocked), M05 approved, M01-M04/M06 blocked, 9 v1 layers (1 measured, 5 blocked, 3 built not mounted); 8 shared interface files hash-frozen (LF bytes). Kerala work may begin; public release (T046) still waits for H11. Acceptance 9 passed. (Sonnet subagent) |
| T111/T112 | `af349f7`, `9d36872` | S26 aisstream ships: **blocked** on owner step H12 (key); disabled contract |
| T120 | `36d6ee5` | S35 Kaggle Kerala floods: disabled contract (H10) |
| T122 | `8d0775e` (D123) | S36 KSDMA assessment adapter enabled in KL: three district tables only, document and page kept; raw PDFs local. Needs pypdf (ocr lock) |
| T123/T124 | `28e95f7`, `d2c3002` | S37 landslide inventory: **blocked** (state-level counts only, no points or dates); disabled contract |
| T125/T126 | `8960e04`, `b066bcb` | S41 news RSS: **blocked** (no publisher permission); disabled contract |
| T127/T128 | `4c9286c`, `ee08b81` | S42 Sentinel-1 / NDVI: **blocked** (Copernicus account, proposed owner step H15); disabled contract |
| T129 | `b25a3c7` (D124) | Kerala configuration and label audit, run with T046 and T118 pending |
| T130-T141 | `0196599` to `89dfbbf` (D125, D126) | M07, M08, M09 and M10 recorded as blocked branches: data gate, no-model fit and notebook, published status and report. No baseline, score or prediction for any of them |
| T142 | `8604abd` (D127) | Kerala event study, climate and 2018 replay on what exists: 157 replay records (35 as-known from S36, 122 reconstructed from S08), 0 forecast vintages; price study not computable |
| T143 | `9b49715` (D128) | Population exposure and route comparison code, tested on hand-built graphs; returns unavailable without roads (S18), shelters (S43) or hazard polygons |
| T144 | `5720f3f` (D129) | Kerala release gate `docs/releases/kl.md`: 4 of 19 KL sources enabled, 7 blocked; M07-M10 all blocked; S08 box-mean files in `reports/eda/` need an H11 ruling before any release. Not a public release |
| T145 | `1d4804c` (D130) | Monsoon and climate product layers on S08 1981-2025 and S06; NDVI and official onset unavailable |
| T224 | `6af2690` (D131) | SQL insights report: ten questions the held data can answer (`reports/sql_insights.md`) |
| T223 | `15e7f3d` (D132) | Power BI report generated as PBIP (`powerbi/MonsoonAtlas.pbip`), four pages, two blocked notes; untested in Power BI Desktop; PNG/PDF exports are an owner step |
| CI fix | `50b7329` | `ci` failed at collection on `6af2690` and `15e7f3d`: four test modules imported shapely, scipy or pypdf, which CI does not install. They now use `pytest.importorskip` (D35) |
| CI fix 2 | `78a989d` | Two failures hidden behind the collection error: `test_pbip` read `powerbi/__pycache__/*.pyc` as UTF-8; the price notebook test needs matplotlib (geo/ml lock) |
| T146 | `85bf52b` (D133) | S24 CPCB stations via data.gov.in: **blocked**. Plain HTTP gets 403 on the resource page; the Browser pane loads it but its read tools returned "Policy check temporarily unavailable" (retried 10 Nov, same). Resource ID, licence, fields, units, averaging interval and history are all unread. A resource ID seen in a third-party tutorial was not used. The S23 key works on the API host (e01). Acceptance 5 passed. (Sonnet subagent) |
| T147 | `9c3e83e` (D134) | S24 disabled adapter: raises `SourceUnavailable` before I/O; schema lists no fields; no Delhi state config yet (T150). Acceptance 3 passed |
| T148 | `6b021c7` (D135) | S38 Delhi Open Transit Data: **blocked on owner step H04**. Static GTFS downloads are POST forms (usage, purpose, name, email, Terms tick); real time is `VehiclePositions.pb` with a private key (no key: 401); no TripUpdates path published. Terms give no open licence (restricted). Static counts published: bus 543 routes (20 Jun 2024), DMRC 36 routes (10 Aug 2023). Docs call static stop times a constant-speed estimate. Acceptance 5 passed. (Sonnet subagent) |
| T149 | `2922ab1` (D136) | S38 disabled adapter; schema lists no fields; secret name `OTD_API_KEY`. Acceptance 3 passed |
| T150 | `31e3dee` (D137) | `configs/states/dl.yaml` (isolated, every source disabled) and `docs/studies/delhi.md`: no access approval, no schema read, no routes selected, no dates frozen; study cannot start. Protobuf decoder and protobufjs deferred until H04 (no sample to test). Acceptance 5 passed. (Sonnet subagent) |
| T151 | `e839147` (D138) | `worker/src/transit.ts`: poll budget 960/day, position aged >= 120 s never live, state "transit live mode unavailable". No cron, upstream call or key binding; nothing imports the module. Acceptance 5 passed; Worker tests 25 of 25 |
| T152 | `fdba7b9` (D139) | `docs/studies/delhi-readiness.md`: gate failed (not run); no measurement claimed; continuous capture unavailable; quota arithmetic checked against `configs/budgets.yaml`. Acceptance 4 passed |
| T153-T164 | `cd4f997` to `48ed322` (D140, D141) | M12 (bus arrival/delay) and M13 (bunching) blocked by S38; M14 (station PM2.5) blocked by S24 (S04 CAMS is a baseline input, never a label); M15 (heat outlook) blocked: no Delhi source enabled and no S01 forecast vintages held, so calibration skill cannot be claimed. Each has a data gate, no-model fit and notebook, registry record (all scores null, 0 rows) and report. Per model: 5, 3 and 3 acceptance tests passed. (Sonnet subagent) |
| T165 | `262040f` (D142) | Delhi interface, built and not mounted: `Transit.tsx` (scheduled/live/predicted distinct; position aged >= 120 s hidden), `AirQuality.tsx` (station and CAMS layers separate), shared `ScoreCard.tsx`, `src/atlas/analysis/route_exposure.py` (time-weighted ambient concentration only; refuses mixed units, averaging or provenance). Rules tested on hand-built inputs. Real Delhi transit, station, CAMS comparison and route exposure are all unavailable. Notebooks 08/09 audit the blocked sources and draw no chart. Acceptance 27 passed; web tests 73 passed. (Sonnet subagent) |
| T166 | `dc82187` (D143) | Delhi release gate `docs/releases/dl.md`: 0 of 8 Delhi sources enabled (S24, S38 blocked); M12-M15 blocked; label windows planned, not started; nothing published or exported; KA and KL gates and the 8 frozen hashes still hold. Acceptance 9 passed |
| T167-T178 | `9281ae3` to `8d8490a` (D144, D145) | P5 model chains, all blocked: M19 GRU reservoir challenger (M02/S28 blocked, no free GPU session), M11 Karnataka-to-Kerala flood transfer (M01 and M08 blocked), M17 Sentinel-1 U-Net (S42 needs H15; no inundation masks), M20 rain what-if explorer (card needs an approved M01 or M08 flood score; M05 is a drought model, so no explorer was built under this ID). No scores, weights or predictions. Per chain 5 (4 for M17), 3 and 3 acceptance tests passed. (Sonnet subagent) |
| T179-T181 (P5 remainder) | `1434432`, `3c53a28` (D146, D147) | Plan-coverage table in `docs/ask.md`: English scope was already done by T252-T266; caps already in `worker/src/ask.ts` (no `quota.ts` added); Workers AI generation and live usage counters blocked on H05; e5 embeddings tested, not adopted. Added `eval/rag/translations.jsonl`: 150 kn/ml/hi question drafts, all `machine_draft_unreviewed`, unscored; report shows non-English as not validated, generation disabled. **Finding: the 8 Nov English scores in `reports/rag.md` do not reproduce.** A re-run on 11 Nov (408 chunks against 348; the indexed logs grew) gives correctness 0.84 and evidence support 0.80, failing Q02, Q12, Q23, Q26, Q33, Q43, Q45. The report keeps the dated 8 Nov numbers; C3 stays research-only either way. Ask tests 56 passed. (Sonnet subagent) |
| T182 | `d05b2ad` (D148) | Ask page strings go through `web/src/i18n` (`t()` throws on a missing key); `en.json` reviewed, `kn`/`ml`/`hi` machine drafts unreviewed, only English selectable (A7). Citation paths link to the file on GitHub `main`. Opt-in voice input and read-aloud (`web/src/voice.ts`), never started before a button press. Existing page extended; no `components/Ask.tsx`. Acceptance 9 passed; web tests 84 passed. (Sonnet subagent) |
| T183 | `eb51db9` (D149) | `Watches.tsx` (IndexedDB only, built, not mounted), `src/atlas/alerts/brief.py` (deterministic brief from S09 after `supersede()`, dedupe, expiry, source links; 30-minute on-time grace is an agent choice), `telegram.py` (formatter; send raises `SourceUnavailable`, S39/H08). Acceptance 11 passed |
| T184 | `66e6202` (D150) | Web push disabled by the no-personal-data rule: `docs/decisions/web-push.md`, detection in `web/src/push.ts`, Worker route refuses every registration with 403. No feature catalogue file exists; "conditional stretch" recorded in the decision. Acceptance 5 passed; Worker tests 27 passed |
| T185 | `a16f6e0` (D151) | `src/atlas/spatial/tiles.py`: licence gate (only S19 may enter a tile build), shard planning under 20 MiB, GeoJSON as the default delivery; manual-only `tiles.yml` that takes the Tippecanoe commit SHA as a required input (not verified, not dispatched). Not run: Tippecanoe, tile sampling, Range 206/CORS (no host). Acceptance 8 passed, 1 explicit skip. (Sonnet subagent) |
| T186 | `22a84eb` (D152) | `web/src/map/Terrain.tsx`, `Globe.tsx`: S14 terrain (exaggeration 1), S13 imagery only with a real date, WebGL/low-memory/reduced-motion fallbacks. Built, not mounted; strings still English literals. Acceptance 6 passed, 1 skip |
| T187 | `bcd6f38` (D153) | `orbits.py`, `Movement.tsx`: only S10 aircraft available (stale > 300 s hidden); satellites unavailable because `sgp4` is in no lock (no propagator written); S20 waits for H11; ships blocked (H12); one poll gate per layer and region. Acceptance 8 passed, 1 skip |
| T188 | `60be31c` (D154) | `WallMode.tsx`: timestamps, source health, existing pausable ticker, Escape exit, stale never styled current; 17 `wall.*` keys in four locales. Built, not mounted. Acceptance 5 passed; web tests 108 passed |
| T189-T208 | `48043e5` (D155) | Twenty news annotation batches recorded as blocked in one record, `eval/news/blocked.json` (S41 no publisher permission; owner step H13): 0 of 1000 articles selected, labelled or reviewed. No per-batch files were created (an empty batch file would look complete). Tests 24 passed. (Sonnet subagent) |
| T209-T211 | `179ae49`, `af5aa67`, `46caaa3` (D156) | M18 news event extraction blocked (S41, H13); registry all null, 0 rows. Tests 11 passed |
| T214-T216, T212-T213 | `42297ff`, `cbbffd0`, `694e733`, `0b11913` (D157-D160) | M16 anomaly rule built (`src/atlas/features/m16.py`: robust z on the 28 days before the report, as-of mutation-tested; MAD 0 gives no z) and run on the held S08 daily grids 1981-2025; counts only in `reports/models/m16-flag-counts.json` (no rainfall value, cell or date). Finding: 18.8% of evaluated Karnataka cell-days flag and 75% of cell-days have no z, so the rule as specified is poorly suited to daily rain. Status `research_only`: precision not measured, 0 of 100 flags adjudicated (`eval/anomalies/blocked.json`; the agent does not label its own detector's flags). IsolationForest not run. Tests 20 + 30 passed. (Sonnet subagent) |
| T217 | `3135bef` (D161) | `dashboard_data()` in `src/atlas/models/accuracy.py` writes `web/src/dashboards.json` (byte-checked against the registry and the three gate pages). New pages `?page=quality`, `analysis`, `compare`; Accuracy gains an all-models section. Only M05 shows numbers (MAE 0.732 vs 0.808, improvement 0.076, 95% CI 0.003 to 0.150, hindcast); 19 models show status and reason only. No state ranking; every metric comparison "unavailable". Acceptance 10 passed. Pages checked in a browser on 11 Nov; fix: healthy sources now show "None needed" under retry condition. (Sonnet subagent) |
| T218 | `77be4fe` (D162) | `manifest.webmanifest`; `sw.ts` as an **unregistered** cache plan (allowlist, 20 MB, timestamps, offline banner); read-only `?page=widget`; licence-gated exports in `src/atlas/export.py` and `web/src/export.ts` (S08, S30, S34 refused; 10,000 rows or 10 MiB shards), sharing one licence rule with tiles. Deferred to deploy: service worker registration, offline spec, `frame-ancestors` header, widget path. Acceptance 7 passed |
| T219 | `06b70ea` (D163) | `src/atlas/monitoring.py` (feed age, missingness, schema, PSI two windows, MAE vs 1.2 x M05 frozen baseline, storage via D24 code; stale feed stops dependent models), manual-only `monitor.yml` (not dispatched), `docs/runbooks/rollback.md`, rollback drill on a temp store. Agent-chosen constants: stale after two cadences, missingness alert above 10%. Gate tests now allow the one tracked file `web/public/manifest.webmanifest`. Acceptance 15 passed |
| CI fix 3 | see log | `ci` failed on `9c87a02`: `web/src/dashboards.json` carried the S38 retry text, which names `OTD_API_KEY`, `VehiclePositions` and the OTD host, so two `tests/test_dl_poll.py` guards failed (they were not in the T217 check set). The builder now ships no retry text for account-gated sources, only an `owner_step` flag; the Quality page shows "Owner account step; see the source record" |
| T220 | `fdc1e97` (D164) | Portfolio pack: README rewritten to the true state (1 measured model, 1 research-only, 18 blocked; 44 source records; nothing deployed), model index from `dashboards.json`, failed-model lessons, licence table; `docs/case-studies/template.md`, `docs/portfolio/video.md` (script only, **not recorded: owner step**), `docs/portfolio/resume.md` (measured lines with sources; plan placeholders marked not usable), `docs/glossary.md`. `tests/test_portfolio.py` recomputes every number and scans for forbidden claims. Acceptance 44 passed. Ask drift again: the README is in the Ask corpus; a scratch re-run after this commit gives correctness 0.82, evidence support 0.77 (not recorded elsewhere). (Sonnet subagent) |
| T221 | `2bbb98f` (D165) | Final acceptance `docs/releases/final.md` with `final-features.json` (64 plan features: 12 shipped-local, 20 built not mounted, 4 research-only, 27 blocked, 1 deferred; blocked MVP features F021, F025, F033), the plan's 20 sections mapped to files, manual keyboard/screen-reader checks listed as **not performed: owner step**, cost evidence, owner task list, and `final-manifest.json` (88 hashed files). `docs/runbooks/maintain.md`. Acceptance 14 passed; two mutation checks failed the test as intended. Findings recorded, not fixed: `ka-v1.md` line 114 misplaces F035 and no task produces SHAP values; HANDOFF wrongly said `EventTicker` is unmounted (corrected here); D161's title says the dashboards are not mounted although `?page=` routes reach them locally. Opus 5.5 high subagent |
| H11 (owner review) | `ddc2d4d` to `706f345` (D166-D170) | Owner answered all nine H11 items in chat on 11 Nov 2026: accuracy table, credits (non-commercial) and safety wording approved; Ask counts for the MVP gate as research-only; IMD (S08) published through derived outputs only (Pai et al. 2014); OpenFreeMap 18+ confirmed; boundary disclaimer on the map and basemap country borders hidden (D168); every tracked S08 rainfall value in mm removed or untracked, per-row grid/gauge ratios replaced by per-district aggregates (D167, D169); M05 v2 refit on data through 2025 is `research_only` (untested, not served; v1 stays champion; gating test on 2026-2027 against persistence, then a new owner approval to serve v2; yearly refit rule paused, D170). Basemap border rule tested on a hand-built style only |

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
actual Worker decoder/restore. T236's local bounded runner passes at `0b8fa6a`.

T236 at `88543ba` also passed core Windows/Ubuntu, Worker/D1 Ubuntu, and web
Windows/Ubuntu CI:
https://github.com/Joepikka/monsoon-atlas/actions/runs/42259620110 ,
https://github.com/Joepikka/monsoon-atlas/actions/runs/42259620437 ,
https://github.com/Joepikka/monsoon-atlas/actions/runs/42259620166 .
T237 paired weather capture and the joint recovery-review fixes pass at `c848989`.
Its live smoke succeeded with three provider requests; a repeat returned not-due
with zero requests. At `02d0ec7`, core Windows/Ubuntu and actual Worker/D1 Ubuntu
CI passed. Web Windows/Ubuntu CI passed on one rerun: the first Windows attempt
timed out at `lens.spec.ts:74` before finding the Place selector (47/48 passed);
the same targeted desktop test passed five local repeats without code changes.
No root cause was established; no speculative UI fix was made. Runs:
https://github.com/Joepikka/monsoon-atlas/actions/runs/42268336651 ,
https://github.com/Joepikka/monsoon-atlas/actions/runs/42268336634 ,
https://github.com/Joepikka/monsoon-atlas/actions/runs/42268336612 . See
`docs/reviews/2026-11-06-weather-refresh.md` for the independent review and rulings.

T238 local weather preparation and shared CAP writer pass at `4d46546` with
43 acceptance checks and 606 full-suite passes. Task review is preserved in
`docs/reviews/2026-11-07-t238.md`; its only Minor item is the unchanged upstream
MLflow warning. Python 3.12.14/DuckDB 1.5.6 and the original source-fixture hashes
were independently confirmed. The retained-live smoke used no new provider call;
its dated prepared-only evidence remains in `.cache/feeds/weather/prepared`.
At `6c7d42d`, core Windows/Ubuntu, actual Worker/D1 Ubuntu and web Windows/Ubuntu
CI completed successfully. Runs are 42335891784, 42335891758 and 42335891767.
The broad review identified two CAP integration defects. `6ea389c` preserves
the selected CAP headline, with description/event fallbacks, and refuses disabled
S09 before retained-input reads. Prepared projection v2 preserves exact v1 files
and rejects a same-cutoff version conflict. CAP acceptance passed 31 checks.
The final suite passed 613 tests with 1 skip and the existing MLflow warning in
666.53s. A focused startup-deadline test failed once and passed isolated and full
reruns. Scoped review marked both findings addressed with no new blocking issue.
See `docs/reviews/2026-11-07-p1-branch.md` for the review and fix assessment.
At `a58a47c`, all three CI workflows passed. The core run is 42338290277,
Worker/D1 is 42338290369, and web Windows/Ubuntu is 42338290272.

T239 local upload passes at `05ff03f`. The original full test session was
interrupted when the implementer reached its usage limit. The saved rerun
exited 0 with 676 passes, 1 skip and the existing MLflow warning. The recorded
scope and integration review are in `docs/reviews/2026-11-07-t239.md`. The
local smoke used a loopback receiver with the actual Worker authentication
and decoder. Real D1 storage remains covered by the separate Worker CI.
The first remote core run exposed a test harness assumption about PowerShell
and a repository-local `.venv`. The loopback smoke now selects the PowerShell
wrapper when installed and uses the active Python CLI on the core-only runners.
The missing-venv failure reproduced in an isolated checkout and passed after
the test correction. All 63 local acceptance tests passed again in 24.16s.
The first T239 Worker and browser workflows passed.
Final T239 `aba2c2a` passed core Windows/Ubuntu run 42364436644, Worker/D1
42364436647 and browser Windows/Ubuntu 42364436645.

T240 final acceptance passed at `77b0c16`. The source overlay uses the existing
same-origin Worker path and actual source cutoffs. It stops in hidden, frozen,
invalid shared and unreleased views. D73 separates the verified stored hash
from `wire_sha256`, so a supported older stored payload can normalize without
losing its identity or failing browser verification. The review and focused
regressions are in `docs/reviews/2026-11-07-t240.md`. The response still uses a
1 MiB cap. The additional field reduces headroom by 81 bytes per returned source.
The existing MapLibre bundle warning remains. No full local Python rerun was
needed for this web/Worker scope. Core and actual D1 checks run in CI.
At `d495dbe`, core and Worker/D1 passed. Ubuntu browser CI passed 55 cases and
failed two marker assertions while the test clock was paused and the lazy map
was still loading. Holding the map import reproduced both failures locally.
The test now advances virtual time while waiting for the actual marker. All
nine acceptance cases passed in 19.0s with the delayed import in place.
Final T240 `8b14262` passed core Windows/Ubuntu run 42367568192, Worker/D1
42367568130 and browser Windows/Ubuntu 42367568125.

T241 uses the original canonical feed root because retained ledgers and weather
receipts bind absolute paths. Keep the returned manifest SHA-256 separately.
The recovery tests require the shared control SQLite, reject inconsistent CAP
clocks and verify actual preparation and cadence after restoration. The initial
full local suite passed 698 tests with one skip and the existing MLflow warning.
The final focused and S09 regressions ran after D75. The real local bundle also
passed the stricter staged reference check. See `docs/reviews/2026-11-07-t241.md`.
Final T241 `4bb7130` passed core Windows/Ubuntu run 42388198767, Worker/D1
42388198770 and browser Windows/Ubuntu 42388198815.

T242's smoke used the actual Worker handler and checked-in SQL with a local
Node SQLite adapter. The signed S01 request received HTTP 201 and replayed
three retained fixture responses. The PowerShell duplicate received HTTP 200
`not_due` and left its feed root absent. The 150-second child bound includes
claim and capture. Ruff, formatting, dependency policy, parity and whitespace
checks passed. The Ubuntu Worker runtime workflow covers actual D1 separately.
Independent review approved the change. See `docs/reviews/2026-11-07-t242.md`.
Final T242 `e471d26` passed core Windows/Ubuntu run 42390151525, Worker/D1
42390151478 and browser Windows/Ubuntu 42390151425.

T243's PowerShell smoke sealed all 27 retained files exactly, reused one
generation on repeat and restored a separate control-only tree. A hard exit
after installing a generation and before committing SQLite preserved the prior
head. A retry verified and reused the installed object. The quota probe refused
the same 45,056-byte boundary that admitted 49,367 bytes before D78. The store
remains path-bound and keeps its catalogue and objects together.
See `docs/reviews/2026-11-08-t243.md` for the review and fix evidence.
Final T243 `f2a7fc8` passed core Windows/Ubuntu run 42450944388, Worker/D1
42450944457 and browser Windows/Ubuntu 42450944467.

T244 retains the original path and stops on a missing or damaged catalogue,
an existing root or a failed save. The fixture tests prove persisted capture
and cooldown, including a handled provider failure. A real child timeout
left the interrupted working root and the previous catalogue head available.
PowerShell restored exact control bytes, honored one loopback denial and
reused the same generation. The 73 combined cycle, store, admission and
bundle regressions passed in 47.80s. Ruff, formatting, policy, amendment
parity and whitespace checks passed. The scoped review checked the exact
restore-before-capture ordering, expected-head save and preserved root.
See `docs/feeds.md` for interruption recovery.
Final T244 `350f548` passed core Windows/Ubuntu run 42451849555, Worker/D1
42451849544 and browser Windows/Ubuntu 42451849496.

T245 kept the 150-second cycle deadline. A preparation failure can save valid
capture state, and a failed save stops before upload. A lost acknowledgement
test retried byte-identical gzip from the committed generation. The 98 related
upload, catalogue and admission tests passed in 30.08s. PowerShell exercised
the actual Worker handler with local Node SQLite, returning stored and then
unchanged for the exact same CAP bytes.

T246's fixture cases verify exact head reuse, a new CAP HTTP 304 check,
CAP expiry, changed weather validity, a corrupt prior payload, and the
existing standalone cutoff and transport byte limits. The source acceptance
passed 77 tests in 35.07s, and the cycle and checkpoint regressions passed 41
tests in 51.68s. Ruff, formatting, amendment parity and whitespace passed.
Combined T245/T246 `44bc5b8` passed core Windows/Ubuntu run 42453474105,
Worker/D1 42453474158 and browser Windows/Ubuntu 42453474023.

T247 keeps the v1 original-path bundle and transfers only its verified
current object. A local import stages and verifies that bundle before
installing a fresh catalogue. The weather fixture test preserved bytes and
provider cooldown across a copied directory. The PowerShell smoke verified
offer, import and restore. The 54 bundle, catalogue and cycle regressions
passed in 64.16s. Ruff, formatting, dependency policy, parity and whitespace
checks passed. The 400 MB preflight uses uncompressed candidate
bytes and caller-supplied retained usage. Hosted artifact selection,
actual usage accounting and activation remain separate.
Final T247 `3a9a139` passed core Windows/Ubuntu run 42454674179, Worker/D1
42454674183 and browser Windows/Ubuntu 42454674168.

T248 checks the actual GitHub API shapes with a fixed HTTPS origin and a
30-second child. It reports the archive and manifest digests separately.
The selector counts all listed artifact bytes under the 400 MB project cap.
The public smoke returned zero listed artifacts and rejected an actual PR run.
The positive and refusal cases use documented metadata fixtures. The 23
handoff and checkpoint regressions passed in 9.58s. Ruff, format, dependency
policy, parity and whitespace checks passed.
Final T248 `33287e1` passed core Windows/Ubuntu run 42459509865, Worker/D1
42459509866 and browser Windows/Ubuntu 42459509869.

T249 verifies the immediate predecessor without filtering out failures.
The documented metadata fixtures cover missing sequence numbers, failed or
repeated attempts, branch rewrites and ambiguous or expired checkpoints.
The public smoke confirmed run numbers and commit ancestry and refused an
actual PR run. The 10 handoff tests passed in 4.70s. Ruff, formatting, policy,
amendment parity and whitespace passed.
Final T249 `c6a19b1` passed core Windows/Ubuntu run 42460440683, Worker/D1
42460440671 and browser Windows/Ubuntu 42460440696.

T250 preserves the downloaded archive and original path. The focused tests
cover raw and manifest digests, central-directory and expansion bounds,
traversal, aliases, links and corrupted members. The PowerShell smoke
imported a local ZIP and recovered identical control bytes. The real weather
fixture recovered its prepared identity and cooldown. The 77 related tests
passed in 9.27s. The GitHub download action inputs are documented in
`docs/feeds.md`; hosted workflow wiring remains a later step.

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

Blocked with retry conditions (T089-T100): M01 (Bengaluru ward floods; the rainfall exposure index is published instead), M02 (KWRIS reservoir levels), M03 (inflows), M04 (gauge gap filling). Each has a data gate in `reports/models/mNN-data-gate.json` and a status record in `models/registry/mNN.json`.
M08 is a non-core descriptive 2018 replay (P3).

### Sources checked

| Source | Task | Outcome | Note |
|---|---|---|---|
| S08 IMD gridded rainfall | T057, T058 | available, enabled | raw local only |
| S01 Open-Meteo forecast | T009, T010 | available, enabled | CC BY 4.0; issue time from model meta.json |
| S02 Open-Meteo ERA5 | T011, T012 | available, enabled | reanalysis (provenance model); 6-day lag |
| S03 Open-Meteo GloFAS | T047, T048 | available, enabled | simulated discharge (provenance model); hindcast unless stored at issue |
| S04 Open-Meteo CAMS | T049, T050 | available, enabled | CAMS global model estimates, never CPCB observations; issue time from meta.json |
| S44 district crime statistics | T087, T088 | available, enabled | police-unit counts 2023-2024 (OpenCity, public domain); under-reporting caveat; D114 |
| S39 Telegram Bot API | T083, T084 | blocked (owner step H08) | output channel; disabled contract |
| S31 Karnataka RERA | T081, T082 | blocked (reproduction needs emailed permission) | 10,106 applications; promoter names include individuals; no location |
| S29 OpenCity KSNDMC rainfall | T079, T080 | available (annual only), enabled | district/taluk/hobli annual 2020-2024, stations 2023; 2025 refused; D113 |
| S27 KSNDMC gauges | T077, T078 | blocked (no HTTPS; undocumented template endpoints) | D112; disabled contract |
| S25 NASA FIRMS | T075, T076 | blocked (owner step H09 MAP_KEY) | open data; pages script-rendered; disabled contract |
| S21 Datameet railways | T073, T074 | available, enabled | CC0; pinned 2016 commit; historical timetable only, never ETAs; D111 |
| S20 USGS earthquakes | T071, T072 | available (licence restricted until read), enabled | feed hourly; history needs starttime; id+updated versioning; D110 |
| S19 Google Open Buildings | T069, T070 | available, enabled | CC BY 4.0 branch; Karnataka = cell 3bb (4.8 GB), streamed to disk; display confidence >= 0.75 |
| S14 AWS Terrarium terrain | T067, T068 | available, enabled | static tiles on S3; R*256+G+B/256-32768 m; sea values are bathymetry |
| S13 NASA GIBS imagery | T065, T066 | available, enabled | NOAA-20 VIIRS true colour; newest listed non-blank date; Suomi NPP stopped |
| S12 CelesTrak orbit elements | T063, T064 | available (restricted), enabled | OMM JSON (TLE lacks 6-digit IDs); once per 2 h; no retries; raw local only (D109) |
| S11 OpenSky fallback | T061, T062 | blocked (owner reads terms) | API use = agreeing to terms; terms page 403 to scripts; anonymous 400 credits/day |
| S10 adsb.lol live aircraft | T059, T060 | available, enabled | ODbL 1.0; free now, key may be required later; now in ms; hide >300 s; drop LADD/PIA |
| S07 NASA POWER daily | T055, T056 | available, enabled | no use restrictions (CC BY 4.0); fill -999; units by community; MERRA2 to GEOSIT switch early Oct 2026; D106 robots |
| S06 Open-Meteo climate | T053, T054 | available, enabled | 7 HighResMIP models, daily 1950-2050; no named scenario; bias-corrected by default; long ranges weighted |
| S05 Open-Meteo ensemble | T051, T052 | available, enabled (IFS 0.25 ensemble) | members per product: IFS 51, GEFS 31, ICON-EPS 40, GEM 21; ~4.5 days of past values only |
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

- **H08 Telegram (S39, T083):** optional: create the bot and public channel, accept Telegram's
  developer terms, store `TELEGRAM_BOT_TOKEN` in `.env`; then T083/T084 run again.

- **S31 Karnataka RERA (T081):** optional: email K-RERA (per its copyright policy) for permission
  to reproduce the registered-projects list; record the reply, then T081 runs again.

- **H09 NASA FIRMS (S25, T075):** get a FIRMS MAP_KEY and store it as `NASA_FIRMS_MAP_KEY` in
  `.env`; then T075/T076 run again. Optional for the MVP.

- **USGS licence (S20, D110) and CelesTrak (S12, D109):** at H11, confirm the USGS copyright
  statement (https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits,
  blocked to scripts) before public display; CelesTrak publishes no licence, so show only derived
  satellite positions.

- **S11 OpenSky (T061):** read https://opensky-network.org/about/terms-of-use in a browser
  and decide whether the project accepts the terms for a non-commercial flight fallback. Using
  the API counts as agreeing, and the page blocks scripted clients, so the agent cannot decide.
  S10 adsb.lol already covers live aircraft; this is optional.

- **H05/H06:** the owner reports both accounts signed in and showed a signed-in
  Cloudflare dashboard in regular Chrome on 6 Nov. Google rejected login in the
  automation-controlled browser; use regular Chrome for account setup. Tokens
  are not configured locally. Account access does not certify a free/no-card
  capability probe or authorize public deployment. Do not create accounts,
  accept terms or enter keys on the owner's behalf.
  The owner explicitly deferred tokens on 6 Nov: "I'll do this later; continue
  local work." Do not repeat the token question; proceed with independent local
  preparation. The concrete owner guide is `docs/account-setup.md`.
  **12 Nov 2026: H05 Cloudflare token done.** The owner created a custom token
  (Workers Scripts Edit, D1 Edit, Cloudflare Pages Edit, Account Settings Read;
  one account) and saved `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in
  `.env`. A read-only check passed: `/user/tokens/verify` active, and account,
  Workers scripts, D1 and Pages list calls succeed (0 items each). Nothing was
  created remotely. H06 (`HF_TOKEN`) still waits for the archive repository.

- **S34 OCR sample reviewed (D102, 8 Nov 2026):** the owner delegated the review;
  the agent read all eight crops with their full rows and headers. Records are
  local only in `data/raw/S34/ocr-review/<id>/review.json` (S34 forbids
  redistribution). OCR method A matched 6 of 8 cells, method B 4 of 8; agreeing
  cells were right; units must come from the cell before the header; dam identity
  needs the operator (Kuttiyadi is in both tables). This does not approve bulk OCR.

- Send the drafted KWRIS helpdesk request to ACIWRM (daily reservoir history). If data arrives
  with units, datum and licence, re-run T008.
- H04: Delhi Open Transit Data registration (needed in P4).
- H10 (optional): Kaggle sign-in only if the owner wants S35 re-checked.
- H11: review at each gate and before any public deployment (licences: S08 and S34 forbid
  reproduction, so only derived outputs may be published). **Answered 11 Nov 2026 (D166) for the
  Karnataka sheet `docs/releases/h11-ka.md`:** accuracy table approved; Ask counts as research-only
  (freeze its document set and regenerate its report once before any release); S08 derived outputs
  only, citing Pai et al. (2014); attribution approved while the project stays non-commercial;
  alerts, model outputs and inferred items stay separate; refit M05 now and label v2 untested; the
  owner is 18 or older (OpenFreeMap); every public map carries a boundary disclaimer and draws no
  international border; the three S08 box-mean files in `reports/eda/` are untracked. Still open:
  the Malayalam strings, S12 and S20 display terms, and any public release.
- Before public deployment also: label WorldPop counts for Bengaluru as an undercount (about 6.0
  million in the GBA wards).
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
   The S34 sample review is done (D102). T267 (D103) read KSEB's 18 dam O&M
   manuals (S32 evidence e81-e98 from kseb.in; dams.kseb.in is gone): only the
   Idukki reservoir, Sengulam, Kakki-Anathode and Pamba state levels above MSL;
   13 give elevations with no named datum. Four is below T130's eight, so the
   datum part of the gate is not met (`docs/labels/kerala.md`). Next for C1: an
   official datum statement for the other dams (KSEB Dam Safety Organisation or
   CWC); never assume it from elevation numbers. Only then continue full T118: validate per-layout cell extraction, dates, units and dam
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
   review fixes also pass locally and in CI. T236's bounded local runner passes.
   T237 now captures weather pairs for the verified single Bengaluru grid point;
   `scripts/feeds.ps1 weather` is raw capture only, not statewide coverage.
   T238 now prepares that source-bound point with `scripts/feeds.ps1 weather-prepare`;
   the output stays partial and prepared-only. T239 local signed upload passes
   under D71/A22. T240 active-page polling and dated fallback pass with exact
   frozen report identity. T241 proves offline recovery of an absent original
   feed directory using a separately saved digest. T242 verifies the signed
   Worker admission before one enabled collector runs. T243 adds a local
   generation catalogue and recovery after process interruption. T244 composes
   one restored and admitted capture with a checkpoint save. T245 prepares
   and sends from the saved generation when `--upload-local` is selected.
   T246 avoids new prepared snapshots when only generated clocks differ.
   T247 verifies the local artifact handoff and fresh-store import. T248
   checks a pinned predecessor and repository artifact bytes. T249 discovers
   the immediate verified predecessor without skipping failed runs. T250
   verifies the raw ZIP and imports its checkpoint. T251 adds the manual-only
   `feeds.yml` relay (bootstrap or immediate predecessor, raw download,
   import, offer, upload). It has not been dispatched: `workflow_dispatch`
   needs the file on `main`, and the first run is an owner decision. Before
   any schedule, test GitHub's `queue: max` concurrency option against the
   T249 chain, measure setup time and runner free space in the three-minute
   job, and wire hosted capture only after H05.
   Remote upload and activation retain the capability and release gates. Research in
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
   `scripts/feeds.ps1 refresh --max-documents 30` combines local S09 capture and
   preparation under one child deadline. It remains partial and local.
   C3 Ask: T252 indexes the committed English corpus with lexical retrieval
   (`docs/ask.md`); T253 adds the Worker answer contract with cited
   extractive fallback; T254 adds the 60-case English gold set and scorer
   (`reports/rag.md`); T255 computes numeric answers (10/10). Gate still
   fails on evidence support (0.86 at T264). T264 tested the e5
   rerank with the owner's approval; it did not help, so BM25 stays. Do not tune on Q41-Q50. Workers AI waits for H05.
   T256 adds the T225 core case studies (H14 owner review pending). Next:
   T257 writes the accuracy rows and docs/releases/ka.md checklist (not
   releasable); T258 adds the M05 model card and T259 the web accuracy page. T260 adds the Ask route over trusted D1 chunks (extractive only) and T261 the English text Ask page. The checklist now marks the accuracy page local. T262 recalibrated the M05 intervals: 72.8%, still below the gate, so they stay hidden; do not try another rule on 2020-2024. The M05 case study (H14) predates T262. T263 finds M05 holds on the unused 2025 year (provisional). The card's retraining rule (refit when a new IMD year is published) is now triggered; a refit is a new version and needs an owner decision, since no untouched test year would remain. P2 has started (D105): T047-T052 are done (S03, S04, S05); T047-T058 are done (S03 to S08); T059-T061 done (S10 enabled, S11 blocked on terms); P2 source pairs T047-T088 are done (S11, S25, S27, S31, S39, S43 disabled; S03-S07, S10, S12-S14, S19-S21, S29, S44 enabled); T089-T100 recorded M01-M04 as blocked branches; T028/T029 (S30 GTFS) and T104-T110 are done; the Karnataka v1 gate (T110, docs/releases/ka-v1.md) opens P3: next is T111 (aisstream ships, needs H12) and the rest of P3 in plan order; shared interfaces are hash-frozen (D122); from 9 Nov simple/medium tasks run on Sonnet 5.5 high subagents and hard ones on Opus 5.5 high; P1 owner items stay open; C3 still fails on evidence support (0.86). T264 (e5) and T265 (log limit) gave no gain; section fixes alone cannot pass (max 0.943). T266 records C3 as research-only (D101); revisit only with a fresh held-out question set or reviewed generated answers after H05; `docs/releases/h11-ka.md` lists the six H11 decisions with recommended answers;
   **Update 10 Nov 2026:** P3 Kerala is done through the gate (T111-T145, `docs/releases/kl.md`,
   all four Kerala models blocked) and T224/T223 are done. P4 Delhi has started: T146/T147 are
   done (S24 blocked on a tooling failure, not on the source: re-run T146 once a browser can
   read https://www.data.gov.in/resource/real-time-air-quality-index-various-locations and take
   the resource ID from its API tab; no new key needed). T148/T149 are done (S38 blocked on H04:
   the owner submits the real time key request and static download forms on otd.delhi.gov.in,
   accepts the Terms, stores the key as `OTD_API_KEY` in `.env` and the static ZIP in
   `data/raw/S38`; then T148 re-runs). CI is green on `6f5b496`. T150-T152 are done on their
   blocked branches (after H04, in order: decoder and protobufjs, 20 routes and trip linkage,
   benchmark, study manifest, live poller). T153-T164 are done (M12-M15 blocked). M15 is the one
   Delhi model not gated by an owner step: it needs S01 and S02 enabled for Delhi and S01
   forecast vintages collected over the plan's prospective window. T165 and the Delhi gate T166 are done
   (`docs/releases/dl.md`; nothing released). **P4 is complete on its blocked branches.** P5:
   T167-T178 are done (M19, M11, M17, M20 blocked). T179-T181 are closed as far as they
   can be without H05 and a native-speaker review (D146, D147). Open Ask item: the corpus
   indexes `docs/decisions.md` and `docs/amendments.md`, which grow with every task, so Ask
   scores drift down as the logs grow (0.86 to 0.80 evidence support in three days). Before
   any Ask release, freeze the corpus to a tagged snapshot and regenerate `reports/rag.md`
   once; do not tune on Q41-Q50 (D101). T182-T184 are done (D148-D150; non-English UI off
   until native review; Telegram waits for H08; web push disabled by policy). The Worker
   `test:runtime` script does not run on this Windows laptop ("Could not resolve
   /D:/.../index.ts"); rely on the Ubuntu "Worker local runtime" CI job. T185-T188 are done (D151-D154), all
   built and not mounted. Follow-ups: verify the Tippecanoe 2.79.0 tag SHA on GitHub before
   any `tiles.yml` run; add `sgp4` to `requirements/geo.in` with pip-tools, then write and
   test `predict()`; move `Terrain` and `Movement` strings into the locale files before
   mounting them (`EventTicker` strings moved to `ticker.*` keys, D171). T189-T211 are recorded as blocked (D155, D156).
   T212-T216 are done (M16 research-only, D157-D160; proposed owner step: adjudicate 100
   anomaly flags with independent evidence). T217-T219 are done (D161-D163). `.claude/launch.json` has a `web-dev`
   entry for the local preview. T220 is done (D164). Run `tests/test_dl_poll.py` with any change
   that adds text under `web/` or `worker/`. **T221 is done (D165): every plan task T001-T221
   is walked; the product is not released.** `docs/releases/final.md` audits all 64 plan
   features (now 20 shipped-local, 12 built not mounted, 4 research-only, 27 blocked, 1 deferred
   after D172 mounted climate, wall, terrain, globe and place watches)
   and pins 88 evidence files in `final-manifest.json` (regenerate with
   `.\.venv\Scripts\python tests/test_final.py --manifest` after changing any of them).
   Operating runbook: `docs/runbooks/maintain.md`. **Karnataka first (owner, 11 Nov 2026): Kerala and Delhi work waits until Karnataka is
   live.** Next agent task without the owner: none for Karnataka; S22 and S23 prices were retried
   in the in-app browser and stay blocked (D173). Later, for Delhi: re-run T146 (S24); the
   data.gov.in resource page now renders in the in-app browser. First owner
   step: H05/H06** (H05 Cloudflare token saved and verified 12 Nov 2026; H06 waits; the H11 Karnataka sheet `docs/releases/h11-ka.md` was answered on 11 Nov 2026,
   D166) for hosting T042-T045, which
   T046 (the Karnataka MVP gate, first unfinished task in plan order) needs. New owner steps from P3: H12 (aisstream key), proposed
   H15 (Copernicus account), T118 bulk OCR approval, S41 publisher permission, Power BI Desktop
   exports (D132);
   the gate itself waits for T045 (H05/H06), T041 (S18) and H11;
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
- Run the full suite alone. `test_s09_collect.py::test_killed_child_keeps_completed_checkpoint_and_raw_evidence`
  gives its child 5 seconds and fails when other heavy jobs share the CPU (8 Nov 2026).
- Geo and ml locks are installed locally; CI installs core and dev only, so tests that need
  rasterio, shapely, h3, scipy or mlflow use `pytest.importorskip` (D35).

## 11. Obsidian vault (owner's second brain)

Active vault location: `D:\Obsidian Vault` (migrated and verified on 8 Nov 2026).
The original C-drive copy is a backup. Update the active D-drive vault.
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
