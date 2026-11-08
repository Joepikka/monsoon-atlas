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
Claude continued on 8 Nov 2026: T251 (D86/A34) adds the manual-only hosted
checkpoint relay workflow. See `docs/HANDOFF.md` sections 7 and 9 for the
current task and next step.

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
