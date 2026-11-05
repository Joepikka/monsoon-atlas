# Monsoon Atlas: handoff for the next AI agent

Last updated: 5 Nov 2026, after T010 (commit `cb7f4ca`, branch `p1/gate-core`).

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
  and `dev.txt`.
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
| `src/atlas/ingest/s08.py` | First real adapter: IMD gridded rainfall year files to the common envelope (T058) |
| `src/atlas/data/validate.py` | Common envelope (`schemas/common.json`) validation, missing-is-not-zero rule, mapping metadata (T005) |
| `src/atlas/data/asof.py` | IST/UTC helpers and DuckDB as-of joins that never use future data (T005) |
| `src/atlas/data/manifest.py`, `store.py`, `budget.py` | Versioned Parquet snapshots, manifests, cache rebuild, 20 GB storage quota (T006) |
| `scripts/audit_dependencies.py` | Licence and Windows-wheel audit (T007) |
| `configs/states/ka.yaml` | Karnataka sources (S08 is the only enabled one) |
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

## 8. Current state

### Core models (portfolio MVP)

| Slot | Model | Status |
|---|---|---|
| C1 | **M07 Kerala seven-day dam forecast** (D17) | Data: S34 KSDMA daily reports from Jun 2020 (scanned; needs OCR, T118) and S32 KSEB from Oct 2023 (T114 adapter). Model tasks T130 to T132 |
| C2 | **M05 Karnataka drought outlook** (D29): next-month SPI-3 and drought probability | Data: S08 done (T057, T058). Needs T101 to T103. Live outlooks need a near-real-time rain source for recent months (S08 files are yearly), or M05 is published as a backtest only |
| C3 | Ask (question answering, English first) | T179 to T181; uses Cloudflare Workers AI free tier with an extractive fallback (D08) |

Blocked with retry conditions: M01 (Bengaluru ward floods), M02 (KWRIS reservoirs), M03.
M08 is a non-core descriptive 2018 replay (P3).

### Sources checked

| Source | Task | Outcome | Note |
|---|---|---|---|
| S08 IMD gridded rainfall | T057, T058 | available, enabled | raw local only |
| S28 KWRIS | T008 | blocked | retry if KWRIS daily history arrives |
| S32 KSEB daily levels | T113 | available (partial history) | adapter T114 |
| S34 KSDMA dam reports | T117 | available (scanned) | OCR T118, adapter |
| S35 Kaggle Kerala floods | T119 | blocked | needs owner Kaggle sign-in (H10) |
| S36 KSDMA memoranda | T121 | available | adapter T122 in P3 |
| S40 ward polygons | T030 | available | adapter T031 |
| S43 Bengaluru flood labels | T085 | blocked | not ground truth |

### Pending human-only steps (owner)

- Send the drafted KWRIS helpdesk request to ACIWRM (daily reservoir history). If data arrives
  with units, datum and licence, re-run T008.
- H04: Delhi Open Transit Data registration (needed in P4).
- H10 (optional): Kaggle sign-in only if the owner wants S35 re-checked.
- H11: review at each gate and before any public deployment (licences: S08 and S34 forbid
  reproduction, so only derived outputs may be published).

### Git

- `main` has P0 (PR #1). Branch `p1/gate-core` holds everything from T008 onwards and is pushed.

## 9. Next tasks, in order

Amendments A8 order, with the D17 and D29 fallbacks:

1. **A8 step 3, weather, alerts and base layers:** T009 to T022 (discovery and adapters for
   S01 Open-Meteo forecast, S02 ERA5 history, alerts and base layers; read each task in the
   plan), then T031 (S40 ward polygons adapter) and T032 (place identity and gazetteer).
2. **A8 step 4, core sources:** T027 (KWRIS) and T086 stay blocked (skip with a note);
   T011/T012 if not done in step 1.
3. **A8 step 5, frameworks:** T033 (feature and target build), T034 (baseline, interval and
   model release framework).
4. **C1 = M07:** T114 (S32 adapter), T118 (OCR for S34; pin a free OCR such as Tesseract,
   record it in decisions; the owner reviews an OCR sample), T130 to T132. T130 must re-plan the
   M07 splits because history starts on 20 Jun 2020.
5. **C2 = M05:** T101 to T103. T101 needs district polygons or H3 cells for Karnataka and a
   decision on near-real-time rain for live outlooks.
6. Then A8 steps 8 to 13: prices, map and product, hosting, C3 Ask, T225 case studies, T046 MVP
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
