# Monsoon Atlas: handoff to Codex (Karnataka only)

Written 18 Nov 2026 by Claude (Opus 5.5) before its usage limit. Scope from now on: **Karnataka
only**. Do not start Kerala (P3) or Delhi (P4) work.

Read in this order: `AGENTS.md` (hard rules), this file, `docs/plans/karnataka-ml-showcase.md`
(the active plan, items 1-12 and tasks T268-T289), the top ~30 entries of `docs/decisions.md`
(D190-D218), `docs/amendments.yaml` entries T268-T289. `docs/HANDOFF.md` is the long history.

## 1. Where things stand

- Repo `D:\monsoon-atlas`, GitHub `Joepikka/monsoon-atlas` (public). Work branch `p1/gate-core`;
  `main` is live. **PR 15** (branch -> main) is open with GitHub auto-merge on.
- Live site: https://monsoon-atlas.pages.dev (Cloudflare Pages). `daily.yml` deploys on every push
  to `main` and at 02:17 UTC; GitHub's schedule fires irregularly.
- `main` requires two CI checks: `test (ubuntu-24.04)` and `test (windows-latest)`. The owner gave
  standing approval: merge PRs into `main` once CI passes (use auto-merge), then report.
- **Unpushed local commits** on `p1/gate-core` (all Karnataka): T269 S23 verify (68133a1, efb0c39,
  58cc74c), T281 (ce43fdc), D216 (e904e36), T283 (65e10b6), D217 (3fa96b1), T282 (6dae72e),
  D218 (f7d075e). They were held back until a full suite run passes.
- **Work in progress when Claude stopped** (uncommitted, check `git status` first):
  - **T284, M21 locked test** (`src/atlas/models/m21_test.py`, `tests/models/test_m21_test.py`,
    `reports/models/m21.md`, `reports/models/m21-card.md`, `models/registry/M21/`, edits to
    `models/gates/m21.json`, `configs/models/m21.yaml`, `m21_fit.py` and M21 tests). Open
    `models/gates/m21.json`: if `test_opened` is **true**, the test has been opened; **never open it
    again**, only finish the report, card, registry and tests from the recorded numbers. If it is
    false, write the interval method into the gate first, then open the test exactly once.
  - **T269 final full-suite run** (S23 stays `blocked` until the T270 adapter; option B). Its last
    commit is 58cc74c. Re-run the full suite yourself and fix what remains (see section 4).
- **T284 is done** (ee81006, D219): M21 research-only; 80% intervals pass. Next free decision is **D220**. **D212** is reserved for T269 (text in section 5).

## 2. What is done for Karnataka (do not redo)

- Live site pages: Overview with a 3D district map (D209), map at `?page=map` with Place Lens and
  district profile (D205), 30-district forecasts (D206), Monsoon tracker with 2001-2025 ERA5
  normals (D202), Data findings (D199), redesigned Model accuracy (D210), Bus access, Warning archive,
  Climate, Ask (research-only RAG), one site shell (D208). Power BI report, 10 pages (D198).
- Models and analyses: M05 drought outlook (promoted, D43). M21 rain anomaly: dataset (D214),
  classical models (D216), MLP + GCN-GRU networks with identity ablation (D217), spatial lags and
  spatial CV (D218), candidate LightGBM, expected research-only. District segmentation (D213).
  Hospital siting (D215). Hospital access (D195). Rain trends (D196).

## 3. Next tasks, Karnataka only, in order

1. T284 is done (D219). D212 is recorded; the full suite passed (only the manifest test needed regenerating), and everything is pushed. Next: T270, refresh the release manifest, push,
   let PR 15 auto-merge.
2. **T270**: S23 adapter and resumable Karnataka **onion** backfill, **one request per
   `filters[Arrival_Date]` day** (offset paging is unreliable, D212), 1 request per 2 s, check each
   day's `total`. Then flip S23 to `available` + `enabled` in the same task (update frozen release
   checks as their tests require, with a decision entry).
3. **T271**: cleaning (min<=modal<=max, zero bounds, per-kg-looking rows, 41 district spellings, APMC
   market-name switch in Nov 2025, string vs integer types), crosswalk, quarantine with reason codes,
   notebook 12.
4. **T272** SQL and price EDA; **T273-T275** M06 price-spike model (labels/gate, then fit on
   train/tune, then locked test once); **T276-T278** M22 weekly price forecast incl. the GRU/TCN
   network; **T279** rain-shock event study.
