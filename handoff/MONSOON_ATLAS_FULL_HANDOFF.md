# Monsoon Atlas: full handoff package

Generated 2026-11-08 11:21 UTC from commit `75f7f67` of https://github.com/Joepikka/monsoon-atlas

## How to use this with Claude (or any agent)

1. Upload this file, `docs/plan.pdf` (ChatGPT's original 263-page plan) and, if the tool allows,
   the current code ZIP (tracked code, tests, configs and docs from `p1/gate-core`).
2. Paste the starter prompt from section 12 of the handoff guide below.
3. The agent works in `D:\monsoon-atlas` on Joe's laptop (Windows, everything on drive D),
   one task at a time: acceptance test, commit with the task ID, push, update `docs/HANDOFF.md`.
4. Human-only steps (accounts, terms, passwords, keys, approvals) stay with Joe.

Contents: continuation guide; handoff; agent rules; current decisions; amendments; GATE-CORE; M05
model report; every source discovery report; state and model configs; file inventory; full
commit history. Local raw data and `.env` are excluded from this portable bundle and never
committed.


---

# 0. Claude continuation guide

Source file: `docs/CLAUDE_HANDOFF.md`

# Continue Monsoon Atlas in Claude

Prepared 8 November 2026. Latest implementation commit is
`75f7f676e1fb2ed1ba51a252d76db630a59c82c2` (T250). Later handoff-only commits may
follow it. The project remains in Karnataka P1. Task IDs are identifiers and do
not imply that every lower-numbered task is complete.

## Start here

Use Claude Code or Claude Desktop with local filesystem and terminal access to
`D:\monsoon-atlas`. The existing checkout contains the working environment and
retained evidence. For a fresh machine, clone the repository and check out
`p1/gate-core`, or extract the supplied code ZIP into a new directory. The ZIP
contains tracked source files and has no Git database. Preserve an existing
checkout and its local data when resuming.

Read this guide, `docs/HANDOFF.md`, `AGENTS.md`, `docs/amendments.md`,
`docs/amendments.yaml`, and `docs/decisions.md`. Then use `docs/plan.pdf` for the
original task specifications and acceptance commands. Amendments override the
original plan. Decisions run through D85 and amendments through A33 at T250.

The owner-supplied `Monsoon-Atlas-Complete-Planning-Handover.pdf` is byte-identical
to `docs/plan.pdf`. It contains 263 pages. It is the original specification;
the current handoff and Git history provide implementation progress.

Repository and draft review are available on GitHub.
[Repository](https://github.com/Joepikka/monsoon-atlas),
[draft PR #5](https://github.com/Joepikka/monsoon-atlas/pull/5).

## What was completed during the Codex continuation

The earlier Claude package described the M05/T103 milestone. The full task-by-task
history, commit IDs, limitations and test evidence are in `docs/HANDOFF.md`
section 7. The combined handoff includes that history and the complete Git log.

- Kerala fallback preparation added isolated state configuration, strict KSEB
  daily parsing, a 700-day gap census and a review packet for scanned KSDMA data
  (T226, T114, T227, T228). Monthly-source discovery and its disabled adapter
  were completed (T115/T116). These results do not establish M07 readiness.
- Source/licence and price-unit review preserved the blocked price-model branch
  (T035-T037), with an explicit M06 evidence report. Karnataka product work
  includes maps, source attribution, dated availability, frozen Place Lens
  reports and partial-data handling. Consult the task table for exact status.
- T229-T240 built and hardened the local Worker transport, CAP alert lifecycle,
  durable admission, bounded collection, normalization, weather capture and
  preparation, signed local upload, and visible-page polling with dated fallback.
  Weather currently covers one verified Bengaluru grid point. CAP-only coverage
  remains partial. Public deployment is pending.
- T241-T247 added path-bound checkpoint bundles, exact-byte recovery, signed
  admission, a durable generation catalogue, one-source runner cycles, recovery
  after failures, repeat-safe preparation and artifact offer/import.
- T248-T250 verify hosted artifact metadata and repository storage, discover the
  immediate trusted predecessor, and verify raw ZIP bytes and manifest members
  before import. The final local ZIP smoke restored identical control bytes.
  Live hosted download and recurring workflow activation remain unfinished.

## First implementation task

Continue T043 with hosted artifact download wiring and recurring-run preparation.
Read `docs/feeds.md`, `src/atlas/ingest/hosted_checkpoint.py`,
`src/atlas/ingest/hosted_archive.py`, `runner_checkpoint.py`, `runner_handoff.py`,
the existing runner-cycle code, `scripts/feeds.ps1`, and their tests.

Create the next bounded child only after checking dependencies and recording its
scope in both amendment files and the decision log. Reuse the existing selectors,
ZIP verifier and checkpoint importer.

1. Wire a fully pinned GitHub download action to the selected repository, run and
   artifact ID. Preserve the raw ZIP for the importer. Bind the selected archive
   size and digest and the independent manifest digest.
2. Resolve explicit bootstrap and predecessor continuity. A missing or failed
   immediate predecessor must not silently select older state or reset cooldown.
3. Apply the parent three-minute bound, configured storage/request budgets,
   durable cadence, serial concurrency and failure recovery to the whole hosted
   sequence. The local 150-second cycle alone does not certify that sequence.
4. Verify retry and interruption behavior before enabling recurrence. Keep
   capability probes, remote writes and activation subject to the existing gates.

## Remaining route to the end of the project

Follow dependency edges and amendments A8. This roadmap is an index into the
full plan, not a replacement for task acceptance criteria.

| Stage | Remaining scope and exit |
|---|---|
| P1 Karnataka MVP | Finish eligible T042-T045 hosting/archive/publish work, C3 English Ask T179-T181, core case studies T225, and amended T046 checks. Resolve or explicitly report core source/model gates. Obtain H11 release review. |
| P2 Karnataka v1 and shared platform | Begin with the added SQL and analyst/dashboard deliverables T223/T224, then remaining P2 tasks in plan order. Skip already completed pulled-forward tasks using evidence. Pass the P2 gate before general Kerala expansion. |
| P3 Kerala | Complete full state dependencies, Kerala sources and model/replay work. The M07 fallback work pulled into P1 does not complete full T129 or the Kerala phase. Require honest dated coverage and model evidence. |
| P4 Delhi | Complete OTD approval-dependent integration, prospective label collection and maturation, ETA/AQI work and the Delhi gate T166. Historical reconstruction cannot replace prospective test labels. |
| P5 Cross-state | Complete remaining cross-state product, multilingual/Ask extensions, news/data extraction and model evaluation, optional/stretch work according to dependencies, and the final plan acceptance through T221. Document blocked optional work and publish only eligible evidence. |

Use the original plan's task catalogue and YAML appendix for every task's files,
dependencies and acceptance command. The amendments add T222-T250. A blocked
dataset must remain disabled until its verification condition passes. Continue
independent work while maintaining an explicit blocked-task list.

## Owner and data gates to carry forward

- H05/H06 credentials were deferred by the owner. Both accounts were signed in,
  but token setup and the free/no-card capability probe remain pending. Continue
  local work without repeating the question. Account creation, terms, passwords
  and key entry remain human-only. Existing secrets are read by variable name.
- S34 OCR needs the owner review packet at
  `data/raw/S34/ocr-review/index.html`. Six of eight sampled cells disagree.
  Sample review does not approve bulk OCR. M07 needs known datum, at least three
  years of daily coverage across at least eight dams, and valid dated splits.
  Resolve T130's full-T129 dependency before training the fallback.
- S23 price denominator is unverified despite verified GODL terms. KWRIS lacks
  usable daily history and datum. S18 remains blocked. S35 needs owner Kaggle
  access if pursued. Preserve their documented retry conditions.
- M05 ridge was approved in D43 as a hindcast champion. Its intervals cover 65%
  against an 80% target and require recalibration before interval publication.
  All models retain issue-time features, time/spatial holdouts and the paired
  bootstrap promotion rule.
- H11 still gates release. H04 Delhi registration, H13 news-label review and H14
  case-study review apply at their specified stages. Keep Rs 0, attribution,
  privacy, raw-data licence restrictions and emergency-service disclaimers.

## Verification evidence at the transition

T250 passed 16 archive tests and 77 related tests. Its actual PowerShell entry
point imported a local ZIP and restored identical control bytes. The weather
fixture recovered prepared identity and cooldown. Lint, formatting, dependency
policy and amendment parity passed during implementation.

All three GitHub workflows passed on implementation commit `75f7f67`.
[Core](https://github.com/Joepikka/monsoon-atlas/actions/runs/42467457043),
[Worker runtime](https://github.com/Joepikka/monsoon-atlas/actions/runs/42467457026),
[browser](https://github.com/Joepikka/monsoon-atlas/actions/runs/42467457006).

Those are implementation results, not a new full-suite run for this handoff.
Run the next task's meaningful acceptance checks, then required repository
checks. CI installs core/dev dependencies; local geo/ML tests may need their
existing locked groups. Some historical runs record the S36 PDF-tool skip and
an MLflow deprecation warning. Read the dated evidence before interpreting counts.

## Local resources and portable limits

The existing `.venv`, `.tools`, `.cache`, raw/clean data and model artifacts stay
on the owner's D drive. The code ZIP contains tracked files. It excludes secrets,
local runtime dependencies, ignored datasets and transient caches. A chat-only
Claude session can review the package but needs terminal/filesystem access to
continue implementation and run acceptance commands.

Retain `.cache/feeds`, all checkpoint stores, original root paths and independent
digests. Bundles are path-bound. Preserve `.cache/t043-research/findings.md` and
the S34 review packet on this machine. The portable package includes a file-count
and byte inventory of local-only folders, without their contents. Refetch permitted
sources using existing adapters only when evidence is absent and source budgets
allow it. Excluded evidence must never be replaced by synthetic observations.

Python is 3.12.14 in `.tools/python`, the environment is `.venv`, and DuckDB must
stay on 1.x. Set TEMP and TMP to `D:\monsoon-atlas\.cache\tmp` before downloads.
Use the scripts under `scripts/` for the web, Worker and feed entry points.
Local helper wrappers under `.cache` may be absent on another machine.

```powershell
git status --short --branch
git log -5 --oneline
.\.venv\Scripts\python -m pytest tests/test_hosted_archive.py -q
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
```

The active Obsidian vault is `D:\Obsidian Vault`. The C-drive vault is a backup.
Update `Projects/kerala-live-map.md`, the handoff notes and `Claude/Work log.md`
after verified milestones. Treat earlier handoff ZIPs as dated snapshots.

## Prompt to paste into Claude

Continue Monsoon Atlas in D:\monsoon-atlas using this handoff and the current
p1/gate-core checkout. Read docs/CLAUDE_HANDOFF.md and docs/HANDOFF.md first,
then AGENTS.md, amendments.md/yaml, decisions.md and the original plan as needed.
Review the existing implementation before editing. The latest implementation
milestone is T250 at 75f7f67, with draft PR #5 open. Start with the next eligible
T043 child for hosted download wiring and recurring-run preparation.

Carry the remaining project forward through P1, P2, P3, P4 and P5 in dependency
order. Make reasonable reversible decisions, record deviations, reuse existing
code and keep work bounded. After each task, run acceptance checks, commit and
push to the appropriate branch, update the repository handoff and D-drive
Obsidian notes, then continue. Preserve blocked tasks and their retry conditions.
Ask only for genuine human-only steps or destructive/irreversible decisions.
H05/H06 tokens remain deferred, so continue independent local work. Keep the
Rs 0, genuine-data, licence, privacy and honest-model constraints. Report what
actually passes and what still prevents the next gate. The original plan remains
unfinished; never infer completion from the highest task number.



---

# 1. Handoff guide

Source file: `docs/HANDOFF.md`

# Monsoon Atlas: handoff for the next AI agent

Last updated: 8 Nov 2026, T250 downloaded checkpoint ZIP verification,
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
| `docs/amendments.md`, `docs/amendments.yaml` | Amendments v1 plus recorded splits through T250. **They win where they conflict with the plan.** GATE-CORE (A4), human-only steps (A5), P1 order (A8) and child-task dependencies |
| `docs/decisions.md` | Decisions D01 to D85. Every deviation from the plan is recorded here before it is made |
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
   verifies the raw ZIP and imports its checkpoint. Continue with hosted
   download wiring and recurring-run preparation.
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

# 3. Decisions log

Source file: `docs/decisions.md`

# Decisions log

## Continuation review (5 Nov 2026)

- **D85 — Verify the downloaded checkpoint archive before import (8 Nov 2026).**
  Split T250 from T043 after T247/T249. Use GitHub's existing artifact download
  action for transport by pinned artifact ID, with extraction disabled. A
  local importer checks the selected archive size and digest before parsing,
  bounds ZIP metadata and expansion, and extracts only manifest-listed files.
  Keep the separately trusted manifest digest and original-path store checks.
  Hosted workflow wiring and activation are later work.

- **D84 — Discover the immediate trusted workflow predecessor (8 Nov 2026).**
  Split T249 from T043 after T248. Pin the active run and examine its
  workflow's recent run metadata without a success filter. Require the
  preceding run number, matching branch and workflow, a successful first
  attempt and a commit in the active run's history. Use its one checkpoint
  name to recover the manifest digest independently of the download. Stop
  on a missing, failed, expired or ambiguous predecessor. Bootstrap and
  hosted download remain separate steps.

- **D83 — Pin hosted artifact selection to a trusted run (8 Nov 2026).**
  Split T248 from T043 after T247. A bounded, read-only GitHub metadata check
  uses explicit repository, workflow, run, branch, commit and manifest
  identities. Require an eligible completed first attempt and a matching
  unexpired checkpoint artifact. Count every listed repository artifact
  against the 400 MB project budget, including expired entries still listed.
  Return separate archive and manifest digests. Missing, malformed or changing
  metadata fails closed. Run selection and activation remain later work.

- **D82 — Verify a hosted checkpoint handoff locally (8 Nov 2026).**
  Split T247 from T043 after T243/T246. Offer only the committed immutable
  bundle directory for artifact transport. Apply the existing 400 MB and
  seven-day project limits and require a retained-byte total for preflight.
  Import the downloaded directory into a fresh store using a separately
  supplied manifest digest and the same absent canonical feed root. Check
  staged bytes and evidence before creating the local head. Keep workflow
  selection, provider accounting and recurring activation as later work.

- **D81 — Reuse the verified runner projection when only its clock changes (8 Nov 2026).**
  Split T246 from T043 after T245. The runner can reuse a prepared head at a
  later cutoff when verified source inputs and the normalized projection are
  identical apart from generated cutoff, publication and revision metadata.
  Preserve the exact prior bytes and clocks. New input validation, an expired
  alert or a changed forecast selection still prepares a new snapshot. Use
  the existing signed retry and Worker idempotency for retained bytes.

- **D80 — Prepare and send the saved local snapshot (8 Nov 2026).**
  Split T245 from T043 after T235/T238/T239/T244. The explicit runner
  `--upload-local` option prepares successful capture at the actual UTC cutoff
  and saves the verified checkpoint before the signed loopback send. Send from
  the installed immutable generation. A preparation failure still allows
  valid capture state to be saved. A `not_due` result can retry an exact
  retained prepared snapshot using the existing Worker idempotency contract.
  Keep the same child deadline and leave the working root after failure.

- **D79 — Bound one restored local capture cycle (8 Nov 2026).**
  Split T244 from T043 after T242/T243. One parent deadline covers verified
  restore to an absent root, one signed loopback admission and capture, and
  an expected-head save. Persist verified capture-stage state even after a
  handled failure so cadence and cooldown survive. An admission denial or
  failure uses the restored digest without sealing another copy. Keep the
  working directory after success or interruption so evidence can be reviewed
  before another run. A timeout never starts a second child. Preparation,
  upload, hosted persistence and recurring activation are later work.

- **D78 — Protect catalogue recovery and count pending SQLite pages (7 Nov 2026).**
  T243 review found two gaps. An explicit bootstrap could recreate a missing
  catalogue beside retained generations, and buffered SQLite pages could
  exceed the quota after the initial copy check. Bootstrap a missing catalogue
  only in an empty store. Keep the proposed head uncommitted while measuring
  the catalogue's pending size and verifying aggregate space. Install the
  generation before committing the transaction. This preserves the prior
  committed head on failure and lets a quota refusal discard owned staging.

- **D77 — Store verified runner checkpoint generations locally (7 Nov 2026).**
  Split T243 from T043 after T241/T242. Keep immutable bundles in a durable
  local directory outside the feed workspace and store the current digest in
  a SQLite catalogue. One transaction compares the caller's expected head,
  seals a new generation and advances the head only after the bundle exists.
  Recovery uses the trusted catalogue and the same absent canonical feed root.
  Count the whole store in the existing storage quota. Keep prior generations
  and allow retry after an interrupted catalogue update. The runner must carry
  forward the digest it restored. Hosted storage, relocation and recurring
  scheduling are later T043 work.

- **D76 — Gate local producer capture on Worker admission (7 Nov 2026).**
  Split T242 from T043 after signed upload, browser polling and checkpoint
  recovery. Add a bounded one-source capture command using the owned signed
  admission endpoint on explicit loopback. Only a matching affirmative Worker
  reply permits the existing collector to run. Keep its separate persisted
  local cooldown and cadence check. A Worker slot can be consumed when the
  reply is lost or the collector later declines. Reuse the uploader's local
  transport policy. Durable runner persistence, scheduling and cloud activation
  are later work.

- **D75 — Bind CAP checkpoint evidence to retained clocks (7 Nov 2026), before fix.**
  T241 review showed that a raw ledger timestamp shifted by one second could
  pass staging verification and prevent preparation at the saved cutoff. Check
  CAP prepared input origin and validation clocks against retained ledger
  events and bind CAP control origin to its recorded content identity. Identical
  bytes fetched on a later day can have a new raw path with the same retained
  content clock. A valid HTTP 304 still records a check of existing bytes.
  Keep the bundle format and exact saved bytes unchanged.

- **D74 — Verified local feed checkpoint bundles (7 Nov 2026), before implementation.**
  Split T241 from T043 after the local capture, preparation and polling children.
  Preserve the actual quiescent S01/S09 feed tree as an immutable, hash-indexed
  local folder. It includes admission, cooldown, checkpoints and the raw and
  prepared bytes they depend on. The existing ledgers and weather receipts
  bind absolute raw paths, so v1 restores only to the original canonical feed
  root. Require the saved manifest digest and a missing target. Validate safe
  member paths, bytes and authoritative references in staging before atomic
  publication. Use the existing storage budget and retain original data.
  Cross-path restoration, remote persistence and runner activation are later
  T043 work. This child grants no publication or scheduling authority.

- **D73 — Preserve older Worker snapshot identities (7 Nov 2026), before fix.**
  T240 review reproduced a contract mismatch for an older supported stored
  snapshot whose parser fills in an optional field. The Worker checks the
  exact stored bytes and keeps their `sha256` identity. Current GET replies
  also expose `wire_sha256`, the digest of the exact normalized source envelope
  returned to the browser. The browser verifies that projection and uses
  `sha256` as the stored identity for monotonic checks. Replies that omit the
  additive field use the existing digest when it matches their wire bytes.
  Extend T240's scope to the GET response, its compatibility tests and contract
  documentation. Stored bytes, identifiers, SQL and upload protocol stay intact.

- **D72 — Active-page source polling (7 Nov 2026), before implementation.**
  Split T240 from T043 after T040/T229/T239. Read the existing same-origin
  Worker current endpoint only from the normal Karnataka view with an approved
  daily snapshot. Verify the bounded per-source response, normalized Worker
  digest and source clocks. Poll S09 every 15 minutes and S01 every six hours
  while visible, with one request in flight and a five-second request deadline.
  Hidden or ended views cancel pending work. A started attempt consumes its
  cadence slot. Keep per-source high-water clocks across failures. Show hot
  results as a separate map and list overlay with their own dates and coverage.
  Failures use the dated daily source. Place Lens, print and frozen links keep
  the approved immutable daily snapshot. Cloud routing and publication still
  require their existing gates.

- **D71 — Local signed snapshot upload (7 Nov 2026), before implementation.**
  Split T239 from T043 after T229/T235/T238 to exercise the prepared-snapshot
  sender through an explicit loopback Worker origin. Verify retained payload
  and input hashes, source identity, cutoff and transport bounds before signing
  the exact deterministic gzip bytes with the existing HMAC protocol. Use an
  environment key, one request, bounded response and a 15-second child deadline.
  The acknowledgement reports the Worker's normalized snapshot identity
  separately from the local payload hash. Keep preparation immutable across
  retries and failures. Restrict this child to `http://127.0.0.1:<port>`.
  Cloud configuration, durable restoration and scheduled use retain their
  existing capability and approval gates.

- **D70 — CAP preparation review fixes (7 Nov 2026), before implementation.**
  Correct the T235 projection to use the selected CAP info block's actual
  headline, with its description and event as ordered fallbacks. The event
  alone omits district and timing details in the retained Karnataka sample.
  Reuse the adapter's language selection and retain its normalized row schema.
  Version the changed prepared projection as `s09-prepared-v2`. Keep older
  immutable files and reject conflicting bytes at the same cutoff. Check the
  S09 enable flag before reading retained evidence so header-only controls
  cannot produce a prepared result for a disabled source.

- **D69 — Local weather snapshot preparation (6 Nov 2026), before implementation.**
  Split T238 from T043 after T235/T237. Project one quality-passed future
  temperature from the verified Bengaluru model grid, with explicit partial
  scope. Consume grouped validated capture receipts; never independently select
  latest metadata and forecast files. Fence receipt completion and every input
  validation at the report cutoff. Preserve the earliest forecast retrieval
  and complete-pair availability clocks for the selected model/run/content
  cohort across revalidation, while using its latest actual successful check
  for source health. Use actual returned coordinates and S01's normalized
  null/quality policy. Reuse a small shared immutable prepared-envelope writer
  extracted from T235, retaining CAP's strict input-continuity guard. Both
  producers keep partial prepared-only output, monotonic/idempotent heads and
  actual creation time distinct from historical cutoff. No source call, upload,
  approval or activation occurs during preparation.

- **D68 — Bounded paired weather capture (6 Nov 2026), before implementation.**
  Split T237 from T043 after T010/T234/T236. Start with the already verified
  Bengaluru query (12.97,77.59), named `ecmwf_ifs025`, whose returned grid point
  is (13.0,77.5); do not invent a statewide query grid or coverage claim. Retain
  each metadata-before/forecast/metadata-after attempt as an immutable local
  receipt so later preparation cannot mix independently latest raw files.
  Only a stable, settled pair with a quality-passed future temperature can
  advance the latest validated-pair pointer. Use shared six-hour admission,
  five-second per-attempt spacing and five HTTP attempts per admitted run,
  bounding four nominal checks to at most 20 attempts per UTC day locally.
  Refactor the existing cadence/backoff transport for both verified profiles;
  enabled-source flags must be checked before provider calls. A 120-second
  HTTP-only child bound covers this local capture. Failed, incomplete, changed
  or unsettled pairs preserve the last pointer, and raw observations remain
  untouched. This child does not create a browser projection, upload, schedule
  or cloud resource; coverage remains the single verified point and partial.
  The joint refresh/weather review additionally requires retaining usable CAP
  preparation after recoverable capture I/O errors, and saving each completed
  weather receipt before validating a possibly damaged previous head.

- **D67 — One bounded local CAP refresh command (6 Nov 2026), before implementation.**
  Split T236 from T043 after T234/T235. Run capture and preparation in one
  HTTP-only child with a 150-second parent deadline, rather than nesting child
  launchers. Shared local admission/cooldown still controls provider calls.
  Preparation can use already retained evidence after not-due, deferred or
  failed collection, so a completed control from an interrupted run need not wait
  for another provider call. Its validation clocks remain the actual retained
  clocks, and coverage remains partial. A preparation error leaves its prior
  pointer intact. This local-only runner does not implement S01, upload, recurring
  jobs or cloud activation; full T043 still requires those steps and its gates.

- **D66 — Local CAP normalization and prepared transport snapshots (6 Nov 2026),
  before implementation.** Split T235 from T043 after T234. Validate retained
  raw evidence and preserve original content clocks; select exact CAP message
  identities and apply Actual/Public Update/Cancel references, including
  header-only controls, without inventing warning rows. Prepare a bounded
  immutable local JSON envelope and source-input manifest with atomic pointer
  movement. Expired messages and controls remain in raw history even when they
  are absent from the current warning projection. CAP-only coverage remains
  partial, including a valid empty Karnataka result. Permit explicitly partial
  source health through the local Worker contract, preserving its classification
  and actual check clocks. This child does not upload, approve publication,
  activate workflows or claim complete coverage. Failed preparation and corrupt
  evidence must not replace the last prepared snapshot. A mixed valid/malformed
  capture may retain dated last-good warnings, with partial health and validation
  clocks derived only from valid documents; malformed downloads cannot refresh
  that clock.

- **D65 — Bounded local CAP-only collection (6 Nov 2026), before implementation.**
  Split T234 from T043 to implement the local collector before activating any
  workflow. A cold CAP+polygon sweep has 200 one-second sleeps for the captured
  100-item feed, already exceeding the three-minute job limit. Admit at most 30
  CAP documents per run, omit supplemental polygons, and wrap the HTTP-only
  child in a hard subprocess deadline. Keep raw evidence and durable per-document
  checkpoints, revalidate with the existing Fetcher/ETags, and never refresh CAP
  validation times from an RSS-only 304. Share admission caps locally through
  SQLite; persist Retry-After deferral before stopping a run. New/changed and
  oldest documents share admission capacity to prevent starvation. Every result
  remains explicitly partial: CAP-only sender/area matching cannot certify full
  Karnataka coverage. This child captures/validates documents and control headers;
  it does not invent analytical rows for a header-only cancellation, publish a
  reviewed snapshot, upload, create a cloud resource or enable cron/polling.

- **D64 — Durable source-check admission before polling (6 Nov 2026), before
  implementation.** A volatile GitHub cache cannot enforce T043's check caps
  after a cache miss, delayed job or manual retry. Split T233 from T043 to add
  signed, server-clock admission at the owned `/internal/feed-check` endpoint.
  A D1 transaction allows at most one S01 admission per six elapsed hours and
  one S09 admission per fifteen elapsed minutes, including across runners and
  UTC bucket boundaries. Lost responses consume the slot rather than permitting
  an unbounded retry. Reserve storage and row/index writes within the existing
  caps; account failures or exhausted capacity deny provider calls. Only KA's
  verified public S01/S09 feeds are eligible. This is a local/CI protocol child,
  not a deployed coordinator or a completed fetch/schedule/poller pipeline.

- **D63 — Match complete CAP reference identities (6 Nov 2026), before
  implementation.** OASIS CAP 1.2 section 3.2.1 defines an extended reference
  as sender, identifier and sent time. The existing identifier-only supersession
  could drop an unrelated issuer/revision; its predecessor test also retained
  the relay sender despite a different sender in the real reference. Split
  T232 from T043 to match all three fields, normalizing only equivalent timezone
  representations. Preserve unmatched/malformed references instead of guessing.
  A relay may reference another sender's real message, but does not license
  rewriting that sender or time. No NDMA relay exception was found in targeted
  primary documentation. Raw Cancel/Update documents remain archived; Cancel
  messages are not themselves displayed as active hazard warnings.
  Primary specification: https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html .
  This lifecycle check also requires valid timezone-bearing CAP dates and
  explicitly Actual/Public messages. Test/Exercise or restricted documents must
  not enter the public warning set. Only Update/Cancel can supersede references;
  Ack/Error control messages cannot themselves become active hazard warnings.

- **D62 — Version RSS cache entries, not permanent GUIDs (6 Nov 2026), before
  implementation.** The captured S09 CAP Update `IN-1793881986295019_19`
  references `IN-1793881986295019_51`, while the RSS GUID and download URL use
  the common base `1793881986295019`. Inferring that a seen RSS GUID identifies
  immutable CAP content is not justified. Split T231 from T043: compare a hash
  of the actual RSS item contents, and reject legacy bare-identifier skip sets.
  A changed item must re-enter the shared conditional-GET fetcher, even at a
  known URL. RSS fingerprints describe index versions, not a guarantee that a
  provider cannot silently revise a linked document. T043 must bound cache age,
  persist checkpoints only after successful processing and retain source clocks.
  No new provider field or observed alert is invented by this cache contract.

- **D61 — Preserve area-only CAP alerts before refresh (6 Nov 2026), before
  implementation.** T014 legitimately parses CAP area descriptions without a
  polygon. Requiring a map point in the browser/hot transport would reject a
  valid official warning or encourage invented coordinates. Split T230 from
  T043 to preserve these rows through the shared validator, record list, ticker,
  Place Lens and Worker. Allow both coordinates to be explicitly null only for
  S09 official area alerts with original area text and a location-limit note.
  Such rows stay in state context, never become a marker, radius distance or
  point-specific incident. Weather, facilities and administrative places still
  require verified numeric coordinates. Check stored canonical bytes before
  revalidation so new optional fields cannot alter old identity or hide a
  modified field behind normalization. Full T043 still needs its producer,
  bounded schedule, polling/fallback integration and the pending cloud gate.

- **D60 — T042 local implementation child and cloud gate (6 Nov 2026), before
  implementation.** Split T229 from T042 to implement and verify the Worker/D1
  endpoint locally and in free CI while H05 remains pending. The owner has
  signed in; no token, billing status or actual service capability is verified.
  Full T042 and any deployment stay pending until the owner completes H05 and
  the free/no-card probe. No account, API token or remote database is created by
  this child. Wrangler 4.157.0 officially requires Windows 11 or supported Linux;
  this laptop is Windows 10. Run pure TypeScript/SQLite checks locally and the
  actual Miniflare/D1 runtime on Ubuntu CI. Keep all caches on D locally.
  Reuse the tested browser snapshot validator for the owned JSON transport;
  initially allow only enabled public KA hot feeds S01 and S09. Store canonical
  validated bytes, not unchecked upload fields. HMAC binds timestamp, method,
  path and exact compressed request bytes; idempotency is content-addressed.
  Storage and daily writes fail closed with conservative reservations checked
  in the same SQLite transaction. An unavailable binding/capability gate returns
  an explicit static-fallback status; it never claims a deployed current feed.

- **D59 — Frozen Place Lens links (T040, 6 Nov 2026), before implementation.**
  A latest pointer cannot reproduce an older approved view after a refresh.
  Shared links bind state, place ID, boundary version, as-of time and the exact
  browser-snapshot SHA256. Resolve that hash through a same-origin immutable
  `<hash>.approval.json` pointer before reading `<hash>.json`; require approved
  status, the matching hash and exact place/boundary/as-of identity. A failed
  historical lookup must not substitute a different last-good release. No
  production approval files are generated by T040; T045 must publish them only
  after the actual review gate. Print and tab views use one report object.
  Source S18 remains blocked, so Nearby states that facilities/operation cannot
  be verified. No facility, risk score or model forecast is fabricated.

- **D58 — Radius and source-health semantics (T039, 6 Nov 2026), before
  implementation.** A polygon alert's representative point cannot establish
  distance to the whole alert area. Keep area-scoped official alerts in the
  state context when filtering a point radius; label that limit rather than
  silently excluding an intersecting warning. Point records use great-circle
  distance from a user-chosen map point. No browser location permission or
  persisted location/query history is needed. Missing health metadata is
  unknown/unavailable, never evidence of no hazards. Preserve the common
  envelope's official/model/inferred/reconstructed provenance, original issue,
  valid, fetched and available times. Reconstructed and inferred records cannot
  masquerade as official alerts; unknown price units cannot be rendered as prices.
  The ticker refers to the dated snapshot and preserves provider severity/expiry.

- **D57 — Align the browser-test transport version (6 Nov 2026), before
  changing the lock.** T038's first TypeScript build found incompatible Page
  types: axe 4.14.0 resolved playwright-core 1.65.0 while @playwright/test 1.64.1
  resolved 1.64.1. Pin the transitive playwright-core to 1.64.1 via npm overrides
  so both tools use the plan's tested Playwright version. Keep all requested
  top-level pins unchanged; rerun type checking and actual browser/axe checks.

- **D56 — T038 browser projection and local toolchain (6 Nov 2026), before
  implementation.** Use the plan's exact web package pins, verified against
  official npm metadata; add matching React types 19.3.0 and Node types 22.16.0.
  Install the official portable Node 22.16.0/npm 10.9.2 on D after checking the
  official SHA256. npm and Playwright caches/temp files stay on D. Use native
  Vite TSX support and defer MapLibre 6, CSS and its worker in a lazy module.
  The public browser JSON is a small typed projection of an immutable release,
  not a Parquet reader: retain release/state/revision/as-of/publication metadata
  and canonical point records with source, provenance and original timestamps.
  A same-origin pointer binds its SHA256 and explicit approved status. The loader
  checks both before use; this is content integrity, not a cryptographic owner
  signature. The pipeline must obtain actual release approval before publishing
  that pointer. No approved pointer or observation data is generated by T038.
  Missing release data has an honest empty state; a failed refresh retains only
  the dated, in-memory last-good snapshot for the same state. No localStorage,
  account, query history, tracking, or synthetic production snapshot is added.
  Browser regression fixtures may project the already committed public-domain
  S09 CAP sample. Preserve its canonical provenance and times; an alert polygon
  is represented only by a labelled point-on-surface, never incident coordinates.
  Keep fixture source hashes and the derivation, and never serve it as live data.

- **D55 — M06 blocked status is not a model release (6 Nov 2026).** T037's
  `models/registry/m06.json` records the failed data gate and its actual evidence
  hashes, with null dataset/split/model hashes and null achieved scores. Do not
  construct a T034 `Release` by inventing a dataset, training timestamp, baseline
  or evaluation. No `M06/v*.json` release or approval is generated, so the serving
  registry cannot select this status record as a champion. Completing the blocked
  branch is not fitting M06 or satisfying the final MVP's model requirements.

- **D54 — Continue independent P1 work while source/owner gates remain pending
  (6 Nov 2026).** The owner explicitly requested continuous execution of the
  plan. Complete T024/T026's prescribed disabled adapters, then T035-T037's
  prescribed blocked-model state and evidence report. Neither unavailable prices
  nor unreviewed OCR may become training rows, invented scores or predictions.
  Continue dependency-ready T038-T040 and local hosting/Ask preparation in A8
  order while their unrelated gates are pending. This is scheduling independent
  work, not declaring the C1 review or any source dependency satisfied. Keep
  T118/T130-T132, unavailable-data analyses, account-dependent deployment and
  final phase gates explicitly pending until their own requirements pass.

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

## A10. Kerala bootstrap child task (D44, 5 November 2026)

The handoff's next-task list placed full T129 before its own adapter prerequisites.
Split out **T226**, a child of T129, for the already approved D17 core C1 fallback.
T226 runs now in P1, after T003, T113, T117, T119 and T121. It creates isolated
`configs/states/kl.yaml`, the existing-evidence audit `docs/labels/kerala.md`, and
`tests/test_kl_data.py`. Every Kerala source stays disabled. Estimate: 2 hours.

Acceptance: `.\.venv\Scripts\python -m pytest tests/test_kl_data.py -q` passes;
two states load with separate paths, no Kerala source is enabled, and the audit
reports real history, unknown datum, unavailable labels and unverified geography.
This is bootstrap acceptance, not completion of the full T129 audit.

T114 and T118 gain T226 as a dependency. Full T129 retains its P3 scope and all
original dependencies (T046, T114, T116, T118, T120, T122, T124), plus T226.
Before T130, record the resolution of its full-T129 dependency for the M07-only
fallback and of T115/T116 scheduling; neither is waived by T226. Known datum,
reviewed OCR, daily coverage and honest splits remain mandatory gates.

## A11. S32 daily coverage census split (D46, 6 November 2026)

**T227**, child of T114, runs in P1 after T113/T114 and before T130. T114 implements
the adapter; its discovery follow-up requested a date-by-date audit of the sampled
15 Aug 2024-15 Jul 2026 gap. That backfill is a separate resumable task, not proof
already supplied by the twice-monthly discovery sample. Estimate: 2 hours.

Files: `scripts/s32_history.py`, `docs/sources/s32-history.md`,
`tests/sources/test_s32_history.py`. Use only the verified date form and shared
fetcher; space requests by at least 3 seconds and obey budgets. Report every date
as validated data, a validated empty report, quarantine, or a fetch/layout failure.
Never infer the entire gap from a sample or invent daily values from monthly data.
Acceptance: `.\.venv\Scripts\python -m pytest tests/sources/test_s32_history.py -q`;
each requested date has cited evidence or an explicit failure. T130 gains T227 as
a dependency before using S32 historical coverage. Other D44 dependencies remain.

## A12. Hot endpoint implementation child (D60, 6 November 2026)

T229 implements T042's signed hot-data endpoint, D1 schema and local/CI checks
after T006/T040. Full T042 remains pending H05 and the actual free/no-card service
probe; no account, token, remote resource or deployment approval is created by
this child. Windows 10 is outside current Wrangler support, so pure logic and
SQLite run locally and the actual Miniflare/D1 runtime runs on Ubuntu CI. Estimate:
3 hours. Acceptance: `.\.venv\Scripts\python -m pytest tests/test_worker_core.py -q`.

## A13. Preserve area-only alerts before refresh (D61, 6 November 2026)

T230 is a child of T043 after T014/T040/T229. It retains official CAP warnings
whose original area text is known but whose geometry is unavailable. The list,
Place Lens, ticker and hot transport preserve the warning and its clocks without
inventing a map point. Estimate: 1 hour. Acceptance:
`.\.venv\Scripts\python -m pytest tests/test_alert_area_context.py -q`.
It does not complete T043's producer, schedule, polling or cloud gate.

## A14. Version RSS cache entries (D62, 6 November 2026)

T231 is a child of T043 after T014/T230. It replaces permanent RSS-identifier
skip sets with hashes of actual item contents, so a changed item at a known URL
is fetched again through the existing HTTP boundary. T043 still owns cache-age
expiry, durable checkpoints and the bounded producer. Estimate: 1 hour.
Acceptance: `.\.venv\Scripts\python -m pytest tests/sources/test_s09.py -q`.

## A15. Complete CAP supersession identity (D63, 6 November 2026)

T232 is a child of T043 after T014/T231. It matches CAP references by the full
sender/identifier/sent-time identity, preserving unresolved references rather
than dropping unrelated warnings. It also requires timezone-bearing dates and
Actual/Public lifecycle messages for public warnings. Estimate: 1 hour. Acceptance:
`.\.venv\Scripts\python -m pytest tests/sources/test_s09.py -q`.

## A16. Durable bounded source-check admission (D64, 6 November 2026)

T233 is a child of T043 after T229/T232. It adds authenticated, atomic source-check
admission using D1's server clock so lost runner caches or duplicate jobs cannot
bypass weather/alert cadence caps. Estimate: 2 hours. Acceptance:
`.\.venv\Scripts\python -m pytest tests/test_schedule_feeds.py -q`.
Actual provider collection, workflow activation and browser polling remain in
T043; full T042 and cloud admission remain pending H05.

## A17. Bounded local CAP collection (D65, 6 November 2026)

T234 is a child of T043 after T230/T231/T232/T233. It captures and validates a
bounded CAP-only subset with ETag checkpoints, persistent local admission and
Retry-After deferral, plus a hard parent-process deadline. Its result remains
partial and local; no reviewed publication, cloud upload or recurring workflow
is enabled. Estimate: 3 hours. Acceptance:
`.\.venv\Scripts\python -m pytest tests/sources/test_s09_collect.py -q`.

## A18. Local CAP normalization and prepared snapshots (D66, 6 November 2026)

T235 is a child of T043 after T229/T230/T232/T234. It turns retained real CAP
evidence into a local bounded transport envelope, applying exact public control
references and preserving source clocks, partial coverage and immutable inputs.
It adds no upload, public approval or recurring work. Estimate: 3 hours.
Acceptance: `.\.venv\Scripts\python -m pytest tests/sources/test_s09_prepare.py -q`.

## A19. Bounded local CAP refresh runner (D67, 6 November 2026)

T236 is a child of T043 after T234/T235. One local command captures and prepares
retained KA CAP evidence under a single 150-second child deadline. Provider
admission/backoff and actual source clocks survive recovery; no upload or
recurring work is enabled. Estimate: 2 hours. Acceptance:
`.\.venv\Scripts\python -m pytest tests/test_feed_refresh.py -q`.

## A20. Bounded paired weather capture (D68, 6 November 2026)

T237 is a child of T043 after T010/T234/T236. Capture the verified single-point
S01 profile with immutable paired metadata/forecast evidence, model settling,
shared cadence/backoff and weather-specific spacing/attempt caps. It remains
local and partial, with no projection, upload or workflow. Estimate: 3 hours.
Acceptance: `.\.venv\Scripts\python -m pytest tests/sources/test_s01_collect.py -q`.

## A21. Source-bound weather preparation (D69, 6 November 2026)

T238 is a child of T043 after T235/T237. It prepares the verified single-point
temperature projection using grouped model-run evidence and a shared immutable
envelope writer, preserving partial coverage and true clocks. Estimate: 3 hours.
Acceptance: `.\.venv\Scripts\python -m pytest tests/sources/test_s01_prepare.py -q`.

## A22. Local signed upload proof (D71, 7 November 2026)

T239 is a child of T043 after T229/T235/T238. It validates and signs the exact
prepared envelope for the local Worker ingest contract, checks bounded replies
and preserves prepared state through failures. Its explicit loopback destination
keeps cloud configuration behind the existing capability gate. Estimate 3 hours.
Acceptance is `.\.venv\Scripts\python -m pytest tests/test_hot_upload.py -q`.

## A23. Active-page source polling (D72, 7 November 2026)

T240 is a child of T043 after T040/T229/T239. It adds bounded active-page
polling of the existing S01/S09 Worker response, dated daily fallback and
separate source cutoffs in the map and list. Frozen reports retain their
approved daily release. Estimate 3 hours. Acceptance is
`powershell -NoProfile -File scripts/web.ps1 run test:e2e -- tests/live-data.spec.ts`.

D73 adds the GET `wire_sha256` field to cover supported older stored snapshots
whose current normalization changes optional fields. The original `sha256`
continues to identify the verified stored bytes. The browser verifies the wire
projection with the new digest and supports the earlier response shape when its
digest matches the wire bytes.

## A24. Verified local checkpoint restore (D74, 7 November 2026)

T241 is a child of T043 after T234/T235/T237/T238/T240. Seal a quiescent local
feed state and restore it only at its original absent path using the saved
manifest digest. Preserve source bytes, clocks and admission across recovery.
Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_feed_checkpoint_bundle.py -q`.
D75 requires CAP prepared and control clocks to agree with the retained
ledger, including unchanged-content revalidation and later duplicate bytes.

## A25. Local Worker-gated capture (D76, 7 November 2026)

T242 is a child of T043 after T233/T234/T237/T239/T241. The local capture
entry point requires a successful signed admission for its enabled source
before calling its collector. It retains the collector's own cadence and
cooldown, and uses one bounded child process. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_feed_admission.py -q`.

## A26. Durable local runner checkpoint store (D77, 7 November 2026)

T243 is a child of T043 after T241/T242. A local store outside the feed root
holds verified generations and a serialized, compare-before-write catalogue.
Resume restores the catalogue's verified current generation at the original
absent path and returns its digest for the next save. Apply the quota to the
whole store. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_runner_checkpoint.py -q`.
D78 also requires an empty store for a missing catalogue and includes pending
SQLite pages in the final quota check before installing a generation.

## A27. Bounded local runner cycle (D79, 8 November 2026)

T244 is a child of T043 after T242/T243. Run one source through verified
restore, signed local admission, capture and expected-head save under one
150-second parent deadline. Preserve the working root and stored generations
on interruption. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_runner_cycle.py -q`.

## A28. Bounded local preparation and upload (D80, 8 November 2026)

T245 is a child of T043 after T235/T238/T239/T244. An explicit local runner
option prepares successful capture, saves it, then sends the immutable saved
bytes. Retry the retained snapshot on `not_due`. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_runner_cycle.py -q`.

## A29. Reuse equivalent runner projections (D81, 8 November 2026)

T246 is a child of T043 after T245. The runner reuses verified prepared bytes
when source inputs and projected data match despite a later preparation clock.
Actual source changes and time-dependent projection changes still advance
the head. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/sources/test_s09_prepare.py tests/sources/test_s01_prepare.py -q`.

## A30. Verified hosted checkpoint handoff (D82, 8 November 2026)

T247 is a child of T043 after T243/T246. Verify an artifact candidate against
the configured budget, then import its verified generation into a fresh local
store at the same original path. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_runner_handoff.py -q`.

## A31. Pinned artifact metadata and storage preflight (D83, 8 November 2026)

T248 is a child of T043 after T247. Check one explicitly trusted run and its
checkpoint artifact against the bounded repository inventory. Report actual
listed bytes and both digests without downloading. Estimate 3 hours. Acceptance
is `.\.venv\Scripts\python -m pytest tests/test_hosted_checkpoint.py -q`.

## A32. Immediate hosted predecessor discovery (D84, 8 November 2026)

T249 is a child of T043 after T248. Discover the immediately preceding trusted
workflow run and its checkpoint without skipping gaps. Estimate 3 hours.
Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_hosted_checkpoint.py -q`.

## A33. Verified downloaded checkpoint archive (D85, 8 November 2026)

T250 is a child of T043 after T247/T249. Verify and stage the raw downloaded
ZIP before importing it into an absent store. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_hosted_archive.py -q`.

## Appendix Y: new and changed tasks (YAML)

D51 (6 November 2026): T115/T116 move to P1 for the approved M07 fallback while
S34 owner review is pending. T115 depends on T113/T226 instead of T110; T116
depends on T115/T006/T226. Monthly statistics are EDA only and never daily model
labels. This makes no change to the pending OCR gate or the general Kerala phase.

T228 (D49, 6 November 2026) is a child of T118 in P1, after T117/T226. It pins the
local OCR toolchain/model, extracts existing PDF images with provenance and builds
an offline owner review packet. The source images and OCR text stay in ignored
`data/raw`. Machine acceptance is `python -m pytest tests/sources/test_s34_ocr.py -q`;
it verifies the packet without inventing approval or promoting observations. The
owner must review the sample before any extracted value is used. Full T118 gains
T228 as a dependency and stays pending. Estimate: 3 hours. Files and detailed steps
are in the synchronized YAML below.

```yaml
amendments_version: 1
date: 2026-11-05
new_tasks:
  - id: T250
    parent: T043
    title: "Verify and import a downloaded checkpoint ZIP"
    phase: P1
    state: KA
    depends_on: [T247, T249]
    files: [src/atlas/ingest/hosted_archive.py, tests/test_hosted_archive.py, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Bind the archive to selected size and SHA-256 before opening it"
      - "Bound ZIP metadata and extract only safe manifest-listed files into owned staging"
      - "Reuse the verified bundle importer and document pinned GitHub download inputs"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_hosted_archive.py -q'
      expected: "Verified archives recover exact feed state; invalid archive or manifest data cannot create a store"
    hours: 3
  - id: T249
    parent: T043
    title: "Discover the immediate trusted hosted checkpoint predecessor"
    phase: P1
    state: KA
    depends_on: [T248]
    files: [src/atlas/ingest/hosted_checkpoint.py, tests/test_hosted_checkpoint.py, docs/feeds.md]
    steps:
      - "Pin the active run and verify the immediate predecessor without a success filter"
      - "Verify commit ancestry and exactly one checkpoint using the existing bounded inventory"
      - "Prove gaps, failed predecessors, branch rewrites and ambiguous artifacts fail closed"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_hosted_checkpoint.py -q'
      expected: "Discovery selects the immediate verified checkpoint and never falls back to an older run"
    hours: 3
  - id: T248
    parent: T043
    title: "Verify trusted hosted artifact metadata and retained storage"
    phase: P1
    state: KA
    depends_on: [T247]
    files: [src/atlas/ingest/hosted_checkpoint.py, tests/test_hosted_checkpoint.py, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Check an explicitly pinned workflow run and match its checkpoint artifact by manifest identity"
      - "Account for the bounded repository inventory and reject untrusted, expired or over-budget metadata"
      - "Exercise read-only API and CLI behavior with documented metadata fixtures"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_hosted_checkpoint.py -q'
      expected: "Only the pinned eligible artifact is selected, with complete conservative storage accounting and no fallback"
    hours: 3
  - id: T247
    parent: T043
    title: "Verify and import a hosted checkpoint handoff locally"
    phase: P1
    state: KA
    depends_on: [T243, T246]
    files: [src/atlas/ingest/runner_checkpoint.py, src/atlas/ingest/checkpoint_bundle.py, tests/test_runner_handoff.py, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Offer only the verified current generation and check configured artifact capacity"
      - "Install a downloaded bundle with its separate trusted digest into a fresh store"
      - "Exercise restart, exact bytes, aggregate capacity and damaged transfer refusal locally"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_runner_handoff.py -q'
      expected: "Verified transfers preserve original paths and clocks; invalid or over-budget transfers leave the destination absent"
    hours: 3
  - id: T246
    parent: T043
    title: "Reuse equivalent verified runner projections across cutoffs"
    phase: P1
    state: KA
    depends_on: [T245]
    files: [src/atlas/ingest/prepared.py, src/atlas/ingest/s09_prepare.py, src/atlas/ingest/s01_prepare.py, src/atlas/ingest/runner_cycle.py, tests/sources/test_s09_prepare.py, tests/sources/test_s01_prepare.py, docs/feeds.md]
    steps:
      - "Compare verified provenance and normalized output before reusing the exact prior head"
      - "Keep actual validation and time-dependent changes visible and preserve explicit standalone cutoff behavior"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/sources/test_s09_prepare.py tests/sources/test_s01_prepare.py -q'
      expected: "Unchanged projections reuse exact bytes; expired warnings, changed forecasts, new validations and corrupt heads are distinguished"
    hours: 3
  - id: T245
    parent: T043
    title: "Prepare and upload a verified checkpoint snapshot in the bounded cycle"
    phase: P1
    state: KA
    depends_on: [T235, T238, T239, T244]
    files: [src/atlas/ingest/runner_cycle.py, tests/test_runner_cycle.py, docs/feeds.md]
    steps:
      - "Prepare successful capture and commit verified state before a signed loopback upload"
      - "Retry exact retained prepared bytes on not-due and retain capture state after handled failure"
      - "Prove checkpoint ordering, immutable retry, refusal and the existing bounded entry point"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_runner_cycle.py -q'
      expected: "Only a verified committed snapshot can be sent; failed preparation or upload preserves evidence and exact retry identity"
    hours: 3
  - id: T244
    parent: T043
    title: "Run one bounded local restore, capture and checkpoint cycle"
    phase: P1
    state: KA
    depends_on: [T242, T243]
    files: [src/atlas/ingest/runner_cycle.py, tests/test_runner_cycle.py, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Restore a verified generation before one signed local source capture"
      - "Commit verified capture-stage state against the restored head and retain evidence on refusal"
      - "Exercise the entry point, denial, cooldown persistence and a reaped child timeout"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_runner_cycle.py -q'
      expected: "One bounded local cycle preserves source evidence and cadence; unsafe restores, denied claims and interruptions fail closed"
    hours: 3
  - id: T243
    parent: T043
    title: "Persist verified local runner checkpoint generations"
    phase: P1
    state: KA
    depends_on: [T241, T242]
    files: [src/atlas/ingest/runner_checkpoint.py, src/atlas/ingest/checkpoint_bundle.py, tests/test_runner_checkpoint.py, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Serialize and compare the expected head before sealing and advancing an immutable generation"
      - "Restore a verified current generation to its original absent root and enforce aggregate quota including pending catalogue pages (D78)"
      - "Prove recovery after an interrupted catalogue advance, stale writer, and corrupted generation"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_runner_checkpoint.py -q'
      expected: "Fresh runs resume exact verified state; stale or interrupted writes and invalid recovery leave the prior committed head intact"
    hours: 3
  - id: T242
    parent: T043
    title: "Require signed local Worker admission before feed capture"
    phase: P1
    state: KA
    depends_on: [T233, T234, T237, T239, T241]
    files: [src/atlas/ingest/admission.py, src/atlas/ingest/upload.py, tests/test_feed_admission.py, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Send one bounded signed source claim to the explicit loopback Worker"
      - "Fail closed on denial, mismatched replies or unavailable admission; retain the local collector guard"
      - "Verify exact signing and genuine fixture capture through the bounded entry point"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_feed_admission.py -q'
      expected: "Only matching Worker admission can reach an enabled collector, whose local cadence and cooldown still apply"
    hours: 3
  - id: T241
    parent: T043
    title: "Seal and restore a verified path-bound local feed checkpoint"
    phase: P1
    state: KA
    depends_on: [T234, T235, T237, T238, T240]
    files: [src/atlas/ingest/checkpoint_bundle.py, tests/test_feed_checkpoint_bundle.py, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Inventory and seal the approved local feed-state files with exact manifest hashes and bounded staged copying"
      - "Verify the trusted manifest, stored references and storage budget before restoring to the original absent root"
      - "Prove recovered cadence, cooldown and source snapshot replay using genuine retained fixtures, with CAP clocks checked against the ledger (D75)"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_feed_checkpoint_bundle.py -q'
      expected: "Exact state recovers at the original root; corrupt, incomplete or misdirected bundles preserve the prior state"
    hours: 3
  - id: T240
    parent: T043
    title: "Poll validated hot sources while active and retain dated daily reports"
    phase: P1
    state: KA
    depends_on: [T040, T229, T239]
    files: [web/src/live-data.ts, web/src/live-data.test.ts, web/src/App.tsx, web/src/map/Layers.tsx, web/src/styles.css, web/tests/live-data.spec.ts, docs/feeds.md, worker/src/index.ts, worker/tests/core.test.mjs, docs/worker.md]
    steps:
      - "Validate bounded same-origin Worker replies, wire_sha256 and actual source clocks while preserving stored identity"
      - "Poll alerts at fifteen minutes and weather at six hours with visibility, deadlines and monotonic source checks"
      - "Apply the dated source overlay in the map and list while keeping approved reports immutable"
    acceptance:
      command: 'powershell -NoProfile -File scripts/web.ps1 run test:e2e -- tests/live-data.spec.ts'
      expected: "Mounted browser proves cadence, visibility and dated fallback while frozen reports retain exact identity"
    hours: 3
  - id: T239
    parent: T043
    title: "Verify and sign prepared snapshots for a bounded local Worker upload"
    phase: P1
    state: KA
    depends_on: [T229, T235, T238]
    files: [src/atlas/ingest/upload.py, tests/test_hot_upload.py, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Verify retained preparation identity, hashes, source and cutoff before signing exact gzip bytes"
      - "Send one bounded signed request to an explicit loopback origin and validate the Worker acknowledgement"
      - "Preserve prepared state after repeat or failed sends and prove compatibility using genuine source data"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_hot_upload.py -q'
      expected: "Exact signed bytes pass Worker authentication; invalid inputs, destinations and replies fail without modifying prepared state"
    hours: 3
  - id: T238
    parent: T043
    title: "Prepare a source-bound partial weather snapshot from paired captures"
    phase: P1
    state: KA
    depends_on: [T235, T237]
    files: [src/atlas/ingest/prepared.py, src/atlas/ingest/s09_prepare.py, src/atlas/ingest/s01_prepare.py, tests/sources/test_s01_prepare.py, tests/sources/test_s09_prepare.py, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Extract the reusable bounded immutable envelope writer without changing CAP preparation behavior"
      - "Validate paired receipt/raw hashes, model/point/settling and cutoff eligibility; preserve per-cohort original clocks"
      - "Prepare the first quality-passed future temperature at actual returned grid coordinates, with partial source health and no publication"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/sources/test_s01_prepare.py -q'
      expected: "Weather records preserve genuine values, coordinates, model and availability clocks; corrupt/future/mismatched inputs cannot replace the prepared head"
    hours: 3
  - id: T237
    parent: T043
    title: "Bounded paired S01 capture for the verified Bengaluru profile"
    phase: P1
    state: KA
    depends_on: [T010, T234, T236]
    files: [src/atlas/ingest/s01_collect.py, src/atlas/ingest/schedule.py, src/atlas/ingest/s09_collect.py, src/atlas/ingest/refresh.py, tests/sources/test_s01_collect.py, tests/sources/test_s09_collect.py, tests/test_feed_refresh.py, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Retain stable metadata-before/forecast/metadata-after receipts from the verified named-model point"
      - "Enforce five-second request spacing, five attempts per six-hour admission and durable source-specific cooldown"
      - "Advance only validated settled pairs, with source-enable gates and a bounded child; no projection or cloud activity"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/sources/test_s01_collect.py -q'
      expected: "Real paired evidence survives capture; failed/unsettled/disabled/limited runs cannot advance the validated pointer or invent forecasts"
    hours: 3
  - id: T236
    parent: T043
    title: "Bounded local CAP capture and preparation runner"
    phase: P1
    state: KA
    depends_on: [T234, T235]
    files: [src/atlas/ingest/refresh.py, scripts/feeds.ps1, tests/test_feed_refresh.py, docs/feeds.md]
    steps:
      - "Combine existing capture/preparation in one HTTP-only child with a 150-second parent bound"
      - "Respect shared local admission/backoff and recover retained controls without inventing validation clocks"
      - "Keep partial prepared-only output and preserve prior state after errors/deadlines without cloud activity"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_feed_refresh.py -q'
      expected: "Duplicate/deferred capture makes no excess provider calls; preparation and capture share the hard deadline and retain completed evidence"
    hours: 2
  - id: T235
    parent: T043
    title: "Prepare bounded local CAP snapshots with exact control handling"
    phase: P1
    state: KA
    depends_on: [T229, T230, T232, T234]
    files: [src/atlas/ingest/s09_prepare.py, src/atlas/ingest/s09.py, src/atlas/ingest/s09_collect.py, tests/sources/test_s09_prepare.py, tests/sources/test_s09_collect.py, worker/src/ingest.ts, worker/tests/core.test.mjs, worker/tests/runtime.test.mjs, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Validate retained raw hashes and prepare source-backed warning records with original clocks"
      - "Apply exact Actual/Public Update/Cancel references, including header-only controls; retain partial coverage"
      - "Write bounded immutable envelopes and input manifests atomically without upload or publication approval"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/sources/test_s09_prepare.py -q'
      expected: "Actual source clocks and control identities survive preparation; corrupt or oversized input preserves the last prepared snapshot"
    hours: 3
  - id: T234
    parent: T043
    title: "Bounded local CAP-only collection with durable evidence checkpoints"
    phase: P1
    state: KA
    depends_on: [T230, T231, T232, T233]
    files: [src/atlas/ingest/s09_collect.py, src/atlas/ingest/schedule.py, scripts/feeds.ps1, tests/sources/test_s09_collect.py, docs/feeds.md]
    steps:
      - "Admit a bounded CAP-only subset and preserve raw evidence plus successful per-document checkpoints"
      - "Use ETag revalidation, bounded cache admission, durable Retry-After and local SQL cadence guards"
      - "Enforce an independent subprocess deadline; report partial coverage without publication or activation"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/sources/test_s09_collect.py -q'
      expected: "Interrupted/unchanged/failed collection preserves evidence, clocks and backoff without fake data or cloud activation"
    hours: 3
  - id: T233
    parent: T043
    title: "Durable source-check admission for bounded weather and alert polling"
    phase: P1
    state: KA
    depends_on: [T229, T232]
    files: [worker/schema.sql, worker/src/, worker/tests/, tests/test_schedule_feeds.py, docs/worker.md]
    steps:
      - "Authenticate source-check admission using the server clock and existing HMAC contract"
      - "Use atomic elapsed-cadence and storage/write guards across retries and UTC bucket boundaries"
      - "Verify 24-hour 4/96 caps and actual D1 duplicate admission without deploying"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_schedule_feeds.py -q'
      expected: "Duplicate/delayed jobs and absent runner cache cannot exceed source-check admission caps"
    human_gate: "Cloud activation still requires H05 and the actual free/no-card capability probe"
    hours: 2
  - id: T232
    parent: T043
    title: "Match complete CAP reference identities during supersession"
    phase: P1
    state: KA
    depends_on: [T014, T231]
    files: [src/atlas/ingest/s09.py, tests/sources/test_s09.py, docs/sources/s09.md]
    steps:
      - "Match the complete sender, identifier and sent-time reference required by CAP 1.2"
      - "Preserve unresolved or malformed reference targets instead of guessing"
      - "Keep non-Actual/non-Public messages and Ack/Error controls out of active hazard warnings; reject naive dates"
      - "Test issuer/time collisions and equivalent timezone representations using source-backed copies"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/sources/test_s09.py -q'
      expected: "An update/cancel cannot supersede another issuer or timestamp that merely shares an identifier"
    hours: 1
  - id: T231
    parent: T043
    title: "Version S09 RSS cache entries instead of permanently skipping identifiers"
    phase: P1
    state: KA
    depends_on: [T014, T230]
    files: [src/atlas/ingest/s09.py, tests/sources/test_s09.py, docs/sources/s09.md]
    steps:
      - "Hash actual RSS item contents and compare version fingerprints"
      - "Refetch changed items at known URLs using the existing conditional-GET boundary"
      - "Reject legacy identifier-only skip sets; leave cache-age/checkpoint policy to T043"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/sources/test_s09.py -q'
      expected: "Changed RSS versions cannot disappear behind a previously seen identifier"
    hours: 1
  - id: T230
    parent: T043
    title: "Preserve official area-only alerts in browser and hot transport"
    phase: P1
    state: KA
    depends_on: [T014, T040, T229]
    files: [web/src/, web/tests/area.spec.ts, web/tests/fixtures/sachet-ka-area.json, tests/test_alert_area_context.py, worker/src/ingest.ts, worker/tests/core.test.mjs, worker/tests/runtime.test.mjs]
    steps:
      - "Preserve actual CAP area text and original clocks when a polygon is unavailable"
      - "Keep area-only warnings in state/list/report context without a marker or invented distance"
      - "Verify the real source projection and shared Worker/browser validation"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_alert_area_context.py -q'
      expected: "Official warning survives missing geometry with no fake point, distance or incident claim"
    hours: 1
  - id: T229
    parent: T042
    title: "Hot Worker endpoint implementation and local/CI checks"
    phase: P1
    state: KA
    depends_on: [T006, T040]
    files: [worker/, scripts/worker.ps1, tests/test_worker_core.py, .github/workflows/worker.yml, docs/worker.md]
    steps:
      - "Implement signed bounded uploads, canonical snapshot validation and D1 atomic caps"
      - "Check pure logic and SQLite locally; check actual Miniflare/D1 on supported Ubuntu CI"
      - "Retain explicit unavailable/static fallback; never create accounts, tokens, remote resources or deployment approval"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_worker_core.py -q'
      expected: "Authentication, timestamp/hash, last-good and capacity checks pass; no cloud capability or public deployment claimed"
    human_gate: "Full T042 still requires owner H05 and an actual free/no-card service probe"
    hours: 3
  - id: T228
    parent: T118
    title: "S34 pinned OCR tooling and owner review packet"
    phase: P1
    state: KL
    depends_on: [T117, T226]
    files: [requirements/ocr.in, requirements/ocr.txt, configs/ocr/s34.json, src/atlas/ingest/s34_ocr.py, scripts/s34_ocr_review.py, tests/sources/test_s34_ocr.py, docs/sources/s34-ocr.md]
    steps:
      - "Pin and hash-lock local OCR dependencies and the official language model; record embedded engine version"
      - "Extract real captured PDF images and retain hashes, page numbers, OCR text and word boxes"
      - "Generate an offline local owner review packet; keep source images/text in ignored data/raw"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/sources/test_s34_ocr.py -q'
      expected: "Machine checks pass and a real local review packet exists; no values promoted or owner approval invented"
    human_gate: "Owner reviews the OCR sample before any extracted value is used (T117/T118)"
    hours: 3
  - id: T227
    parent: T114
    title: "S32 daily gap census"
    phase: P1
    state: KL
    depends_on: [T113, T114]
    files: [scripts/s32_history.py, docs/sources/s32-history.md, tests/sources/test_s32_history.py]
    steps:
      - "Fetch every date from 2024-08-15 through 2026-07-15 using the verified date form and shared Fetcher"
      - "Space requests by at least 3 seconds, enforce budgets, resume from immutable evidence"
      - "Separate valid empty reports, quarantined rows and fetch/layout failures; never interpolate missing days"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/sources/test_s32_history.py -q'
      expected: "Every requested date accounted for by cited evidence or explicit failure; no sampled gap claimed as a verified daily gap"
    hours: 2
  - id: T226
    parent: T129
    title: "Kerala configuration bootstrap and existing-evidence audit"
    phase: P1
    state: KL
    depends_on: [T003, T113, T117, T119, T121]
    files: [configs/states/kl.yaml, docs/labels/kerala.md, tests/test_kl_data.py]
    steps:
      - "Load isolated Kerala paths through the existing StateConfig; keep every source disabled"
      - "Audit captured history, units, datum, flood labels and unverified geography without inventing records"
      - "Keep full T129 pending; T226 is only the prerequisite for the D17 dam fallback adapters"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_kl_data.py -q'
      expected: "Two states load with isolated paths; no Kerala source enabled; evidence audit exists"
    hours: 2
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
  - {id: T115, change: "D51: move to P1 for M07 source discovery; replace T110 with T113/T226"}
  - {id: T116, change: "D51: move to P1; depends on T115/T006/T226; monthly EDA only"}
  - {id: T118, change: "D49: add T228 dependency and require owner OCR review before using extracted values"}
  - {id: T114, change: "D46: adapter contract complete independently; daily gap census split into child T227"}
  - {id: T130, change: "D46: add T227 dependency before claiming S32 historical coverage"}
  - {id: T129, change: "D44: add T226 dependency; retain original dependencies and P3 full-audit scope"}
  - {id: T114, change: "D44: add T226 dependency for disabled Kerala configuration"}
  - {id: T118, change: "D44: add T226 dependency for disabled Kerala configuration"}
  - {id: T130, change: "D44: before starting, record resolution of full-T129 dependency and T115/T116 scheduling; no readiness gate is waived"}
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
files of new or changed RSS item versions; `parse(cap, config, polygon=...)` gives one row per alert in the
state (English info block) with `sender` and `msg_type` added (D33); `supersede(table)` drops
replaced alerts and cancels. Geometry is WKB MultiPolygon in lon, lat order. The CAP, polygon
and feed samples are committed as public-domain test fixtures.

T231/D62 replaces the original permanent identifier-only skip set. `feed_versions`
hashes each actual item into a local fingerprint; `known` maps its numeric ID to
that hash. A changed item at an already seen URL must be fetched again. The real
sample's Update `IN-1793881986295019_19` references another message ending `_51`
under the same numeric base. Treating that RSS base as an immutable CAP revision
is therefore not justified. The existing Fetcher still controls conditional GET,
timeouts, retries, budgets and host checks. A channel timestamp change alone does
not change item versions; an empty valid channel is distinct from malformed RSS.

These hashes are local cache metadata, not a newly discovered provider field or
a promise that a linked document cannot change silently. T043 must expire cache
entries, checkpoint only after successful processing and preserve original source
clocks. Bare identifier lists/sets are rejected before any network request.

The [NDMA integration guide](https://sachet.ndma.gov.in/docs/Integration_Guide_For_Agencies.pdf)
also documents retaining XML and its ETag, revalidating a subsequent request to
the CAP URL, reusing XML on 304 and replacing it on 200. It supplies no numeric
refresh TTL or rate quota. That supports conditional revalidation, not a claim
that a skipped document is fresh. The earlier capture remains a single observed
response at that URL; the guide is separate documentation evidence.

T232/D63 matches reference targets by the full `(sender, identifier, sent)` tuple
required by [CAP 1.2 section 3.2.1](https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html).
Only Update/Cancel messages can supersede a predecessor. A relay's sender may
differ from the referenced sender; the reference must match the predecessor,
including its time. Unknown or malformed targets remain unresolved. Matching
normalizes equivalent timezone representations and rejects naive timestamps;
it never substitutes the laptop's timezone. Self-references cannot erase their
own Update warning. Cancel/Ack/Error documents are not active hazard warnings.

Public warnings require explicit Actual/Public lifecycle fields. Known
Test/Exercise/System/Draft or restricted/private messages yield no public warning
rows; missing/unsupported lifecycle values fail closed. Raw evidence remains
separate from this public warning selection. Tests use declared mutated copies
for collisions/control cases, not invented observed predecessor messages.



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

**Outcome: blocked on price units; GODL licence verified.** The 6 Nov 2026 browser
retry resolved the licence blocker. It did not establish the denominator for the
API's min/max/modal prices, so S23 remains disabled. The API key was already
supplied and tested; no new key or licence confirmation is needed.

Structured record: [`configs/sources/s23.yaml`](../../configs/sources/s23.yaml).
Evidence manifest: [`tests/fixtures/s23/manifest.json`](../../tests/fixtures/s23/manifest.json).

| Item | Finding | Evidence |
|---|---|---|
| Resource | `9ef84268-d588-465a-a308-a864a43d0070`, read from the API tab and echoed by the API and public resource metadata | e01, e05 |
| Publisher | Ministry of Agriculture and Farmers Welfare | e01 |
| Snapshot | Captured on 5 Nov: 17,718 current-day records, all dated 05/11/2026; Karnataka 565. No new observation snapshot was fetched in the retry | e01 to e03 |
| Fields | state, district, market, commodity, variety, grade, arrival_date (DD/MM/YYYY), min/max/modal price; no arrivals quantity | e01 |
| Checks | Two pages of 100 Karnataka rows, all distinct; positive ordered min/modal/max prices | e02, e03 |
| Units | API numbers are unlabelled. Catalog Info describes daily wholesale prices without a denominator; selected description/note/field metadata is empty | e01, e04, e05 |
| Licence | The actual resource page states GODL-India for published datasets/resources and metadata; Catalog Info identifies NDSAP and AGMARKNET. Public GODL tabs establish reuse conditions | e04, e06 |

The [resource page](https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)
and [GODL text](https://www.data.gov.in/Godl) rendered in a fresh browser without
authentication or a challenge. The earlier Akamai 403 remains a dated HTTP-client
failure, not a claim that the website is inaccessible today. A separate catalogue
navigation reached a sign-in page and was closed without interaction (D53).

GODL permits lawful reuse, including commercial use, subject to its conditions.
Any use must cite the provider, dataset, publication/version date, resource URL and
licence URL, preserve non-endorsement, and respect exclusions. The numeric
`field_license: 1` in e05 is not decoded or used as the licence proof. The footer's
licence-labelled hyperlink points to MeitY; the separate published GODL navigation
link leads to the actual licence text. No redistribution is introduced here.

Evidence e04 to e06 consists of explicitly labelled browser projections (D53),
not unmodified HTTP responses. They retain source URLs, UTC capture times,
observed HTTP 200 status, field paths/selectors and transformations. The JSON
metadata projection also records the original response hash. Only metadata and
licence text is retained; contacts, user identifiers, cookies, credentials and
authentication URLs are excluded. The content-addressed projections stay local
under `data/raw/S23`; git contains only their manifest. They are not entered into
the Fetcher's HTTP cache, which must never substitute a projection for a server
response. Original e01 to e03 remain unchanged.

**Retry condition:** obtain a publisher statement tied to this resource that
establishes the price denominator and any commodity-specific exceptions. Re-run
T025 and validate the mapping before enabling S23. Do not infer INR/quintal from
the canonical column name, typical AGMARKNET usage or a numeric range. T026 and
the price-model tasks remain blocked for ingestion/use.

The API returned transient 502s before the successful 5 Nov capture. A future
adapter must retry conservatively and preserve dated daily snapshots: the checked
resource supplied a current-day snapshot, not a verified historical archive.



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

# 7.12 Source report S32-HISTORY

Source file: `docs/sources/s32-history.md`

# S32 daily gap census (T227)

**Status: complete availability census, 6 November 2026.** All **700** requested
dates returned correctly dated, validated header-only reports: **700 empty,
0 populated, 0 failed, 0 unattempted**. No dam observations were synthesized.

Evidence: [`s32_history_manifest.json`](../../tests/fixtures/s32_history_manifest.json).
All cited local report bytes and the robots artifact passed SHA256 recomputation.
The census reused 47 previously captured reports and fetched 653 additional
reports. The 700 cited report bodies total 91.63 MiB. Current robots.txt permitted
the path. Every date in the range was accounted for, rather than inferred from
the earlier twice-monthly sample.

This proves that these public KSEB report requests supplied no dam rows for the
checked dates. It does not prove that KSEB holds no underlying observations, and
it never represents an empty report as zero water level or zero storage. M07
requires another verified historical source (S34 OCR is next), plus a known
vertical datum and its other data/evaluation gates.

## Protocol

The requested range is 15 August 2024 through 15 July 2026, inclusive: 700 dates.
`scripts/s32_history.py` uses the verified KSEB GET date form, shared Fetcher and
the T114 parser. Current robots.txt is checked before requests. Every live HTTP
attempt, including redirects and retries, starts at least three seconds after
the previous one. Hash-checked existing report captures may be reused.

Run from the repository with its Python 3.12 interpreter, with TEMP and TMP set
to `D:\monsoon-atlas\.cache\tmp`:

```powershell
.\.venv\Scripts\python scripts/s32_history.py
```

The default checkpoint is `data/manifests/S32/history.json` (local, ignored).
Each date is checkpointed atomically. Re-running rebuilds the census from the
immutable raw ledger and fetches uncaptured dates. Raw report paths in the public
audit manifest are relative to `data/raw`; the legacy ledger can retain relative
or absolute paths. Every cited artifact keeps its original SHA256 and fetch time.

Limits per run: 1,000 HTTP attempts, 1 MiB per response, 256 MiB fetched artifacts,
and a 20 GiB free-space preflight. Three consecutive failures stop new requests.
The remaining dates are marked unattempted with the stopping cause. No TLS,
authentication or robots restriction is bypassed.

## Meaning of outcomes

| Outcome | Meaning |
|---|---|
| `empty` | Correctly dated, complete report with the verified headers and zero dam rows |
| `data` | Report contains dam rows; valid, quarantined and incomplete counts are separate |
| `failed` | Fetch, date/layout, hash or parsing failure; it is not evidence of an empty day |
| `not_attempted` | Requests stopped; the recorded cause explains why this date remains unknown |

`complete` is true only when all 700 dates are classified as validated reports.
An audit with failures can explain its limitations but cannot establish a complete
availability census. No daily observations are interpolated or invented.

The test fixture `tests/fixtures/s32_history_manifest.json` contains only
provenance and counts from this run. Production code never reads test data.
The raw HTML stays in `data/raw/S32` under the existing KSEB attribution/share-alike
policy. T114's quarantine rules and M07's known-datum requirement remain in force.

Acceptance command:

```powershell
.\.venv\Scripts\python -m pytest tests/sources/test_s32_history.py -q
```

Result: **7 passed in 1.08s**. These include real-date accounting, local hash
recomputation, resume without re-fetching, explicit failure/unattempted states,
request pacing and legacy relative-path handling. Independent code review found
no actionable defect. Final full-suite results are recorded in HANDOFF.



---

# 7.13 Source report S32

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

## Adapter implementation (T114, 6 November 2026)

`atlas.ingest.s32.S32` now implements the shared fetch/parse contract. S32 is the
only enabled Kerala source. D46 records the parsing and quarantine policy; the
datum and M07 gates are unchanged. No new upstream requests were made in T114.

- Exactly 17 columns and the dated 07:00 IST title are required. Fetching an
  explicit date uses the discovered `date=YYYY-MM-DD` form. A mismatched date,
  altered header, incomplete table, duplicate dam or wrong artifact hash fails.
- IDs are internal `kseb:<published-district-code>:<normalized-dam-name>`, with
  original name and operator retained. They are not upstream IDs or a cross-source
  alias registry. Unknown geography and vertical datum stay null.
- Today's level/live storage/live capacity are normalized; previous-year columns
  remain in raw evidence. `observed_at`/`valid_at` are 07:00 IST converted to UTC;
  `available_at` is the fetch time. No historical availability is invented.
- Explicit feet convert by 0.3048. A level above the stated MWL, nonpositive
  capacity, negative values or percentage disagreement over 0.1 percentage points
  quarantines the row. Missing core values or validation inputs null the core
  group under D23. `quality_details` explains each rejection; the raw hash remains.
  The latest sample also has inconsistencies (for example Kallarkutty storage /
  capacity does not match its reported percentage). No capacity or percentage
  is silently recalculated. Missing storage is not zero.
- `inflow_m3s` remains null with `inflow_missing_reason=not_reported` because MU
  is energy. `vertical_datum` is null with its own reason. These unsupported
  fields do not erase otherwise valid measurements. Header-only reports yield
  an empty typed table; a blank response raises an error.

Replay of all **77** previously captured report pages (T113 manifest): **50 empty
reports**, 27 reports containing 432 rows: **224 valid**, **154 quality-rejected**,
**54 incomplete**. These are counts of captured samples, not a daily historical
coverage claim. No generated rows were used. Five attributed original title/table
excerpts and their hashes are in `tests/fixtures/s32_samples.json` so CI can run
the adapter checks without local raw data.

The daily gap census **T227** is complete: all 700 dates from 15 Aug 2024 through
15 Jul 2026 returned validated empty reports, with no failed/unattempted dates.
See [the census report](s32-history.md) and its linked per-date manifest. There
were no invented zero readings. Known datum, three years across eight dams, OCR review of S34 and new
dated splits are still prerequisites for M07. Enabling ingestion does not enable
a forecast or certify public deployment.



---

# 7.14 Source report S33

Source file: `docs/sources/s33.md`

# S33 KSEB monthly dam statistics: discovery (T115)

**Outcome: blocked, 6 November 2026.** No usable reservoir artifact was obtained.
This is a discovery result, not a claim that KSEB holds no underlying records.
S33 remains disabled. D51 pulls this check into P1 for the M07 fallback while
the S34 owner OCR review remains pending.

Record: [`configs/sources/s33.yaml`](../../configs/sources/s33.yaml).
Evidence: [`tests/fixtures/s33/manifest.json`](../../tests/fixtures/s33/manifest.json).
The nine successful evidence responses and their SHA256 values are retained;
source bytes stay in ignored `data/raw`. The robots 404 is in `failed_fetches`.

## What was actually checked

| Evidence | Published URL / content | Observed result |
|---|---|---|
| e01 | Main KSEB robots.txt | Allows access |
| e02 | KSEB historic-data dashboard | No verified monthly reservoir archive; its Monthly data link was followed |
| e03 | Main KSEB website terms | CC BY-SA 2.5 India or later; this does not verify the missing dam-file licence |
| e04 | `https://dams.kseb.in/` | HTTP 200 with “wrong address” error text |
| e05 | RFC 9309 | Handling of an unavailable robots file |
| e06 | Published Monthly data link, `https://kseb.in/dashboard/view/consumers` | Electricity consumer counts/consumption; not a reservoir dataset |
| e07 | Published Monthly Statistics article, `https://dams.kseb.in/?p=329` | Same wrong-address error; no file links |
| e08 | Published Statistics index, `https://dams.kseb.in/?page_id=45` | Same error; no file links |
| e09 | Published dams index, `https://dams.kseb.in/?page_id=39` | Same error; no dam registry or datum verified |

The article URLs were located through search results, then fetched through the
shared ingestion boundary. A cached search description mentions daily water
levels collected in monthly reports. The live article returned an error, so that
description is **not verification** of a file, its fields, temporal resolution,
units, archive depth or licence. No resource IDs or download URLs were guessed.
No PDF or spreadsheet was downloaded, and no canonical field mapping was invented.

The dams host's robots file returned HTTP 404. Under
[RFC 9309 section 2.3.1.3](https://www.rfc-editor.org/rfc/rfc9309.html#section-2.3.1.3),
a 4xx robots response permits resource access; server/network failures have a
different, restrictive rule. This justified bounded probes of the published
pages, without overriding TLS, authentication or a robots disallow. Requests were
spaced by at least three seconds. No account, key, card or payment was used.

## Effect on the model and retry condition

No earliest/latest observation dates, reservoir identifiers, measurements, unit
conventions, datum or historical availability were established. The source record
uses null upstream mappings. The main site's open-licence statement is recorded,
but missing reservoir artifacts remain unverified for redistribution.

T116 implements the blocked source contract only: disabled access must raise
`SourceUnavailable`, and no fabricated sample or public rows are permitted.
T130 still has to resolve its explicit dependencies and pass the M07 gate.
Monthly aggregates are EDA-only under the current card and must never be
interpolated into daily seven-day labels. If a future file has actual daily rows,
verify those rows and publication timing, then record a decision before changing
that restriction; a monthly publication cadence alone does not prove granularity.

Retry T115 when KSEB restores the Monthly Statistics/Statistics pages or supplies
a directly linked, licensed reservoir file with dates, units and datum. The S34
owner-review requirement remains separate. No human approval was inferred from
the instruction to continue working.

Acceptance: `python -m pytest tests/sources/test_s33_discovery.py -q` produced
**8 passed in 0.11s**. Checks cover cited discovery claims, disabled status,
actual error/consumer-page content, missing-robots reporting, raw-file hashes
and absence of committed source pages.

## Blocked adapter (T116)

`src/atlas/ingest/s33.py` now implements the blocked-source contract. Both fetch
and parse always raise `SourceUnavailable` with the T115 reason and retry record,
before network or file access. Changing the config flag alone cannot enable an
unverified source. `schemas/s33.json` explicitly remains disabled with no invented
upstream fields. No fabricated sample, dataset rows or public output was created.

Acceptance: `python -m pytest tests/sources/test_s33.py -q` produced **3 passed in
0.42s**, including a forced-enable attempt and a network-call trap. Full-suite
results are in HANDOFF. T116 completion records this disabled behavior only;
it does not clear any M07 data gate or replace the pending S34 owner review.



---

# 7.15 Source report S34-OCR

Source file: `docs/sources/s34-ocr.md`

# S34 OCR review tooling (T228, child of T118)

**Machine preparation complete; owner review pending. Full T118 remains pending
and S34 remains disabled.** No observation, label or prediction rows are created.

## Reproducible local tools

`requirements/ocr.in` and its pip-tools hash lock pin pypdf 6.21.4 (BSD-3-Clause),
tesserocr 2.12.0 (MIT) and Pillow 13.0.0 (MIT-CMU). The Windows Python 3.12 wheel supplies
Tesseract 5.5.3 and Leptonica 1.87.0 without a system installer. The exact embedded
build string is recorded in `configs/ocr/s34.json` and checked at runtime.
The optional OCR group is included in the dependency policy and forbids torch.

Sources: [tesserocr package/installation documentation](https://pypi.org/project/tesserocr/2.12.0/),
[pypdf package](https://pypi.org/project/pypdf/6.21.4/),
[Pillow package](https://pypi.org/project/Pillow/13.0.0/).
The package hashes are in `requirements/ocr.txt`; `pip check` passes locally.

English language data comes from the official
[tessdata_fast repository](https://github.com/tesseract-ocr/tessdata_fast), under
Apache-2.0, commit `87416418657359cb625c412a48b6e1d6d41c29bd`.
The 4,113,088-byte `eng.traineddata` SHA256 is
`7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`.
It lives in ignored `.tools/ocr/tessdata/`, on drive D. No accounts, installer
terms, paid service, GPU training or source PDF downloads were needed.

## Actual sample and known limits

The packet uses existing, hash-checked T117 evidence:

| Evidence | PDF pages (1-based) | Content |
|---|---|---|
| e08 | 3 | KSEB table, 20 June 2020, 11 am |
| e10 | 2, 3 | KSEB and irrigation tables, 1 August 2023, 11 am |

`scripts/s34_ocr_review.py` writes original decoded page images, uncorrected
whole-page OCR text, per-word confidence/coordinates, and eight targeted numeric
cell crops. Every packet records PDF/model/image hashes and engine settings.
The original image/crop is retained unchanged for comparison.

Whole-page English OCR misreads digits, decimals, Malayalam names and row
associations. Coloured backgrounds and grid rules cause additional errors.
After three unsuccessful attempts at a universal recipe, D50 rejects the
assumption that one preprocessing recipe is reliable across these layouts.

Two draft readings are retained for each sample cell: contrast/Lanczos and
binary-80/tight-crop/nearest, both at 3x scale with single-line numeric OCR.
The second records removed grid rows/columns and its content bounding box.
**Six of eight sample cells disagree. No candidate is selected automatically,
including the two that agree.** These development samples do not establish an
OCR accuracy rate or validate a bulk extraction method. Alert colours are not
interpreted. No feet/metres conversion or dam alias mapping is performed here.

The local review index is:
`D:\monsoon-atlas\data\raw\S34\ocr-review\index.html`.
Open its two links, compare both readings to the original crops, and confirm or
correct the eight values/units. Expand the full-page images to verify operator,
date and row associations. Owner review is required by T117's source check and
the T118 process before extracted values may be used. It is a review of this
sample only, not approval of every future OCR result or of M07.

## Files and validation

Restricted PDF images, crops, OCR text and full packet JSON stay in ignored
`data/raw/S34/ocr-review`. The committed `reports/ocr/s34-review.json` contains
only packet/source hashes, source URLs, page IDs, counts and pending status.
Production ingestion does not read test fixtures. S34 stays disabled until its
complete adapter and review requirements pass.

```powershell
.\.venv\Scripts\python -m pip install --require-hashes --only-binary=:all: -r requirements/ocr.txt
.\.venv\Scripts\python scripts/s34_ocr_review.py
.\.venv\Scripts\python -m pytest tests/sources/test_s34_ocr.py -q
```

Set TEMP/TMP to the repository's `.cache/tmp` before downloads (D26). The review
gate rejects a status string or malformed approval; a real owner record must be
tied to the exact packet digest. This is a workflow record, not authentication.
No approval file is produced by the generator. PDF object-header whitespace
warnings are retained; they do not fabricate or correct table contents.

Machine acceptance: **10 passed in 3.88s**. Final suite: **419 passed, 1 skipped,
1 warning in 106.21s**. Lint, formatting, dependency policy, installed-package
compatibility, amendment parity and all 13 local artifact links passed. Independent
read-only review found no actionable defect. The skip and warning are unchanged
S36 PDF-tool availability and MLflow deprecation, described in HANDOFF.



---

# 7.16 Source report S34

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

# 7.17 Source report S35

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

# 7.18 Source report S36

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

# 7.19 Source report S40

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

# 7.20 Source report S43

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

350 tracked files (raw data and secrets are git-ignored).

| File | Bytes |
|---|---|
| `.env.example` | 368 |
| `.gitattributes` | 62 |
| `.github/workflows/ci.yml` | 1,546 |
| `.github/workflows/web.yml` | 1,541 |
| `.github/workflows/worker.yml` | 1,335 |
| `.gitignore` | 564 |
| `AGENTS.md` | 3,472 |
| `CLAUDE.md` | 11 |
| `LICENSE` | 1,217 |
| `README.md` | 1,449 |
| `configs/budgets.yaml` | 1,084 |
| `configs/models/m05.yaml` | 1,109 |
| `configs/models/m06.yaml` | 720 |
| `configs/ocr/s34.json` | 709 |
| `configs/sources/s01.yaml` | 4,308 |
| `configs/sources/s02.yaml` | 4,054 |
| `configs/sources/s08.yaml` | 4,925 |
| `configs/sources/s09.yaml` | 5,042 |
| `configs/sources/s15.yaml` | 3,728 |
| `configs/sources/s16.yaml` | 3,946 |
| `configs/sources/s17.yaml` | 4,514 |
| `configs/sources/s18.yaml` | 3,440 |
| `configs/sources/s22.yaml` | 3,286 |
| `configs/sources/s23.yaml` | 5,338 |
| `configs/sources/s28.yaml` | 5,613 |
| `configs/sources/s32.yaml` | 5,778 |
| `configs/sources/s33.yaml` | 4,078 |
| `configs/sources/s34.yaml` | 5,461 |
| `configs/sources/s35.yaml` | 5,037 |
| `configs/sources/s36.yaml` | 5,900 |
| `configs/sources/s40.yaml` | 5,206 |
| `configs/sources/s43.yaml` | 6,664 |
| `configs/states/ka.yaml` | 5,806 |
| `configs/states/kl.yaml` | 2,593 |
| `docs/CLAUDE_HANDOFF.md` | 11,770 |
| `docs/HANDOFF.md` | 67,918 |
| `docs/account-setup.md` | 1,975 |
| `docs/amendments.md` | 47,399 |
| `docs/amendments.yaml` | 25,304 |
| `docs/decisions.md` | 54,964 |
| `docs/dependency-audit.md` | 21,095 |
| `docs/feeds.md` | 27,439 |
| `docs/gates/core_data_gate.md` | 7,549 |
| `docs/labels/kerala.md` | 7,469 |
| `docs/plan.pdf` | 1,816,140 |
| `docs/planning/1-handoff.pdf` | 69,979 |
| `docs/planning/2-project-overview.pdf` | 49,886 |
| `docs/planning/3-chatgpt-prompt.pdf` | 81,468 |
| `docs/research/kw-live-and-india-data-research.md` | 22,590 |
| `docs/reviews/2026-11-05-continuation.md` | 4,578 |
| `docs/reviews/2026-11-06-p1-batch.md` | 3,381 |
| `docs/reviews/2026-11-06-t235.md` | 2,491 |
| `docs/reviews/2026-11-06-weather-refresh.md` | 2,738 |
| `docs/reviews/2026-11-07-p1-branch.md` | 12,808 |
| `docs/reviews/2026-11-07-t238.md` | 6,249 |
| `docs/reviews/2026-11-07-t239.md` | 10,786 |
| `docs/reviews/2026-11-07-t240.md` | 12,355 |
| `docs/reviews/2026-11-07-t241.md` | 2,924 |
| `docs/reviews/2026-11-07-t242.md` | 1,109 |
| `docs/reviews/2026-11-08-t243.md` | 1,761 |
| `docs/sources/s01.md` | 2,869 |
| `docs/sources/s02.md` | 2,473 |
| `docs/sources/s08.md` | 3,935 |
| `docs/sources/s09.md` | 5,413 |
| `docs/sources/s15.md` | 1,807 |
| `docs/sources/s16.md` | 2,111 |
| `docs/sources/s17.md` | 2,176 |
| `docs/sources/s18.md` | 1,655 |
| `docs/sources/s22.md` | 981 |
| `docs/sources/s23.md` | 3,796 |
| `docs/sources/s28.md` | 3,800 |
| `docs/sources/s32-history.md` | 3,769 |
| `docs/sources/s32.md` | 6,648 |
| `docs/sources/s33.md` | 4,801 |
| `docs/sources/s34-ocr.md` | 4,673 |
| `docs/sources/s34.md` | 3,502 |
| `docs/sources/s35.md` | 2,699 |
| `docs/sources/s36.md` | 4,243 |
| `docs/sources/s40.md` | 3,572 |
| `docs/sources/s43.md` | 3,475 |
| `docs/web-dependencies.md` | 2,041 |
| `docs/web-layers.md` | 2,802 |
| `docs/web-lens.md` | 2,789 |
| `docs/web-shell.md` | 2,724 |
| `docs/worker.md` | 7,469 |
| `handoff/CLAUDE_START_PROMPT.txt` | 1,257 |
| `handoff/MONSOON_ATLAS_FULL_HANDOFF.md` | 326,989 |
| `models/registry/M05/v1.approval.json` | 128 |
| `models/registry/M05/v1.evaluation.json` | 1,269 |
| `models/registry/M05/v1.json` | 1,853 |
| `models/registry/m06.json` | 1,069 |
| `notebooks/models/m06.ipynb` | 814 |
| `pyproject.toml` | 1,251 |
| `reports/models/m05.md` | 2,415 |
| `reports/models/m06-data-gate.json` | 1,976 |
| `reports/models/m06.md` | 2,721 |
| `reports/ocr/s34-review.json` | 880 |
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
| `requirements/ocr.in` | 139 |
| `requirements/ocr.txt` | 12,261 |
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
| `schemas/s22.json` | 148 |
| `schemas/s23.json` | 144 |
| `schemas/s32.json` | 2,584 |
| `schemas/s33.json` | 499 |
| `schemas/s40.json` | 994 |
| `scripts/audit_dependencies.py` | 9,836 |
| `scripts/build_handoff.py` | 4,322 |
| `scripts/feeds.ps1` | 2,229 |
| `scripts/m05_release.py` | 7,307 |
| `scripts/s32_history.py` | 7,265 |
| `scripts/s34_ocr_review.py` | 5,238 |
| `scripts/web.ps1` | 660 |
| `scripts/worker.ps1` | 566 |
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
| `src/atlas/data/validate.py` | 5,388 |
| `src/atlas/features/__init__.py` | 55 |
| `src/atlas/features/base.py` | 4,184 |
| `src/atlas/features/m05.py` | 10,015 |
| `src/atlas/features/m06.py` | 2,030 |
| `src/atlas/ingest/__init__.py` | 0 |
| `src/atlas/ingest/admission.py` | 5,088 |
| `src/atlas/ingest/base.py` | 1,090 |
| `src/atlas/ingest/checkpoint_bundle.py` | 26,069 |
| `src/atlas/ingest/discovery.py` | 6,522 |
| `src/atlas/ingest/hosted_archive.py` | 9,138 |
| `src/atlas/ingest/hosted_checkpoint.py` | 12,773 |
| `src/atlas/ingest/http.py` | 12,507 |
| `src/atlas/ingest/prepared.py` | 7,706 |
| `src/atlas/ingest/raw_store.py` | 2,638 |
| `src/atlas/ingest/refresh.py` | 3,291 |
| `src/atlas/ingest/runner_checkpoint.py` | 11,675 |
| `src/atlas/ingest/runner_cycle.py` | 5,314 |
| `src/atlas/ingest/s01.py` | 8,607 |
| `src/atlas/ingest/s01_collect.py` | 10,416 |
| `src/atlas/ingest/s01_prepare.py` | 12,341 |
| `src/atlas/ingest/s02.py` | 7,451 |
| `src/atlas/ingest/s08.py` | 7,562 |
| `src/atlas/ingest/s09.py` | 13,751 |
| `src/atlas/ingest/s09_collect.py` | 9,672 |
| `src/atlas/ingest/s09_prepare.py` | 10,367 |
| `src/atlas/ingest/s15.py` | 4,741 |
| `src/atlas/ingest/s16.py` | 6,975 |
| `src/atlas/ingest/s17.py` | 8,753 |
| `src/atlas/ingest/s18.py` | 820 |
| `src/atlas/ingest/s22.py` | 671 |
| `src/atlas/ingest/s23.py` | 681 |
| `src/atlas/ingest/s32.py` | 13,359 |
| `src/atlas/ingest/s33.py` | 850 |
| `src/atlas/ingest/s34_ocr.py` | 12,964 |
| `src/atlas/ingest/s40.py` | 5,975 |
| `src/atlas/ingest/schedule.py` | 4,648 |
| `src/atlas/ingest/upload.py` | 8,871 |
| `src/atlas/jsonl.py` | 1,222 |
| `src/atlas/models/__init__.py` | 55 |
| `src/atlas/models/base.py` | 3,119 |
| `src/atlas/models/evaluate.py` | 2,741 |
| `src/atlas/models/m05.py` | 13,163 |
| `src/atlas/models/m06.py` | 840 |
| `src/atlas/models/registry.py` | 4,565 |
| `src/atlas/models/splits.py` | 4,670 |
| `src/atlas/models/uncertainty.py` | 3,301 |
| `src/atlas/spatial/__init__.py` | 85 |
| `src/atlas/spatial/crosswalk.py` | 3,612 |
| `src/atlas/spatial/places.py` | 6,284 |
| `tests/conftest.py` | 1,306 |
| `tests/fixtures/README.md` | 4,852 |
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
| `tests/fixtures/s23/manifest.json` | 3,665 |
| `tests/fixtures/s28/manifest.json` | 5,657 |
| `tests/fixtures/s32/manifest.json` | 42,942 |
| `tests/fixtures/s32_history_manifest.json` | 552,547 |
| `tests/fixtures/s32_kseb_e02.html` | 18,788 |
| `tests/fixtures/s32_kseb_e03.html` | 18,853 |
| `tests/fixtures/s32_kseb_e04.html` | 1,877 |
| `tests/fixtures/s32_kseb_e09.html` | 18,791 |
| `tests/fixtures/s32_kseb_e10.html` | 18,776 |
| `tests/fixtures/s32_samples.json` | 3,179 |
| `tests/fixtures/s33/manifest.json` | 4,712 |
| `tests/fixtures/s34/manifest.json` | 7,573 |
| `tests/fixtures/s35/manifest.json` | 3,567 |
| `tests/fixtures/s36/manifest.json` | 5,965 |
| `tests/fixtures/s40/manifest.json` | 6,844 |
| `tests/fixtures/s43/manifest.json` | 6,323 |
| `tests/models/test_leakage.py` | 8,466 |
| `tests/models/test_m05_features.py` | 5,348 |
| `tests/models/test_m05_fit.py` | 5,432 |
| `tests/models/test_m05_gate.py` | 3,544 |
| `tests/models/test_m06_features.py` | 2,154 |
| `tests/models/test_m06_fit.py` | 1,684 |
| `tests/models/test_m06_gate.py` | 1,544 |
| `tests/models/test_release.py` | 5,673 |
| `tests/sources/conftest.py` | 1,952 |
| `tests/sources/test_s01.py` | 7,928 |
| `tests/sources/test_s01_collect.py` | 10,207 |
| `tests/sources/test_s01_discovery.py` | 2,604 |
| `tests/sources/test_s01_prepare.py` | 22,072 |
| `tests/sources/test_s02.py` | 6,499 |
| `tests/sources/test_s02_discovery.py` | 2,335 |
| `tests/sources/test_s08.py` | 6,929 |
| `tests/sources/test_s08_discovery.py` | 3,002 |
| `tests/sources/test_s09.py` | 16,583 |
| `tests/sources/test_s09_collect.py` | 13,809 |
| `tests/sources/test_s09_discovery.py` | 2,597 |
| `tests/sources/test_s09_prepare.py` | 18,606 |
| `tests/sources/test_s15.py` | 5,037 |
| `tests/sources/test_s15_discovery.py` | 1,960 |
| `tests/sources/test_s16.py` | 4,971 |
| `tests/sources/test_s16_discovery.py` | 2,426 |
| `tests/sources/test_s17.py` | 5,260 |
| `tests/sources/test_s17_discovery.py` | 1,994 |
| `tests/sources/test_s18.py` | 1,418 |
| `tests/sources/test_s18_discovery.py` | 1,192 |
| `tests/sources/test_s22.py` | 1,852 |
| `tests/sources/test_s22_discovery.py` | 1,008 |
| `tests/sources/test_s23.py` | 2,105 |
| `tests/sources/test_s23_discovery.py` | 3,660 |
| `tests/sources/test_s28_discovery.py` | 987 |
| `tests/sources/test_s32.py` | 9,785 |
| `tests/sources/test_s32_discovery.py` | 3,780 |
| `tests/sources/test_s32_history.py` | 5,919 |
| `tests/sources/test_s33.py` | 1,944 |
| `tests/sources/test_s33_discovery.py` | 2,268 |
| `tests/sources/test_s34_discovery.py` | 2,273 |
| `tests/sources/test_s34_ocr.py` | 5,690 |
| `tests/sources/test_s35_discovery.py` | 1,951 |
| `tests/sources/test_s36_discovery.py` | 3,470 |
| `tests/sources/test_s40.py` | 4,476 |
| `tests/sources/test_s40_discovery.py` | 2,055 |
| `tests/sources/test_s43_discovery.py` | 2,136 |
| `tests/spatial/test_places.py` | 6,877 |
| `tests/test_alert_area_context.py` | 2,034 |
| `tests/test_asof.py` | 9,539 |
| `tests/test_config.py` | 8,278 |
| `tests/test_core_data_gate.py` | 2,282 |
| `tests/test_discovery.py` | 2,612 |
| `tests/test_environment.py` | 1,491 |
| `tests/test_feed_admission.py` | 8,482 |
| `tests/test_feed_checkpoint_bundle.py` | 17,726 |
| `tests/test_feed_refresh.py` | 7,819 |
| `tests/test_hosted_archive.py` | 8,102 |
| `tests/test_hosted_checkpoint.py` | 12,192 |
| `tests/test_hot_upload.py` | 20,401 |
| `tests/test_http.py` | 12,486 |
| `tests/test_kl_data.py` | 2,424 |
| `tests/test_layers.py` | 2,453 |
| `tests/test_lens.py` | 3,621 |
| `tests/test_locks.py` | 6,270 |
| `tests/test_runner_checkpoint.py` | 10,939 |
| `tests/test_runner_cycle.py` | 12,307 |
| `tests/test_runner_handoff.py` | 8,068 |
| `tests/test_schedule_feeds.py` | 4,171 |
| `tests/test_storage.py` | 10,253 |
| `tests/test_web_manifest.py` | 2,990 |
| `tests/test_worker_core.py` | 4,106 |
| `web/.npmrc` | 58 |
| `web/.nvmrc` | 8 |
| `web/index.html` | 483 |
| `web/package-lock.json` | 62,520 |
| `web/package.json` | 730 |
| `web/playwright.config.ts` | 599 |
| `web/src/App.tsx` | 11,217 |
| `web/src/MapView.tsx` | 3,710 |
| `web/src/area.test.ts` | 1,745 |
| `web/src/components/EventTicker.tsx` | 1,585 |
| `web/src/components/PlaceLens.tsx` | 7,972 |
| `web/src/components/SourceBadge.tsx` | 1,873 |
| `web/src/data.test.ts` | 5,403 |
| `web/src/data.ts` | 16,686 |
| `web/src/live-data.test.ts` | 13,718 |
| `web/src/live-data.ts` | 7,933 |
| `web/src/main.tsx` | 196 |
| `web/src/map/Layers.test.ts` | 3,084 |
| `web/src/map/Layers.tsx` | 3,094 |
| `web/src/report.test.ts` | 4,351 |
| `web/src/report.ts` | 4,223 |
| `web/src/styles.css` | 15,325 |
| `web/src/time.ts` | 200 |
| `web/tests/area.spec.ts` | 2,093 |
| `web/tests/fixtures/bangalore-place.json` | 531 |
| `web/tests/fixtures/bangalore-place.provenance.json` | 952 |
| `web/tests/fixtures/openmeteo-temperature-point.json` | 943 |
| `web/tests/fixtures/openmeteo-temperature-point.provenance.json` | 569 |
| `web/tests/fixtures/sachet-ka-area.json` | 1,079 |
| `web/tests/fixtures/sachet-ka-area.provenance.json` | 377 |
| `web/tests/fixtures/sachet-ka-point.json` | 1,094 |
| `web/tests/fixtures/sachet-ka-point.provenance.json` | 500 |
| `web/tests/layers.spec.ts` | 4,920 |
| `web/tests/lens.spec.ts` | 5,209 |
| `web/tests/live-data.spec.ts` | 11,493 |
| `web/tests/shell.spec.ts` | 5,482 |
| `web/tsconfig.json` | 381 |
| `web/vite.config.ts` | 176 |
| `worker/package-lock.json` | 61,843 |
| `worker/package.json` | 378 |
| `worker/schema.sql` | 3,598 |
| `worker/src/feed-check.ts` | 2,690 |
| `worker/src/index.ts` | 5,857 |
| `worker/src/ingest.ts` | 5,404 |
| `worker/src/responses.ts` | 308 |
| `worker/tests/core.test.mjs` | 9,576 |
| `worker/tests/runtime-config.mjs` | 506 |
| `worker/tests/runtime.test.mjs` | 7,640 |
| `worker/tsconfig.json` | 297 |
| `worker/wrangler.toml` | 386 |



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
1747a53 2026-11-05 Handoff: combined full handoff document for ChatGPT
7c0c8f5 2026-11-05 T226: Bootstrap isolated Kerala config and audit continuation readiness
812e111 2026-11-06 T114: Parse KSEB daily dam reports with strict quarantine and provenance
e017b1e 2026-11-06 T227: Audit every KSEB date in the 700-day history gap
67a47c6 2026-11-06 T228: Prepare pinned local OCR review packets with unresolved candidates
e613666 2026-11-06 T115: Verify KSEB monthly archive access and record blocked evidence
546ad49 2026-11-06 T116: Fail closed for unavailable KSEB monthly statistics
53ad4de 2026-11-06 T025: Verify GODL licence while keeping unlabelled prices disabled
fa6589c 2026-11-06 T024: Add fail-closed India Data Portal adapter
d2ae46b 2026-11-06 T026: Keep mandi price ingestion disabled until units are verified
882521b 2026-11-06 T035: Record blocked M06 price-history gate without synthetic labels
aa3ca68 2026-11-06 T036: Preserve no-model state for blocked price training
5da4702 2026-11-06 T037: Publish evidence-backed blocked price-model status
4f3c36e 2026-11-06 T038: Build typed responsive map shell with immutable snapshot loading
3dbbd04 2026-11-06 T039: Add dated provenance layers, area-aware radius and pausable alerts
03383a2 2026-11-06 T040: Add frozen place reports, source-backed tabs and printable PDF
d5dc0f2 2026-11-06 T229: Implement signed hot-data Worker with atomic caps and local checks
3360eae 2026-11-06 T229: Adapt runtime harness to installed Miniflare 5 configuration
cc3b025 2026-11-06 T229: Preserve actual source age and identify D1 schema failures
4cdffde 2026-11-06 T229: Avoid comment-only SQL tails in pinned D1 runtime
5868748 2026-11-06 T229: Record successful local and supported D1 runtime verification
8565cc9 2026-11-06 T230: Preserve official area-only alerts and verify stored bytes before normalization
504de77 2026-11-06 T230: Record passing browser and area-only D1 integration checks
9dbb233 2026-11-06 T231: Revalidate changed RSS versions at known CAP URLs
acd8168 2026-11-06 T232: Match complete CAP references and filter public warning lifecycle
f48d418 2026-11-06 T233: Add signed atomic source-check admission and elapsed cadence caps
1d226c7 2026-11-06 T233: Record passing durable admission and full regression checks
2b949c7 2026-11-06 T234: Bound local CAP capture and fix reviewed retry and source-clock validation
c186d5e 2026-11-06 T234: Record collector acceptance and independent review fixes
bc8ed92 2026-11-06 T234: Record passing Windows and Ubuntu CI and draft PR
6aa8b24 2026-11-06 T235: Prepare immutable partial CAP snapshots and preserve exact control history
08fd4d0 2026-11-06 T235: Record preparation acceptance and independent review regressions
0b8fa6a 2026-11-06 T236: Bound local CAP capture and preparation under one recoverable deadline
88543ba 2026-11-06 T236: Record bounded refresh acceptance and live smoke
c848989 2026-11-06 T237: Capture bounded paired weather evidence and retain recovery data on failures
02d0ec7 2026-11-06 T237: Record weather capture acceptance and joint review fixes
3740347 2026-11-06 T238: Record source-bound weather preparation scope before implementation
1fad828 2026-11-06 T237: Record successful CI rerun and investigated browser timeout
4d46546 2026-11-07 T238: Prepare source-bound weather snapshots from paired receipts
6c7d42d 2026-11-07 T238: Record 606-test acceptance and independent weather preparation review
883eff0 2026-11-07 T235: Record CAP review corrections before implementation
fcc7880 2026-11-07 T239: Record bounded local upload scope and acceptance before implementation
6ea389c 2026-11-07 T235: Preserve CAP warning text and refuse disabled preparation
a58a47c 2026-11-07 T235: Record branch review fixes and 613-test acceptance
05ff03f 2026-11-07 T239: Sign and send verified prepared snapshots over loopback
191248e 2026-11-07 T239: Record signed upload review and full regression evidence
aba2c2a 2026-11-07 T239: Exercise local upload CLI in core-only CI environments
0682fa3 2026-11-07 T240: Record active-page source polling scope and acceptance
47fee40 2026-11-07 T240: Poll validated active Karnataka sources
95f69db 2026-11-07 T240: Record separate wire digest for supported stored snapshots
77b0c16 2026-11-07 T240: Verify Worker wire digest separately from stored identity
d495dbe 2026-11-07 T240: Record polling acceptance and Worker compatibility review
8b14262 2026-11-07 T240: Synchronize the paused-clock map assertion with lazy mount
befe64a 2026-11-07 T241: Record the local path-bound checkpoint scope
2f44faf 2026-11-07 T241: Seal and restore verified local feed checkpoints
7435334 2026-11-07 T241: Record CAP checkpoint clock validation
cdefdb8 2026-11-07 T241: Verify CAP checkpoint clocks against retained events
4bb7130 2026-11-07 T241: Record local checkpoint acceptance and review
87c1493 2026-11-07 T242: Record local Worker-gated capture scope
0f1775a 2026-11-07 T242: Require local Worker admission before source capture
e471d26 2026-11-07 T242: Record local admission verification and review
a21e0bb 2026-11-07 T243: Record durable local checkpoint store scope
9032843 2026-11-07 T243: Commit and resume verified runner checkpoint generations
777dfaf 2026-11-07 T243: Record catalogue loss and quota boundary safeguards
7a51610 2026-11-07 T243: Protect lost catalogues and reserve pending SQLite pages
f2a7fc8 2026-11-08 T243: Record runner checkpoint review and recovery evidence
2346a17 2026-11-08 T244: Record bounded local runner cycle scope
350f548 2026-11-08 T244: Run a bounded restored local capture cycle
bef459c 2026-11-08 T245: Record bounded local preparation and upload scope
0f4a090 2026-11-08 T245: Prepare and send the committed local snapshot
754c898 2026-11-08 T246: Record equivalent projection reuse scope
44bc5b8 2026-11-08 T246: Reuse verified projections when source evidence and output match
ca99d4f 2026-11-08 T247: Record verified hosted checkpoint handoff scope
3a9a139 2026-11-08 T247: Verify and import checkpoint artifact handoffs
3e4091f 2026-11-08 T248: Record pinned hosted artifact preflight scope
33287e1 2026-11-08 T248: Verify pinned hosted checkpoint metadata
0898b54 2026-11-08 T249: Record immediate hosted predecessor discovery scope
c6a19b1 2026-11-08 T249: Discover the immediate trusted checkpoint predecessor
fad30e5 2026-11-08 T250: Record downloaded checkpoint archive verification scope
75f7f67 2026-11-08 T250: Verify and import downloaded checkpoint ZIP archives
```



---

# 12. Feed and checkpoint operations

Source file: `docs/feeds.md`

# Local CAP capture (T234)

Run one bounded, public-source-only capture from the repository:

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 --max-documents 30
```

The parent kills and reaps its HTTP-only child after 120 seconds. Process startup
and cleanup add overhead; this is not certification of a three-minute cloud job.
The child must not spawn descendants. Maximum admission is 30 CAP documents,
with one second before every HTTP attempt, a shared request budget, conditional
GET and the existing host/TLS/byte protections. Polygon requests are omitted.

`.cache/feeds/control.sqlite` holds local elapsed-cadence admission (15 minutes
for S09), provider Retry-After cooldown and per-document work. Duplicate local
processes share that file. Keep the whole directory, including raw evidence and
its ledger: copying the SQLite file alone is insufficient. Do not delete it to
bypass throttling. A lost or aborted run consumes its admission slot. This local
guard cannot replace the T233 D1 guard across independent cloud runners.
Retry-After is saved from retryable response headers even on the final allowed
attempt, before reading the body. It does not depend on another retry remaining.

New/changed item fingerprints and oldest attempts share bounded admission;
failures rotate rather than monopolizing the queue. Linked CAPs become eligible
for revalidation after 15 minutes, even with an unchanged RSS item. This age is
an engineering revisit target, not a provider freshness promise. RSS 304 does
not check linked documents. A successful CAP 304 advances only that document's
check clock; content origin, source issue time and original bytes remain retained.
Checkpoints advance only after header/content validation. Malformed downloaded
evidence stays in the raw ledger while the last good checkpoint survives.

Every result is **partial**. The all-India feed is a limited rolling window;
bounded work, failures and CAP-only text matching cannot certify complete
Karnataka coverage or absence of hazards. Disappearing items remain stored and
do not imply cancellation. Header-only control messages retain their actual
identity/references without fabricated warning fields. Their eventual application
to retained warnings belongs to the normalization/producer task.

No reviewed snapshot, browser polling, cloud upload, resource or recurring
workflow is created. Full T043 remains pending producer/projection, durable
runner restoration/backoff integration, bounded workflow tests and H05.

## Local snapshot preparation (T235)

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 prepare
```

This reads retained CAP evidence without provider calls. If S09 is disabled,
preparation stops before reading the ledger. Every input hash/path is checked.
A 304 check retains the original content's first retrieval clock.
Only Actual/Public messages with issue times at or before the cutoff enter
control handling. Exact sender/identifier/sent references apply even for
header-only Updates and Cancels; these contribute no invented warning rows.
Ack/Error and non-public controls cannot remove a
warning. Expired messages stay in raw history and leave the current projection.
Malformed documents retain dated last-good warnings and explicitly partial
health; their downloads cannot refresh the successful validation clock.

The `s09-prepared-v2` projection uses the selected CAP info block's original
headline as warning text. It falls back to that block's description and then its
event. The adapter selects the first English info block when present and the
first info block otherwise. Existing v1 prepared files remain immutable.

`.cache/feeds/prepared/` contains content-addressed envelopes and input manifests.
Their local `prepared.json` pointer is **prepared_only**, without publication
approval. Payload and input hashes are distinct and cover their exact bytes.
Both raw and compressed transport sizes must fit one MiB. The pointer moves
atomically after the immutable files exist; concurrent/older preparations cannot
roll it back, and different bytes at the same cutoff conflict. Corruption or a
failed preparation preserves the previous pointer. No files are purged.
Preparation reads the ledger strictly. A damaged entry, even one the collector's
tolerant reader can skip, stops preparation. Known input identities and their
content clocks cannot disappear or move between later preparations; deleting or
retargeting a completed control entry cannot resurrect its warning. Restore
damaged evidence from retained originals rather than bypassing these checks.
The report cutoff stays separate from the actual preparation time stored in
`published_at`; repeated identical preparation preserves that first creation
time and byte identity. This field does not grant public publication approval.

All prepared S09 results remain partial, including empty/expired-state results.
The Worker validator can carry partial health with its actual validation clock;
it does not relabel that source available. Python-produced bytes are checked
against the actual Worker validator in the optional local integration test.
Preparation performs no upload or public release. Full T043 still needs the
bounded scheduling/upload integration, with H05/H11 before cloud/public
activation.

## One bounded local refresh (T236)

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 refresh --max-documents 30
```

The parent gives the entire capture/preparation child 150 seconds. Neither phase
launches another process. Completed raw/checkpoint writes and atomic prepared
files survive a deadline. Startup/cleanup overhead is additional; this is not
certification of a three-minute GitHub job.

The JSON result reports both collection and preparation. A not-due/deferred or
failed provider check can still prepare already retained evidence, including a
completed control captured before an interruption. Its actual validation clock
stays dated; preparing again does not make the source newly validated. Identical
replay at one cutoff keeps its byte identity. Missing/corrupt evidence fails
preparation and retains the previous head; absence of evidence cannot generate
a fake empty feed. The public command exits unsuccessfully on failed preparation
or a deadline.
Recoverable capture I/O failures are retained in `collection` diagnostics while
usable dated evidence is still prepared. Explicit source-disable and invalid
input errors stop the command before preparation.

This runner is local S09 preparation. Authenticated cloud admission/upload,
durable cloud restoration and scheduling remain in T043. No credential,
account, recurring job or public release is used.

## Paired local weather capture (T237)

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 weather
```

The verified profile queries Bengaluru (12.97,77.59) using named model
`ecmwf_ifs025`; the source returns grid centre (13.0,77.5). This is one model grid
point, with partial coverage. It establishes no statewide weather coverage.

Capture retains metadata-before, forecast and metadata-after together, including
their exact hashes and HTTP validation clocks. A changed model run, pre-settling
forecast response, unexpected grid or absence of a quality-passed future
temperature cannot replace the validated-pair pointer. Waiting after an early
capture does not certify its model vintage. Raw body bytes and every completed
attempt receipt remain stored under `.cache/feeds/weather/`; later revalidation
does not overwrite original receipts. The pointer also rejects older model runs
and regressing capture clocks. Offline weather preparation is described below.
Each newly completed receipt is saved before the previous head is checked. If
that head or its old receipt is damaged, advancement fails and the result still
includes the new immutable receipt's path/hash; the grouping is not lost.

Shared local admission allows at most four six-hour checks per UTC day. Each
weather run admits at most five HTTP attempts, including retries/redirects, so
the initial 20/source/day weather cap is respected. Every underlying attempt
waits five seconds; a normal metadata/forecast/metadata capture uses three calls.
Retry-After is durable and source-specific. A 120-second parent deadline bounds
the child, with startup/cleanup overhead additional. Both local source producers
check enabled-source flags before any provider call. No account, upload,
projection, recurring job or deployment is created.

## Offline weather preparation (T238)

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 weather-prepare
```

This command reads `.cache/feeds/weather/pairs/` and `weather/raw/` without
network requests. `--root` accepts the common feed root. Only complete validated
receipts for the verified Bengaluru `ecmwf_ifs025` request can supply the single
temperature record. Receipt completion and all three HTTP clocks must precede
the report cutoff. The newest eligible model initialization, then newest capture,
supplies the first quality-passed finite temperature at or after the cutoff.
The original value, unit and returned grid centre (13.0,77.5) are preserved;
this is a model-grid forecast, with partial single-point coverage.

For each model/run/forecast-content cohort, `fetched_at` remains its earliest
qualified forecast HTTP retrieval and `available_at` waits for its earliest
complete validated receipt. Revalidation advances only the selected cohort's
actual `last_success_at`; preparing again cannot imply a provider check.
Settling is verified at retrieval, so waiting cannot certify an early attempt.

The shared immutable writer stores prepared-only envelopes and input manifests
in `weather/prepared/`, with the same one-MiB canonical/compressed body bounds,
quota, atomic monotonic pointer, same-cutoff conflicts and idempotent replay as
CAP preparation. `published_at` is the actual local creation time. Receipt/raw
corruption, missing known evidence, disabled source, or no eligible future row
preserves the previous output. A missing latest-pair pointer may recover a fully
qualified archived receipt; a present damaged pointer stops preparation.
Keep all receipts and raw bytes. Nothing is purged, uploaded, scheduled,
approved for publication or activated by this command.

## Signed local Worker upload (T239)

With a local Worker already running and `ATLAS_INGEST_HMAC_KEY` set in the
environment to the same value (at least 32 characters), run:

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 upload-local --source S09 --origin http://127.0.0.1:8787
```

Choose `S01` for `weather/prepared/` or `S09` for `prepared/`; `--root` accepts
the common feed root. The explicit origin must be `http://127.0.0.1:<port>`
without a trailing slash, path, query, fragment or credentials. Environment
proxies and redirects are disabled. The environment key is never a CLI argument.

The sender verifies the prepared-only pointer, immutable payload and streamed
input-manifest hash, then signs a deterministic gzip of the exact prepared
bytes. One HTTP-only child has a 15-second deadline, finite request timeouts,
one request and a 4096-byte acknowledgement limit. Startup/cleanup add overhead.
Success reports the Worker's normalized `snapshot_id` separately from the local
`prepared_sha256`. A repeat sends identical bytes for Worker idempotency.
Failures preserve preparation and report bounded diagnostics without response
bodies. This local acknowledgement grants no static publication approval.
Remote destinations, durable cloud restoration and scheduled admission remain
T043 work behind the existing activation gates.

## Active Karnataka view (T240)

The normal Karnataka view starts checking `/api/v1/current` after it verifies
an approved daily release. It checks S09 every 15 minutes and S01 every six
hours, with S09 first when both are due. One request runs at a time with a
five-second deadline and a one-MiB response limit. A started check uses its
cadence slot even if it fails or the tab becomes hidden. Returning to the tab
checks due sources. Refreshing the daily release keeps the source cadence.

The map, list and ticker use the verified active source data where available.
Each source shows its cutoff, last successful check and coverage separately.
A partial S09 result can contain zero records while coverage remains limited.
S01 coverage is confined to the reported model grid points. On failure or
when the active source predates the daily cutoff or last successful daily
check, the view uses that source's dated daily data where available. The
fallback label also appears when the daily release contains no rows for the
source. Previously accepted source clocks guard against older or conflicting
responses across failures.

The daily release still provides the cutoff and verified hash for Place Lens,
frozen links and print. Frozen, invalid shared and unreleased views skip the
active checks. Cloud routing, remote upload, durable restoration, archiving
and public activation stay behind their existing gates.

## Local checkpoint and recovery (T241)

1. Stop local capture, refresh and preparation processes. Keep the feed tree,
   bundle and their parent directories idle until each command finishes. Run
   one checkpoint operation at a time.
2. Save to a new directory with an existing parent, outside the feed tree.

   ```powershell
   rtk proxy powershell -NoProfile -File scripts/feeds.ps1 checkpoint-save --bundle .cache/feeds-checkpoint-01
   ```

   Record the reported `manifest_sha256` separately from the bundle. Keep both
   for recovery.
3. When recovery is needed, hold any remaining feed tree aside so the original
   path is absent. Set `$savedManifestSha256` to the separately recorded digest
   and restore to that original path.

   ```powershell
   rtk proxy powershell -NoProfile -File scripts/feeds.ps1 checkpoint-restore --bundle .cache/feeds-checkpoint-01 --expected-sha256 $savedManifestSha256
   ```

Both commands default to `.cache/feeds`. Use `--root` for a different local feed
directory and supply that same canonical absolute location on restore. The
versioned `manifest.json` binds that location and lists each member of `files/`
by relative path, byte length and SHA-256. The separately saved digest is the
integrity check for the manifest and its file list. The archive quota counts
repository data, the current input tree and the incoming copy. Sibling bundles
count toward that quota when they sit within repository data. Save and restore
leave the configured physical free-space reserve on the destination drive.

The bundle requires the shared `control.sqlite` and retains exact SQLite
controls, raw S09 and S01 objects and ledgers,
partial and validated weather receipts, the latest pair pointer, and immutable
prepared history and pointers. Unrelated files, credentials, configuration and
interrupted temporary writes are outside the inventory. The commands refuse
links, reparse points and SQLite sidecars in the inspected layout. A damaged
ledger or missing referenced artifact causes verification to fail.
CAP preparation and control clocks must match their retained ledger events.

Restore copies to staging beside the missing destination, checks the manifest,
bytes, SQLite integrity and references there, then publishes with a single
directory rename. The bundle remains available for another recovery. Restored
collectors and preparers use the retained source bytes, admission, cooldown and
clocks at the original path. The checkpoint commands run entirely offline.

## Capture with local Worker admission (T242)

With the trusted local Worker running and its `ATLAS_INGEST_HMAC_KEY` available
in the command environment, run one capture for `S09` or `S01`.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 capture-admitted --source S09 --origin http://127.0.0.1:8787
```

The command checks source enablement and sends one signed request to
`/internal/feed-check`. A matching HTTP 201 acknowledgement grants admission.
A matching HTTP 200 denial returns `not_due` at the admission stage. Errors,
wrong-source replies and timeouts fail closed before the collector starts.
Use an explicit `http://127.0.0.1:<port>` origin. The signed transport disables
environment proxies and redirects and bounds successful replies to 4096 bytes.

After admission the existing collector still applies its SQLite cadence,
Retry-After cooldown and quota. Its result uses `stage: capture`. A lost Worker
reply or a later local deferral can consume the Worker slot. The command runs
the claim and capture in one child with a 150-second parent deadline. Startup
and cleanup add overhead. Completed capture evidence remains in `--root`,
which defaults to `.cache/feeds`. Use `--max-documents` to bound S09 work.
Preparation, upload, durable runner persistence and scheduling are separate
steps. The cloud capability and release gates apply before activation.

## Runner checkpoint store (T243)

Use a dedicated local directory that survives cleanup of the feed workspace.
Its parent must exist, and the store and feed root must be disjoint. Stop
capture and preparation while saving or restoring. Initialize the store with
one explicit save from the intended feed root.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-save --store .cache/runner-checkpoints --expected-head empty
```

On the next run, when the original feed path is absent, restore from that
same store. Keep the reported `manifest_sha256` in the runner state.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-restore --store .cache/runner-checkpoints
```

After the run, save with `--expected-head $restoredManifestSha256`, using the
digest that run actually restored. A stale value fails before copying. Both
commands default to `.cache/feeds`; `--root` selects the same canonical
absolute feed path used at initialization.

The trusted `catalog.sqlite` serializes store operations. A missing catalogue
requires an empty directory for bootstrap. Save verifies and installs an
immutable bundle under `objects/<manifest_sha256>` before committing the
current digest. It preserves older generations. A process interruption
before the catalogue commits can leave a complete unreferenced bundle. A
retry verifies its bytes before using it. After interruption, restore selects
the last committed digest and verifies it before creating the feed directory.
The quota counts repository data, the feed tree during save, the whole store
and the incoming copy. It includes pending catalogue pages and the temporary
copy used to verify an unchanged save. Physical free-space checks apply on
the destination drive.

The store is a local trust boundary. Keep its catalogue and objects together
on a local filesystem, with access restricted to the operator or runner.
Recovery depends on the catalogue and manifest agreeing. Hosted runner
persistence, cross-path recovery and recurring activation remain later work.

## Bounded runner cycle (T244)

With a committed runner checkpoint, an absent original feed root and a trusted
loopback Worker, run one source through restore, admission, capture and save.
Use the Worker's existing local signing key in the command environment.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-cycle --store .cache/runner-checkpoints --source S09 --origin http://127.0.0.1:8787
```

One child has a 150-second deadline for all three phases. `restored_sha256`
identifies the starting generation. `manifest_sha256` identifies the verified
generation returned after save, or the restored generation if admission
stopped capture. Handled capture failures can still save valid evidence and
provider cooldown. A failed checkpoint reports the starting digest and the
capture result so the working tree can be inspected.

The command leaves the working root in place. After a successful save, hold
it aside before the next cycle so restore can use the original absent path.
After a timeout, keep the root in place and inspect the catalogue and working
tree before resuming. SQLite may have committed just before the child was
stopped. Retain any newer capture evidence and cooldown by sealing the
validated working tree against the current head before another capture.

## Prepare and upload from a runner cycle (T245)

Add `--upload-local` to prepare a successful capture at the current UTC cutoff.
The cycle commits the checkpoint before sending the prepared snapshot from its
immutable generation to the same loopback Worker.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-cycle --store .cache/runner-checkpoints --source S09 --origin http://127.0.0.1:8787 --upload-local
```

The 150-second deadline covers preparation and upload too. A preparation failure
can still save valid capture evidence and cadence. A failed checkpoint stops
before upload. An upload failure reports the saved digest, so the next cycle can
restore the committed snapshot. When the next capture is `not_due`, the option
resends a retained prepared head if present, with its original cutoff and exact
bytes. The Worker reports `stored` or `unchanged` at the upload stage. Recurring
scheduling and hosted persistence remain separate steps.

The runner reuses the existing prepared bytes when the verified source inputs
and normalized output are equivalent at the later cutoff. This keeps the
original cutoff, revision and publication clock. A new validation, alert
expiry or changed forecast selection can still produce a new snapshot.
An exact retry uses the Worker's existing duplicate handling.

## Checkpoint artifact handoff (T247)

Offer the current committed bundle from a quiescent store. Supply the measured
bytes of artifacts already retained. The result includes `bundle_path`,
`manifest_sha256`, uncompressed `payload_bytes` and `retention_days`.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-offer --store .cache/runner-checkpoints --retained-artifact-bytes $retainedArtifactBytes
```

The preflight uses the project's 400 MB aggregate budget and seven-day limit.
Future hosted transport must check actual artifact usage and select the trusted
run and artifact before download. GitHub supports cross-run download with a
token and run identifier. Offer the returned bundle directory alone. [GitHub artifact guide](https://docs.github.com/en/actions/tutorials/store-and-share-data)

Import the downloaded `manifest.json` and `files/` directory with the expected
manifest digest from a separate trusted source. Use the same canonical original
feed path. The store and feed root must both be absent.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-import --bundle .cache/downloaded-bundle --store .cache/next-run-checkpoints --expected-sha256 $savedManifestSha256
```

Import verifies staged evidence and creates a fresh local catalogue. The feed
root stays absent for the next `runner-cycle` or `runner-restore`. Both handoff
commands run locally. Hosted accounting, workflow activation and release review
remain separate steps. Retained weather data credits Open-Meteo and ECMWF.

## Hosted checkpoint metadata preflight (T248)

`runner-select` checks an explicitly trusted predecessor before downloading.
Pass the repository and workflow IDs, run ID, branch, commit SHA and separately
recorded manifest SHA-256. The artifact name is
`ka-feed-checkpoint-<manifest_sha256>`. Use a read-only `GITHUB_TOKEN` in the
environment when required. Public metadata may be read without a token.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-select --repository $repo --repository-id $repoId --workflow-id $workflowId --run-id $runId --branch main --head-sha $commitSha --manifest-sha256 $savedManifestSha256
```

The pinned run must be a completed successful first attempt from a schedule or
manual dispatch in the same repository. The artifact must match that run and
commit, carry its GitHub archive digest, and be unexpired within the project's
seven-day limit. An ineligible or missing predecessor stops selection.
The archive and manifest digests are separate checks. [GitHub run API](https://docs.github.com/en/rest/actions/workflow-runs) · [GitHub artifact API](https://docs.github.com/en/rest/actions/artifacts)

The 30-second child reads up to ten inventory pages. It checks the reported
count, page completeness and unique artifact IDs. It sums `size_in_bytes`
for all listed repository artifacts, including expired entries still listed.
The result reports remaining bytes under the project's 400 MB limit. This is
repository inventory at check time. Hosted upload still needs current usage
verification and budget approval. The selector leaves predecessor choice and
artifact download to the workflow that calls it.

## Discover the immediate predecessor (T249)

For discovery, use `--discover` in place of `--manifest-sha256`. Supply the
active run's ID and commit, with its trusted repository, workflow and branch.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-select --repository $repo --repository-id $repoId --workflow-id $workflowId --run-id $activeRunId --branch main --head-sha $activeCommitSha --discover
```

The selector verifies the active first attempt and looks for exactly the prior
workflow run number on the recent listing. A gap, failure or different branch
stops recovery. The predecessor must have the same commit or be an ancestor.
Use `Actions: read` for metadata and `Contents: read` for commit comparison.
[GitHub run variables](https://docs.github.com/en/actions/reference/workflows-and-actions/variables) · [GitHub commit comparison API](https://docs.github.com/en/rest/commits/commits#compare-two-commits)

One checkpoint name from that verified run supplies the manifest digest. Its
archive digest, retained bytes and expiry use the same checks as pinned mode.
The first run needs a separate verified bootstrap. Download and recurring
activation are separate steps.

## Import the downloaded checkpoint ZIP (T250)

For hosted transport, use the pinned GitHub download action with the selected
`artifact-ids`, `run-id` and repository. Supply a read-only token for the
cross-run fetch. Set `skip-decompress: true` and `digest-mismatch: error`.
Keep the raw ZIP in an isolated download directory. [GitHub download action](https://github.com/actions/download-artifact)

Pass the selected `archive_sha256` and `artifact_bytes` together with the
separate manifest digest. The feed path and destination store must be absent.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-import-zip --archive $downloadedZip --store .cache/next-run-checkpoints --archive-sha256 $archiveSha256 --archive-bytes $artifactBytes --expected-sha256 $savedManifestSha256
```

The 60-second child checks the raw archive size and digest before parsing.
It bounds ZIP metadata and expanded bytes, then streams only exact listed
members into staging. The existing importer checks their evidence and creates
the catalogue. The downloaded ZIP stays available for inspection, and the
original feed root stays absent for the next cycle. Keep the ZIP quiescent
during import. Hosted workflow wiring and activation remain separate.

