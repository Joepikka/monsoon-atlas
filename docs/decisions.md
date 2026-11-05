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
| D17 | reserved | GATE-CORE fallback choice (amendments A4), filled in by T222 | Only set if a core data check fails |
| D18 | 2026-11-05 | Adopt plan amendments v1 (`docs/amendments.md`); they win where they conflict with the plan | AI agent builds; portfolio core first; early data gate |
| D19 | 2026-11-05 | Project name: Monsoon Atlas (owner approved, H01). Free subdomain `monsoon-atlas.pages.dev` had no DNS record and the GitHub name `Joepikka/monsoon-atlas` was free on this date | Original name, no paid domain |
| D20 | 2026-11-05 | Repository at `D:\monsoon-atlas` | Drive C has 15 GB free, below the plan's 20 GB storage preflight |
| D21 | 2026-11-05 | Add `CLAUDE.md` that imports `AGENTS.md` | Claude Code reads `CLAUDE.md`, not `AGENTS.md` |
| D22 | 2026-11-05 | T002 uses the uv-managed CPython 3.12.14 already on the laptop (`%APPDATA%\uv\python\cpython-3.12.14-windows-x86_64-none`) to create `.venv` with stdlib `venv`, instead of installing official 3.12.10. `py -3.12` does not resolve it, so the venv is created from that interpreter's path | Same 3.12 minor with newer security patches; no admin installer needed. All other T002 steps (pip-tools hash locks, `--require-hashes` installs, section 5 pins) are as planned |
| D23 | 2026-11-05 | Add a nullable `missing_reason` enum column to the common envelope (`schemas/common.json`); a null measure requires a reason, and a row with a reason must have null measures | T005 requires a missing-reason enum and "missing != 0", but the section 7 envelope has no column to carry it |
| D24 | 2026-11-05 | Storage quota counts `data/clean` and `data/manifests` against a 20 GB archive budget: warn at 80%, archive-only (new ingestion refused) at 95%. `ManifestFile` gains a required `rows` count | Plan section 6 storage arithmetic and T006; T006 wording ("archive-only status at 80%") conflicts with section 6 ("80% warn, 95% archive-only"); section 6 is followed. Row counts let a rebuild prove it matches the manifest |
