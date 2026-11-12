# Final acceptance and handover (T221)

Prepared 11 Nov 2026 on branch `p1/gate-core`, on top of commit `4b6e84d`. `tests/test_final.py`
checks this page against `docs/releases/final-features.json`, the model registry, the source
records, the state configs, the gate pages and the release manifest, so the page cannot drift from
the evidence without a failing test.

## Result

**The plan's tasks T001 to T221 are walked as executed; the product is not released. 12 of 64
plan features are shipped locally (`shipped-local`); 20 are built but not mounted, 4 are
research-only, 27 are blocked and 1 is deferred.** Nothing is deployed: there is no public host, no
approved snapshot and no registered service worker. Of the 20 models, 1 is measured and
owner-approved (M05, a hindcast), 1 is research-only (M16, counts only) and 18 are blocked. Ask
(C3) is research-only. The Karnataka MVP gate T046 has not passed ([ka.md](ka.md) says "not
releasable").

`shipped-local` means: the code is reachable in the local app (`web/src/App.tsx` or a `?page=`
route in `web/src/main.tsx`) or runs as a local pipeline command, and at least one tracked test
exercises it. It does not mean public. No approved snapshot exists, so a fresh local run of the map
shows the honest empty state and the basemap; the map tests run on committed real S09 and
Open-Meteo fixtures.

## Suite evidence

| Suite | Command | Result | Who ran it, when |
|---|---|---|---|
| Python, full | `.\.venv\Scripts\python -m pytest -q` | 1850 passed, 3 skipped, 1 warning in 972.74 s | Run by the coordinator on 11 Nov 2026 for commit `4b6e84d` (an earlier brief misdated it 12 Nov). Not re-run here (16 minutes). |
| Python, targeted gates | `tests/test_portfolio.py tests/test_dashboards.py tests/test_dl_poll.py tests/test_ka_v1.py tests/test_ka_release.py tests/test_kl_release.py tests/test_dl_release.py tests/test_case_studies.py tests/rag` | before the commit: 133 passed, 1 failed, 11 errors, all in `tests/rag`, because the corpus loader refuses the uncommitted `docs/decisions.md` by design; the re-run after the commit is in the T221 hand-back, not here | Agent, 11 Nov 2026 |
| Python, this page | `.\.venv\Scripts\python -m pytest tests/test_final.py -q` | 14 passed; fails when a feature status or a manifest hash is changed (two mutation checks) | Agent, 11 Nov 2026 |
| Web unit (vitest) | `scripts/web.ps1 test` | 23 files, 123 tests passed | Agent, 11 Nov 2026 |
| Web build | `scripts/web.ps1 run build` | built; Vite warns that the MapView chunk is over 500 kB | Agent, 11 Nov 2026 |
| Web end to end (Playwright, axe) | `scripts/web.ps1 run test:e2e` | 84 passed in 2.1 min | Agent, 11 Nov 2026 |
| Worker type check | `scripts/worker.ps1 run check` | exit 0 | Agent, 11 Nov 2026 |
| Worker node tests | `scripts/worker.ps1 test` | 27 passed, 0 failed | Agent, 11 Nov 2026 |
| Worker runtime (Miniflare) | `scripts/worker.ps1 run test:runtime` | not run on this laptop: it fails with "Could not resolve /D:/.../index.ts" | Runs in the Ubuntu CI job "Worker local runtime" |
| GitHub Actions on `4b6e84d` | `ci`, `Web shell`, `Worker local runtime` | reported as succeeded | Reported by the coordinator; not re-checked here (no network) |
| Dependency policy | `.\.venv\Scripts\python scripts/audit_dependencies.py --policy` | `policy: 0 problem(s)` | Agent, 11 Nov 2026 |

Skips in the full suite: three explicit "not run" markers (tile archive, PMTiles reads, the SGP4
known example). The warning is MLflow's SQLAlchemy deprecation. Known flaky: one Playwright Ask
case (5 s timeout on "document sections loaded") failed once and succeeded on re-run before T221; it
did not fail in the 84-case run above.

## Manual checks (plan section 14)

The plan's accessibility row asks for "axe plus NVDA/keyboard/zoom" and a manual checklist with
defects fixed. axe runs inside the Playwright suite. The agent cannot use a keyboard or a screen
reader, so every manual check below is open. Start the local app with `scripts/web.ps1 run dev`
and open http://127.0.0.1:5173/.

| Check | Page | What to look for | Status |
|---|---|---|---|
| Keyboard only | `/` (map) | Tab reaches the header links, state selector, refresh, layer toggles, radius control, ticker pause, record list and Place Lens tabs in a sensible order; focus is always visible; no trap; arrow keys move between Lens tabs | not performed: owner step |
| NVDA screen reader | `/` (map) | Status changes are announced once through the polite region; records read with source and time; the empty state and "Not an emergency service" are read; the map has a text alternative in the record list | not performed: owner step |
| NVDA and keyboard | `/?page=ask` | The research-only note is read; citation cards read path, heading and evidence age; the voice button is labelled and starts nothing until pressed | not performed: owner step |
| NVDA and keyboard | `/?page=accuracy`, `?page=quality`, `?page=analysis`, `?page=compare`, `?page=widget` | Tables have header cells; "Unavailable" is read as a word, never as 0; links say where they go | not performed: owner step |
| Zoom and reflow | All pages above | At 200% and 400% browser zoom (320 CSS px wide) no content is lost and no horizontal scrolling is needed except the map | not performed: owner step |
| Manual accessibility checklist | All pages above | Write each defect found with page and step; fix or record it | not performed: owner step |
| Network smoke tests (manual marker) | Source adapters | Each enabled source answers its live request; the agent had no network in T221 | not performed: owner step |
| Worker CPU, memory and D1 sizes on actual samples | Hosted Worker | Needs H05 and a deployed Worker; nothing is measured | not performed: owner step |

## Feature audit

Source of truth: [final-features.json](final-features.json) (64 rows from the plan's section 8
catalogue, with names, states and tiers as the plan gives them). Status counts by tier:

| Status | MVP | v1 | stretch | Total |
|---|---|---|---|---|
| shipped-local | 9 | 7 | 4 | 20 |
| built-not-mounted | 1 | 11 | 3 | 15 |
| research-only | 0 | 3 | 1 | 4 |
| blocked | 2 | 15 | 7 | 24 |
| deferred | 0 | 0 | 1 | 1 |
| total | 12 | 36 | 16 | 64 |

Updated 11 Nov 2026 (D172): F004, F005, F006, F009, F042, F043, F044 and F049 moved from
built-not-mounted to shipped-local; the T221 audit counted 12 shipped-local and 20 built-not-mounted.

Of the 12 MVP features, 9 run locally and 3 are blocked (F021 prices, F025 facilities, F033
price-spike model). Rows marked "Judgement call" in their notes could reasonably sit in another
status; the note says why this one was chosen.

| ID | Feature | States | Tier | Status | Tasks | Evidence | Tests | Blocker or owner step | Notes |
|---|---|---|---|---|---|---|---|---|---|
| F001 | Live state map with freshness labels | ALL | MVP | shipped-local | T038, T039 (plan T039) | `web/src/App.tsx`, `web/src/MapView.tsx`, `web/src/components/SourceBadge.tsx`, `docs/web-shell.md` | `web/tests/layers.spec.ts`, `web/tests/live-data.spec.ts`, `web/src/data.test.ts`, `tests/test_web_manifest.py` | Owner: H11. | Judgement call: the map and its freshness labels run locally and their tests use committed S09 and Open-Meteo fixtures. No approved snapshot exists, so a fresh local run shows the empty state and the basemap only. |
| F002 | Radius filter and nearby list | ALL | MVP | shipped-local | T039, T040 (plan T040) | `web/src/map/Layers.tsx`, `web/src/App.tsx` | `web/src/area.test.ts`, `web/tests/area.spec.ts` | none | Point records use great-circle distance; area warnings stay in the list with a label (D58). Same snapshot caveat as F001. |
| F003 | Time slider and replay | ALL | v1 | built-not-mounted | T142 (plan T142) | `web/src/components/Replay.tsx`, `notebooks/05_kl_flood2018.ipynb`, `docs/releases/kl.md` | `web/src/components/Replay.test.ts`, `tests/test_replay2018.py` | No published snapshots exist to slide over (T045); the 2018 replay's S08 export is untracked and local only (H11 item 9, D166). Owner: H11, H05, H06. | Judgement call: only the 2018 replay with its reconstructed mode is built (D127); a slider over immutable published snapshots has nothing to read. |
| F004 | 3D terrain | ALL | stretch | shipped-local | T186 (plan T186) | `web/src/map/Terrain.tsx`, `web/src/MapView.tsx`, `web/src/App.tsx` | `web/src/map/Terrain.test.ts`, `tests/test_tiles.py` | Owner: H11. | Mounted 11 Nov 2026 (D172): opt-in Map view select, Flat 2D stays the default; chooseView() fallbacks apply. No tile is stored. |
| F005 | Globe view | ALL | stretch | shipped-local | T186 (plan T186) | `web/src/map/Globe.tsx`, `web/src/MapView.tsx`, `web/src/App.tsx` | `web/src/map/Globe.test.ts` | Owner: H11. | Mounted 11 Nov 2026 (D172): Globe option of the Map view select; reduced motion sets camera durations to 0. |
| F006 | Wall mode | ALL | stretch | shipped-local | T186, T188 (plan T186) | `web/src/map/WallMode.tsx`, `web/src/pages/Wall.tsx`, `web/src/main.tsx` | `web/src/map/WallMode.test.ts`, `tests/test_wall.py` | Owner: H11. | Mounted 11 Nov 2026 (D172) at ?page=wall: connected means online and the last snapshot load did not fail; stale or disconnected walls show no alerts. With no approved snapshot it shows its empty state. |
| F007 | Feed health badges | ALL | MVP | shipped-local | T039 (plan T039) | `web/src/components/SourceBadge.tsx`, `web/src/map/Layers.tsx` | `web/src/map/Layers.test.ts`, `web/tests/layers.spec.ts` | none | Missing health metadata reads unknown, never no hazard (D58). Same snapshot caveat as F001. |
| F008 | Event log and ticker | ALL | MVP | shipped-local | T039 (plan T039) | `web/src/components/EventTicker.tsx`, `web/src/App.tsx` | `web/tests/layers.spec.ts` | none | The ticker is mounted in App.tsx; its strings are English literals (D154). Same snapshot caveat as F001. |
| F009 | Daily satellite image layer | ALL | stretch | shipped-local | T186 (plan T186) | `web/src/map/Terrain.tsx`, `web/src/MapView.tsx`, `configs/sources/s13.yaml` | `web/src/map/Terrain.test.ts` | Owner: H11. | Judgement call: Mounted 11 Nov 2026 (D172) with the terrain view, but no snapshot carries a dated S13 row, so the page says no imagery date was reported and shows none (no date is guessed). |
| F010 | Satellites overhead | ALL | stretch | blocked | T187 (plan T187) | `src/atlas/spatial/orbits.py`, `web/src/map/Movement.tsx`, `configs/sources/s12.yaml` | `tests/test_movement.py` | sgp4 is in no lock, so predict() raises SourceUnavailable; S12 display terms wait for H11 (D109, D153). Owner: H11. | Adding sgp4 to requirements/geo.in is an agent follow-up that needs network access. |
| F011 | Transit stations and scheduled positions | KA/KL | v1 | built-not-mounted | T028, T029, T104 (plan T104) | `src/atlas/transit/schedule.py`, `web/src/map/ScheduledTransit.tsx`, `docs/releases/ka-v1.md` | `tests/test_schedule.py`, `web/src/map/ScheduledTransit.test.ts` | S30 is licence restricted; no public transit snapshot until H11 (D115, D116). Owner: H11. | Kerala schedules are not verified. |
| F012 | Live buses | DL | v1 | blocked | T148, T151, T165 (plan T165) | `configs/sources/s38.yaml`, `web/src/components/Transit.tsx`, `worker/src/transit.ts`, `docs/releases/dl.md` | `tests/test_dl_poll.py`, `web/src/components/Transit.test.ts` | S38 blocked on owner step H04; live mode unavailable (D135, D138). Owner: H04. | none |
| F013 | Historical train routes/stations | ALL | stretch | built-not-mounted | T073, T074, T104 (plan T104) | `src/atlas/transit/schedule.py`, `configs/sources/s21.yaml` | `tests/test_schedule.py`, `tests/sources/test_s21.py` | Not mounted with the transit layer (D116). Owner: H11. | S21 is a 2016 reference: clock text only, no position or ETA. |
| F014 | Flights and optional coastal ships | ALL/KL | stretch | built-not-mounted | T059, T060, T187 (plan T187) | `web/src/map/Movement.tsx`, `web/tests/fixtures/movement-layers.json`, `configs/sources/s10.yaml` | `web/src/map/Movement.test.ts`, `tests/test_movement.py` | Not mounted (D153); ships need S26, blocked on H12. Owner: H12, H11. | Aircraft (S10) is the only layer that qualifies; S11 is blocked on terms. |
| F015 | Fire hotspots | ALL | v1 | built-not-mounted | T075, T076, T105 (plan T105) | `configs/sources/s25.yaml`, `src/atlas/ingest/s25.py`, `docs/sources/s25.md` | `tests/test_context_layers.py`, `tests/sources/test_s25.py` | S25 is available with the owner's MAP_KEY (D176); not mounted until a public snapshot carries detections (T045). Owner: H11, H05. | Hotspots are thermal anomalies, never confirmed fires. |
| F016 | Sachet alerts including provider-issued lightning | ALL | MVP | shipped-local | T013, T014, T039 (plan T039) | `configs/sources/s09.yaml`, `web/src/App.tsx`, `docs/feeds.md` | `tests/sources/test_s09.py`, `web/tests/area.spec.ts`, `web/tests/live-data.spec.ts` | none | Judgement call: local capture and display only; partial CAP coverage, no hosted feed. Lightning shows only when Sachet issues it; none is inferred from rain. |
| F017 | News-derived preliminary event pins | KL then ALL | stretch | blocked | T125, T189-T208, T209, T211 (plan T211) | `configs/sources/s41.yaml`, `eval/news/blocked.json`, `reports/models/m18.md` | `tests/labels/test_news_blocked.py` | S41 has no publisher permission; 0 labelled texts; H13 review not done (D155, D156). Owner: H13. | none |
| F018 | Flood-exposed roads | KA/KL | v1 | blocked | T143 (plan T143) | `src/atlas/spatial/exposure.py`, `configs/sources/s18.yaml`, `configs/sources/s43.yaml` | none | No road graph is built from S18 yet (S18 available, D174) and no flood labels or polygons (S43) (D128). | S18 roads come from the owner's browser download (D174). |
| F019 | Public RERA projects | KA | v1 | blocked | T081, T082, T105 (plan T105) | `configs/sources/s31.yaml`, `docs/sources/s31.md` | `tests/test_context_layers.py` | Reproduction needs written K-RERA permission. | Owner item: email K-RERA (not a numbered H-step). |
| F020 | Building outlines | ALL | v1 | built-not-mounted | T069, T070, T105, T185 (plan T105) | `web/src/map/ContextLayers.tsx`, `src/atlas/spatial/tiles.py`, `docs/releases/ka-v1.md` | `tests/test_context_layers.py`, `web/src/map/ContextLayers.test.ts` | Not mounted until a public snapshot carries it; no PMTiles archive built (D117, D151). Owner: H11, H05. | none |
| F021 | Mandi price ticker | ALL | MVP | blocked | T023, T025, T039 (plan T039) | `configs/sources/s22.yaml`, `configs/sources/s23.yaml`, `docs/sources/s23.md` | `tests/sources/test_s23.py` | S22 needs a browser render; S23 has no publisher statement of its price denominator. | Unknown price units cannot be rendered as prices (D58). |
| F022 | District crime totals if source exists | ALL | stretch | built-not-mounted | T087, T088, T105 (plan T105) | `web/src/map/ContextLayers.tsx`, `configs/sources/s44.yaml`, `docs/releases/ka-v1.md` | `tests/test_context_layers.py` | Not mounted until a public snapshot carries it (D114, D117). Owner: H11. | Lists the published district totals per year; maps nothing. |
| F023 | Place Lens: now/risk/forecast/history/nearby/sources | ALL | MVP | shipped-local | T040 (plan T040) | `web/src/components/PlaceLens.tsx`, `docs/web-lens.md` | `web/tests/lens.spec.ts`, `tests/test_lens.py` | none | Judgement call: the Lens runs locally, but risk and forecast show no model output and Nearby states that facilities cannot be verified (S18 facilities not yet exported, D59, D174). Same snapshot caveat as F001. |
| F024 | Official/model/inferred provenance | ALL | MVP | shipped-local | T038, T039 (plan T039) | `web/src/data.ts`, `web/src/components/SourceBadge.tsx`, `schemas/common.json` | `tests/test_web_manifest.py`, `web/src/data.test.ts`, `tests/test_layers.py` | none | Same snapshot caveat as F001. |
| F025 | Nearest hospitals/shelters/police/fire stations | ALL | MVP | built-not-mounted | T021, T022, T040 (plan T040) | `configs/sources/s18.yaml`, `src/atlas/ingest/s18_prepare.py`, `configs/sources/s43.yaml`, `docs/web-lens.md`, `src/atlas/publish.py` | `tests/test_lens.py`, `tests/sources/test_s18_prepare.py`, `tests/test_publish.py` | Facilities ship in every T045 release (D175, D185); shown once the owner approves public release. Owner: H11. | Hospitals, police and fire stations only; OSM shelters are mostly bus shelters and stay out (D175). |
| F026 | Shareable place URL and printable PDF | ALL | MVP | shipped-local | T040 (plan T040) | `web/src/report.ts`, `web/src/components/PlaceLens.tsx`, `docs/web-lens.md` | `web/src/report.test.ts`, `web/tests/lens.spec.ts`, `tests/test_lens.py` | Owner: H11. | Judgement call: print and link parsing run locally; a shared link resolves only through an approval file, and none is published until T045 and H11 (D59). |
| F027 | Reservoir levels and inflow forecasts | KA/KL | v1 | blocked | T008, T092, T094, T130 (plan T094) | `models/registry/m02.json`, `models/registry/m03.json`, `models/registry/m07.json`, `docs/releases/kl.md` | `tests/test_ka_v1.py`, `tests/test_kl_release.py` | M02 and M03 need S28 daily history; M07 needs datum for 8 dams and S34 bulk OCR (T118). | S32 Kerala dam levels are held locally (kl.md 'measured'), but no levels layer is mounted. |
| F028 | Ward/taluk flood risk | KA/KL | v1 | blocked | T089, T091, T130 (plan T091) | `models/registry/m01.json`, `models/registry/m08.json` | `tests/test_ka_v1.py`, `tests/test_kl_release.py` | No dated ward flood labels (S43) and no audited Kerala history (S35, H10). Owner: H10. | none |
| F029 | Landslide susceptibility | KL | v1 | blocked | T136, T138 (plan T138) | `models/registry/m09.json`, `reports/models/m09.md` | `tests/test_kl_release.py` | S37 has no inventory with footprint; S42 needs a Copernicus account (D126). Owner: H15. | H15 is proposed, not in amendments A5. |
| F030 | Taluk drought outlook | KA then ALL | v1 | built-not-mounted | T101, T102, T103 (plan T103) | `models/registry/M05/v1.json`, `models/registry/M05/v1.approval.json`, `reports/models/m05.md`, `reports/models/m05-card.md` | `tests/test_ka_v1.py`, `tests/test_web_accuracy.py` | No outlook layer exists: M05 is a hindcast (D39) at district level (no taluk polygons); S08-derived outputs may be published, never rainfall values (H11 item 3, D166). Owner: H11. | Judgement call: the model is measured and owner-approved (D43) and its scores show on the local accuracy page (F036); ka-v1.md calls F030 measured in that sense. Intervals stay hidden (D42, T262). |
| F031 | 24-72h AQI/pollutant forecasts | DL | v1 | blocked | T146, T159, T161 (plan T161) | `models/registry/m14.json`, `configs/sources/s24.yaml` | `tests/test_dl_release.py` | S24 resource page could not be read by any tool (D133); 0 station rows. | Retry is a re-run of T146 with a browser that can read page content; no new key. |
| F032 | Bus ETA/delay and bunching | DL | v1 | blocked | T153, T155, T156 (plan T155) | `models/registry/m12.json`, `models/registry/m13.json` | `tests/test_dl_release.py` | S38 blocked on H04; 0 vehicle positions (D140). Owner: H04. | none |
| F033 | 16-day price-spike warning | KA then KL | MVP | blocked | T035, T036, T037 (plan T037) | `models/registry/m06.json`, `reports/models/m06.md` | `tests/test_ka_v1.py` | Zero price rows: S22 and S23 blocked (D55). | none |
| F034 | Rain what-if simulator | KA/KL | stretch | blocked | T176, T178 (plan T178) | `models/registry/m20.json`, `reports/models/m20.md` | `tests/test_dashboards.py` | M20 needs an approved base model for the target; recorded as a blocked branch (D145). | none |
| F035 | SHAP explanations and uncertainty bands | ALL | v1 | research-only | T034, T262 (plan T034) | `models/registry/M05/v1.intervals.json`, `reports/models/m05-intervals.md`, `requirements/ml.in` | `tests/test_dashboards.py` | M05 intervals cover 72.8% against an 80% gate, so they stay hidden (D42, T262). | Judgement call: the intervals are measured and fail their gate. No SHAP values exist for any model: shap is pinned in requirements/ml.in but no code calls it (see Findings). |
| F036 | Accuracy page and daily matured backtests | ALL | MVP | shipped-local | T257, T259 (plan T046) | `web/src/pages/Accuracy.tsx`, `docs/releases/ka.md`, `web/tests/fixtures/accuracy-ka.json` | `web/tests/accuracy.spec.ts`, `web/src/accuracy.test.ts`, `tests/test_web_accuracy.py` | Owner: H11. | Judgement call: the minimal MVP table runs at ?page=accuracy locally (T257, T259); its plan task T046, the MVP gate, has not passed. No daily matured backtest exists because no model serves live predictions. H11 item 1 approved publishing the table on 11 Nov 2026 (D166); nothing is deployed. |
| F037 | Anomaly feed | ALL | v1 | research-only | T212-T216 (plan T216) | `models/registry/m16.json`, `reports/models/m16.md`, `reports/models/m16-flag-counts.json`, `eval/anomalies/blocked.json`, `web/src/pages/Quality.tsx` | `tests/labels/test_anomaly_blocked.py`, `tests/test_dashboards.py` | 0 of 100 flags adjudicated, so precision is not measured (D159, D160). | Proposed owner step: adjudicate 100 M16 flags with independent evidence. |
| F038 | Population exposed to risk | ALL | v1 | blocked | T143 (plan T143) | `src/atlas/spatial/exposure.py`, `configs/sources/s16.yaml` | none | No verified hazard polygon exists (S37, S43); the exposure code is tested on an H3 cell only (D128). | none |
| F039 | Experimental route avoiding flagged roads | KA/KL | v1 | blocked | T143 (plan T143) | `src/atlas/spatial/routes.py`, `web/src/components/RouteComparison.tsx` | `web/src/components/RouteComparison.test.ts` | No road graph is built from S18 yet (D174) and no official shelter record (S43); every result says not a safe route (D128). | none |
| F040 | Heatwave/heat exposure layer | ALL/DL | v1 | blocked | T162, T164 (plan T164) | `models/registry/m15.json`, `reports/models/m15.md` | `tests/test_dl_release.py` | No Delhi source enabled; S01 keeps no issue-time vintages; S18 has no Delhi extract (D141, D174). | Not owner-gated: enable S01 and S02 for Delhi and collect forecast vintages. |
| F041 | Crop health / NDVI | ALL | stretch | blocked | T127, T145 (plan T145) | `configs/sources/s42.yaml`, `src/atlas/analysis/vegetation.py` | `tests/test_climate_product.py` | S42 needs a Copernicus account (proposed H15); no crop mask (D130). Owner: H15. | none |
| F042 | Rainfall trend since 1901 | ALL | v1 | shipped-local | T145 (plan T145) | `web/src/pages/Climate.tsx`, `web/src/climate.json`, `reports/eda/08_climate_product/climate.json`, `web/src/main.tsx` | `web/src/pages/Climate.test.ts`, `tests/test_climate_product.py` | Owner: H11. | Mounted 11 Nov 2026 (D172) at ?page=climate after H11 item 3 (derived outputs only). Indices only, never millimetres (S08 licence); trends cover 1981-2025. |
| F043 | CMIP6 outlook to 2050 | ALL | v1 | shipped-local | T145 (plan T145) | `web/src/pages/Climate.tsx`, `web/src/climate.json`, `web/src/main.tsx` | `web/src/pages/Climate.test.ts`, `tests/test_climate_product.py` | Owner: H11. | Mounted 11 Nov 2026 (D172) at ?page=climate. Labelled climate projection, not a forecast; S06 has no named scenario. |
| F044 | Monsoon progress tracker | ALL | v1 | shipped-local | T145 (plan T145) | `web/src/pages/Climate.tsx`, `web/src/climate.json`, `web/src/main.tsx` | `tests/test_climate_product.py` | Owner: H11. | Mounted 11 Nov 2026 (D172) at ?page=climate. The tracked year is 2025, a past year; onset is labelled inferred. |
| F045 | Past-disaster replay | KL then ALL | v1 | built-not-mounted | T142 (plan T142) | `web/src/components/Replay.tsx`, `notebooks/05_kl_flood2018.ipynb`, `docs/releases/kl.md` | `tests/test_replay2018.py`, `web/src/components/Replay.test.ts` | Not mounted; the 122 S08 records exist only in a local, untracked export (H11 item 9, D166); S35 blocked (D127, D129). Owner: H11, H10. | none |
| F046 | Cited RAG Ask by text | ALL | v1 | research-only | T179, T180, T181, T252-T266 (plan T180) | `web/src/pages/Ask.tsx`, `reports/rag.md`, `docs/ask.md`, `configs/rag.yaml` | `web/tests/ask.spec.ts`, `tests/test_web_ask.py`, `tests/test_ask_config.py` | Evidence support below the 0.95 gate (0.86 on 8 Nov, 0.77 in the report frozen for release on 12 Nov); extractive only; Workers AI not connected (D101, D147, D187). Owner: H05, H11. | The page runs at ?page=ask locally, labelled research-only; the owner counts it for the MVP gate as research-only (H11 item 2, D166). |
| F047 | Voice input and read-aloud | ALL | stretch | research-only | T182 (plan T182) | `web/src/voice.ts`, `web/src/pages/Ask.tsx` | `web/src/voice.test.ts`, `tests/test_i18n.py` | It is an input to Ask, which is research-only (D148). | Judgement call: the voice controls run on the local Ask page; they inherit Ask's research-only status. |
| F048 | Kannada/Malayalam/Hindi/English | ALL | v1 | blocked | T181, T182 (plan T182) | `web/src/i18n/kn.json`, `web/src/i18n/ml.json`, `web/src/i18n/hi.json`, `eval/rag/translations.jsonl` | `tests/test_i18n.py` | kn, ml and hi strings and questions are unreviewed machine drafts; only English is selectable (A7, D147, D148). Owner: H11. | Needs a native-speaker review (A7). |
| F049 | Place watches | ALL | v1 | shipped-local | T183 (plan T183) | `web/src/components/Watches.tsx`, `web/src/App.tsx` | `web/src/components/Watches.test.ts` | Owner: H11. | Mounted 11 Nov 2026 (D172) in the record panel; device-local IndexedDB only. It appears once a snapshot exists; only expiry stops a signal (records carry no cancelled flag). |
| F050 | Telegram bot delivery to public state channels | ALL | v1 | blocked | T083, T084, T183 (plan T183) | `configs/sources/s39.yaml`, `src/atlas/alerts/telegram.py` | `tests/test_alerts.py` | S39 needs the bot, channel and token (H08). Owner: H08. | none |
| F051 | Background Web Push | ALL | stretch | deferred | T184 (plan T184) | `docs/decisions/web-push.md`, `web/src/push.ts`, `worker/src/push.ts` | `tests/test_push_policy.py`, `web/src/push.test.ts` | Disabled by the no-personal-data policy; needs a written owner policy revision (D150). | none |
| F052 | Daily cited brief | ALL | v1 | built-not-mounted | T183 (plan T183) | `src/atlas/alerts/brief.py` | `tests/test_alerts.py` | No job or schedule runs the brief and no completion stamp exists (D149). Owner: H11. | Judgement call: the brief builder is tested on real Sachet fixtures but no command or workflow produces a brief. |
| F053 | City Memory: every published snapshot | ALL | v1 | built-not-mounted | T045 (plan T045) | `docs/account-setup.md`, `docs/releases/ka.md`, `src/atlas/publish.py`, `src/atlas/replay.py` | `tests/test_hosted_archive.py`, `tests/test_publish.py` | Releases are built daily from the Worker and archived privately (D185); public publication waits for the owner's approval. Owner: H11. | none |
| F054 | Analysis dashboards | ALL | v1 | shipped-local | T217 (plan T217) | `web/src/pages/Analysis.tsx`, `web/src/dashboards.json`, `web/src/main.tsx` | `tests/test_dashboards.py`, `web/src/dashboards.test.ts` | Owner: H11. | Judgement call: D161 calls the dashboards built, not mounted, meaning no public snapshot; they are reachable locally at ?page=analysis. |
| F055 | Data-quality dashboard | ALL | v1 | shipped-local | T217 (plan T217) | `web/src/pages/Quality.tsx`, `web/src/dashboards.json`, `web/src/main.tsx` | `tests/test_dashboards.py`, `web/src/dashboards.test.ts` | Owner: H11. | Reachable locally at ?page=quality; same D161 wording as F054. |
| F056 | Open downloads and public static API | ALL | v1 | built-not-mounted | T218 (plan T218) | `src/atlas/export.py`, `web/src/export.ts` | `tests/test_offline.py` | No export button is mounted and there is no host (D162). Owner: H05, H11. | Only open, available sources pass the licence rule; S08, S30 and S34 are refused. |
| F057 | Offline PWA | ALL | v1 | built-not-mounted | T218 (plan T218) | `web/src/sw.ts`, `web/public/manifest.webmanifest` | `web/src/offline.test.ts`, `tests/test_offline.py` | No service worker is registered until an approved snapshot and host exist (D162). Owner: H05, H06, H11. | none |
| F058 | Embeddable read-only widgets | ALL | stretch | blocked | T218 (plan T218) | `web/src/pages/Widget.tsx` | `tests/test_offline.py` | Embedding needs its own path with frame-ancestors headers on a host; no host and no partner origin (D162). Owner: H05, H11. | Judgement call: the read-only summary renders locally at ?page=widget, but it cannot be embedded anywhere. |
| F059 | State comparison | ALL | v1 | shipped-local | T217 (plan T217) | `web/src/pages/Compare.tsx`, `web/src/dashboards.json` | `tests/test_dashboards.py`, `web/src/dashboards.test.ts` | Owner: H11. | Judgement call: reachable locally at ?page=compare; it compares status counts and coverage only, and every metric pair reads unavailable (D161). |
| F060 | Gauge interpolation / gaps study | KA | v1 | blocked | T077, T098, T100 (plan T100) | `models/registry/m04.json`, `reports/models/m04.md` | `tests/test_ka_v1.py` | No daily gauge data with coordinates (S27; S29 annual only). | none |
| F061 | Rain-price effect study | KL | v1 | blocked | T139, T141, T142 (plan T141) | `models/registry/m10.json`, `reports/models/m10.md` | `tests/test_kl_release.py` | Zero price rows (S22, S23) (D126, D127). | none |
| F062 | Cross-state transfer and drift | ALL | stretch | blocked | T170, T172 (plan T172) | `models/registry/m11.json`, `reports/models/m11.md` | `tests/test_dashboards.py` | No shared labels across states (D145). | none |
| F063 | U-Net flood mapping and GRU challenger | KL/KA | stretch | blocked | T167, T173, T175 (plan T175) | `models/registry/m17.json`, `models/registry/m19.json`, `reports/models/m17.md`, `reports/models/m19.md` | `tests/test_dashboards.py` | M17 needs S42 (proposed H15) and labelled events; M19 needs the blocked M02 baseline and a free GPU (H10) (D144). Owner: H15, H10. | none |
| F064 | Downloadable evidence and correction ledger | ALL | v1 | built-not-mounted | T219 (plan T219) | `src/atlas/monitoring.py`, `docs/runbooks/rollback.md` | `tests/test_monitor.py` | No prediction ledger exists (no model serves live predictions) and there is no host for downloads (D163). Owner: H05. | Correction and re-score functions are tested on temporary stores. |

## Models

From `models/registry/` (M05 from `M05/v1.json` and its owner approval). The status column is the
registry's own word.

| Model | State | Registry status | Record |
|---|---|---|---|
| M01 | ka | blocked | `models/registry/m01.json` |
| M02 | ka | blocked | `models/registry/m02.json` |
| M03 | ka | blocked | `models/registry/m03.json` |
| M04 | ka | blocked | `models/registry/m04.json` |
| M05 | ka | approved | `models/registry/M05/v1.json`, `models/registry/M05/v1.approval.json` (champion, hindcast, D43; intervals hidden, D42) |
| M06 | ka | blocked | `models/registry/m06.json` |
| M07 | kl | blocked | `models/registry/m07.json` |
| M08 | kl | blocked | `models/registry/m08.json` |
| M09 | kl | blocked | `models/registry/m09.json` |
| M10 | kl | blocked | `models/registry/m10.json` |
| M11 | kl | blocked | `models/registry/m11.json` |
| M12 | dl | blocked | `models/registry/m12.json` |
| M13 | dl | blocked | `models/registry/m13.json` |
| M14 | dl | blocked | `models/registry/m14.json` |
| M15 | dl | blocked | `models/registry/m15.json` |
| M16 | all | research_only | `models/registry/m16.json` (counts only, 0 of 100 flags adjudicated) |
| M17 | kl | blocked | `models/registry/m17.json` |
| M18 | kl | blocked | `models/registry/m18.json` |
| M19 | ka | blocked | `models/registry/m19.json` |
| M20 | all | blocked | `models/registry/m20.json` |

## Plan sections audit

The plan's summary promises "20 ordered sections". Its table of contents runs from section 1
(Summary) to section 20 (Appendix B). Each is mapped to where the repository answers or records it.

| No. | Plan section | Where the repository answers or records it |
|---|---|---|
| 1 | Summary | `README.md`, `docs/plan.pdf` |
| 2 | Assumptions and answers to questions | `docs/amendments.md`, `docs/decisions.md` |
| 3 | Decisions log | `docs/decisions.md` (D17 onward; D01 to D16 are in the plan) |
| 4 | Architecture and file tree | `src/atlas/`, `web/src/`, `worker/src/`, `docs/HANDOFF.md` (section 5, code map) |
| 5 | Tools and versions | `requirements/core.txt`, `requirements/dev.txt`, `docs/dependency-audit.md`, `tests/test_locks.py` |
| 6 | Data source catalogue | `configs/sources/` (44 records), `docs/sources/`, `docs/releases/ka-v1.md`, `docs/releases/kl.md`, `docs/releases/dl.md` |
| 7 | Data schemas | `schemas/common.json`, `src/atlas/contracts.py` |
| 8 | Feature catalogue | `docs/releases/final-features.json` and the feature audit above |
| 9 | Data analysis plan | `notebooks/`, `reports/eda/`, `reports/sql_insights.md` |
| 10 | Data science plan | `docs/methods.md`, `reports/models/`, `models/registry/` |
| 11 | ML model cards | `configs/models/`, `reports/models/m05-card.md`, `web/src/dashboards.json` (20 models) |
| 12 | LLM and RAG plan | `configs/rag.yaml`, `eval/rag/questions.jsonl`, `reports/rag.md`, `docs/ask.md` |
| 13 | Frontend plan | `web/`, `docs/web-shell.md`, `docs/web-layers.md`, `docs/web-lens.md` |
| 14 | MLOps, testing, security and legal | `tests/`, `.github/workflows/`, `src/atlas/monitoring.py`, `docs/runbooks/rollback.md`, `docs/runbooks/maintain.md`; manual checks above are not performed |
| 15 | Timeline, milestones and risk register | `docs/amendments.md` (A8 session order), `docs/HANDOFF.md` (section 7 work log) |
| 16 | Task list for Claude Code | `docs/HANDOFF.md` (section 7), `docs/amendments.yaml` (T222 onward) |
| 17 | Portfolio and interview pack | `docs/portfolio/`, `docs/case-studies/template.md`, `README.md` |
| 18 | Glossary of concepts | `docs/glossary.md` |
| 19 | Appendix A: full task list as YAML | `docs/plan.pdf` (Appendix A), `docs/amendments.yaml` (changes and added tasks) |
| 20 | Appendix B: open questions and UNVERIFIED items | `docs/releases/final.md` (owner tasks below), `docs/HANDOFF.md` (section 8) |

## Sources in publication

Nothing is published: there is no host, no approval file for any snapshot and no registered service
worker. No source with an unverified licence is enabled in any state config (`configs/states/`), so
none can reach a build. Enabled restricted sources: S08, S12, S20, S30, S36. Their raw files stay in
`data/raw`, which git does not track; only derived outputs may be published, after H11.

- The web build bundles `web/src/dashboards.json`, which holds M05 scores derived from S08 and no
  S08 rainfall value or interval (`tests/test_dashboards.py`). The owner answered H11 item 3 on
  11 Nov 2026 (D166): derived outputs only, citing Pai et al. (2014), never rainfall values
  ([h11-ka.md](h11-ka.md)).
- As [kl.md](kl.md) records under "Licence finding, settled at H11": the T142 files
  `replay2018.json`, `monthly_2018.csv` and `s08_kerala_annual.csv` under `reports/eda/` hold S08
  box-mean rain values. On 11 Nov 2026 the owner had them removed from the repository (D166): they
  are untracked and stay local, and old copies remain in git history. The replay keeps derived
  departures only. The same day (D167) the tracked EDA summaries and `district_year_comparison.csv`
  dropped their S08 mm values (percentages and the grid-to-gauge ratio stay) and four S08 charts
  were untracked.
- S12 and S20 display terms wait for H11 (D109, D110); S30 is labelled unofficial and restricted
  (D115); S36 is used as district facts with document and page citations (D123).

## Cost evidence

- `scripts/audit_dependencies.py --policy` reports `policy: 0 problem(s)` (agent, 11 Nov 2026):
  free sources only, no secret value in configs, no paid service referenced.
- 44 of 44 source records have `no_card: true` (`configs/sources/`).
- No workflow in `.github/workflows/` holds a deploy step or reads a secret; `feeds.yml`,
  `tiles.yml` and `monitor.yml` are manual dispatch only and have never been dispatched.
- No domain was bought. The plan and `docs/account-setup.md` use a free subdomain only; none is set
  up.
- Not verified from the repository: the billing state of the owner's Cloudflare, Hugging Face,
  GitHub and data.gov.in accounts, and GitHub Actions minutes used. The owner reported the
  Cloudflare and Hugging Face accounts as free with no card on 6 Nov 2026; no capability probe has
  run (H05).

Cost: Rs 0 as far as the repository shows; no billing account is referenced anywhere in it.

## Release manifest

`docs/releases/final-manifest.json` lists SHA-256 hashes (line endings normalised to LF) of the
files this page relies on: the model registry, the gate pages, `kl-ml.json`, `dashboards.json`,
`reports/rag.md`, every source record, the state configs, the Python lock files, the web and Worker
`package-lock.json` files and `final-features.json`. It pins this commit's state. When any of those
files changes, regenerate it, never edit it by hand:

```powershell
.\.venv\Scripts\python tests/test_final.py --manifest
```

`tests/test_final.py` re-hashes every listed file and fails on any difference.

## Owner tasks

Open steps with an H number, from [ka.md](ka.md), [ka-v1.md](ka-v1.md), [kl.md](kl.md),
[dl.md](dl.md), [h11-ka.md](h11-ka.md), `docs/HANDOFF.md` section 8 and `README.md`.

| ID | What the owner does | What it unblocks | Recorded in |
|---|---|---|---|
| H04 | Completes the Delhi Open Transit Data registration (key, Terms, static GTFS) | S38, T148 re-run, M12, M13, F012, F032 | dl.md, HANDOFF section 8 |
| H05 | Creates the Cloudflare API token and records free, no-card status | T042 to T045, Workers AI for Ask, F053, F056, F057, F058, F064 | ka.md, account-setup.md |
| H06 | Done 12 Nov 2026 (D179): private archive dataset and a token scoped to it | T045 (archive), F053, F057 | ka.md, account-setup.md |
| H08 | Creates the Telegram bot and public channel, stores the token | S39, T083, T084, F050 | ka-v1.md, HANDOFF section 8 |
| H09 | Done 12 Nov 2026 (D176): NASA FIRMS MAP_KEY saved in `.env` | S25, T075, T076, F015 | ka-v1.md, HANDOFF section 8 |
| H10 | Kaggle sign-in (optional) | S35 re-check, M08, free GPU for M17 and M19 | kl.md, HANDOFF section 8 |
| H11 | Karnataka sheet answered on 11 Nov 2026 (D166): six items, 18+ OpenFreeMap terms, boundary disclaimer, S08 files. Still open: the Malayalam strings, S12 and S20 display terms, the WorldPop undercount label, and the review of the Kerala and Delhi layers | T046, publication of any layer, mounting the 19 built-not-mounted rows that list H11 | h11-ka.md, ka.md, kl.md, dl.md |
| H12 | Gets an aisstream key | S26, T111, T112, ships in F014 | kl.md |
| H13 | Reviews at least 20% of every news batch and every held-out item | T189 to T211, M18, F017 | amendments.md, D155, D156 |
| H14 | Reads each core case study and rewrites its summary | Portfolio case studies (M05, M07, Ask) | ka.md, README.md |
| H15 | (proposed in T127, not in amendments A5) Registers a Copernicus Data Space account | S42, M09, M17, F029, F041 | kl.md |

Other open owner items without an H number (from the same pages):

| Item | What the owner does | What it unblocks |
|---|---|---|
| T118 | Approves bulk OCR of the S34 dam reports | S34, M07 (C1) |
| S18 | Done 12 Nov 2026 (D174); repeats the browser download monthly | T041, roads, routes, facilities (F018, F025, F039) |
| S31 | Emails K-RERA for permission to reproduce the project list | F019 |
| S11 | Reads the OpenSky terms and decides (optional) | Flight fallback |
| S28 | Sends the drafted KWRIS request to ACIWRM | T008 re-run, M02, M03 |
| S41 | Obtains written publisher permission for news items | S41, T125, F017 |
| S24 | Opens the data.gov.in resource page in a browser that can read it (dl.md lists this as an owner item) | T146 re-run, M14, F031 |
| Power BI | Opens `powerbi/MonsoonAtlas.pbip` in Power BI Desktop and exports PNG and PDF (D132) | Report images |
| Demo video | Records the demo from `docs/portfolio/video.md` | Portfolio |
| M16 flags | (proposed) Adjudicates 100 M16 flags with independent evidence (D159) | M16 precision |
| M05 v2 | Nothing now: v2 is built and published as untested (H11 item 6, D166, D170) and v1 serves. Once IMD 2026 and 2027 are published and v2 passes its one test, the owner approves or rejects serving it (D38) | Serving M05 v2 |
| Language review | Native-speaker review of the kn, ml and hi drafts (A7) | F048 |

### Done owner steps

| ID | Step | Evidence |
|---|---|---|
| H01 | Final name approved | D19 in `docs/decisions.md` |
| H02 | GitHub repository and authentication | `docs/HANDOFF.md` section 8 (Git: PRs merged to `main`) |
| H03 | Python 3.12 installed | `AGENTS.md` (Python 3.12.14 in `.tools/python`), `tests/test_environment.py` |
| H07 | data.gov.in API key supplied | `docs/HANDOFF.md` section 8 (T025 used the owner's key) |

## Exact next unfinished task

- **Next task the agent can do without the owner: re-run T146 (S24 verify).** Its retry condition
  needs only a browser tool that can read the data.gov.in resource page and its API tab (no new
  key, D133); a pass would let T147 enable the adapter and reopen M14 (T159 to T161) and F031. It
  needs network access, which T221 did not have.
- **First owner step: H05** (then H06). The Karnataka H11 sheet [h11-ka.md](h11-ka.md) was
  answered on 11 Nov 2026 (D166); H11 is still named by 30 of the 64 feature rows (public release,
  Kerala and Delhi layers). The hosting chain T042 to T045, and with it T046, cannot start
  without H05.

T046 (the Karnataka MVP gate) stays the first unfinished task in plan order: it waits for T045
(H06 and the capability probe; H05 token saved 12 Nov 2026) and H11; T041 is done (D177).

## Findings

Defects found by this audit. T221 did not fix them, because each sits in a gate page or the handoff,
which T221 may not edit. All three were fixed afterwards (D171).

1. `docs/releases/ka-v1.md` line 114 lists F035 (T034) among rows that "belong to later tasks", but
   T034 is a P1 task done before T110. No task produced SHAP values: `shap` is pinned in
   `requirements/ml.in` and no code calls it, so the SHAP half of F035 has no task that would
   ever produce it.
2. `docs/HANDOFF.md` line 847 asks to move `EventTicker` strings into locale files "before
   mounting", but `EventTicker` has been mounted in `web/src/App.tsx` since T039; its English
   literals are on the local map page today (D154 says the same of the wall, correctly).
3. `docs/decisions.md` D161's title says the four dashboards are "built, not mounted", while
   `web/src/main.tsx` routes `?page=quality`, `analysis` and `compare` in the local app. The body
   explains that no public snapshot carries them; the title alone reads as unreachable. This page
   counts F054, F055 and F059 as `shipped-local`.
