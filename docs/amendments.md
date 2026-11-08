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

## A34. Manual hosted checkpoint relay (D86, 8 November 2026)

T251 is a child of T043 after T249/T250. Add a manual-only workflow that
continues the immediate verified checkpoint, or starts an explicitly
requested empty chain, within the job's three-minute bound. Recurrence and
hosted capture stay disabled. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_feeds_workflow.py -q`.

## A35. English Ask corpus and lexical retrieval (D87, 8 November 2026)

T252 is a child of T179 after T037/T103/T222. Index only committed project
documents listed in `configs/rag.yaml`, with commit-time availability, and
retrieve with as-of, state and language filters before BM25 ranking. The e5
embedding rerank is a later child. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/rag/test_retrieval.py -q`.

## A36. Ask answer contract with extractive fallback (D88, 8 November 2026)

T253 is a child of T180 after T229/T252. Add the Worker's pure answer
contract: fixed system rules, evidence passed as JSON data, plan quotas,
validation of generated citations and numbers, and a cited extractive
fallback. No AI binding, route or account is created. Estimate 3 hours.
Acceptance is `.\.venv\Scripts\python -m pytest tests/test_ask_config.py -q`.

## A37. English Ask evaluation set (D89, 8 November 2026)

T254 is a child of T181 after T252/T253. Record the 50 fixed plan questions
and 10 numeric snapshot cases in English, resolve gold keys to indexed
documents, freeze Q41-Q50, and score citations, evidence, numbers and
refusals deterministically. Translations stay unreviewed and disabled.
Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/rag/test_eval.py -q`.

## A38. Computed numeric answers and full top-five fallback (D90, 8 November 2026)

T255 is a child of T180 after T254. Answer recognised numeric templates with
DuckDB queries over frozen committed snapshots listed in `configs/rag.yaml`,
cite the queried file, and show all retrieved chunks (at most five) in the
extractive fallback. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/rag/test_numeric.py tests/rag/test_eval.py -q`.

## A39. Core case studies for the actual cores (D91, 8 November 2026)

T256 is a child of T225 after T103/T228/T255. Write one plan section 17 case
study per actual core: M05 (C2), the blocked M07 (C1 fallback) and Ask (C3),
using only numbers found in their cited committed sources. Estimate 3 hours.
Acceptance is `.\.venv\Scripts\python -m pytest tests/test_case_studies.py -q`.

## A40. Accuracy rows and release checklist (D92, 8 November 2026)

T257 is a child of T046 after T037/T103/T256. Build the accuracy rows for
C1, C2 and M06 from committed release records, with unavailable values kept
null, and generate a release checklist of every T046/A3 check with its
evidence. It is preparation only: the web page, browser checks and
deployment stay in T046. Estimate 2 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_ka_release.py -q`.

## A41. M05 model card (D93, 8 November 2026)

T258 is a child of T046 after T257. Write the C2 model card in the plan's M05
card fields, using only numbers from its cited sources. Estimate 1 hour.
Acceptance is `.\.venv\Scripts\python -m pytest tests/test_ka_release.py -q`.

## A42. Web accuracy page (D94, 8 November 2026)

T259 is a child of T046 after T038/T257/T258. Add the F036 accuracy page: it
loads only an approved, hash-checked accuracy release, shows unavailable
values as unavailable, and explains when no release exists. Browser checks
use a fixture generated from the committed records. No production data is
seeded. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_web_accuracy.py -q`.

## A43. Ask route over trusted chunks (D95, 8 November 2026)

T260 is a child of T180 after T252/T253. Add `POST /api/v1/ask`: the Worker
reads the requested chunk IDs from the current trusted D1 release, rechecks
hashes and the as-of, state and expiry rules, and returns the cited
extractive answer. `atlas.rag.manifest` exports the release and its SQL load
file. Generation and its quota counters wait for H05 and the free/no-card
probe. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/rag/test_manifest.py -q`.

## A44. English text Ask page (D96, 8 November 2026)

T261 is a child of T182 after T260, pulled into P1 for C3 (F046, text,
English). The web page `?page=ask` loads the hash-checked public corpus,
searches it in the browser, sends the top five chunk IDs to the Worker and
shows the cited answer with citation cards and evidence age, or the local
search results when the Worker is unavailable. Voice and the other three
languages stay outside the MVP. Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/test_web_ask.py -q`.

