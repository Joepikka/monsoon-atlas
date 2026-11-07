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
