# Maintenance runbook (T221)

Owner-run. This page names only commands and files that exist in the repository;
`tests/test_final.py` checks every repository path cited here. Nothing below deploys anything:
there is no host until H05, H06 and H11 (see [final.md](../releases/final.md)).

## 1. Environment

- Windows 10, PowerShell, repository at `D:\monsoon-atlas`. Everything stays on drive D.
- Python 3.12.14 in `.tools/python`, virtual environment `.venv`. DuckDB 1.x only.
- Before any command that downloads, set the temp folders:

```powershell
$env:TEMP = 'D:\monsoon-atlas\.cache\tmp'; $env:TMP = $env:TEMP
```

- Rebuild the environment: install uv, `uv python install 3.12.14` into `.tools/python`, create
  `.venv` from it, then install the hash-locked files:

```powershell
.\.venv\Scripts\python -m pip install --require-hashes -r requirements/core.txt -r requirements/dev.txt
```

  Raster and polygon work also needs `requirements/geo.txt`. Change a lock only through its `.in`
  file and pip-tools (D25), then run `scripts/audit_dependencies.py --policy`.
- Web and Worker use the portable Node in `.tools`; run them through `scripts/web.ps1` and
  `scripts/worker.ps1`.

## 2. Checks to run after any change

```powershell
.\.venv\Scripts\python -m pytest -q                      # full suite, about 16 minutes
.\.venv\Scripts\python -m pytest tests/test_final.py -q  # this release page and manifest
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python scripts/audit_dependencies.py --policy
.\scripts\web.ps1 test; .\scripts\web.ps1 run build; .\scripts\web.ps1 run test:e2e
.\scripts\worker.ps1 run check; .\scripts\worker.ps1 test
```

`scripts/worker.ps1 run test:runtime` does not run on this laptop; rely on the Ubuntu CI job
"Worker local runtime". Run `tests/test_dl_poll.py` with any change that adds text under `web/` or
`worker/`.

## 3. Periodic commands

| When | Command | What it does |
|---|---|---|
| When you want a local S09 capture | `scripts/feeds.ps1 refresh --max-documents 30` | Local Sachet capture and preparation under one deadline; partial and local only (`docs/feeds.md`) |
| Weather point capture | `scripts/feeds.ps1 weather`, then `scripts/feeds.ps1 weather-prepare` | Raw capture and preparation for the one verified Bengaluru grid point |
| Daily | `.\.venv\Scripts\python -m atlas quota --check` | Storage (80% warn, 95% archive-only) and daily caps; exits 3 when over |
| Daily | `.\.venv\Scripts\python -m atlas.monitoring` | Feed age, missingness, schema, drift and storage checks as a table (T219) |
| After a registry, report or source change | `.\.venv\Scripts\python -m atlas.models.accuracy` | Regenerates `docs/releases/ka.md`, `web/tests/fixtures/accuracy-ka.json` and `web/src/dashboards.json` |
| After any file in the release manifest changes | `.\.venv\Scripts\python tests/test_final.py --manifest` | Regenerates `docs/releases/final-manifest.json`; never edit it by hand |
| Only after freezing the Ask corpus to a tagged snapshot | `.\.venv\Scripts\python -m atlas.rag.evaluate` | Rewrites `reports/rag.md`; scores drift while `docs/decisions.md` and `docs/amendments.md` grow (D147, D164); never tune on Q41 to Q50 (D101) |

The feeds control database lives under `.cache/feeds`.

## 4. Re-run a blocked source when its retry condition is met

1. Read `retry_condition` in `configs/sources/sNN.yaml` and the source page in `docs/sources/`.
   Owner-gated conditions (H04, H08, H09, H10, H12, H15) wait for the owner; the agent never
   creates accounts, accepts terms or types keys.
2. Re-run the source's verify task (for example T146 for S24, T148 for S38) exactly as the plan
   states it. Store evidence in `data/raw/SNN`, update `tests/fixtures/sNN/manifest.json` and the
   discovery record, and record the outcome honestly (`available` or `blocked`).
3. Run `tests/sources/test_sNN_discovery.py` and `tests/sources/test_sNN.py`.
4. Only if the outcome is `available` and the licence is not `unverified`, set `enabled: true` in
   the state config under `configs/states/`, then run that state's gate test
   (`tests/test_ka_v1.py`, `tests/test_kl_release.py` or `tests/test_dl_release.py`).
5. Regenerate `web/src/dashboards.json` and the release manifest (section 3), and add a decision.

## 5. Decisions and amendments

- Add a decision before any deviation from the plan: a new entry at the top of
  `docs/decisions.md`, next number after the latest, in the form
  `- **DNNN — title (date, task).**` with the reason and evidence.
- Amendments: `docs/amendments.md` and `docs/amendments.yaml` must stay in parity; change both in
  the same commit (amendments.md, T001 note). Where they conflict with the plan, the amendments win.
- A change to a hash-frozen file (table in `docs/releases/ka-v1.md`) needs a decision entry and the
  new hash in the same commit (D122).
- Both `docs/decisions.md` and `README.md` are in the Ask corpus (`configs/rag.yaml`), so editing
  them moves Ask scores slightly.

## 6. Rollback

Use [rollback.md](rollback.md): a rollback moves `manifests/latest.json` back one release and
never edits a prediction, ledger line or old manifest.

## 7. Manual-only workflows

All three are `workflow_dispatch` only, read-only, with no secrets, and none has been dispatched.
`workflow_dispatch` needs the file on `main`.

| Workflow | File | Preconditions before the first run |
|---|---|---|
| feeds | `.github/workflows/feeds.yml` | The owner decides the first run; test the `queue: max` concurrency option against the T249 chain; measure setup time and runner free space in the three-minute job; no hosted capture until H05 |
| tiles | `.github/workflows/tiles.yml` | Verify by hand the 40-character commit SHA of tag 2.79.0 in the Tippecanoe repository (input `tippecanoe_commit`); the data step comes with the first owner-approved run (D151) |
| monitor | `.github/workflows/monitor.yml` | None; it runs `python -m atlas.monitoring` on the committed state, and in a clean checkout the feed, PSI and storage rows read "unavailable" (D163) |

## 8. Never do these

- Never enable a source without its verify task passing; a disabled source raises
  `SourceUnavailable` and never returns synthetic rows.
- Never publish restricted raw values: S08 rainfall (including box means), S34, S36 text beyond
  cited facts, S12 and S20 beyond what H11 approves. Raw files stay in `data/raw`, untracked.
- Never register the service worker, mount unmounted layers publicly, or deploy anything before
  H11 approves a snapshot and H05 and H06 give a host.
- Never reset or delete the feeds control database under `.cache/feeds` to bypass admission or
  cooldown, and never present its partial results as a complete warning feed.
- Never buy a domain, add a card, or use a paid API (Rs 0 rule).
- Never write caches, models or datasets to drive C; never use Python 3.14 or DuckDB 2.
