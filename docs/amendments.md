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

## Appendix Y: new and changed tasks (YAML)

```yaml
amendments_version: 1
date: 2026-11-05
new_tasks:
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