## A45. M05 interval recalibration (D97, 8 November 2026)

T262 is a child of T103. Recalibrate the M05 80% intervals with the rule
fixed in D97: out-of-sample rolling-origin residuals, six candidate rules
chosen on 2010-2019 only, then one check on 2020-2024 against the 75-85%
coverage gate. Point forecasts and the v1 release file stay unchanged.
Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/models/test_m05_intervals.py -q`.

## A46. M05 2025 monitoring check (D98, 8 November 2026)

T263 is a child of T103 after T262. Score the approved M05 forecast and the
persistence baseline once on the unused, provisional IMD 2025 year, with
the measures and flags fixed in D98. It is a monitoring check, not a new
release. Estimate 2 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/models/test_m05_monitor.py -q`.

## A47. e5 rerank for Ask retrieval (D99, 8 November 2026)

T264 is a child of T179 after T252/T254/T255. Embed the committed chunks
with the pinned e5 model and compare four retrieval methods on dev cases
only, as fixed in D99, then run the C3 report once with the chosen method.
Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/rag/test_rerank.py -q`.

## A48. Limit append-only logs in Ask results (D100, 8 November 2026)

T265 is a child of T179 after T264. Compare three log rules fixed in D100
on dev cases only, apply the chosen one to Python and browser retrieval,
then run the C3 report once. It cannot pass the C3 gate alone (ceiling
0.943). Estimate 3 hours. Acceptance is
`.\.venv\Scripts\python -m pytest tests/rag/test_log_cap.py -q`.

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
  - id: T265
    parent: T179
    title: "Limit append-only logs in Ask results"
    phase: P1
    state: KA
    depends_on: [T264]
    files: [configs/rag.yaml, src/atlas/rag/retrieve.py, src/atlas/rag/evaluate.py, web/src/ask-search.ts, reports/rag.md, reports/rag-logs.md, tests/rag/test_log_cap.py, docs/ask.md]
    steps:
      - "Compare L0, L1 and L2 on dev cases only (D100)"
      - "Apply the chosen rule to Python and browser retrieval"
      - "Run the C3 report once and record the result"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/rag/test_log_cap.py -q'
  - id: T264
    parent: T179
    title: "e5 rerank for Ask retrieval"
    phase: P1
    state: KA
    depends_on: [T252, T254, T255]
    files: [src/atlas/rag/embed.py, src/atlas/rag/retrieve.py, src/atlas/rag/evaluate.py, configs/rag.yaml, reports/rag.md, reports/rag-rerank.md, tests/rag/test_rerank.py, docs/ask.md]
    steps:
      - "Embed committed chunks with the pinned, hash-checked e5 model on drive D"
      - "Choose one of four retrieval methods on dev cases only (D99)"
      - "Run the C3 report once with the chosen method; record whether the gate passes"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/rag/test_rerank.py -q'
  - id: T263
    parent: T103
    title: "M05 2025 monitoring check"
    phase: P1
    state: KA
    depends_on: [T103, T262]
    files: [scripts/m05_monitor.py, models/registry/M05/v1.monitor-2025.json, reports/models/m05-2025.md, tests/models/test_m05_monitor.py]
    steps:
      - "Rebuild 1981-2025 features; the 1981-2024 rows must hash to the v1 dataset"
      - "Score the v1 ridge and persistence once on 2025 with the D98 measures"
      - "Flag holds or degraded; keep intervals hidden; label provisional and hindcast"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/models/test_m05_monitor.py -q'
  - id: T262
    parent: T103
    title: "M05 interval recalibration"
    phase: P1
    state: KA
    depends_on: [T103, T034]
    files: [src/atlas/models/m05.py, scripts/m05_intervals.py, models/registry/M05/v1.intervals.json, reports/models/m05-intervals.md, tests/models/test_m05_intervals.py]
    steps:
      - "Compute out-of-sample residuals from rolling origins every five years up to 2019"
      - "Choose one of six interval rules by mean 2010-2019 coverage closest to 80%"
      - "Apply it once to 2020-2024; show intervals only if coverage is within 75-85%"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/models/test_m05_intervals.py -q'
  - id: T261
    parent: T182
    title: "English text Ask page"
    phase: P1
    state: KA
    depends_on: [T260, T038]
    files: [src/atlas/rag/manifest.py, web/src/ask-search.ts, web/src/ask.ts, web/src/ask.test.ts, web/src/pages/Ask.tsx, web/src/main.tsx, web/src/App.tsx, web/src/styles.css, web/tests/ask.spec.ts, web/tests/fixtures/ask-corpus.json, tests/test_web_ask.py, docs/ask.md, .github/workflows/web.yml]
    steps:
      - "Publish the canonical chunk list whose SHA-256 is the release ID; load it only when the bytes match"
      - "Search in the browser with the retrieval rules; send the top five chunk IDs to the Worker"
      - "Show the cited answer, citation cards and evidence age, or labelled local results when the Worker fails"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_web_ask.py -q'
  - id: T260
    parent: T180
    title: "Ask route over trusted chunks"
    phase: P1
    state: KA
    depends_on: [T252, T253]
    files: [src/atlas/rag/manifest.py, worker/schema.sql, worker/src/index.ts, worker/src/ingest.ts, worker/tests/ask-route.test.mjs, worker/tests/runtime.test.mjs, worker/package.json, tests/rag/test_manifest.py, tests/test_ask_config.py, docs/ask.md]
    steps:
      - "Export the committed index as a hashed release and an atomic D1 load file"
      - "Serve POST /api/v1/ask from trusted chunk IDs only, rechecking hashes, as-of, state and expiry"
      - "Keep generation off and answers extractive until H05 and the free/no-card probe pass"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/rag/test_manifest.py -q'
  - id: T259
    parent: T046
    title: "Web accuracy page"
    phase: P1
    state: KA
    depends_on: [T038, T257, T258]
    files: [src/atlas/models/accuracy.py, web/src/accuracy.ts, web/src/accuracy.test.ts, web/src/pages/Accuracy.tsx, web/src/main.tsx, web/src/App.tsx, web/tests/accuracy.spec.ts, web/tests/fixtures/accuracy-ka.json, tests/test_web_accuracy.py]
    steps:
      - "Export accuracy rows as release bytes; bind the browser fixture to the committed records"
      - "Load only an approved pointer with a matching SHA-256; keep null values unavailable, never zero"
      - "Check empty, error and populated states at three viewports with keyboard and axe checks"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_web_accuracy.py -q'
      expected: "The page shows C1, C2 and M06 from a verified release; missing or unapproved releases show an honest state"
    hours: 3
  - id: T258
    parent: T046
    title: "M05 model card"
    phase: P1
    state: KA
    depends_on: [T257]
    files: [reports/models/m05-card.md, tests/test_ka_release.py, docs/releases/ka.md]
    steps:
      - "Fill the plan's M05 card fields with release results and stated deviations"
      - "Check every number against cited sources and regenerate the release checklist"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_ka_release.py -q'
      expected: "The C2 card check passes with source-backed numbers; the release stays not releasable"
    hours: 1
  - id: T257
    parent: T046
    title: "Accuracy rows and Karnataka release checklist"
    phase: P1
    state: KA
    depends_on: [T037, T103, T256]
    files: [src/atlas/models/accuracy.py, docs/releases/ka.md, tests/test_ka_release.py]
    steps:
      - "Build C1, C2 and M06 rows from release and status records; keep unavailable values null"
      - "List each T046 and A3 check with its current evidence; release only when all pass"
      - "Keep the generated checklist identical to the committed file"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_ka_release.py -q'
      expected: "Blocked models show unavailable, never zero; the checklist reports not releasable while any check fails"
    hours: 2
  - id: T256
    parent: T225
    title: "Core case studies for M05, M07 and Ask"
    phase: P1
    state: KA
    depends_on: [T103, T228, T255]
    files: [reports/models/m05-case-study.md, reports/models/m07-case-study.md, reports/models/ask-case-study.md, tests/test_case_studies.py]
    steps:
      - "Follow the plan section 17 outline in order, with one positive result and one negative lesson"
      - "Use only numbers that appear in each study's cited committed sources; state unrecorded costs as unrecorded"
      - "Report the blocked M07 data gate and the failed Ask gate honestly; leave H14 review to the owner"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_case_studies.py -q'
      expected: "Each study follows the outline and every number appears in a cited source"
    hours: 3
  - id: T255
    parent: T180
    title: "Computed numeric Ask answers and full top-five fallback"
    phase: P1
    state: KA
    depends_on: [T254]
    files: [src/atlas/rag/numeric.py, configs/rag.yaml, src/atlas/rag/evaluate.py, worker/src/ask.ts, tests/rag/test_numeric.py, reports/rag.md, docs/ask.md]
    steps:
      - "Match only explicit numeric templates; query frozen snapshots with DuckDB, independently of the gold code"
      - "Return value, unit and the queried file as citation; unknown places, sources or times stay unanswered"
      - "Show every retrieved chunk (at most five) in the extractive fallback; tune on development questions only"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/rag/test_numeric.py tests/rag/test_eval.py -q'
      expected: "N01, N02 and N07 are computed exactly with citations; unmatched or out-of-snapshot questions are not answered"
    hours: 3
  - id: T254
    parent: T181
    title: "English Ask gold cases and deterministic scoring"
    phase: P1
    state: KA
    depends_on: [T252, T253]
    files: [eval/rag/questions.jsonl, eval/rag/snapshot_gold.jsonl, docs/methods.md, configs/rag.yaml, src/atlas/rag/evaluate.py, reports/rag.md, tests/rag/test_eval.py]
    steps:
      - "Record plan Q01-Q50 and N01-N10 in English; resolve each in-scope gold key to a verifiable phrase in an indexed document"
      - "Freeze Q41-Q50 as holdout; recompute numeric gold from committed files; keep translations unreviewed"
      - "Score faithfulness, correctness, citations, evidence and refusals; perturb citations, stale facts, places and injections"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/rag/test_eval.py -q'
      expected: "At least 60 English gold cases with explicit language coverage; an invalid numeric answer or citation fails evaluation"
    hours: 3
  - id: T253
    parent: T180
    title: "Ask answer contract with cited extractive fallback"
    phase: P1
    state: KA
    depends_on: [T229, T252]
    files: [worker/src/ask.ts, worker/tests/ask.test.mjs, worker/package.json, tests/test_ask_config.py]
    steps:
      - "Keep system rules fixed and pass retrieved chunks only as JSON evidence within the 3000-token input cap"
      - "Apply 100 answers/day, 6 requests/minute and 8000 neurons/day before any generation call"
      - "Accept generated JSON only when every citation is retrieved and every number appears in cited evidence; otherwise return cited excerpts"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_ask_config.py -q'
      expected: "Quota exhaustion returns a cited extractive answer; hostile evidence cannot change rules or citations; no AI binding or secret is configured"
    hours: 3
  - id: T252
    parent: T179
    title: "Index the English Karnataka Ask corpus with lexical retrieval"
    phase: P1
    state: KA
    depends_on: [T037, T103, T222]
    files: [configs/rag.yaml, src/atlas/rag/corpus.py, src/atlas/rag/index.py, src/atlas/rag/retrieve.py, eval/rag/retrieval_dev.jsonl, tests/rag/test_retrieval.py, docs/ask.md]
    steps:
      - "Index only committed project documents listed in configs/rag.yaml, with commit-time availability, licence and hashes"
      - "Chunk by heading into 300-token windows with 50-token overlap; keep each table row whole"
      - "Filter by as-of, state and language before BM25; quote every query term; cap per-document results and context"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/rag/test_retrieval.py -q'
      expected: "As-of, expiry, state, language and licence filters hold; a gold document is in the top five for at least 85% of development questions"
    hours: 3
  - id: T251
    parent: T043
    title: "Wire the manual hosted checkpoint relay workflow"
    phase: P1
    state: KA
    depends_on: [T249, T250]
    files: [.github/workflows/feeds.yml, src/atlas/ingest/hosted_checkpoint.py, src/atlas/ingest/hosted_archive.py, src/atlas/ingest/runner_checkpoint.py, tests/test_feeds_workflow.py, scripts/feeds.ps1, docs/feeds.md]
    steps:
      - "Add a manual-only, serial, three-minute workflow with pinned actions and read-only scopes"
      - "Select the immediate predecessor or verify an explicit manual bootstrap; download by artifact ID without extraction"
      - "Import from an isolated single-file download directory, then offer and upload the committed bundle"
    acceptance:
      command: '.\.venv\Scripts\python -m pytest tests/test_feeds_workflow.py -q'
      expected: "Workflow uses only real selector and offer fields; bootstrap never replaces state; relayed bundles import byte-identically"
    hours: 3
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