5. **T287** explainability (SHAP/permutation), **T288** leaderboard, Accuracy page rows, findings
   sections, Power BI pages, a website layer for the D215 siting cells and the D213 segments;
   **T289** case studies and an interview map.
6. Redesign steps 3-4 (owner asked): Monsoon tracker page with a choropleth and chart, Climate page
   Karnataka-first, Ask as a chat-style page with example questions, Warning archive empty state,
   Wall display; district explorer page, compare two districts, CSV download under every chart.

Owner steps still open: **H14** (owner writes summaries in `reports/models/owner-review.md`; the
agent never writes them) and **H16** (owner reads AGMARKNET price units for tomato, potato, maize,
ragi, tur, dry chillies, copra; until then prices are onion only).

## 4. Pitfalls that already bit (read before editing)

- `docs/decisions.md`: insert new entries right after `## Continuation review (5 Nov 2026)`.
- `web/src/styles.css`: put new CSS **above** the `T188: wall mode` comment (a test forbids motion
  after it).
- Frozen interfaces: `src/atlas/ingest/discovery.py` and others are hash-pinned in
  `docs/releases/ka-v1.md`, `kl.md`, `dl.md`; changing them needs a decision and updated hashes.
- `docs/releases/final-manifest.json` pins file hashes; regenerate with
  `.venv\Scripts\python tests/test_final.py --manifest` only after all work is committed.
- `docs/amendments.yaml` and the YAML block in `docs/amendments.md` Appendix Y must stay identical.
- Running `python -m atlas.models.m21_fit` rewrites the gate's `tune` section; afterwards rerun
  `nn_graph` and `spatial_ml` mains so their sections come back.
- `tests/test_monitor.py` counts model configs (now 21); a new `configs/models/m22.yaml` changes it.
- Web e2e tests open the map at `/?page=map`; a bare `/` is the Overview.
- `README.md` and `docs/portfolio/resume.md` mirror source counts and model rows; `web/src/dashboards.json`,
  `docs/releases/ka.md` and `web/tests/fixtures/accuracy-ka.json` are regenerated by
  `python -m atlas.models.accuracy`.
- Never publish IMD S08 rain in mm (indices only). No bus stops/routes/times (D191).

## 5. Ready text for D212 (T269)

- **D212 - S23 variety-wise history verified; Karnataka onion scope recorded; S23 stays blocked until
  the T270 adapter (13 Nov 2026).** T269 re-ran the S23 verify for data.gov.in resource
  35985678-0d79-46b4-9ed6-6f13308a1d24 (same catalogue and publisher, GODL): 103,423 Karnataka onion
  rows from 10/01/2001 to 12/11/2026 (evidence e07-e27), about one day behind the daily resource.
  Units are per commodity; only Onion is confirmed (Rs./Quintal, owner-observed AGMARKNET, D201);
  others wait for H16. Limits 1,000-10,000 work; about 150 requests at one per 2 s met no refusal.
  Offset paging is unstable (11 pages gave 93,423 distinct rows), so T270 backfills one
  `filters[Arrival_Date]` request per day. S23 stays `outcome: blocked` with the onion scope in its
  record until T270 delivers a working adapter. M06/M10/M16 gate reasons now cite this status.

## 6. Environment and commands

- Windows 10, Python 3.12 only in `.venv` (`.\.venv\Scripts\python`), DuckDB 1.x, Node via
  `.tools/node`. **Everything on drive D** (C is nearly full). Before any download set
  `TEMP=D:\monsoon-atlas\.cache\tmp` and `TMP` the same (the folder exists; create it if missing).
- Tests: `.\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp=.cache/tmp/<name>`
  (full suite about 25 min). Lint: `ruff check .` and `ruff format --check .`.
- Web: in `web/`, `npx tsc --noEmit`, `npx vitest run`, `npx playwright test` (axe WCAG 2.2 AA).
- Keys are in `.env` (never print or commit). Variable names: DATA_GOV_IN_API_KEY, CLOUDFLARE_*,
  NASA_FIRMS_MAP_KEY, HF_TOKEN, HF_ARCHIVE_REPO, ATLAS_INGEST_HMAC_KEY, CDSE_S3_ACCESS_KEY,
  CDSE_S3_SECRET_KEY. Never sign in, create accounts, accept terms or type keys into web forms.
- Commits: message starts with the task ID (e.g. `T270: ...`), one decision entry per deviation.
