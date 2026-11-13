# Decisions log

## Continuation review (5 Nov 2026)

- **D210 — Model accuracy page leads with working models (13 Nov 2026).**
  Owner, in chat: 18 of 20 cards said BLOCKED and read as weakness. The Model accuracy page
  now opens with one framing line (a model counts as working only if it beats the strongest simple
  baseline on held-out data; no labels means roadmap, never invented data), a state switch
  (Karnataka default, Kerala, Delhi, All; Kerala and Delhi say their phase has not started), a hero
  card for M05 with every number read from `dashboards.json`, and M16 labelled research-only.
  Blocked models move, unchanged, into a collapsed "Roadmap: models waiting for data" list with
  their reasons and report links; none is removed or scored. The approved table stays below.

- **D209 — Redesign step 2: Overview landing page with a 3D district map (13 Nov 2026).**
  Owner, in chat: "Start step 2". A bare address now opens `Overview` (hero, four headline
  numbers, a 3D map, district panel, links to every analysis); the map workspace moves to
  `?page=map`, and shared place links (which carry query parameters) still open the map. The 3D
  map uses MapLibre `fill-extrusion` (no new dependency) over a plain background with no basemap
  tiles, so no third-party tile failure can blank it and no international border is drawn. The
  30 district outlines are `web/src/ka-districts.json` (61 KB), written by
  `scripts/ka_districts.py` from the local S17 geoBoundaries file (ODbL, simplified about 1 km,
  credited under the map). Measures: southwest monsoon % of the ERA5 normal, % of people over
  10 km from a hospital, rain trend per decade (significant districts outlined); a district
  without a value stays grey, never zero. The district panel reuses the Place Lens profile, and a
  ranked table is the accessible fallback. Also: on wide screens the map panel is now one screen
  tall and sticky, so `?page=map` opens on Karnataka instead of the top of a tall panel. Browser
  tests now open `/?page=map` for the map; a new Overview test runs axe WCAG 2.2 AA.

- **D208 — Redesign step 1: one site shell (13 Nov 2026).**
  Owner, in chat: the site "is not impressive"; approved a four-step redesign and "start step 1".
  `web/src/components/SiteShell.tsx` gives every page the same dark header with grouped navigation
  (Explore: Map, Monsoon tracker, Bus access, Warning archive; Analysis: Data findings, Model
  accuracy, Climate; Tools: Ask, Wall display; Official warnings as an outlined button), the
  current page marked with `aria-current`, a breadcrumb back to the map and a footer with the
  emergency note and the GitHub link. The map keeps its workspace and uses the same header (its
  h1 stays "Monsoon Atlas"); wall and widget modes stay bare. Shared page styles: system fonts
  (no external font request), tabular numbers, carded tables, 44 px nav targets, visible amber
  focus rings, reduced motion. On phones the nav is one scrollable row and wide tables scroll
  inside themselves (focusable). The per-page "Back to the map" links are removed. All 87
  Playwright tests (with axe WCAG 2.2 AA checks) and 144 unit tests pass.

- **D207 — Accuracy table published with the site (13 Nov 2026).**
  Owner, in chat, reported pages that show nothing. Audit: `?page=accuracy` showed "Unexpected
  token '<'" because no deploy wrote `/data/ka/accuracy/latest.json`, so Pages served the HTML
  shell. `python -m atlas.models.accuracy --publish <site>` now writes the owner-approved table
  (H11, D166) as `data/ka/accuracy/<sha256>.json` plus an approved pointer, in both `daily.yml` and
  `scripts/deploy_site.py` (tested). The monsoon tracker already works since D202's deploy.

- **D206 — Weather forecast for all 30 districts (13 Nov 2026).**
  Owner, in chat: "Yes, all 30". S01 now captures the 30 district representative points
  (`configs/static/ka/places.json`, 2 dp) in one Open-Meteo request, 3 forecast days instead of 16
  to keep the relayed checkpoint small (about 90 KB raw per capture). Probe on 13 Nov: 30 distinct
  ECMWF IFS 0.25-degree cells, each within 18.6 km of its point, so every district's Place Lens
  (25 km radius) gets its own next-hour temperature. Each grid centre is pinned in
  `s01_collect.DISTRICTS` and a moved cell is refused, as before. Receipts carry a profile, and the
  T009 Bengaluru profile stays valid in collect, prepare and the checkpoint check, so receipts
  already in the hosted chain keep verifying (no new bootstrap). Prepare emits one record per
  district with a usable hour (none is filled) and `mapping_version` becomes `s01-prepared-v2`.
  Tests replay genuine fixtures: the old single-point pair (now pinned in `tests/conftest.py`) and a
  new 30-point response with its model metadata.

- **D205 — District profile in the Place Lens (13 Nov 2026).**
  Owner, in chat: after picking Bengaluru, "only really helpful is nearby". Cause: the live
  release held one S01 forecast point (Bengaluru only) and no active warning, so Now, Risk,
  Forecast and History were near empty for most districts. The Now tab now opens with a district
  profile built from committed results: this year's southwest and northeast monsoon (% of the
  2001-2025 ERA5 normal, from `/data/ka/monsoon.json`), hospital access (share over 10 km, mean km,
  rank of 30), the 1981 rain trend (Sen slope, BH q) and, for Bangalore only, bus access. Each
  fact links to its page; no new number. All 30 place names match the findings and tracker
  names (checked). Next: S01 forecasts for all 30 district points.

- **D204 — Merge when CI passes; deploy on every merge (13 Nov 2026).**
  Owner, in chat: chose standing approval to merge each PR once CI passes ("a"), then "turn on"
  auto-merge. `main` requires the two `ci` checks (`test` on Ubuntu and Windows; `web` runs only when site files change, so it cannot be required;
  admins not enforced, no review rule), so GitHub auto-merge can wait for them. `daily.yml` also
  runs on every push to `main`, so a merged PR deploys without waiting for GitHub's irregular
  schedule (feeds ran on schedule only twice in 12 hours on 12-13 Nov).

- **D203 — H15 Copernicus account done; S3 keys verified (13 Nov 2026).**
  The owner registered a Copernicus Data Space Ecosystem account in their own browser (the
  built-in browser failed the site's Captcha.eu check) and created S3 keys, saved in `.env` as
  `CDSE_S3_ACCESS_KEY` and `CDSE_S3_SECRET_KEY`. The agent never signs in with the account
  password: a read-only, SigV4-signed ListObjectsV2 on `eodata` (Sentinel-1 GRD prefix) returned
  HTTP 200, so the keys work. S42 stays blocked until its verify task re-runs with the keys
  (Kerala phase, M17); nothing was downloaded.

- **D202 — District monsoon tracker normals committed (13 Nov 2026).**
  The ERA5 (S02) backfill finished: 25 reference years, 2001-2025, June to December, one grid
  point per district (`data/clean/S02/ka-districts/`, local). `configs/static/ka/monsoon-normals.json`
  is written by `python -m atlas.analysis.district_monsoon normals`, so `daily.yml` and
  `scripts/deploy_site.py` now build `?page=monsoon` (D192). Sanity check before commit: the 2026
  request uses the same `models=era5` as the history and has no missing day in 160 days; the
  2026 southwest season ranks below normal in 29 of 30 districts (statewide mean about 530 mm
  June to September against about 914 mm in 2025). This is reanalysis, not a gauge total, and is
  labelled so on the page; no gauge cross-check exists yet (S29 is annual only).

- **D201 — Karnataka price history found; M06 can move from blocked to a verify task (13 Nov 2026).**
  Owner, in chat, opened the AGMARKNET daily price and arrival report (captcha solved by the
  owner) for Onion, Karnataka, 12 Nov 2026: each row carries a "Price Unit" column, here
  "Rs./Quintal". This is the publisher statement the S23 retry condition asks for, and it is per
  commodity, so the unit must be read per commodity (livestock, eggs and fish are not per quintal).
  A second data.gov.in resource from the same catalogue and publisher, "Variety-wise Daily Market
  Prices Data of Commodity" (API resource 35985678-0d79-46b4-9ed6-6f13308a1d24, GODL), holds
  83,029,616 rows with the same fields; Karnataka onion alone has 103,423 rows back to 2014, and
  the Arrival_Date filter works (14 Karnataka onion rows on 02/01/2019). Probe responses are in
  `data/raw/S23/probe/` (raw, local only). S23 stays blocked until a verify task records this
  resource as evidence, maps each commodity's unit from AGMARKNET and checks the history for gaps;
  then the T026 adapter and the M06 price-spike model can follow the honest-ML rules. The key went
  only into API requests from `.env`; no form was filled by the agent.

- **D200 — H14 owner review file and gate check (12 Nov 2026).**
  Owner, in chat: "ok continue with thise work". `reports/models/owner-review.md` holds three
  sections (M05, M07, Ask) for the owner's own summaries, with guidance comments only; the agent
  writes nothing under the headings. `release_checks()` turns "Case study per core model (H14
  review)" from pending to pass only when each section has at least 40 words outside comments
  (tested). Also: Data findings page deployed by a manual `daily` run (D199 live), and the ERA5
  backfill reached 20 of 25 reference years (2018-2020 added); 2021-2025 wait for the next daily
  API allowance.

- **D199 — Karnataka data findings page on the site (12 Nov 2026).**
  Owner, in chat: "continue the work", after asking for the data, science and ML work to be shown.
  `?page=findings` ("Data findings", linked in the masthead) presents six analyses: hospital
  access (KPIs, share over 10 km by district, Lorenz curve), rain trends (Sen slope with
  significant districts marked), Bengaluru bus access bands, the M05 drought model (MAE against
  persistence, climatology and the LightGBM challenger, and its five promotion gates), interval
  coverage at every look against the 75-85% gate, and Moran's I of residuals by month. Charts are
  plain SVG with a data table under each (no chart library). The bundle `web/src/findings.json` is
  written by `scripts/findings_product.py` through the Power BI row functions, so the page and the
  report cannot disagree; a test checks it is in sync and holds no rain in mm and no stop, route
  or time. Page text is English only, as on the Accuracy page; only the nav label has locale
  drafts. On phones each chart scrolls inside its frame at 540 px wide, so labels stay readable.

- **D198 — Power BI report expanded to ten pages (12 Nov 2026).**
  Owner, in chat: "make it better more graphs ... a whole good big dashboard". The report now has
  ten pages and 79 visuals: KPI cards on Overview, Hospital access, Bus access, Spatial errors and
  Data quality; a Sen slope against BH q scatter; a district-by-year gauge rain matrix and a
  coefficient-of-variation bar; a Lorenz curve; a 1 km cell scatter of Bengaluru bus access
  (lon, lat, people and share only, as D191 allows); M05 against persistence, climatology and the
  LightGBM challenger (not promoted, D41) with its bootstrap interval, promotion gates and Brier and
  CRPS scores; a Forecast reliability page (calibration by season, every 80% interval look against
  the 75-85% gate, and the D97 rule search); a Spatial errors page (Moran's I by month, variogram);
  and a Data quality page (S08 completeness, S29 gauges per district). Twelve new CSVs are copied
  from committed reports and the M05 registry; tests check them against their sources. No trips
  per hour are shown (D191 allows no times). The 2025 tracker in `climate.json` is the Kerala box,
  so it is left out of this Karnataka report. A sort column orders the bands, gates and interval
  looks; a light theme adds card borders and a grey page. All 93 report JSON files pass the
  published PBIR schemas (checked offline with jsonschema, not committed as a dependency).

- **D197 — Karnataka Power BI report rebuilt around the analyses (12 Nov 2026).**
  Owner, in chat: Power BI Desktop is installed and open; "this is mainly a data project".
  `powerbi/build_pbip.py` now writes seven Karnataka pages: Overview (headline table), Rain trends
  (Sen slope bar, test table, significance slicer), Hospital access (D195), Bus access (D191
  derived bands), Model accuracy (M05), Gauge rain (S29) and Data limits (blocked notes for
  prices, flood labels, M07/M06). The Kerala S32 reservoir page and its table are removed. New
  CSVs (`rain_trend`, `hospital_access`, `bus_access`, `headline`) are copied from committed
  reports; tests check they match and hold no blocked or restricted values.

- **D196 — Rain trends tested: Mann-Kendall, Sen slope, Benjamini-Hochberg (12 Nov 2026).**
  Each annual-rain trend (S08 indices only, 1981-2025) now carries Sen's slope, a tie-corrected
  Mann-Kendall p-value and its lag-1 autocorrelation; the 30 Karnataka districts are corrected
  together with Benjamini-Hochberg. Result: 18 districts have p < 0.05 but only 9 have q < 0.05,
  8 of those flagged as autocorrelated (so weaker than they look). The Kerala cell box is a
  single test. `significance` changes from "not tested" to the corrected result.

- **D195 — Karnataka hospital access equity (12 Nov 2026).**
  Owner, in chat: "choose the best 2 or 3". `src/atlas/analysis/access.py` and notebook 11:
  every S16 WorldPop 2025 1 km cell (203,344, 70.8 M people) to the nearest of 3,581 S18 OSM
  hospitals, exact great-circle nearest site (KD-tree on unit vectors), people-weighted. Median
  3.79 km, mean 4.75 km, 90th percentile 10.5 km, 11.5% beyond 10 km, weighted Gini 0.48;
  Yadgir worst (38% beyond 10 km), Bangalore best (median 0.6 km). Limits: straight-line, OSM
  thinner in rural areas, hospitals of any size, modelled population. 51,869 people fall in cells
  outside the S17 district polygons and are counted statewide only.

- **D194 — Bus-access squares on request (12 Nov 2026).**
  Owner, in chat: "make it as a option so user click a button and only then it shows stuff like
  that". The bus-access map now opens as a plain map; a "Show bus access" button (aria-pressed)
  turns the coloured 1 km squares and their legend on and off, and tapping a square opens a popup
  with its people count and covered share. Tile or glyph errors after the map has loaded no longer
  show "the map could not load".

- **D193 — Feeds schedule without `queue: max` (12 Nov 2026).**
  No scheduled run of any workflow fired between the first merge to `main` (10:45 UTC) and 14:48
  UTC, while manual dispatches of the same files passed. The one unusual key is
  `concurrency.queue: max` (D182). It is removed: a feeds run takes about a minute every 15
  minutes, so GitHub's single pending slot is rarely replaced; if a pending run is ever cancelled,
  the chain needs one manual bootstrap and the Worker's D1 admission still sets the real cadence.
  If schedules still do not fire, the fallback is an external trigger (needs an owner token).

- **D192 — District monsoon tracker from ERA5 (12 Nov 2026).**
  Owner, in chat: "ok do all that" (warning archive, monsoon tracker, transit map).
  `atlas.analysis.district_monsoon` uses S02 ERA5 daily rain at the 30 S17 district points: for
  the southwest (1 Jun to 30 Sep) and northeast (1 Oct to 31 Dec) seasons it compares rain to the
  latest weekly checkpoint with the same window in 2001-2025 (percent of median, rank), with plain
  bands (not IMD categories); a missing day is never filled; two districts in one ERA5 cell are
  mapped by request position, never by cell ID. History is fetched once, one year per request for
  all points, within Open-Meteo's free limits (about 480 weighted calls a year; two batches today,
  the rest tomorrow); derived normals are committed as `configs/static/ka/monsoon-normals.json`
  (CC BY 4.0, ERA5 mm are not IMD data), so the daily job fetches only the current season.
  `?page=monsoon` ("Monsoon tracker") lists districts driest first, labelled reanalysis, about
  6 days behind, one grid point per district.

- **D191 — Public Bengaluru bus-access page from derived T041 shares (12 Nov 2026).**
  Owner, in chat (question on S30's restricted licence): "Yes, derived numbers only". `?page=transit`
  ("Bus access") maps the 2,450 WorldPop cells of Bangalore district coloured by the share of
  people within a 500 m walk of a BMTC stop with scheduled service (4 bands), with the 65.3% of
  8.27 million headline, the service date, the T041 limits and credits. The bundle
  `web/src/transit-coverage.json` is generated by `python -m atlas.analysis.coverage` from the
  committed `reports/eda/04_bmtc_coverage/` files and holds only lon, lat, population and share
  per cell; a test checks it equals the report and contains no stop, route, trip or time.
  The S30 transit layer itself (stops, scheduled positions) stays unmounted (D116).

- **D190 — Gate waivers and daily automatic deploy (12 Nov 2026).**
  Owner answers, in chat: waive C1 and priced data for the Karnataka gate; add the Cloudflare
  secrets so the site redeploys daily; publish derived transit numbers only (D191). The gate
  records C1 and priced data as "waived" (not passed) and treats waived and C3's research-only
  (counted by the owner, D166) as non-blocking; the only open check is the H14 case-study review.
  GitHub Actions secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` and
  `CLOUDFLARE_D1_DATABASE_ID` were set with `gh` from `.env` over stdin. `daily.yml` now builds
  the approved release with the warning archive, archives it privately (read-back) before
  deploying, refreshes Ask (index, public files, D1 chunks) and deploys to Pages.

- **D189 — Google Maps links and the Karnataka warning archive (12 Nov 2026).**
  Owner, in chat: "ok do all that, and instead of open street map link is not good to give
  google map link". (1) Each Nearby facility now has "Open in Google Maps" (a Maps search URL by
  coordinates: no key, no tracking parameters) as its main link; the "Source: © OpenStreetMap
  contributors" link stays, because ODbL requires attribution of the facility data. (2)
  `atlas.alerts.archive` reads every stored S09 snapshot through the signed Worker export and
  keeps each official CAP warning once, as issued, with first- and last-seen times; publish
  writes `data/ka/alerts/archive.json` into each site release (`--alerts`), and `?page=warnings`
  ("Warning archive" in the header) lists them newest first with district/text search and a
  severity filter. The Sachet feed keeps no history, so the archive starts at the first stored
  snapshot (12 Nov 2026) and is empty until a Karnataka warning is issued. The alerts privacy
  guard now lists `archive.py`; it stores nothing about readers. kn, ml and hi strings for the
  page are unreviewed drafts like the rest.

- **D188 — Nearby keeps every facility kind and shows them on the map (12 Nov 2026).**
  Owner, in chat: "when i click nearby i do see anythinf on the map why is it only showing
  hospitals only". Cause: Nearby took the 10 nearest of any kind, and around central Bengaluru
  those are all hospitals; the map drew records only, never facilities. Now Nearby keeps up to
  4 of each kind (hospital, police, fire station) within 25 km, nearest first, and while the
  Nearby tab is open the map shows them as lettered pins (H, P, F with distinct colours and an
  accessible label) and fits them in view. Bangalore now lists 4 + 4 + 4, from 0.8 to 4.4 km.

- **D187 — Public Karnataka release on pages.dev (12 Nov 2026).**
  Owner, in chat: "Approve public release" (H11 public-release approval for Karnataka). Licence
  check at deployment: the site bundles `dashboards.json`, `climate.json` (S08 derived outputs
  only; no rainfall values, per H11 item 3) and the i18n strings; the release carries S01
  (CC BY 4.0, non-commercial), S09 (public domain), S17 and S18 (ODbL, credited) only; the S30
  transit layer (restricted) and S12/S20 layers are not mounted. Per H11 item 2 the Ask document
  set was frozen and its report regenerated once before release: 31 documents, 521 chunks,
  correctness 0.82, evidence support 0.77 against 0.95, so Ask stays research-only; its release
  `bd058915` was loaded into D1 and published with the site. Approved Karnataka release
  `bb00a60b` (pointer `approval: approved`). Pages project `monsoon-atlas` created and deployed
  (`https://monsoon-atlas.pages.dev`) with two Pages Functions that forward `/api/v1/current` and
  `/api/v1/ask` to the Worker, because the browser calls its own origin. Checked live: approved
  snapshot loads, 30 districts, Nearby lists real hospitals with the not-walking-distance and
  opening-hours notice, boundary disclaimer shown, no console errors. The live-update line
  reads "unavailable" until a feed snapshot newer than the release arrives (T240 rule).
  `scripts/deploy_site.py` repeats the deploy from `.env`; Kerala and Delhi stay "not released".

- **D186 — T045 on main; first hosted feeds hop and daily release (12 Nov 2026).**
  Owner, in chat: "Merge PR 2" and "Merge PR 3". PRs Joepikka/monsoon-atlas#6 (T044) and
  Joepikka/monsoon-atlas#7 (T045) merged (`a1bf81a`, `0ec34af`). Manual runs on `main`: feeds
  run 43229709170 selected the bootstrap run as its predecessor, imported its checkpoint,
  stored a new S09 snapshot (S01 `not_due`) and offered a 546,710-byte checkpoint; daily run
  43229714892 built release `0434e32c` (approval pending) and archived it privately. No
  scheduled feeds run had fired by 13:39 UTC, about three hours after the workflow reached
  `main`; manual dispatch works and continues the chain. Watch `gh run list --workflow
  feeds.yml --event schedule`.

- **D185 — T045 static releases, project API and replay; no public deploy (12 Nov 2026).**
  Owner, in chat: "continue the work and tell me when 1 state is done". `atlas.publish` builds a
  Karnataka release from the Worker's verified S09/S01 snapshots (wire digests checked), 30 S17
  district places and 433 S18 facilities, as canonical JSON named by its SHA-256 (140,690 bytes,
  under the browser's 1 MiB limit). Pointers `data/ka/latest.json` and `api/v1/current.json`
  carry `approval: pending`, which the browser refuses, until the owner approves public release
  (H11). `api/v1/snapshots/<id>.json` copies the release; `atlas.replay` reopens a release by ID,
  checks its hash and refuses anything fetched after the cutoff. A failed or empty hot fetch
  raises before any pointer is written. Deviations: (1) the API description is
  `docs/api/openapi.json`, copied into each release, because `web/public` holds no data (D162);
  (2) CI has no raw files, so derived inputs are committed in `configs/static/ka/` (S17 district
  points and S18 facilities, both ODbL, credited); (3) `daily.yml` (02:17 UTC) builds the release
  and archives it to the private Hugging Face dataset with read-back, and does **not** deploy:
  Pages waits for H11 and the T046 gate; (4) no live model predictions are published (M05 stays
  off public pages, H11), so "score only matured predictions" has nothing to score yet. A
  Python-built release passes the browser's own `parseSnapshot` (vitest) and its Place Lens finds
  the facilities. F025 and F053 move to built-not-mounted (owner H11); the gate check for T045
  and T041 now passes.

- **D184 — T044 verified daily archive, without purge (12 Nov 2026).**
  Owner, in chat: "continue" (after the agent proposed T044). The Worker gains a signed, read-only
  `POST /internal/export` (cursor pages, exact stored gzip bytes, capacity figures).
  `atlas.data.hot_export` checks that every payload gunzips to bytes whose SHA-256 equals the row
  ID and stored digest, writes one immutable zstd Parquet per source per run (named by its
  SHA-256), commits the files and `hot/manifest.json` (cursor, file hashes, snapshot IDs, licence
  notes, capacity history and days-to-cap forecast) in one commit to the owner's private Hugging
  Face dataset, then downloads each file at that commit and checks its hash. `archive.yml` runs
  daily at 02:47 UTC; it masks the repository name, because Actions logs are public, and the CLI
  prints only its own error text. `huggingface-hub` 2.4.0 (plan section 5 pin) comes from a new
  hash-locked `requirements/archive.txt` (constrained to core; no torch). First real run: 3
  snapshots (2 S09, 1 S01) archived and read back. **Purge is not built.** The Worker's cap guard
  takes the larger of reserved bytes and D1's file size, and SQLite does not shrink the file
  after deletes, so deleting rows would not restore headroom without a guard change. The
  manifest's forecast shows when the 400 MB cap nears; at the cap, writes stop and nothing is
  lost (T229). A purge with a matching guard change is a separate decision.

- **D183 — PR 5 merged to main; hosted feeds started (12 Nov 2026).**
  Owner, in chat: "Merge and start it". Before merging, only `feeds.yml` had a schedule; `ci.yml`,
  `web.yml` and `worker.yml` run on push or pull request, `monitor.yml` and `tiles.yml` only by
  hand. PR Joepikka/monsoon-atlas#5 was marked ready and merged at 10:45 UTC (merge commit
  `fae8260`). Bootstrap dispatch run 43203183286 passed in 1 min 8 s: bootstrapped an empty
  chain, S09 captured and stored on the Worker, S01 `not_due` (the 09:27 UTC check from this PC
  used the six-hour slot), checkpoint 292,744 bytes offered for the next run. No scheduled run
  had started by 11:33 UTC; GitHub registers a new workflow's schedule with delay. The public
  website stays off until the T046 gate and release approval.

- **D182 — T043 hosted capture and upload to the Worker (12 Nov 2026).**
  Owner, in chat: "Build T043". `atlas.ingest.upload.signing_key` now also trusts the hosted
  origin, but only when it equals `ATLAS_HOT_ORIGIN` exactly and is an https workers.dev origin
  with no path (tested against lookalike hosts, paths and http). Uploads send a fixed user agent
  (Cloudflare's bot filter returned error 1010 to Python's default). `runner_cycle` gains
  `--deadline-seconds` (30 to 150). `feeds.yml` runs at minutes 7, 22, 37 and 52 (plan T043)
  with `queue: max` (GitHub docs: up to 100 pending runs, none cancelled), which settles the D86
  concern; it runs one S09 and one S01 cycle (60 s and 45 s), each continuing on error so a
  provider outage keeps the chain, and the secret reaches only those two steps. Deviation: the
  job limit is 6 minutes, not the plan's 3, because install and relay time are not yet measured.
  Live check from this PC on a fresh chain: S09 admitted, 19 CAP documents validated (11 failed,
  79 pending), 0 current Karnataka warnings, stored; S01 captured and stored; the public current
  API returned both, labelled partial, 2 and 36 seconds old. Activation needs the workflow on
  `main` (GitHub schedules run only from the default branch) and a manual bootstrap dispatch.

- **D181 — GitHub Actions secrets for hosted feeds and the archive (12 Nov 2026).**
  Owner, in chat: "Yes, add secrets". Set with `gh` from `.env` over stdin (no value printed or
  typed into a web form): secrets `ATLAS_INGEST_HMAC_KEY` and `HF_TOKEN`; repository variables
  `ATLAS_HOT_ORIGIN` (the Worker origin) and `HF_ARCHIVE_REPO` (variables are visible to
  collaborators, not the public). No workflow reads them yet: `feeds.yml` is manual-only and
  `atlas.ingest.upload` still accepts only a loopback origin, so hosted capture and upload to the
  Worker remain T043 work, and the archive export is T044. The Cloudflare token stays local only.

- **D180 — T042 cloud step: Worker and D1 deployed, empty (12 Nov 2026).**
  Owner, in chat: "Start hosting"; the owner confirmed the Cloudflare free plan with no card
  (the token cannot read billing, by design) and chose the workers.dev subdomain
  `monsoon-atlas`, which keeps the owner's name out of public URLs. Read-only probe: account
  standard, no Worker, D1 or Pages project before. Created: subdomain, D1 `monsoon-atlas-hot`
  with the committed schema (tables, caps and triggers), and Worker `monsoon-atlas-hot`; a
  random 64-hex `ATLAS_INGEST_HMAC_KEY` (agent-generated project secret) is in `.env` and is the
  Worker secret. The committed `wrangler.toml` stays disabled; `scripts/deploy_worker.py` writes
  the git-ignored deploy config from `.env`. Live checks: current KA 503 unavailable with the
  static fallback, unknown state 400, unsigned or wrongly signed upload 401. Nothing is uploaded:
  scheduled feeds need GitHub Actions secrets (T043) and the public site waits for the T046 gate
  and the owner's release approval.

- **D179 — H06: private Hugging Face archive repository and a scoped token (12 Nov 2026).**
  The owner created a **private** dataset repository for the T045 archive (private until H11
  approves any public subset) and a fine-grained token limited to that repository: read and
  write contents, no user-wide or other scopes. Read-only check (`/api/whoami-v2`): role
  fineGrained, no global scopes, one scoped repository; the repository reports `private: true`.
  The token is `HF_TOKEN` and the repository id `HF_ARCHIVE_REPO` in `.env`; neither is committed,
  so the owner's account name stays out of the public repository. Nothing was uploaded.

- **D178 — Owner skips the S23 publisher email (12 Nov 2026).**
  Owner, in chat: "lets skip email i do not think any one is going to respnd". The data.gov.in
  CDO request for the price denominator is not sent. S23 stays blocked (D58, D173), and with it
  F021, F033 and F061 and the priced-data item of the T046 checklist. Retry stays as recorded in
  `configs/sources/s23.yaml`; the agent does not guess the unit.

- **D177 — T041 BMTC population coverage study (12 Nov 2026).**
  Built now that S18 is available (D174). `src/atlas/analysis/coverage.py` measures 500 m
  catchments along the S18 OSM walking network (motorways and `foot=no` excluded; ways split at
  shared nodes) from every BMTC stop with service on Wednesday 9 Sep 2026 in the S30 Vonter GTFS
  (commit ee945dc), snapped to the nearest walkable node within 100 m (the snap distance counts).
  Population is S16 WorldPop 2025 1 km cells inside the S17 Bangalore district: a cell is covered
  in proportion to its covered walkable length, so overlaps never add people twice and covered
  plus uncovered equals the total. Result: 5,402,563 of 8,268,006 people (65.3%) are within a
  500 m walk; 6,987 of 6,998 served stops snapped (median 7 m); 18,103 of 30,895 walkable km are
  covered; 57,836 trips with the 08:00 hour busiest. Notebook `notebooks/04_bmtc_coverage.ipynb`
  re-runs byte for byte (the road extraction is cached in `data/clean/S18/` by input SHA256).
  Limits are listed in `summary.json`: unofficial scheduled feed, unknown OSM completeness,
  modelled population, district-only stops, access only. WorldPop counts in Bengaluru are known to
  run low (owner label item at H11), so the share, not the head count, is the headline.

- **D176 — S25 FIRMS available with the owner's MAP_KEY (12 Nov 2026).**
  The owner saved `NASA_FIRMS_MAP_KEY` (H09); its status service showed 5,000 transactions per
  10 minutes. The FIRMS API puts the key in the URL path, which the frozen `Fetcher` cannot hide
  (it adds secrets as query parameters), so `src/atlas/ingest/s25.py` adds `KeyPathFetcher`, a
  subclass that substitutes the key into the outgoing request only and refuses a redirect;
  recorded URLs, raw files, the ledger and manifests keep the literal segment `MAP_KEY` (tested;
  `http.py` is unchanged). T075 retry: area page (e06), data availability page (e07) and CSV
  (e08, NRT 2026-08-01 to 2026-11-12), and a Karnataka area CSV (e09): 113 VIIRS NOAA-20
  detections, 0 duplicates, confidence 101 nominal, 8 low, 4 high. S25 is enabled; the adapter
  keeps detections inside the state polygon, maps l/n/h to low/nominal/high, and stores per-row
  latency. Rows are `provenance=model`. The fire context layer is now available but stays
  built-not-mounted until a public snapshot carries detections (T045, H11). The committed test
  fixture is that real CSV (NASA open data; credit FIRMS, LANCE and ESDIS).

- **D175 — S18 facilities exported for the Nearby tab (12 Nov 2026).**
  `src/atlas/ingest/s18_prepare.py` turns S18 rows into the browser's Facility shape:
  hospitals, police and fire stations only, the nearest 10 of each kind within 25 km of
  each S17 district representative point, so a release stays far below the 1 MB snapshot
  limit. OSM `amenity=shelter` is left out because it mostly marks bus and rain shelters;
  official shelters remain S43 (blocked). Unnamed objects say "Unnamed hospital
  (OpenStreetMap)"; each row links to its OSM object and carries `source_checked` (T021
  passed on this extract). Facility rows gain a required `kind` field, which the browser
  validates and Nearby shows. The export is written under `data/prepared/S18/` (untracked);
  nothing is published: facilities reach users only when T045 builds an approved release
  (H06, H11), so F025 stays blocked on that, not on S18. Tests use the real Bengaluru cut
  (6 facilities) in Python, vitest and Playwright. Real Karnataka run: 433 facilities (297
  hospitals, 110 police, 26 fire stations; 21 unnamed), 146,688 bytes, near 30 districts (S17 has no Vijayanagara).
  `data/prepared/` is now git-ignored.

- **D174 — S18 available through the owner's browser download (12 Nov 2026).**
  Retry condition 1 of T021 is met: the owner downloaded the published dated Southern Zone file
  `southern-zone-261111.osm.pbf` (559,594,968 bytes, replication timestamp
  2026-11-11T21:22:47Z) in a browser into `data/raw/S18` (evidence e05; stored under its
  SHA256). D34 still holds: `fetch` downloads nothing and raises `SourceUnavailable`; the
  adapter reads the owner file through `owner_file`, and monthly updates repeat the owner step.
  The T021 rule passed on e05 (0 duplicate type/id, 0 missing versions, 0 invalid geometries
  over 3,779,956 amenity/highway/emergency objects), so S18 is `available` and enabled for
  Karnataka. Rows are `provenance=inferred` (volunteer-mapped, like S10, D108), ODbL 1.0, and
  carry no shelter opening status. The committed test fixture
  `tests/fixtures/s18_southern_zone_bengaluru_261111.osm.pbf` is a small real cut of e05 (ODbL,
  credit OpenStreetMap contributors). The file also covers Kerala; Kerala use waits (D173).
  M15 stays blocked: its S18 input is Delhi impervious cover, which this zone does not hold.

- **D173 — Karnataka first; S22 and S23 price retries stay blocked (11 Nov 2026).**
  Owner, in chat: "is it wise to do just one state for now and do rest some other time"; the
  agent recommended Karnataka first, as A8 already orders, and the owner did not object. Kerala and
  Delhi work waits until the Karnataka MVP gate (T046) passes; the S24 (Delhi AQI) retry and the
  `sgp4` lock (S12 display still waits on its terms) are set aside. S22 retry: the in-app browser
  renders https://indiadataportal.com/p/agmarknet, which now shows the portal's not-found page
  ("doorway to the great nothing"); no new address was found, so S22 stays blocked. S23 retry:
  the data.gov.in resource page and its catalogue and API tabs now render, and its swagger file
  (`backend/dataapi/v1/swagger/9ef84268-...`) loads, but none states the unit of min_price,
  max_price or modal_price; the Agmarknet 2.0 dashboard needs a captcha, which the agent does not
  solve. S23 stays blocked (D58). Owner route: ask the dataset's Chief Data Officer (named on the
  resource page) for the price unit, or note the unit Agmarknet shows after a manual search.
  Source records are unchanged.

- **D172 — Climate, wall, terrain, globe and place watches mounted (11 Nov 2026).**
  After H11 (D166, D167) `?page=climate` is mounted: its data, bundled as `web/src/climate.json` (like `dashboards.json`; `web/public/` holds no data, D162)
  (a vitest checks it is byte-identical to `reports/eda/08_climate_product/climate.json`; refresh
  the copy when the export changes), holds percent of median, percentile, rank and percent per
  decade only, no S08 value in mm; the only "mm" is the inferred-onset rule text "at least 2.5 mm".
  `?page=wall` is mounted with `wallConnected(status, online)`: online and the last snapshot load
  did not fail; the page reloads every 5 minutes and a failed reload shows the last snapshot as
  disconnected with alerts hidden (D154 unchanged). Terrain and globe are an opt-in "Map view"
  select, Flat 2D by default; `chooseView()` fallbacks and reduced motion still apply. No snapshot
  carries a dated S13 row, so imagery reports none (no date is guessed; F009 is a judgement call).
  Place watches sit in the record panel (IndexedDB only); signals are official alerts and mm
  forecasts that name a place; only expiry stops a signal, because records carry no cancelled flag.
  Strings moved to 60 keys per locale (kn, ml, hi are unreviewed machine drafts). Checked in the
  in-app browser: climate page, view select, wall page, no script errors. The full suite's
  Playwright contracts then found two regressions, both fixed: the toolbar overflowed at 768 px
  (it now wraps below 900 px), and the watches select repeated the place lens label "Place" (now
  "Place to watch").

- **D171 — T221 findings fixed (11 Nov 2026).**
  (1) `docs/releases/ka-v1.md` no longer lists F035 among later tasks; a note says T034 measured
  the M05 intervals, they fail their 80% gate, F035 is research-only, and no task produces SHAP
  values (`shap` stays pinned but unused; adding SHAP would be new scope, not a plan task).
  `final-manifest.json` is regenerated for the new page hash. (2) `EventTicker` strings go
  through `t()` as six `ticker.*` keys; kn, ml and hi values are unreviewed machine drafts (A7).
  (3) D161's title now says the dashboards are reachable locally and in no public snapshot.
  (4) SPI invertibility (open after D167), checked: SPI back to mm needs each district and
  calendar month's gamma fit, which is computed at run time from local S08 files. No tracked file
  holds those parameters, a per-district SPI series or a fitted model file (`git ls-files` finds no
  joblib, pickle, parquet, npy or duckdb; the M05 registry files are summaries under 2.3 kB), so
  committed SPI cannot be inverted to IMD mm. Re-check if a model file or SPI table is ever tracked.

- **D170 — M05 v2: refit with IMD 2025, published as untested; v1 keeps serving (11 Nov 2026, builds D166 item 6).**
  (1) Window: the v1 pipeline unchanged (features, SPI reference 1981-2010, 92-day purge), train
  1981-07-01 to 2025-09-30 (15930 district-months), purged before an untouched test from
  2026-01-01. No tune step: v2 keeps v1's model choice (ridge) and alpha 0.1, chosen on the
  2017-2018 tune (D41); LightGBM is not searched again. A new tune would need a held-out year in
  2019-2025, and each of those was already used (2019 calibration, 2020-2024 test, 2025 monitor),
  so it would use a year twice for selection; keeping v1's choice changes no decision. Scaler,
  climatology and ridge weights are refitted (`atlas.models.m05.refit`, `scripts/m05_v2.py`,
  deterministic); the script stops unless the 1981-2024 rows match v1's dataset hash. Weights are
  in `data/models/m05/v2/` (git-ignored). (2) Status: `models/registry/M05/v2.json`, written once
  with the v1 schema: `research_only`, reason "untested refit", empty baseline scores, null
  candidate scores and improvement (no in-sample number is reported). `decide()`, `approve()` and
  `champion()` are unchanged: `approve()` refuses v2 and `champion()` still returns v1's ridge.
  v1 stays the approved, evaluated release and the source of every accuracy number, and v1 is
  what serves once hosting exists. A page that names v2 says "M05 v2 (refit with IMD 2025) is
  untested and not served; accuracy shown is v1's on 2020-2024 (hindcast)". The owner's answer
  built v2; it approved no serving, so no approval file is written. (3) Retest: the record fixes
  the test as 2026-01-01 to 2027-12-31. One year is 12 monthly blocks, below the 24-block minimum
  of the T103 gate (`m05.evaluate`), so 2026 alone cannot make v2 eligible under the unchanged
  rules; this differs from "evaluated once on 2026". When IMD 2026 is published, v2 gets a
  monitoring check on 2026 against persistence with the paired block bootstrap (as T263 did for
  v1, D98); it is reported only and changes neither status nor weights. With 2027 published, v2
  is scored once on the 24 months against persistence with the T103 gates; the drought spread is
  fixed beforehand from pre-2026 rows. Release files are immutable, so a pass is carried by a new
  release record with those scores, and serving still needs a separate owner approval (D38). The
  card's yearly retraining rule is paused for M05 until that test is scored, so no version trains
  on 2026-2027 first. (4) Intervals: v2 inherits the hidden-interval rule (D42, T262) and is not
  recalibrated on any year. Updated: the M05 report and card (v2 sections; v1 text kept),
  `atlas.models.accuracy` (M05 card reason) and its outputs, the README model index and
  measured-result limits, `docs/releases/final.md` (M05 v2 row) and `final-manifest.json`. All
  `v1*.json` files are byte-unchanged (tested). The case study is unchanged (H14 pending).

- **D169 — The last IMD (S08) rainfall values in mm are removed (11 Nov 2026, follows D167).**
  (1) The per-district-year `ratio` leaves `reports/eda/02_ka_rain/district_year_comparison.csv`
  (it keeps `gauge_mm`, `status` and the district and year), because the published S29 totals
  times that ratio gave exact grid mm. Published instead: the summary statistics already in
  `summary.json` (median, mean, min, max, wetter share) and the new
  `reports/eda/02_ka_rain/district_ratio_summary.csv`, one row per district with years compared,
  counts of years more than 10 percent wetter or drier, and the mean ratio over those years.
  Both come from `notebooks/02_ka_rain.ipynb`. Four yearly ratios are not recoverable from their mean and two counts, so yearly
  grid mm cannot be inverted; Ballari has one compared year, where the mean would be that year's
  ratio, so its row is left out. SQL Q03 (`sql/insights/q03_gauge_grid_disagreement.sql`) reads
  the summary through the `s08_ratio_by_district` view; its table is unchanged, and the Power BI
  files carry no ratio and are unchanged. (2) The single-cell 2024 totals in
  `configs/sources/s08.yaml` and `docs/sources/s08.md` become a plausibility statement without
  values, citing the same evidence e04. Because `s08.yaml` is hashed, the files that record its
  sha256 were regenerated with their own generators: `reports/models/m16-data-gate.json` and
  `models/registry/m16.json` (`atlas.models.m16.write_status`), `docs/releases/final-manifest.json`
  (`tests/test_final.py --manifest`); `atlas.models.accuracy` was re-run and left
  `web/src/dashboards.json` unchanged (it carries no s08.yaml hash).
  `eval/anomalies/blocked.json` is a hand-written record with no generator; its one hash field,
  for `configs/sources/s08.yaml`, was updated by a computed sha256 (a one-off script, nothing
  typed). (3) `docs/HANDOFF.md` T107 gives the median
  grid-to-gauge ratio instead of the bias in mm. D167 no longer repeats the values. Evidence
  content is otherwise unchanged.

- **D168 — The public map hides the basemap's international borders (11 Nov 2026, owner answer in chat: "Hide basemap borders").**
  At `style.load`, `MapView.tsx` calls `hideInternationalBorders` (`web/src/map/Borders.ts`), which
  sets `visibility: none` on every style layer whose `source-layer` is the OpenMapTiles `boundary`
  layer and whose filter can admit `admin_level` 1 or 2 (disputed and maritime variants included).
  Layers are found by source layer and filter, not by id, because the live "liberty" style cannot
  be fetched offline (no network in this task) and its layer ids are unverified. The filter is read
  with a small three-valued evaluator for the legacy and expression syntaxes; a filter it cannot
  evaluate (another operator, a property it does not model) counts as "may draw" and the layer is
  hidden, so an unknown shape errs towards no border. State lines of the basemap
  (`admin_level` 4 and above) stay. Our own geoBoundaries layers have no `source-layer` and are
  never selected; `MapView.tsx` still adds no layer of its own. The OSM and OpenFreeMap
  attribution and the boundary disclaimer (`map.disclaimer`, `e808bbc`) are unchanged. Tested by
  `web/src/map/Borders.test.ts` against a hand-built style fixture marked as a test input (nine
  country-line filter shapes hidden; state lines, a water layer and a source-less layer kept);
  `web/src/map/Layers.test.ts` now allows exactly this border-related code in `MapView.tsx`.
  **Not verified:** the rule has not run against the live style in a browser (offline); that check
  belongs to the first connected run before any deployment. No new dependency.

- **D167 — Tracked EDA outputs carry no IMD (S08) rainfall in mm (11 Nov 2026, owner answer in chat: "Strip mm, keep derived").**
  Rule: absolute S08 rainfall in mm (area averages, differences, extremes, climatologies) is
  removed from every committed file; percent departures, percent of the mean, ratios, shares,
  SPI, counts, ranks and years are kept; charts that plot S08 mm are untracked and listed in
  `.gitignore` by exact path; git history is not rewritten. Changed at the generators, then
  regenerated (outputs byte-identical elsewhere): `notebooks/02_ka_rain.ipynb` (CSV drops `grid_mm`
  and `bias_mm`; summary `bias_mm` becomes `ratio_grid_to_gauge` with median, mean, min, max and
  `grid_wetter_share`; caption in ratio), `notebooks/05_kl_flood2018.ipynb` (summary drops the
  Jun-Sep 2018 and 1981-2010 mm and the CI in mm, keeps `departure_pct`; caption in percent),
  `notebooks/07_climate.ipynb` (summary drops mean, min and max mm, gains driest and wettest year
  and each as a percent of the 1981-2010 mean). Regenerated: `reports/eda/02_ka_rain/
  district_year_comparison.csv` and `summary.json`, `reports/eda/05_kl_flood2018/summary.json`,
  `reports/eda/07_climate/summary.json`. Untracked, kept local: `gauge_vs_grid.png`,
  `bias_by_district.png`, `rain_2018_vs_climatology.png`, `s08_annual_rain.png`. The notebooks
  still write them (and the three files of D166) locally, so the clean-process tests still run
  where `data/raw` exists; `tests/test_replay2018.py` lets those two summary-listed charts be
  absent. Checked and kept: `reports/sql_insights.md` Q01 and Q02 (S29 gauge totals only, no S08),
  `reports/powerbi/data/*.csv` and `powerbi/build_pbip.py` (only S29 `gauge_mm`; the S08 columns
  were already dropped, D132), `reports/eda/07_climate/s06_model_change.csv` (S06 CMIP6 model
  values), `reports/eda/08_climate_product/climate.json` (indices only), all SPI-unit reports. The
  web app imports no S08 mm. **Left open then, closed by D169:** `district_year_comparison.csv`
  kept a per-district-year grid-to-gauge `ratio` beside S29 `gauge_mm`; the single-cell example totals in
  `configs/sources/s08.yaml` and `docs/sources/s08.md`; one S08 bias figure in
  `docs/HANDOFF.md`. Old copies stay in git history.

- **D166 — Owner answers to the H11 Karnataka release review (11 Nov 2026, owner answer in chat).**
  The owner answered the sheet `docs/releases/h11-ka.md` and three extra pre-deployment checks.
  (1) Publish the model accuracy table (M07, M05, M06): **approve**. (2) Count a research-only Ask
  (C3) for the MVP gate: **(a) yes**, publish Ask labelled research-only (D101); before any release,
  freeze Ask's document set and regenerate its report once. (3) IMD rainfall (S08) only through
  derived outputs: **(a)** derived outputs only, citing Pai et al. (2014); never rainfall values.
  (4) Attribution for the open sources: **approve**, on condition the project stays
  non-commercial. (5) Official alerts, model outputs and inferred items stay separate ("not an
  emergency service"): **approve**. (6) Refit M05 now that IMD 2025 is published: **(b)** refit now
  and label v2 untested (no unused year remains to test it); a later agent builds M05 v2, and this
  entry only records the decision. (7) OpenFreeMap terms (S15): the owner **confirms they are 18 or
  older**. (8) India mapping: **add a disclaimer**; geoBoundaries stays the analysis source, every
  public map carries a boundary disclaimer, and no international border is drawn. (9) The three
  committed files holding IMD area-averaged rainfall in mm for the 2018 Kerala replay
  (`reports/eda/05_kl_flood2018/replay2018.json`, `monthly_2018.csv`, `s08_kerala_annual.csv`) are
  **removed from the repository** (untracked, kept local; the replay keeps derived departures only);
  old copies stay in git history and history is not rewritten. **Conditions that now bind:**
  non-commercial use only; S08-derived outputs only, Pai et al. (2014) cited; Ask research-only; M05
  v2, when built, is labelled untested. **What this does not change:** nothing is deployed or
  published (H05 and H06 are unanswered, T045 and T041 stay open), no feature becomes
  `shipped-local` by this alone (D165 rule: reachable locally with a tracked test), and C1 stays
  blocked (D104), so `docs/releases/ka.md` still says "not releasable". Applied in the three
  `H11:` commits: this record and page updates, the untracked S08 files, and the boundary
  disclaimer on the map (`map.disclaimer`). Frozen interface files (D122) are untouched; the dated
  gate page `ka-v1.md` still lists the H11 items as owner-gated because it is a 9 Nov record.

- **D165 — Final acceptance: tasks walked, product not released (11 Nov 2026, T221).**
  Result line in `docs/releases/final.md`: the plan's tasks T001 to T221 are walked as executed;
  the product is not released; 12 of 64 plan features are `shipped-local`, 20 built but not
  mounted, 4 research-only, 27 blocked and 1 deferred (F051, web push, by policy). Of the 12 MVP
  features 9 run locally and 3 are blocked (F021, F025, F033). The feature list, names and tiers
  come from the plan's section 8 catalogue; `docs/releases/final-features.json` is the source of
  truth and `tests/test_final.py` checks the page row by row (D150 noted that no catalogue file
  existed; this one is copied from the plan, not invented). Classification rule: `shipped-local`
  only when the code is reachable in the local app (`App.tsx` or a `?page=` route) or runs as a
  local pipeline command, and a tracked test exercises it; anything else is not shipped. Rows that
  needed judgement say so in their notes (for example F030: M05 is approved, but no outlook layer
  exists, so it is `built-not-mounted`; F054, F055 and F059 count as `shipped-local` because
  `main.tsx` routes them, though D161's title says "not mounted"). No approved snapshot exists, so
  the local map shows its empty state; its tests use committed real fixtures. **Manual checks not
  performed:** keyboard, NVDA, zoom, the manual accessibility checklist, network smoke tests and
  Worker resource measurement are listed as "not performed: owner step"; none is marked as done.
  The "20 sections" in the acceptance line are the plan's own numbered sections 1 to 20 (its
  summary promises "20 ordered sections"; the table of contents ends at Appendix B), each mapped to
  tracked files. `docs/releases/final-manifest.json` pins SHA-256 hashes of the registry, gate
  pages, dashboard data, source records, state configs and lock files; regenerate it with
  `python tests/test_final.py --manifest`. **Next task:** re-run T146 (S24), which needs only a
  browser tool that can read the data.gov.in page and network access, no owner step; first owner
  step: H11 (named by 30 of 64 feature rows), then H05 for the hosting chain T042 to T045. T046
  stays the first unfinished task in plan order. Three findings are recorded in the page and not
  fixed (ka-v1.md F035 task wording, HANDOFF's EventTicker mounting note, D161's title).

- **D164 — Portfolio and interview evidence pack (11 Nov 2026, T220).**
  `README.md` is restructured to the plan's section 17 outline only as far as the evidence allows:
  status first (1 measured, 1 research-only, 18 blocked; 44 source records), then the one measured
  M05 result, a model index and a licence table copied from `web/src/dashboards.json` and
  `configs/sources/`, a Mermaid architecture diagram, failed-model lessons, reproduction commands
  and owner-pending steps. `docs/case-studies/template.md`, `docs/portfolio/video.md`,
  `docs/portfolio/resume.md` and `docs/glossary.md` are new. **Demo not recorded:** the video page
  is a script and shot list marked "not recorded: owner step", and each shot says whether it can be
  shown on the local dev server today (yes, partly, no) and why; no narration claims a hidden,
  blocked or unmounted item is shown. I did not run the dev server, so the "partly" rows are
  unchecked. **Resume:** the four plan lines stay as bracket placeholders (`[N]`, `[X]%`,
  `[metric]`, `[baseline]`, `[L,U]`, `[dates / independent events]`, `[coverage]%`, `[latency]`)
  under "Not usable until measured", each with the reason; four usable lines carry only counts
  and numbers recomputed by `tests/test_portfolio.py` (sources, models by status, M05 MAE and
  bootstrap CI, M16 cell-day counts, the 8 and 11 Nov Ask scores, corpus size). Time split only:
  the usable data-science line says no spatial holdout was run. **Not included, on purpose:** a
  tasks-completed or tests-passing count (not computable from a record and dated at once), badges,
  screenshots, a demo or hosting link, any accuracy number for a model other than M05, interval
  coverage as a result (it does not pass), the 2025 interval coverage, external links (none are
  fetched), and any edit to the three existing case studies (H14 is the owner's rewrite), the gate
  pages or a hash-frozen file. `tests/test_portfolio.py` is the guard: relative links resolve to
  tracked files, every model is indexed with its registry status and reason, counts and M05
  numbers are recomputed, and a scan rejects deployed, live or demo claims without a negation, a
  metric on any model but M05, interval coverage shown as passing, and a KW Live mention outside
  the no-reuse sentence. **Ask corpus:** `configs/rag.yaml` indexes `README.md` as
  `project/readme` and this log as `project/decisions`, so this commit changes the corpus. The
  README keeps the sentences the fixed questions rely on (Karnataka then Kerala then Delhi; free;
  not an emergency service). `reports/rag.md` is not regenerated, so its committed numbers stay
  the 8 Nov measurement (D147); a re-run after the commit is reported in the task hand-back, not
  written here, because writing it here would change the corpus again.

- **D163 — Monitoring checks, owner-run workflow and rollback drill (11 Nov 2026, T219).**
  `atlas.monitoring` holds pure checks that return an `Alert` (kind, subject, evidence, action) and
  write nothing private. Feed age uses the cadence the source record states (`schedule`, parsed
  only when it starts with "every N minutes or hours", hourly, daily, weekly or monthly; a one-off,
  yearly or on-demand schedule has no recurring cadence, so no age alert). Two numbers are mine, not
  the plan's, and are owner-tunable constants: a feed is stale after **two** stated cadences without
  a success (`STALE_FACTOR`), and missingness alerts above **10%** (`MISSING_LIMIT`); the plan
  states no limit for either. An empty expectation (undefined denominator) is an alert with a null
  fraction, never 0. Schema change reports added, removed and retyped fields. PSI uses fixed
  interior-quantile bins from the training window and asks for more than 0.2 in the latest two
  windows; residual MAE is the mean over the latest 14 labelled days against 1.2 times the frozen
  baseline MAE (fewer than 14 days is not assessable, so no alert). The M05 frozen baseline is read
  from `models/registry/M05/v1.json` (persistence MAE 0.808, limit 0.970); the 2025 monitor MAE of
  0.625 passes, shown as a 12-month hindcast monitor and not as the 14-day rule. A stale feed marks
  every model that reads it "stopped", from `configs/models/*.yaml` (M16 counts only the sources it
  uses; M05 reads `rain_source`). Storage reuses the D24 code (`budget.check`, 80% warn, 95%
  archive-only) and a service over its daily cap alerts; no second quota logic. `deliver` appends to
  an owner-run JSONL log and is the only destination; the module imports no network or messaging
  library. Rollback: `rollback_if_corrupt` verifies the current release against its manifest, checks
  the prior release too, then calls `ManifestStore.rollback`, so only `latest.json` moves; the test
  corrupts a published release's file and proves the prediction ledger, the report and every
  manifest keep their hashes. A corrected label is a new ledger revision (`append_correction`)
  and a re-score is a new `name.rN.json` (`write_report_revision`); old lines and reports are kept.
  The ledger and report files in the drill are test inputs: no prediction ledger exists in the
  repository yet, since no model serves live predictions. `.github/workflows/monitor.yml` is
  `workflow_dispatch` only with read-only permissions, SHA-pinned actions copied from `ci.yml`,
  no secrets and no notification step; it runs `python -m atlas.monitoring` on the committed state
  and tees the table into the job summary. In a clean checkout the feed, PSI and storage rows read
  "unavailable" because there is no feed log, no live prediction and no `data/`. It has not been
  dispatched. `docs/runbooks/rollback.md` gives the commands and the test runs the same calls.

- **D162 — Offline plan, widget and export controls built; no service worker registered (11 Nov 2026, T218).**
  Registration is deferred until H11 (retry: the owner approves a public snapshot and a host, H05,
  H06, H11; then register from `main.tsx` with `planCache` and add the offline Playwright spec). There
  is no public host and no approved snapshot, and a registered worker that cached an unapproved
  shell is hard to undo on a user's device. Built and tested instead: `web/public/manifest.webmanifest`
  (name Monsoon Atlas, relative start URL, no icons because none exist and none is borrowed from
  another project, so browsers may not offer install yet) linked from `index.html`; `sw.ts`, an
  unregistered module with a pure `planCache` (explicit allowlist of shell files plus an empty list
  of permitted state summaries, a hard 20 MB budget, every entry stamped with its fetch time),
  `stamp` (adds `x-atlas-cached-at` to a response) and `offlineBanner(cachedAt, now)`, which always
  names the cache date and says risk in it is not current and that this is not an emergency service
  with nothing running in the background; a missing, invalid or future date reads "unknown date".
  A test greps that nothing calls `serviceWorker.` or `.register(`. `web/tests/offline.spec.ts` is
  not written: with no worker an offline reload has nothing to test, and a mock would only
  pretend. `Widget.tsx` (`?page=widget&state=ka`) is a read-only catalogue summary with source links
  that open in a new tab: no form, button, script or iframe, no `postMessage`, no read of the parent
  or referrer. Framing: no place defines response headers for the web shell (the Worker serves the
  API only), so nothing is added. Deploy-time requirement: serve the app with
  `frame-ancestors 'self'` (`APP_FRAME_ANCESTORS`) and give the widget its own path with
  `frameAncestors(WIDGET_ORIGINS)`; headers cannot match a query string, so the widget needs a path of
  its own (for example a second HTML entry) before anyone can embed it. `WIDGET_ORIGINS` is empty,
  since no partner exists, and `frameAncestors` accepts only exact https origins. Exports:
  `atlas.export.export_manifest` and `web/src/export.ts` allow a source only when its discovery
  record is available and open, through `require_open_source`, which `require_tile_source` (T185) now
  calls too, so there is one licence rule. S08, S30 and S34 are refused and S02 passes on its
  committed Open-Meteo fixture. The manifest carries source ID, licence, row count, a content hash
  and a hash per shard; a shard holds at most 10,000 rows and 10 MiB. No export button is mounted. The Kerala and Delhi gate tests that forbid tracked files under
  `web/public/` now allow exactly `web/public/manifest.webmanifest`, which holds no data.
  Strings go through `t()` in four locales (kn, ml, hi are unreviewed machine drafts, A7).

- **D161 — Four dashboards built on one generated data file; reachable locally at `?page=`, in no public snapshot (11 Nov 2026, T217; title reworded D171).**
  `atlas.models.accuracy.dashboard_data()` (beside `accuracy_rows`, no new package) writes
  `web/src/dashboards.json` from files that already exist: per model the registry status and reason;
  scores only where the registry has them (M05: MAE 0.732 against persistence 0.808, improvement
  0.076, 95% CI 0.003 to 0.150, 1800 district-months over 60 months, test 2020 to 2024, label
  "hindcast", D39); a link to each report and, for M05, its model card; the hidden M05 intervals stay
  hidden (D42, T262), and a test checks the data holds no interval or S08 cell field. A test
  regenerates the file and compares bytes, and compares the per-state source counts with the three
  gate pages (ka 23 of 33, kl 4 of 19, dl 0 of 8), so the pages cannot drift. `Accuracy.tsx` keeps its
  release table and gains a model-status section; `Quality.tsx` shows source health from the source
  records, the M16 counts as a review queue labelled "unadjudicated rule output, not incidents" (0 of
  100 flags adjudicated; counts only, no S08 value) in its own section, a "Hazard extremes" section
  that shows none, and the M05 2025 monitor result as drift (PSI and the 14-day labelled MAE ratio
  are "unavailable": no live issue-time predictions exist). `Analysis.tsx` indexes ten committed
  reports with their sources and a licence note, and inlines no S08 rainfall value (the H11 item on
  S08 publication stays open). `Compare.tsx` shows source and model status counts side by side with
  coverage (enabled/total) and no ranking; its pure `comparable(a, b)` rejects a different geography
  level, unit or non-overlapping span and requires a normalisation (per capita, per area or climate
  reference) and a coverage in (0, 1]. Only Karnataka has a metric series (M05), so every metric pair
  reads "unavailable" with its reason. An undefined denominator (`ratio`) renders "Unavailable", never
  0 or NaN. Like Accuracy and Ask, the pages are reachable only by `?page=quality`, `analysis` and
  `compare` (a lookup in `main.tsx` replaced the nested conditional); no public snapshot carries them.
  Strings go through `t()` in four locales (kn, ml, hi are unreviewed machine drafts, A7).
  Placeholders must keep the English order in every locale, so some English sentences are phrased in
  the order the other languages use. Models with state ALL (M16, M20) belong to no state count.

- **D160 — M16 is published as research-only, not blocked (11 Nov 2026, T216).**
  The card allows no quality claim under 100 manual labels. The rule ran on real data (D158) and
  flag counts exist, so the blocked branch (used for M18, which had no data at all) would
  understate what was done. The status is `research_only`, the one the release framework gives
  when a score is missing (D38), with `dataset_sha256`, `split_sha256`, weights, baseline and
  candidate scores and improvement all null, 0 published prediction rows and no champion
  (`champion` finds no release). It is a status file in the M06 to M20 shape, not a `Release`
  (a Release needs baseline scores). The report says "rule implemented; flag counts reported;
  precision not measured (0 of 100 adjudicated)" in those terms and states what the counts do
  not show (75% of Karnataka cell-days have no z; the flag rate on evaluated cell-days is above
  the card's 1 false alert per entity-week if most flags are false). M16 is state ALL; the
  Kerala and Delhi release pages list only M07 to M10 and M12 to M15, so their "no model is
  research-only" sentences stay true and no frozen file changed. T216 also fixed the M16
  notebook line length that the T215 commit left over 100 characters. Retry: see D159.

— The two anomaly adjudication batches are one recorded blocked batch (11 Nov 2026, T212 and T213).**
  The plan gives each batch `eval/anomalies/batch_N.jsonl` and a test, accepted by 50 adjudicated
  real flags each. None can exist: the only flags are the agent's own M16 rule output on S08 (T215),
  and the agent does not adjudicate its own detector's flags as ground truth (the H13 principle:
  AI-only labels cannot judge an AI detector). A sample stratified across feeds is also
  impossible, because S08 is the only feed with flags (S22 and S23 hold zero price rows, S32 has no
  28-day window, S02 and S07 hold no daily history); the S08 licence (D129) forbids rainfall values
  in a committed flag record; and no independent evidence packet exists. Deviation: instead of two
  empty batch files and two tests, which would look like finished batches, one record
  (`eval/anomalies/blocked.json`) and one test (`tests/labels/test_anomaly_blocked.py`) cover both
  tasks: required 50 per batch, 5 second-reviewed per batch, selected 0, adjudicated 0,
  second-reviewed 0, candidate real flags 417,948 (ka) and 152,086 (kl) from the committed count
  table, with the SHA256 of that table and of the S08 record. There is no numbered owner step for
  this review yet; one is proposed (owner adjudication plus a 10% second review). Retry: select 50
  dated real flags per batch stratified by feed, season and strength band, attach independent
  source evidence (S02 ERA5 or S07 NASA POWER for the same place and date), and have the owner
  label each (data error, genuine extreme, normal, unknown). The agent may prepare the evidence
  packet in a later bounded task but does not assign the labels. Because the T214 to T216 chain
  needs the count table, these two tasks were committed after T215 (order T214, T215, T212-T213,
  T216).

- **D158 — M16 rule run on the held S08 daily grids; per-source usability; counts only (11 Nov 2026, T215).**
  Decided from the files: **S08** (IMD 0.25 degree daily rain, 1981-2025, 45 year files, enabled
  for ka and kl) is the only source with a real daily history on this machine. **S02 and S07**
  hold only single-point (Bengaluru) discovery probes, no daily series; **S32** has two sampled
  dates a month, so a trailing 28-day window is undefined (and T114 quarantine applies);
  **S22 and S23** hold zero price rows (blocked); no other enabled source is a held daily or finer
  feed. S08 is licence restricted (D129): no rainfall value, cell or date is committed, only
  `reports/models/m16-flag-counts.json` with flags by state, year, season (IMD) and strength band
  (|z| 4-6, 6-10, above 10) plus per-year coverage (evaluated, missing, too_few_valid, mad_zero,
  bound). The run uses `read_grid` and `state_cells` directly (as M05 does), not the Arrow adapter
  table, the 28 days before each year come from the previous held year, and 1981 starts with no
  history (no earlier day is invented). The ka and kl cell boxes overlap, so shared cells count in
  both. Result: ka 417,948 and kl 152,086 flags (all but 19 are above the window median, none
  breaks the 0 mm bound). Flags are 18.8% of evaluated ka cell-days and 0.33 per entity-week over
  all cell-days (1.32 per evaluated entity-week), above the card's "at most 1 false alert per
  entity-week" if most were false; with no labels this is reported, not judged. Rain is
  zero-heavy and heavy-tailed, and 75% of ka cell-days have no z (mad_zero or too few valid days).
  The table by year includes 2025 (the card's test year) as a count only: nothing is tuned,
  scored or selected on it. `fit` reads no train or tune row; nothing is learned.

- **D157 — M16 rule implemented as pure functions; gaps in the card settled and recorded (11 Nov 2026, T214).**
  `src/atlas/features/m16.py` computes `robust_z = (x - median) / (1.4826 * MAD)` against the 28
  report days strictly before the report; a future row cannot change an earlier flag (mutation
  test). Flag: `abs(z) > 4` or a value outside a stated unit bound. Settled where the card is
  silent: a missing value never becomes 0, never flags and stays out of every window; a value that
  breaks a bound flags as `bound` and stays out of later windows; MAD of exactly 0 gives no z (no
  division by zero, no flag, counted as `mad_zero`, so a 200 mm day after a dry spell is not
  flagged by this rule); fewer than 21 usable days in the window gives no z (21 is an
  implementation choice, not on the card). The only unit bound is S08 rain >= 0 mm, taken from the
  source record ("from 0 upward"; the adapter already rejects negatives, D30); no upper bound is
  stated by any source, so none is invented. Season/hour correction is not applied: the trailing
  window follows the local level and daily data has no hour; season only stratifies reports. The
  feature framework's `build_features` (duckdb, one sub-query per row) does not fit millions of
  cell-days, so the window is a vectorised regular daily grid (shortcut noted in the module). No
  IsolationForest: with 0 adjudicated labels no challenger can be evaluated. Tests use hand-built
  series labelled as test inputs for the rule, not feeds.

- **D156 — M18 is recorded as a blocked branch (11 Nov 2026, T209 to T211).**
  M18 (Malayalam/English news event extraction) needs 1000 permitted annotated texts, at least
  100 per class, across 2 or more publishers and both languages. Actual: 0. S41 is blocked (T125,
  T126): no publisher permission to store or classify items is on record, so there are 0 permitted
  articles and no frozen temporal split. The twenty annotation batches T189 to T208 are recorded
  as blocked (D155) with 0 articles selected, 0 labelled and 0 owner-reviewed, and owner step H13
  (owner review of at least 20% of every batch and every held-out test item) has not happened, so
  no ground truth exists for an AI extractor. M18 stops at the data gate and follows the M12 and
  M19 pattern (config, gate JSON, no-model manifest, status record, report, disabled-state
  tests); its gate hashes the batches record as well as the S41 record and manifest. Blocking IDs:
  S41, H13 and the news batches record. The plan's prospective dates (collect from 2027-10-18,
  locked test 2028-01-31 to 2028-02-14) are recorded as planned only. No embedding model was
  downloaded, no deep-learning package was installed, and the registry holds no baseline,
  candidate, score, weights or prediction. No fallback is published. Retry when permission is on
  record, the batches are labelled and reviewed (H13), and the gate is met.

- **D155 — The twenty news annotation batches are one recorded blocked batch (11 Nov 2026, T189 to T208).**
  The plan gives each batch its own `eval/news/batch_NN.jsonl`, report and test, accepted by
  50 labelled records. None can exist: S41 (permitted news RSS sources) is blocked (T125, T126),
  because every publisher limits RSS use to personal reading and no permission to store a
  headline, link and timestamp is on record, so there are 0 permitted articles and no frozen
  temporal split to select from. Owner step H13 also needs the owner to review at least 20% of
  every batch and every held-out test item, and AI-only labels cannot be the ground truth for an
  AI extractor; no review exists. Deviation: instead of twenty empty batch files, twenty reports
  and twenty tests, which would look like finished batches with zero rows, one record
  (`eval/news/blocked.json`), one page (`reports/labels/news.md`) and one test
  (`tests/labels/test_news_blocked.py`) cover T189 to T208. The record lists the twenty task IDs,
  counts (selected 0, labelled 0, reviewed 0, against 50 per batch and 1000 in total) and the
  SHA256 of the S41 record and manifest, so the test fails loudly if S41 changes. All 1000 records
  are carried into future bounded tasks; none is done. Retry when written publisher permission is
  on record and T125 is re-run, then select from a frozen temporal split, pre-label and obtain the
  H13 review.

- **D154 — Wall mode built, not mounted; nothing stale is styled as current (11 Nov 2026, T188).**
  `web/src/map/WallMode.tsx` shows the snapshot timestamp large, a tile per source (status text plus
  last-success time as `<time>`) and the existing `EventTicker` unchanged: it already has a pause
  button, starts paused under reduced motion and rotates only on a timer, so no second ticker was
  written. The wall's state is `current` only when the feed is connected and the snapshot is at
  most 24 hours old (`STALE_MS`, now exported from `data.ts`, the same limit the app uses; a future
  or unreadable time counts as stale), otherwise `stale` or `disconnected`. A source tile is
  `available` only if the source says so and its last success is within 24 hours, and every tile
  is `disconnected` when the feed is; a stale or disconnected wall keeps its timestamps but shows no
  alerts, because an old alert may have been cancelled. The word "live" appears nowhere. State is
  written as text and by a dashed border, not by colour alone; there is no sound, animation,
  transition or flashing (CSS and component are scanned for these). Escape and a focused exit
  button leave. Strings use `t()`: 17 `wall.*` keys in all four locale files, English reviewed and
  Kannada, Malayalam and Hindi unreviewed machine drafts (D147, D148); `EventTicker`'s own strings
  are still English literals, to be moved before mounting. The 1920 px check is a pure rule
  (`wallColumns`: four columns from 1920 px) plus the server-rendered markup carrying the grid; no
  Playwright step was added because the app does not mount the wall, and so none can be flaky.
  The wall renders as 1920 wide by default where `window` does not exist (server rendering only).
  `connected` is an input; no code yet decides it, because nothing mounts the wall.

- **D153 — Movement overlays built, not mounted; satellite propagation unavailable (11 Nov 2026, T187).**
  `src/atlas/spatial/orbits.py` and `web/src/map/Movement.tsx` draw a layer only when its source is
  enabled, available and licence-open: today only S10 aircraft qualifies. S12 and S20 are licence
  restricted until the H11 review (D109, D110) and S26 ships are blocked on H12; S11 OpenSky is
  blocked, so aircraft has exactly one upstream. The layer status is written to
  `web/tests/fixtures/movement-layers.json` and a Python test keeps it equal. **SGP4 is not in any
  lock and is not installed**, so `propagation_status()` is unavailable with the reason "sgp4 not in
  the lock (add to requirements/geo.in with pip-tools in a follow-up)", `predict()` raises
  `SourceUnavailable`, and no satellite position is drawn; no propagator was written by hand. Kept
  and tested: OMM epoch parsing (CelesTrak serves OMM JSON, so the plan's "TLE epoch" is the OMM
  `EPOCH`, D109), the 7-day element age rule, the "predicted, not observed" label with the element
  date. Not run: the TLE known-example propagation (nothing to propagate with). Follow-up: add
  `sgp4==<version>` to `requirements/geo.in`, compile with pip-tools (D25), write `predict()` over
  the OMM fields and test it against a published example. Aircraft older than 300 s, in the future
  or with no zone are hidden (the adapter already drops LADD and PIA and stores no callsign,
  registration or owner; the web allowlist equals the adapter's columns). `region_key()` snaps a
  centre to 0.5 degrees and the radius up to a 25 nm step, wraps the antimeridian, and serves both
  flights and ships; `PollGate` allows one poll per layer and region per interval (300 s aircraft,
  2 h satellites, 1 h earthquakes) whichever source asks, so a fallback cannot double the upstream
  poll; ships have no recorded interval and raise `SourceUnavailable`. The browser component makes
  no request. Earthquakes show `updated_at` as the revision time and the row's `source_url` (the
  USGS feed address S20 stored; no per-event page address was invented), hide `deleted` events and
  accept https `earthquake.usgs.gov` links only. Strings are English literals; they need keys in
  all four locale files (D148) before mounting.

- **D152 — Terrain and globe built, not mounted; globe works in the pinned MapLibre (11 Nov 2026, T186).**
  `web/src/map/Terrain.tsx` builds the MapLibre `raster-dem` source (Terrarium encoding, the S14
  bucket, zoom 15 as in the adapter) and `setTerrain` with exaggeration 1 by default (a zero,
  negative or non-finite value throws). S13 imagery is added only from a row that carries a valid
  date and an https GIBS tile address; otherwise terrain is shown without imagery and the message
  says S13 reported none (no date is assumed from the clock, and a test forbids `Date.now`).
  `chooseView()` returns the 2D map on low reported memory (`deviceMemory` of 2 GB or less; the
  value is coarse and absent in some browsers, where it is not guessed) and an accessible status
  message pointing to the record list when WebGL is missing or the context is lost. `Globe.tsx`
  uses `setProjection({type: 'globe'})`: maplibre-gl 6.16.0 has it (the build type-checks the
  call against the pinned `Map` through `MapLike`), so no "globe unavailable" state is needed on
  this build, but the state exists for a map without it. Longitudes from a click are wrapped into
  [-180, 180). Camera durations become 0 under reduced motion. No tile is stored for later use and
  nothing is requested outside the S13 and S14 hosts; the S15 basemap and its credit stay in
  `MapView`. Strings are English literals; they need keys in all four locale files (D148) before
  mounting. Not run: PMTiles tile reads against source geometry (no archive, D151). Python
  contract: `tests/test_tiles.py`; behaviour: `Terrain.test.ts`, `Globe.test.ts`.

- **D151 — PMTiles city-layer build: clip, licence gate, shard plan and a manual workflow; no archive (11 Nov 2026, T185).**
  `src/atlas/spatial/tiles.py` holds what runs locally: `clipped_buildings()` wraps the T105
  `buildings_in_place()` (no second clipper) and adds the credit to the collection and to every
  feature; `require_tile_source()` lets a source into a tile build only when its record says
  outcome available, licence open and a credit is registered in `ATTRIBUTION` (only S19, CC BY 4.0,
  so S08, S12, S20, S30 and the blocked S26 are refused, tested); `plan_shards()` packs features in
  order under 20 MiB minus a 1 MiB reserve and `check_shard_sizes()` fails a built file at or over
  20 MiB (source bytes only bound the real size, so the built-file check is the one that counts);
  `delivery()` returns GeoJSON unless a probe saw HTTP 206 and a CORS header for the site. Not
  built: a PMTiles v3 reader, because no archive exists to read (a header parser tested on a
  hand-made header would only confirm itself). `.github/workflows/tiles.yml` is `workflow_dispatch`
  only, read-only, with every action pinned as in `ci.yml`; it builds Tippecanoe from felt/tippecanoe
  and runs the tile tests. **The commit SHA of tag 2.79.0 is not in the repository and was not
  invented**: the workflow takes it as a required input, refuses anything that is not 40 hex
  characters before any checkout, and checks that the tag points at it. Before the first run the
  owner or agent must verify the tag on GitHub (the repository name `felt/tippecanoe`, the tag
  spelling and the `tippecanoe_args()` flags are also unverified: nothing could run here). Not run:
  tile samples against source geometry (no archive), Range 206 and CORS on a no-card host (no host
  until H05/H06). Retry when `tiles.yml` has produced an archive and a host exists. The workflow
  does not yet tile real data: S19 cell 3bb is a 4.8 GB download kept off CI, so a data step comes
  with the first owner-approved run.

- **D150 — Background Web Push stays disabled; only detection and a refusal are built (11 Nov 2026, T184).**
  `docs/decisions/web-push.md` records the conflict (a push endpoint plus keys is a retained,
  pseudonymous device identifier, i.e. a subscriber database, which `AGENTS.md` forbids), the
  default (off; in-app watch notifications from D149 stay on) and the conditional design (consent,
  encrypted private subscriptions, 30-day expiry, delete endpoint, batch send, nothing in the
  public repository), which is not built and needs a written owner policy revision. `web/src/push.ts`
  detects the service worker, Push API and Notification support and always returns
  `enabled: false` with `disabled: privacy_mode=no_personal_data`. `worker/src/push.ts` refuses every
  method on `/api/v1/push/subscription` with 403 without reading the body (501 for any other mode
  name, since no storage exists). The route is wired in `worker/src/index.ts` before the capability
  gate: the change is one import and one line, and the handler touches no binding. No code creates a
  subscription, asks for permission or registers a service worker; `tests/test_push_policy.py`
  scans for that. `privacy_mode` has no config file yet, so it is a constant in both modules.
  The plan's feature catalogue exists only in `docs/plan.pdf` (F051, stretch); no catalogue file
  was invented, so the "conditional stretch" status is recorded in the decision document.

- **D149 — Place watches, daily brief and Telegram message; Telegram stays blocked (11 Nov 2026, T183).**
  `web/src/components/Watches.tsx` (built, not mounted, like T165) keeps watches only in this
  browser's IndexedDB (place ID, label, the user's alert flag and rain threshold); it makes no
  network call, asks for no location and has no account. `triggered()` is a pure rule: wrong
  place, cancelled or superseded status, an expired or unreadable end time, or a forecast with no
  end time never triggers (an alert with no end time stays active, as in the brief). Notifications
  appear in the page only while it is open (no Notification API, no push, see T184). Its strings
  are English literals; they need keys in all four locale files (D148) before it is mounted.
  `src/atlas/alerts/brief.py` builds the brief from an S09 table (`supersede()`, then dedupe by
  sender and alert ID keeping the latest sent time, then drop alerts expired at or before the job's
  completion time or sent after it) plus hand-passed `CurrentRecord`s that need an https source
  link; an expired current record is dropped. Official, model and inferred lines are separate
  sections; every line keeps its source URL and sent time. Active alerts repeat in each daily brief
  while valid; only cancelled, superseded, duplicate and expired ones are not repeated. 06:30 IST
  is the same instant as 01:00 UTC, so a job that starts on schedule cannot finish at 06:30:
  `ON_TIME_GRACE` (30 minutes, my choice, change it in `brief.py`) lets a run that finished by
  07:00 IST show "06:30 IST"; a later run shows its actual IST completion time, and a stamp before
  01:00 UTC of the run date (yesterday's run) is refused. No job, schedule or completion stamp
  exists in the repository yet, so the stamp is a required argument. `telegram.py` formats the
  message (4096-character cut with a count) and `send_message` raises `SourceUnavailable` with the
  S39 reason before any I/O; the channel, bot token and terms are owner step H08. Nothing about
  readers is stored: no DM, subscriber list or chat ID, and the alerts package never writes a
  file or opens a connection. Tests: `tests/test_alerts.py` (real Sachet fixtures edited as in
  `tests/sources/test_s09.py`), `web/src/components/Watches.test.ts`.

- **D148 — Ask: citation links, four-language strings and opt-in voice (11 Nov 2026, T182).**
  The page stays `web/src/pages/Ask.tsx` (no `components/Ask.tsx` is added: the page already
  held the cards and a second file would only duplicate it). Every Ask string, including the
  corpus status and error messages in `web/src/ask.ts`, now comes from `t()` in
  `web/src/i18n/index.ts`, a flat-key lookup with no library; a missing key or placeholder value
  throws. `en.json` is `reviewed`; `kn.json`, `ml.json` and `hi.json` are my machine drafts,
  `machine_draft_unreviewed`, and `SELECTABLE` is `['en']`, so no other language is offered until
  a native review and 10 reviewed Kannada questions exist (A7, D147). The draft sentence order
  around the "official warnings" link is a review item. Citation cards (path, heading,
  evidence age from the chunk's own `available_at`) already existed; each path is now a link to
  `https://github.com/Joepikka/monsoon-atlas/blob/main/<path>` (the public repository in
  `docs/HANDOFF.md`; it shows the file at `main`, which can be newer than the cited commit).
  Voice (`web/src/voice.ts`): recognition starts only from the "Speak your question" button;
  the page never calls `getUserMedia`; the result fills the question box and is not submitted;
  denial, no support, no speech or an unsupported language show a reason and leave typing
  working; the note says the browser may send audio to its own speech service. "Read the answer
  aloud" shows only when an installed English voice exists and speaks only on a press; nothing
  is spoken automatically. Tests: `tests/test_i18n.py` (key and placeholder parity, status
  metadata, English only, no literal Ask strings, voice starts only in the two handlers),
  `web/src/voice.test.ts`, and a Playwright case that counts microphone calls (0 before the
  press). Recognition language is fixed at `en-IN`; the Web Speech API cannot be asked which
  languages it supports, so `language-not-supported` is handled when it fires.

- **D147 — Kannada, Malayalam and Hindi question drafts; language slice in the Ask report (11 Nov 2026, T181).**
  `eval/rag/translations.jsonl` holds machine drafts of the 50 fixed questions in the three
  languages (150 rows: English ID, language, question, `language_review`). Every row is
  `machine_draft_unreviewed`; none is scored, none has an expected answer, and no tuning used
  them (Q41-Q50 stay hash-frozen, D101). `questions.jsonl` is unchanged. `language_coverage`
  reads the file, and `reports/rag.md` now shows English as measured and kn, ml and hi as 50
  drafted, 0 reviewed, "not validated", generation disabled. Owner steps before any non-English
  Ask: a native-speaker review of the drafts (and 10 reviewed Kannada questions, A7) and H05.
  Only the Languages section of `reports/rag.md` was edited by hand-splicing the generator's
  own text; the English scores were not regenerated because they do not reproduce. Re-running
  `python -m atlas.rag.evaluate` on 11 Nov 2026 (31 documents, 406 chunks; the logs grew since
  the 8 Nov report's 348) gives correctness 0.84, evidence support 0.80 and failing cases
  Q02, Q12, Q23, Q26, Q33, Q43 and Q45, against the committed 0.89, 0.86 and five failures.
  The retrieval rules were not touched (D99, D100), the cause was not investigated, and C3
  stays research-only (D101); the committed English numbers are the 8 Nov measurement.

- **D146 — Plan coverage audit for T179 and T180 (11 Nov 2026).**
  Every step of T179 and T180 was checked against the code and recorded in
  `docs/ask.md`, section "Plan coverage T179-T181", which `tests/test_ask_config.py` reads
  (quota caps, 300/50 chunks, the model ID absent from code and config, every named file
  exists). Result: the English scope is done; the open items are the e5 embedding (T264,
  tested and not adopted), the probe-gated Workers AI model and the live per-minute and
  per-day counters, which wait for owner step H05 (no Cloudflare token). The caps stay in
  `worker/src/ask.ts` and no `quota.ts` is added, because `ask.ts` has owned the limits since
  D88 and a second module would only duplicate them; the Worker test stays `.mjs`. No code
  changed, no AI binding was added and no model was downloaded.

- **D145 — M11 and M20 are recorded as blocked branches (11 Nov 2026, T170 to T172, T176 to T178).**
  Both depend on a flood model that does not exist. M11 (Karnataka-to-Kerala transfer) freezes
  M01 and needs common Kerala flood labels: M01 is blocked (S43 holds no official dated
  ward-level inundation records, T085) and M08 is blocked (S35 is blocked, S36 holds 2018
  district tables only), so there is no frozen score, no common 2023-24 labels and no 30 Kerala
  flood events. M20 (rain what-if) must recompute an already-approved flood score from the exact
  M01 or M08 input snapshot, so its gate is not satisfiable: M05 is the only approved model, it
  is a drought model and the card names flood models only, so no M05 sensitivity explorer is
  built under this ID. Blocking IDs: M11 S43, S35, S36 through M01, M08; M20 the same. Both
  follow the M07 to M10 pattern with no weights, scores, predictions or fallback; M20's controls
  stay disabled. Retry both after M01 or M08 is released and approved.

- **D144 — M19 and M17 are recorded as blocked branches (11 Nov 2026, T167 to T169, T173 to T175).**
  M19 (GRU reservoir challenger) must beat M02 on the same level target and needs 5 reservoirs
  with 5 years of daily data: M02 is blocked because S28 KWRIS has no verified daily history
  (T092), so there is no baseline and no target. M17 (Sentinel-1 flood extent U-Net) is blocked
  by S42, whose downloads need a Copernicus account (proposed owner step H15, so no scene was
  read), and by the absence of independent inundation masks for 5 events (S35 blocked, S36 2018
  district tables only, S43 no official impact labels); the card's threshold illustration also
  needs the gated scenes, so none is shown. Both are deep-learning models: no torch or other
  package was installed, the 2 GB local GPU is too small (AGENTS.md), and the free GPU session
  needs the open Kaggle owner step H10. Blocking IDs: M19 S28 through M02; M17 S42, S35, S36,
  S43. Plan dates are recorded as planned only (M19's 2028 dates are identical to M02's). No
  weights, scores, predictions or fallback exist.

- **D143 — Delhi release gate records a blocked product; nothing is released or exported (10 Nov 2026, T166).**
  `docs/releases/dl.md` follows the Kerala page (D129) section by section and
  `tests/test_dl_release.py` checks each table against `dl.yaml`, the S01 to S38 discovery
  records, the M12 to M15 registry and configs, git, and the Karnataka and Kerala gates. Result:
  the Delhi config passes the shared checks (0 of 8 sources enabled, S24 and S38 blocked, six
  available but unconfigured); every item has measured or blocked evidence; M12 to M15 are all
  blocked and none is research-only; no ETA or AQI accuracy exists or is shown. The label
  windows (collect from 2028-01-17, locked test 2028-04-27 to 2028-05-26) are planned, not
  started, and approval delay is a calendar delay that shifts the whole manifest, not a
  development failure. The plan's fallback (publish scheduled transit and observed air quality
  with blocked cards) is only partly possible: no static GTFS and no station data were read, so
  only the blocked cards are published. "Export frozen study and metrics to portfolio": there is
  no study manifest and no metric, so nothing is exported. Cross-state regression re-checks the
  eight frozen interface hashes (D122), the Karnataka and Kerala source counts and blocked
  models, and that the three state configs keep separate paths. No-card audit: all eight Delhi
  records have `no_card: true` and `scripts/audit_dependencies.py --policy` reports 0 problems.
  Owner-gated: H04 (S38), the S24 browser read (no new key), H05 and H06 (hosting), H11 (any
  release). M15's retry is not an owner step: enable S01 and S02 for Delhi and collect S01
  forecast vintages over the prospective window. Nothing here approves a public release.

- **D142 — Delhi transit, air and exposure interface is built and tested without a feed (10 Nov 2026, T165).**
  With S38 (D135) and S24 (D133) blocked there is no Delhi marker, ETA or station value, so the
  real states are "unavailable" and "blocked", never a number. `Transit.tsx` separates scheduled,
  live and predicted markers; a GPS position aged 120 s or more, in the future, or without a
  clock offset is `aged_out` (hidden, never animated); `STALE_SECONDS = 120` equals the Worker
  constant and `tests/test_delhi_product.py` checks both. No static GTFS was read, so there are no
  scheduled markers either. ETA p10/p50/p90 with source and release parse only when the model
  card is available; M12 is blocked, so the card says "blocked" with the planned (not started)
  window from its config (2028-04-27 to 2028-05-26, months Jan to May) and no score.
  `AirQuality.tsx` keeps the station (observation) and gridded model (CAMS) layers distinct and
  compares them only on identical pollutant, unit and averaging; `ScoreCard.tsx` (new, shared)
  puts test period and months beside any score. `atlas.analysis.route_exposure` computes the
  time-weighted ambient concentration (sum of concentration x seconds over total seconds), never
  a dose, and returns "unavailable" with a reason for mixed pollutant, unit, averaging or
  provenance, naive or overlapping times, non-finite or negative values, an instantaneous value
  (no interpolation), or a segment outside the window its reading represents (the reading's own
  averaging interval and start/end stamp are passed in, no constant is guessed). Units must match
  as strings; nothing is converted. CAMS is instantaneous (S04 record) and `dl.yaml` lists no
  S04, so the real Delhi comparison and route exposure are "unavailable". The rules are tested
  on hand-built TEST INPUTS only. Notebooks 08 and 09 audit S38, S24 and S04, draw no chart and
  reproduce byte for byte from a clean process (core packages only, so no skip is needed). The
  components are not mounted (no route, no public snapshot) pending H11, as for D116 and D127.
  `source_status` now tolerates a null retry condition (S04 is available).

- **D141 — M14 and M15 are recorded as blocked branches (10 Nov 2026, T159 to T164).**
  M14 (station PM2.5 forecast) takes its labels from S24, which is blocked (D133, D134): the
  resource ID, licence, fields, units, averaging interval and history are unread and there are
  0 station rows. S04 CAMS is available but enabled for Karnataka only and is a model estimate
  (its archive carries no run time), so it is a baseline input and never a label; a
  CAMS-versus-CAMS score is not allowed. M15 (heat outlook) is blocked too: `dl.yaml` enables
  no source, S01 keeps no issue-time forecast vintages (D07) and none exists for Delhi, S02 is
  ERA5 reanalysis (model output, trends and exposure only, per the card's gate), S18 is blocked
  by robots.txt (D34), and no Delhi temperature truth exists to score a forecast. Blocking IDs:
  M14 S24; M15 S01, S02, S18. Both follow the M07 to M10 pattern with no weights, scores or
  predictions; plan dates (2028-01-17 on) and the conditional 2021 to 2025 pollution extension
  are recorded as planned or unavailable only. No fallback is published.

- **D140 — M12 and M13 are recorded as blocked branches (10 Nov 2026, T153 to T158).**
  Both Delhi bus models take their labels from S38 only, and S38 is blocked on owner step H04
  (D135): no static GTFS, real-time sample, protobuf field list or trip linkage was read, so
  there are 0 vehicle positions, 0 service days, no scheduled arrival (the publisher calls
  static stop_times a rough constant-speed estimate) and no scheduled headway. No study approval,
  routes or dates exist (D137) and the readiness gate failed, not run (D139). M12 (arrival and
  delay) and M13 (bunching) therefore stop at the data gate and follow the M07 to M10 pattern
  (config, gate JSON, no-model manifest, status record, report, disabled-state tests), with
  no weights, scores or predictions. The plan's prospective dates (collect from 2028-01-17) are
  recorded as planned only and shift as a whole if approval is late. No fallback is published:
  a schedule ETA and the headway rule need the same unread GTFS. Retry both when the owner
  completes H04 and T148 is re-run with a real sample.

- **D139 — T152 readiness gate is recorded as failed (not run); no measurement is claimed (10 Nov 2026, T152).**
  Without approved S38 access there is no real sample, so Worker CPU, memory, snapshot blob size,
  compressed daily history and the hot to archive to replay counts are "not measured" or "not
  run" in `docs/studies/delhi-readiness.md`, never a number. Continuous capture is unavailable,
  live mode stays disabled (`TRANSIT_LIVE`, D138), and the first collection day and the
  train/tune/calibration/test chronology are not frozen, with no study manifest written. The
  plan's fallback (owner-run windows with narrower claims) applies only after H04. The one thing
  that can be checked now is quota arithmetic from `configs/budgets.yaml`: 960 polls, 960 D1
  writes and 960 Worker requests per day against caps of 960, 10000 and 20000, and 7 days at the
  plan's 40 MB per day (280 MB) against the 400 MB hot database. `tests/test_dl_collection.py`
  derives those from the configured values and checks the page against the S38 record. Retry:
  owner completes H04, T148 re-runs with a real sample, then benchmark and fill the page.

- **D138 — T151 builds no live poller; only the fail-closed rules exist (10 Nov 2026, T151).**
  With S38 blocked (D135, D137) there is no feed to poll, so no cron trigger, upstream URL, key
  binding, decoder or storage write was added to the Worker, and `worker/src/cron.ts` is untouched
  (it does not exist; nothing in the blocked state belongs there). `worker/src/transit.ts` holds
  only what can be true and tested now: the poll budget (16 h x 60 s = 960 polls/day, below the
  D1 write and Worker request caps in `configs/budgets.yaml`), the rule that a position aged
  120 s or more (or in the future, or with a bad timestamp) is never fresh, and a
  `TRANSIT_LIVE` state, unavailable with the reason "transit live mode unavailable: S38 blocked
  (H04)", that keeps `liveMarker` false. Nothing imports the module yet. The module test is added
  to `npm test`. `tests/test_dl_poll.py` checks the constants against the budgets, that no Worker
  or web file names `OTD_API_KEY`, `VehiclePositions` or the OTD host, and that `wrangler.toml` has
  no `crons`. Deferred, with T150's retry condition: the 60 s cron, one upstream call per tick,
  route-filtered decode, one compressed snapshot per tick and the static schedule fallback.

- **D137 — T150 Delhi is registered with every source disabled; the study cannot start and the decoder is deferred (10 Nov 2026, T150).**
  `configs/states/dl.yaml` is an isolated Delhi config in the shape of `kl.yaml`: paths under
  `data/*/dl`, S24 and S38 listed disabled with their discovery records, and the shared national
  sources (S01, S02, S09, S15, S16, S17) disabled until a Delhi adapter test exists. `docs/studies/delhi.md`
  records access approval = none (H04 pending), protobuf schema = not published and not read, trip
  linkage = unknown, selected routes = none (the 543 bus and 36 DMRC route counts are public-page
  counts, not a selection), study dates = not frozen (the plan's 2028-01-17 start assumed approval
  on schedule, so the whole manifest shifts and nothing earlier is invented). Deviation from the
  plan: step 3 (`worker/src/protobuf.ts` with pinned protobufjs) is deferred, because there is no
  real sample to inspect and no feed to decode, so a decoder would be untested speculative code and
  a new dependency with no user. `tests/test_dl_study.py` reads the S24/S38 records so the page
  cannot drift. Retry: owner completes H04, T148 re-runs with a real sample, then add the decoder.

- **D136 — T149 S38 is a disabled contract; the Delhi state config is still not created (10 Nov 2026, T149).**
  Because T148 ended blocked on H04, `src/atlas/ingest/s38.py` raises `SourceUnavailable` from
  `fetch` and `parse` before any I/O, even if force-enabled, and `schemas/s38.json` lists no
  fields (the plan's eight section 7 fields stay unverified: no protobuf or GTFS file was read).
  No enabled-source tests (real sample, malformed, empty, changed columns) exist, because no real
  sample was permitted or read. `configs/states/dl.yaml` is not created (T150), so the test builds
  a disabled `SourceConfig` with `OTD_API_KEY` as the secret name, as D134 did for S24.

- **D135 — T148 S38 is blocked on owner step H04; only the public pages were read (10 Nov 2026, T148).**
  otd.delhi.gov.in answers plain HTTP (no robots.txt, 404). Its static GTFS files and the real time
  feed are behind forms that ask for a purpose, name and email and a tick accepting the Terms
  (POST to `/data/static/` and `/data/realtime/`); the pages publish no direct file URL, and the
  documented feed path `/api/realtime/VehiclePositions.pb?key=...` returns HTTP 401 without a
  key. Submitting a form, registering and accepting terms are owner-only actions (H04), so none
  was done and no GTFS file, key or sample was obtained. Recorded from real evidence: the file
  list with counts and dates, the Terms PDF (restricted: DoT copyright, intent-based permission,
  accurate reproduction with credit, no tracking or profiling of individuals), no published quota,
  no history, and no units or timestamp semantics. No upstream field is claimed. The plain-http
  `agency.txt` footer link was not fetched (the fetcher is https only) and not guessed at over
  https. Dependents T149 to T153 and T156 are blocked. Retry: owner completes H04, then T148
  re-runs.

- **D134 — T147 S24 is a disabled contract with no Delhi state config (10 Nov 2026, T147).**
  Because T146 ended blocked, `src/atlas/ingest/s24.py` raises `SourceUnavailable` from `fetch` and
  `parse` before any I/O, even if force-enabled, and `schemas/s24.json` lists no fields. No
  enabled-source tests (real sample, malformed, empty, changed columns) exist, because no real
  sample was read. `configs/states/dl.yaml` is not created (T150 owns Delhi registration), so the
  test builds a disabled `SourceConfig` itself.

- **D133 — T146 S24 is blocked because the resource page could not be read; the ID is not taken from a tutorial (10 Nov 2026, T146).**
  Plain HTTP gets 403 on the data.gov.in resource and catalogue pages (as in T025). The Browser pane
  loaded the S24 resource page, but every content-reading tool returned "Policy check temporarily
  unavailable", so the API tab (resource ID) and the licence text were not read, and Claude in
  Chrome was not connected. A third-party tutorial quotes an ID; it is not a page the source
  publishes, so it was not used or tested. The one evidence file (e01) is a one-record keyed request
  for the S23 resource, kept only to show that the key and API host work and that no rate limit is
  published; the YAML says it is not an S24 sample. Licence is unverified, units, averaging
  interval and history are unestablished, the field map lists no upstream fields, and
  redistribution stays false. Dependents T147, T150 and T159 are blocked. Retry: read the page in a
  browser that can read content, then re-run T146 (no new key needed).

- **D132 — T223 Power BI report is generated with four pages, two of them blocked notes; PNG and PDF exports are an owner step (9 Nov 2026, T223).**
  `powerbi/build_pbip.py` writes `powerbi/MonsoonAtlas.pbip` (TMDL model plus PBIR report, as in
  kerala-veg-prices) and four small CSVs in `reports/powerbi/data/`, all derived from committed
  files. Reservoir trends: S28 is blocked (D105), so the page shows the S32 storage change for the
  8 of 16 dams in `reports/sql_insights.md` Q08 and Q09 (sampled about every 15 days, net of
  rain and releases; CC BY-SA 2.5 India, credit KSEB, share alike) and a blocked note for S28.
  Ward rain and flood exposure: S43 is blocked and no ward-level rain is committed, so the page
  shows S29 gauge totals by district (the S08 columns `grid_mm`, `bias_mm` and `ratio` are
  dropped) and a blocked note for flood exposure. Prices: S22 and S23 hold zero rows (D120), so the
  page is a blocked note with no data. Model accuracy: M05 against persistence from the registry
  records (accuracy figures only, derived from S08; H11 item 3 still decides S08 publication,
  D129), with a blocked note for M07 and M06. The base theme is not copied (it ships with Power BI
  Desktop), the DataFolder parameter holds this checkout's path (rerun the script after moving
  it), and no Power BI Service publishing or sign-in is used. Power BI Desktop is not installed
  here and the GUI is not driven, so the project is untested in Desktop and **no PNG or PDF
  exports exist**; none are fabricated. Owner steps: open `powerbi/MonsoonAtlas.pbip` in Power BI
  Desktop, confirm it loads, then File > Export (PDF) and save PNGs of each page into
  `reports/powerbi/`, and add them to the README. `tests/test_pbip.py` checks determinism against
  the committed files, JSON validity, that every visual reads an existing CSV, no blocked source
  or S08 column as data, and that blocked pages carry their reason.

- **D131 — T224 answers ten questions the held data can support; the spec's examples are not answerable (9 Nov 2026, T224).**
  The example "which reservoirs filled fastest after the heaviest 3-day rain?" needs daily
  reservoir levels (S28 KWRIS, blocked) and the price and flood-label examples need S22, S23 and
  S43 (blocked), so none is answered; `reports/sql_insights.md` lists them under "Not answerable".
  The ten questions use S29 (open), S44 (open), S21 (CC0), S32 (CC BY-SA 2.5 India, credit
  KSEB), S06 (open) and M05 accuracy records. The S08 IMD grid enters only as the grid-to-gauge
  ratio (an index) in Q03, never as millimetres, and H11 item 3 still decides its publication
  (D105, D129). Q01 to Q06 read files tracked in git and run in CI; Q07 to Q10 need `data/raw`
  and skip in CI. Two Kerala reservoir questions use the S32 reports sampled about every 15 days
  (8 of 16 dams with complete readings), so they say storage change, not fill speed after rain.
  S44 counts are registered cases, not incidence. S30 (restricted) is not used.

- **D130 — Climate product runs on S08 1981-2025 and S06; NDVI and official onset are unavailable (9 Nov 2026, T145).**
  S42 is blocked on the owner account (H15), so `atlas.analysis.vegetation` implements NDVI
  (cloud, nodata, negative reflectance and zero denominator stay NaN, so values lie in [-1, 1];
  10-day valid-pixel median) and tests it on small hand-checked arrays only; the layer status is
  "unavailable" and the wording is "vegetation greenness" (no verified crop mask). S08 is held for
  1981-2025, not 1901, so trends cover 1981-2025 and the 1901-1980 gap is a stated limit. No
  enabled source publishes an IMD onset date (no config mentions one), so `official_onset` is null
  with a reason; the heuristic onset (first 3 days in a row with at least 2.5 mm from 1 May) is
  labelled "inferred". The tracker uses cumulative rain from 1 Jun against the strictly 1981-2010
  distribution. To respect the S08 licence (D129) `reports/eda/08_climate_product/climate.json`
  holds indices only (percent of median or normal, percentile rank, slope per decade), never mm;
  H11 still decides the S08 finding. The tracked year is 2025, a past and provisional year, not a
  live feed. S06 projections reuse T142's results, keyed by model and labelled "climate
  projection, not a forecast". `Climate.tsx` is built and tested but not mounted, because
  `Accuracy` is mounted only for approved releases and this page waits for H11.

- **D129 — Kerala release gate passes with all four Kerala models blocked (9 Nov 2026, T144).**
  `docs/releases/kl.md` records 19 Kerala sources (4 enabled: S06, S08, S32, S36; 7 blocked;
  8 available but not yet configured for Kerala), M07 to M10 blocked with null scores and 0
  predictions, the 2018 chronology (35 `as_known` S36 records from the 7 Aug and 13 Sep 2018
  memoranda, 122 `reconstructed` S08 records, 0 forecast vintages), a licence audit (restricted
  sources keep raw files local; git holds manifests only) and the Karnataka frozen-interface
  hashes, unchanged. No Kerala model is research-only; the case-study draft quotes only measured
  or blocked results. The Malayalam strings in `docs/releases/kl-ml.json` are machine-drafted and
  need native review before release (H11). The committed S08 box-mean rain in `reports/eda/`
  conflicts with S08's no-area-average licence if ever published, so H11 must decide (drop the
  S08 records or get IMD permission). The gate does not approve a public release: that still
  waits for H11.

- **D128 — Exposure and route comparison run without roads, shelters or hazard polygons (9 Nov 2026, T143).**
  `atlas.spatial.exposure` splits S16 cell people by the area share inside the union of any
  supplied hazard polygons (EPSG:6933; overlaps count once; inside + outside = total; coverage
  = share of hazard area with population cells). It assumes people are spread evenly in a 1 km
  cell. No verified Kerala flood or landslide polygon exists (S37 blocked; S36 has district
  area numbers only), so the real-data test uses an H3 analysis cell over Karnataka S16 cells
  (Kerala S16 is disabled in `kl.yaml`). `atlas.spatial.routes` has a heapq Dijkstra tested on
  small hand-built graphs; with no road network (S18 blocked, D34) real use returns
  "unavailable". Shelter routing is disabled with no official shelter record (S43 blocked, D124)
  and with a record older than 2 days. Every result carries the "not a safe route" label and
  the KSDMA link from S36. `RouteComparison.tsx` is built and tested but not mounted.

- **D127 — Kerala event study, 2018 replay and climate run on what exists (9 Nov 2026, T142).**
  The rain-to-price event study is not computable: S22/S23 hold zero price rows (D120, D126),
  so `notebooks/06_rain_price.ipynb` reports n = 0, "not computable" and no chart. The method is
  ready and tested in `atlas.analysis.event_study` (fixed effects with event-time dummies, CR1
  cluster-robust SEs with t(G-1) CIs, pre-trend and placebo checks); any failed check, or no
  data, labels the result "association only", and `coef_chart` refuses a chart without a CI,
  source or vintage. S08 gets a `"kl"` cell box (8.25-12.75 N, 74.75-77.5 E; it holds Tamil Nadu
  and Karnataka border cells, so it is a box, not the boundary), and S06 and S08 are enabled in
  `kl.yaml` (national/global grids whose verify tasks passed). A replay record is **as_known**
  only when the publisher's own dated issue falls on or before 30 Sep 2018, and it shows only
  from that date: the S36 memoranda submission dates (7 Aug and 13 Sep 2018; the web copies sit
  under a 2019 upload path, so this means issued by the state, not online). Every S08 value is
  **reconstructed** (a fetch date is not a publication date). S32 holds no 2018 dam row (the
  15 Aug 2018 report is empty). No forecast vintage is held or imitated. S06 projections use two
  points (request budget), are labelled with no scenario, and show model spread, never a CI.
  `Replay.tsx` is built and tested but not mounted, like T104/T105.

- **D126 — M09 and M10 are recorded as blocked branches (9 Nov 2026, T136 to T141).**
  M09 stops at the data gate: S37 is blocked (the NRSC Atlas gives Kerala counts only, with no
  landslide point, date, positional error or survey footprint, D124) and S42 waits for the
  owner's Copernicus account (H15), so there is no label and no surveyed absence cell. M10
  stops too: S22 exposes no price row and S23 is a one-day snapshot with an unverified unit
  (D120), so there is no weekly panel, 30 markets or 50 rain events, and no effect is
  estimated from zero data. Both follow the M07/M08 pattern (config, gate JSON, no-model
  manifest, status record, report, disabled-state tests). No fallback is published: the cards
  name none, and a terrain-only layer from S14 would be exposure, not susceptibility.
  Retry M09 when S37 gives a downloadable inventory with footprint; retry M10 when S22 or S23
  gives weekly modal prices for 30 markets with a publisher-stated unit.

- **D125 — M07 and M08 are recorded as blocked branches (9 Nov 2026, T130 to T135).**
  M07 (C1 fallback) stops at the data gate: a known datum for 4 of the 8 dams (D103, D124),
  S32 history is sampled dates only with a 700-day empty stretch, and S34 needs the T118
  bulk OCR the owner has not approved (D102). M08 stops too: S35 is blocked and S36 has
  2018 district labels only, with no audited pre-2018 negatives, so no classifier is trained.
  The descriptive 2018 replay stays with T142 and makes no accuracy claim (D29). Each
  branch follows the M01 to M04 pattern: config, gate JSON, no-model manifest, status record,
  report and disabled-state tests, with no weights, scores or predictions and no fallback
  output (persistence needs the same missing daily data). C1 stays blocked (D104).

- **D124 — T129 Kerala audit runs with T046 and T118 pending (9 Nov 2026, T129).**
  T046 gates public release (H11, H05, H06), not the audit's inputs, and T118 (S34 bulk
  OCR) was not approved: D102 covered eight crops only. So S34 labels count as unavailable
  and the audit changes no source flag. T114/T116, T120, T122 and T124 are done. Result:
  16 S32 dams registered in `configs/states/kl/dams.yaml` (outside `kl.yaml`, because
  `StateConfig` rejects extra keys and config.py is frozen), 4 with a known datum (MSL, D103),
  12 unknown; the 8-dam datum gate for T130 is still unmet. Precedence: S32 daily, S34 after
  T118, S33 monthly never daily. Available label families: S32 dated daily levels (sampled
  dates only, 700 verified-empty days) and one S36 dated 16 Jul 2018 flooded-area table.
  Excluded: S36 period totals, 2018 narrative dates, pre-2018 negatives, S35, S34, S33,
  S37 landslides (survey footprint unknown), and Kerala ward and shelter evidence (none
  verified; Karnataka geometry is not reused). S33 now cites its blocked discovery record.

- **D123 — S36 parses three district tables only; raw PDFs stay local (9 Nov 2026, T122).**
  The KSDMA PDFs have a readable text layer (pypdf 6.21.4, already pinned in
  `requirements/ocr.in`), so S36 is enabled. It reads NRSC flooded area (Memorandum 1,
  page 9, as on 16-7-2018, 7 districts, 55,007 ha) and district human fatalities
  (Memorandum 1 page 14, 138; Memorandum 2 page 20, 339) and checks each against the
  published Total row. Rows keep the published district name (`district_id` is a name, not
  an ID; `place_id` null; no crosswalk), the document, page and row text. Period totals have
  a null `event_date` and `date_basis=period_total`. Not parsed: the relief-cost column, houses,
  wards, other memoranda, the PDNA and the 2013 memorandum (mixed hazards). Licence is all
  rights reserved, so `redistribution_allowed` is false, no PDF is committed, and the real-PDF
  tests skip when `data/raw` lacks the files (CI); text-layer failure cases are tested with
  patched page text. Fetch streams each memorandum once (`fetch_large`, no conditional GET).
  `tests/test_kl_data.py` now expects S32 and S36 as the enabled Kerala sources.

- **D122 — Karnataka v1 gate passes; interfaces frozen (9 Nov 2026, T110).**
  `docs/releases/ka-v1.md` and `tests/test_ka_v1.py` audit all 33 Karnataka
  sources (23 enabled, 10 blocked and disabled with retry conditions), the six
  KA models (M05 approved; M01 to M04 and M06 blocked with null scores) and
  nine KA layers (1 measured, 5 blocked, 3 built but not mounted). Every item
  has measured or blocked evidence, so Kerala work can begin. The shared files
  listed there (contracts, config, ingest base, discovery, http, raw store,
  validate, common schema) are frozen: changing one during Kerala work needs a
  decision entry and new hashes in the same commit. T110 does not approve a
  public release: T046 still waits for H11, and C1 stays blocked (D104).

- **D121 — Spatial statistics use M05 residuals; M04 is not comparable (9 Nov 2026, T109).**
  M04 is blocked, so there are no M04 outputs to compare; nothing is
  substituted. `notebooks/10_spatial_statistics.ipynb` tests Moran's I on the
  approved M05 ridge residuals (saved v1 fit, never refitted) for each of
  the 60 locked-test issue months 2020-01 to 2024-12, 30 S17 districts.
  Weights: queen contiguity (any shared boundary point), row-standardised.
  999 permutations (seed 109), two-sided pseudo p = (1 + #{|I_perm - E| >=
  |I_obs - E|}) / 1000; Benjamini-Hochberg at q = 0.05 across the tested
  months. The semivariogram uses only out-of-sample residuals of the D97
  rolling-origin refits, target years 2000-2019: no 2020+ row enters it.
  `rolling_residuals` now also returns `place_id` (values unchanged).

- **D120 — Price notebook is a unit and availability audit (9 Nov 2026, T108).**
  S22 and S23 are blocked (T023, T025), so there are zero price rows and
  the plan's market-season, spike and future-label questions cannot be
  answered. `notebooks/03_ka_prices.ipynb` audits every discovery field and
  its unit status (S23 price unit stays unlabelled) and reports those
  measures as n = 0, "not computable", never 0% and never a filled label.
  The adapters still raise `SourceUnavailable`. The single 5 Nov S23
  snapshot is not used: its unit is unverified.

- **D119 — Rainfall notebook compares annual district totals (9 Nov 2026, T107).**
  S29 is annual only (D113), so the seasonal gauge/grid comparison the plan
  asks for is impossible; the notebook compares annual district totals for
  2020, 2021, 2022 and 2024 against the S08 grid area-weighted to S17
  districts (the 2023 file has stations only: its coverage is reported, no
  pairs). S29 names reach S17 only through the committed crosswalk
  `configs/crosswalks/s29_s17_districts.csv` (same spelling or the 1 Nov
  2014 renamings). Ballari from 2021 loses Vijayanagara, which S17 Bellary
  keeps, and Vijayanagara has no S17 polygon, so both are excluded for 2021
  on (6 of 123 district-years), never filled. S08 is labelled a
  reconstruction (a gauge-based analysis), so it is not independent of the
  gauges.

- **D118 — Feed-quality notebook uses the feeds with real history (9 Nov 2026, T106).**
  T106 names S01 and the price feeds, but S22/S23 have no rows (blocked)
  and S01/S09 have one local capture day, so a daily heatmap of them would
  be empty. The notebook measures what exists: S08's Karnataka box (540
  cells, 1981-2025: 8,875,440 of 8,875,440 cell-days, no missing day, no
  duplicate rows; 2 of 48 year-file fetches were unchanged re-downloads),
  the reporting lag of the committed S10 sample (20 aircraft) and the single
  S01 run's availability lag. The limits are written into the outputs. S08
  is local only, so the notebook re-run test skips in CI; the exported
  counts and charts are derived outputs and are committed.

- **D117 — Context layers follow the source contracts (9 Nov 2026, T105).**
  FIRMS (S25) and RERA (S31) are blocked, so T105 cannot render hotspots or
  projects; their controls are disabled with the recorded retry condition
  and evidence, and the guards (thermal anomaly only; public RERA fields
  only) are in place for when they open. S44 cleared its gate, but police
  units are not districts (D114): the crime layer lists the published
  district "Total" per year and maps nothing; the 2024 table has no total,
  and its offence heads are not summed into one. Building clipping is tested
  on real S19 footprints inside a real H3 cell, because no Bengaluru shard is
  stored locally. The controls are not mounted in the app until a public
  snapshot carries them.

- **D116 — Scheduled transit layer built, not mounted (9 Nov 2026, T104).**
  The position engine and the web component are complete and tested on the
  real pinned feeds, but the component is not added to the app: S30 is
  restricted (D115), so no public transit snapshot may be built until H11.
  A stop counts as on the trip's shape within 150 m, matched in stop order;
  otherwise the segment pauses (18 of 4,153 BMTC trips at 08:00 on 12 Nov
  2026). GTFS blank times are not interpolated: any missing time pauses the
  running trip, as the plan says to pause on gaps.

- **D115 — S30 uses unofficial GTFS compilations, restricted and labelled (9 Nov 2026, T028).**
  BMTC and BMRCL publish no GTFS feed: the Mobility Database lists only a
  deprecated 2013 BMTC feed and Vonter's unofficial BMTC feed, and has no
  Namma Metro feed; OpenCity and the BMRCL home page have none. The plan's
  F011 transit layer can still be built from Vonter's two ODbL compilations
  (BMTC scraped from the Namma BMTC app, BMRCL transcribed from BMRCL
  timetable images), read at pinned commits. Because BMTC keeps copyright in
  some contents and BMRCL states no licence, the licence is recorded as
  restricted: raw files stay local, tests skip in CI, and public display
  waits for H11. Rows are `reconstructed` (third-party timetables, not the
  operators' own feed); BMRCL stop times with `timepoint` 0 are approximate
  and flagged `imputed`. P1's T028/T029 had been left out of the A8 order;
  they run now because T104 depends on T029.

- **D114 — S44 crime rows keep police units (9 Nov 2026, T087 and T088).**
  The police tables count registered cases per police unit, and those units
  are not revenue districts: city commissionerates are split from their
  districts, range rows are empty headings, and railways, coastal security
  and CID cover no area. The adapter keeps the published unit name in
  `district_id` and adds `unit_kind` (district, commissionerate, state total
  or no area; a range row with counts would be a range subtotal); joining units to S17 districts is a
  later, explicit crosswalk, never a name guess inside the adapter. Offence
  heads are stored as published in `offence_category`, because they change
  between years and with the IPC to BNS change. Every display says that
  registered cases are not crime incidence.

- **D113 — S29 is annual hobli rainfall, not a daily 2017-2023 series (9 Nov 2026, T079).**
  The plan names "OpenCity KSNDMC hobli rainfall 2017-2023" with a daily
  `date_local`. OpenCity's KSNDMC organisation has five datasets and none is
  daily: the rainfall dataset holds annual district, taluk and hobli totals
  for 2020 to 2025 (one CSV per year, each with its own layout) and annual
  totals for 5,266 stations in 2023. S29 therefore records annual values:
  the period is the calendar year named by the resource, `coverage` is null
  (not published), and hoblis and stations are identified by their published
  name path (district / taluk / hobli or station), because no codes are
  published. Names that repeat inside one taluk are flagged, and paths are
  matched across years only by exact name. No daily S29 rows are invented;
  models that need daily hobli rain wait for another source (S27 retry).

- **D112 — Plain-HTTP discovery evidence for hosts without HTTPS (9 Nov 2026, T077).**
  ksndmc.org refuses connections on port 443 and answers only over plain
  HTTP. The shared Fetcher stays HTTPS-only for every ingestion path. For
  discovery evidence only, such a host's public pages may be read once over
  HTTP with the project's generic user agent, without secrets or forms, and
  stored in the raw store with a `shows` text that says they came over plain
  HTTP and outside the Fetcher. No adapter may ingest from such a host; the
  source stays blocked until the publisher serves HTTPS.

- **D111 — S21 railway stops (9 Nov 2026, T073 and T074).**
  The Datameet files stopped changing on 8 Aug 2016, so S21 rows are a
  historical timetable: provenance `reconstructed`, `published_at` the pinned
  commit time, no `valid_at`, and the map labels them "2016 timetable", never
  a current time or ETA. The schedules publish no stop sequence; the adapter
  numbers stops in file order within each train (stop ids rise in that order
  for 5,199 of 5,208 trains) and flags the stops of the other trains
  `imputed`. It adds `journey_day` (the published `day`), because a clock time
  means nothing without the day of the journey. Rows are kept for stops at
  stations whose published state is the configured state; the string "None"
  becomes null.

- **D110 — S20 USGS earthquake rows (9 Nov 2026, T071 and T072).**
  www.usgs.gov answers the project's scripted client with HTTP 202 and an
  empty body (policies, copyrights-and-credits and robots.txt), and the
  browser retry used for S23 (D53) was unavailable, so no licence text was
  recorded. S20 is treated as restricted, like S12: raw files stay local,
  rows carry `redistribution_allowed = false`, tests read the local raw files
  and skip in CI, and the USGS statement is confirmed before public display
  (H11). The adapter adds `mag_type` and `updated_at` to the plan's fields:
  the magnitude means nothing without its type, and `updated_at` is the
  version key the plan's "deduplicate by event ID and update time" needs.
  Only `type` earthquake is kept (feeds also carry quarry blasts and
  explosions), and a deleted event is dropped.

- **D109 — CelesTrak GP queries under D31; OMM instead of TLE (9 Nov 2026, T063).**
  celestrak.org's robots.txt disallows `/NORAD/elements/gp*.php` and `*.txt`
  for all agents, but its documentation and usage policy are written for
  machine-to-machine software: documented query URLs, one download per
  update (every 2 hours), and "M2M software should immediately stop querying
  when it receives any non-HTTP 200 responses and report the results to a
  human" (T063 e03, e05). D31 therefore applies as in D106: only documented
  GP queries, at most once per group and format per 2 hours, and the adapter
  stops on any non-200 response without retrying. Since 11 July 2026 new
  objects have 6-digit catalog numbers that the TLE format cannot carry; the
  stations group lists 19 objects in OMM JSON but 15 in TLE (crewed Soyuz and
  Dragon flights are missing). The adapter therefore uses OMM JSON and keeps
  the plan's `tle_line1`/`tle_line2` null with that reason. No licence is
  published, so the licence status is restricted: raw element sets stay
  local, CelesTrak is credited, and only derived positions may be shown after
  H11.

- **D108 — S10 adsb.lol rows (9 Nov 2026, T060).**
  Aircraft positions are community receiver reports, some computed by
  multilateration, not an official air-traffic feed and not a model, so rows
  get provenance `inferred` and keep the upstream `type` as `position_type`.
  Under the project's privacy rule the adapter drops aircraft whose `dbFlags`
  mark LADD or PIA (T059 e09), and it never stores callsign, registration or
  type designator, so nothing links a row to an owner. Positions already
  older than 300 seconds at fetch time are dropped; `valid_at` is the position
  time so the map can hide later ones after 5 minutes. `on_ground` replaces an
  altitude for aircraft reporting "ground", and a null `altitude_m` or
  `speed_ms` means not reported (both optional in the plan). The committed
  test fixture is the real T059 response with `flight`, `r` and `t` removed.

- **D107 — Extra source columns for S06 and S07 (9 Nov 2026, T054 and T056).**
  As D33 did for S09, the adapters add columns to the plan's section 7 fields
  where the discovery found they are needed to read a row honestly. S06 adds
  `bias_corrected`, because the API returns either ERA5-Land-corrected or raw
  model values on different cells (T053). S07 adds `met_product`,
  `solar_product` and `api_version`, because POWER names products per request
  and asks for the version in citations (T055), and `solar_missing_reason`,
  following the S32 pattern for a measure outside the row's core reason:
  shortwave lags rain and temperature by months, and one row-level reason
  would erase good rain and temperature. Rain and temperature stay the core
  measures checked against `missing_reason`.

- **D106 — NASA POWER API calls under D31 (9 Nov 2026, T055).**
  `power.larc.nasa.gov` serves both the website and the API. Its robots.txt
  disallows `/api/` for all agents (allowing `/api/pages/` and the docs) and
  blocks named AI training crawlers. The POWER docs invite scripted use: the
  API tutorial says developers can include "a POWER API URL in your scripted
  application", and the Daily API page documents the `/api/temporal/daily/point`
  route, a 20-parameter limit, HTTP 429 and blocking of repeated same-location
  requests (T055 e01, e03, e04). D31 therefore applies: the documented API is
  called within those limits with the project's generic user agent, never for
  crawling or training data, at least 3 seconds apart and once per location
  and range. Website pages outside the docs are not crawled. Revisit if POWER
  publishes terms that say otherwise.

- **D105 — P2 starts while T046 stays open (9 Nov 2026; owner: "continue with the project", C1 deferred in D104).**
  A8 puts P2 after the T046 gate and H11. T046 cannot close now: C1 is
  deferred (D104), and the H11 sheet (`docs/releases/h11-ka.md`) and the
  H05/H06 tokens are open. The owner asked to continue, so P2 work proceeds
  locally; nothing is deployed and no restricted-licence values are
  published until H11. T223 (Power BI) and T224 (SQL insights) are deferred
  to the end of P2: their example pages need reservoir, flood-label and price
  data that are blocked (KWRIS, S43, S23), and IMD-derived values wait for
  H11 item 3. P2 continues in the plan's order with the open-data source
  tasks, starting with T047 (S03 Open-Meteo GloFAS river discharge).

- **D104 — C1 deferred to the owner at the end of the project (9 Nov 2026; owner in chat: "do not bother with emails to kseb i do not think there is going to be a reply and continue with the project" and "mark it i will think when the whole project is done").**
  C1 stays blocked at its data gate: M02 has no daily history (KWRIS, T008),
  and M07 has a stated datum for 4 of the 8 dams T130 needs (D103). No email
  is sent to KSEB. Other routes (for example India-WRIS or CWC reservoir data,
  the plan's optional D16 discovery) are listed for that end-of-project
  decision, not pursued now. The release checklist keeps C1 "blocked", never
  "pass". Work continues with the next tasks that do not need C1.

- **D103 — Vertical datum evidence for KSEB dams (8 Nov 2026; owner approved the downloads in chat: "Yes, download them").**
  Split T267 from T130, whose data gate needs a known vertical datum and
  whose sources (S32, S34) state none. KSEB's Dam Safety section on kseb.in
  publishes operation and maintenance manuals per dam; the Idukki manual
  (O&M-09) says its levelling references come from Survey of India
  benchmarks above mean sea level. kseb.in's robots.txt disallows nothing.
  The 18 manuals (about 101 MB) are fetched through the project fetcher into
  ignored `data/raw/S32/` as S32 evidence e81-e98, because KSEB publishes
  S32. Each dam counts as datum-known only when its own manual states the
  reference (mean sea level or a named datum) in text that can be quoted with
  its page; a dam whose manual is silent, or only gives "EL" numbers, stays
  unknown. The datum table goes in `docs/labels/kerala.md`. This settles the
  datum part of the T130 gate only; daily coverage, OCR validation and splits
  stay mandatory. Irrigation-department dams need a separate source.

- **D102 — S34 OCR sample reviewed by the agent on the owner's delegation (8 Nov 2026; owner in chat: "u do the review and all then continue the project").**
  D50 asks the owner to read each crop and supply the value. The owner
  delegated this to the agent. The agent read all eight crops of the T228
  packets (e08: 20 Jun 2020; e10: 1 Aug 2023), each with its full table row
  and column header, and recorded value, unit and dam row. This is a second
  machine reading (vision), not a human check, and is labelled as such. The
  records are `data/raw/S34/ocr-review/<id>/review.json` (local only, because
  S34 forbids redistribution) and match the packet SHA-256 in the manifest.
  Findings, without values: OCR method A matched the crop in 6 of 8 cells and
  method B in 4 of 8; both cells where A and B agreed were right; a column
  headed "(m)" holds cells written in ft (2020 KSEB Idukki and Sholayar), so a
  unit must come from the cell first and the header second; Kuttiyadi appears
  in both the KSEB and the irrigation table with different levels, so dam
  identity needs the operator; irrigation rows have yellow or orange
  backgrounds whose meaning is not inferred. The approval covers these eight
  cells only, not bulk OCR (D50). S34 stays disabled.

- **D101 — C3 Ask is research-only (8 Nov 2026; owner approval in chat: "Yes, record it").**
  Split T266 from T046. C3 (F046 cited Ask, text, English) fails the T181
  thresholds on evidence support: 0.86 (30 of 35) against 0.95, with every
  other measure passing. The e5 rerank (T264, D99) and the log limit (T265,
  D100), both chosen on dev cases only, gave no gain, and fixing every
  wrong-section miss would reach at most 0.943. Under A3 an honest failing
  result counts as a finished core model, so C3 is recorded as
  research-only rather than tuned further on 27 dev cases. Ask stays
  extractive (quoted sections with citations, no generated answer) and the
  page says it is research-only. The release checklist shows the C3 check
  as "research-only", not "pass": whether a research-only C3 meets T046
  extra check (2) is the owner's call at H11, and the release stays not
  releasable until then. Revisit only with a fresh held-out question set
  written before any tuning, or with reviewed generated answers after H05.

- **D100 — Limit the two append-only logs in Ask results (8 Nov 2026).**
  Split T265 from T179. `docs/decisions.md` (project/decisions) and
  `docs/amendments.md` (project/amendments) grow with every task and mention
  nearly every topic; they are 154 of the 333 chunks and crowd specific
  documents out of the top five (practice recall fell from 0.90 at T252 to
  0.85 at T264). Three rules are compared, all keeping the other retrieval
  rules: L0 as now (any document at most two of the top five); L1 each log
  at most one of the top five; L2 as L1, with the logs' BM25 scores halved
  before ranking. The rule is chosen on the 27 dev cases by evidence
  support, then by recall on the 20 retrieval dev questions, then the
  simpler rule (L0, L1, L2). The C3 report is then run once. Expected
  ceiling: even if Q23, Q33 and Q43 are fixed, evidence support is 33 of
  35 (0.943), below 0.95, so the gate cannot pass through this change.
  The browser search mirrors the chosen rule.

- **D99 — e5 rerank for Ask retrieval, chosen on dev cases only (8 Nov 2026).**
  Split T264 from T179 (step 2 and 3, deferred in D88). The owner approved
  the full dl lock (torch 2.15.0 CPU, transformers 5.22.1,
  sentence-transformers 6.2.0) and `intfloat/multilingual-e5-small` at
  revision 614241f6 (MIT, not gated; `model.safetensors` and
  `tokenizer.json` match their published SHA-256), stored in the ignored
  `data/models/e5/614241f6/`. Passages are embedded as
  `passage: <heading>. <text>` and questions as `query: <question>`,
  normalized 384-dimensional vectors, cosine similarity. Four retrieval
  methods are compared, all keeping the as-of, state, language and expiry
  filters, the two-per-document cap, the near-duplicate rule and the top
  five: R0 BM25 (current); R1 e5 order of the BM25 top 50 (the plan's
  rerank); R2 reciprocal rank fusion (k = 60) of BM25 and e5 ranks within
  the BM25 top 50; R3 the same fusion over the union of the BM25 top 50
  and the e5 top 50 of all filtered chunks. The method is chosen on the
  27 dev cases of `eval/rag/questions.jsonl` by evidence support, then by
  recall on `eval/rag/retrieval_dev.jsonl`, then the simpler method
  (R0, R1, R2, R3 in that order). The full report, holdout included, is
  then run once with the chosen method and the gate is read as it falls.
  The pass applies to the Python Ask path; the web page stays lexical
  until a separate decision on an in-browser model.

- **D98 — M05 2025 monitoring check, fixed before scoring (8 Nov 2026).**
  Split T263 from T103. The IMD 2025 file (SHA-256 b4fa5ffb..., identical
  when fetched on 5 and 8 Nov 2026) has never been used by M05. IMD does not
  say it is final, so every 2025 result is provisional and a hindcast (D39).
  Rebuild the features for 1981-2025 with the v1 pipeline; the rows with
  target months up to December 2024 must hash to the v1 dataset, or the
  check stops. Score the approved v1 ridge (saved weights) and the v1
  baseline (persistence) once on the 360 rows of 2025: MAE of each, their
  ratio, the mean improvement with a paired block bootstrap by month (12
  months, below the 24-month release minimum, so reported only), the number
  of drought rows (SPI-3 < -1), and 80% interval coverage with the D97 rule
  (last five years, by season) built from the champion's own 2020-2024
  test residuals. Flags: the forecast "holds" if ridge MAE is at most the
  persistence MAE, otherwise "degraded", which goes to the owner; nothing is
  demoted automatically. Intervals stay hidden whatever 2025 shows, because
  one year cannot meet the 24-month minimum. Results go to
  `models/registry/M05/v1.monitor-2025.json` and
  `reports/models/m05-2025.md`.

- **D97 — M05 interval recalibration rule, fixed before any test use (8 Nov 2026).**
  Split T262 from T103. The approved v1 ridge point forecasts do not change.
  Calibration residuals come from expanding-window rolling origins every five
  years (plan M05 card): origins 2000, 2005, 2010 and 2015 each refit ridge
  with the v1 alpha and features on rows whose target month ends at least 92
  days before the origin (the v1 purge), then predict the next five years,
  stopping at December 2019. Six rules are compared: residuals from the last
  1, 5 or 10 years before the predicted year, pooled or split by season
  (June to September and the rest); the interval is the forecast plus the
  10th and 90th residual percentiles (`conformal_interval`). The rule is
  chosen on 2010-2019 only: each year is covered with residuals from the
  years before it, and the rule whose mean coverage is closest to 80% wins
  (ties: narrower). The chosen rule, fed residuals up to 2019, is then
  applied once to the 2020-2024 test. Intervals may be shown only if test
  coverage is within 75-85% (the plan's interval gate); otherwise they stay
  hidden. The test years were already seen once for v1 intervals (65%), so
  this is a second look for intervals only and is reported as such. The
  release file stays unchanged; results go to
  `models/registry/M05/v1.intervals.json`.

- **D96 — English text Ask page searches in the browser (8 Nov 2026).**
  Split T261 from T182 and pull only its English text part into P1, because
  C3 (F046 cited Ask, text, English) needs a page people can use. Voice, the
  Kannada, Malayalam and Hindi interfaces and the rest of T182 stay outside
  the MVP (A3). The page opens at `?page=ask`. It loads the public corpus
  from `/data/ask/latest.json`, which names `/data/ask/<release>.json`; the
  file is the canonical chunk list whose SHA-256 is the release ID served by
  the Worker (D95), so the browser rejects altered bytes. Search is BM25 in
  TypeScript with the same as-of, state, expiry, per-document and
  near-duplicate rules as `retrieve.py` (plan T179 step 3: browser lexical
  search first). The top five chunk IDs go to `POST /api/v1/ask`; when the
  Worker is unavailable or its reply does not match, the page shows the
  same local search results, labelled as such. Answers and citation cards
  show the document path, heading, commit time and evidence age. No corpus
  is seeded in `web/public`; the deploy step publishes it (H05).

- **D95 — Ask route reads chunks from a trusted D1 release (8 Nov 2026).**
  Split T260 from T180. `POST /api/v1/ask` takes `query`, `language`,
  `place_id`, `as_of` and up to five `chunk_ids` (plan section 4). The
  Worker never accepts evidence text from the client: it reads the chosen IDs
  from the current release in D1 tables `ask_chunks` and `ask_current`,
  rechecks each chunk's SHA-256, and drops chunks not yet committed at
  `as_of`, expired, or outside the place's state. Unknown IDs are refused.
  `python -m atlas.rag.manifest` exports the committed index as a release
  (ID = SHA-256 of the manifest) and a SQL load file that inserts the new
  rows, then moves the pointer, then deletes old rows, so a half-loaded
  release is never served. A committed manifest file was rejected: chunk
  times are commit times, so it would go stale with every documentation
  commit, and CI's shallow checkout cannot rebuild an older pinned commit.
  Generation, its quota counters and the D1 load stay off until H05 and the
  free/no-card probe pass; until then every answer is extractive. Other
  languages get the same quoted English excerpts (T180 step 3).

- **D94 — Accuracy page uses the approved-release contract (8 Nov 2026).**
  Split T259 from T046. The page reads `/data/ka/accuracy/latest.json`, a
  pointer that must say `approved` and name `/data/ka/accuracy/<sha256>.json`;
  the bytes must match that digest. Without a release it says none exists.
  Null values render as "Unavailable", never 0. The page opens at
  `?page=accuracy` instead of adding a router dependency. The browser fixture
  is generated from the committed records by `atlas.models.accuracy`, and a
  test keeps them identical. No production accuracy release is seeded; H11
  approves publication.

- **D93 — M05 model card states its deviations (8 Nov 2026).** Split T258
  from T046. The card follows the plan's M05 fields and records where the
  release differs: district units instead of taluks (no taluk polygons), no
  temperature feature, no reported rolling-origin results, and a hindcast
  instead of operational timing. Numbers come only from cited sources.

- **D92 — Prepare T046 locally; the release stays blocked (8 Nov 2026).**
  Split T257 from T046. T046 itself depends on T045 (H05/H06) and T041
  (S18), and needs H11. This child builds the accuracy rows for C1, C2 and
  M06 from committed records and a generated checklist of every T046 and A3
  check. A check passes only with evidence: the C2 model card is reported
  missing because only the evaluation report exists, and C3 fails while
  `reports/rag.md` reports a failed gate. Unavailable values stay null.

- **D91 — Case studies cover the actual cores, including blocked ones (8 Nov 2026).**
  Split T256 from T225. Amended T225 names M02, M01 and Ask, but D17/D29 made
  the cores M07 (C1 fallback), M05 (C2) and Ask (C3). Write those three
  studies. M07 has no model, so its study reports the data gate and why it
  stops; Ask's reports the failed English gate. A test requires the plan
  outline order and that every standalone number appears in a cited
  committed source; runtimes that were never recorded are stated as such.
  H14 (owner rewrites the summary) stays pending.

- **D90 — Compute numeric answers from frozen snapshots; show all five results (8 Nov 2026).**
  Split T255 from T180 after T254. The plan's fallback shows exact computed
  table values with citations, so recognised numeric templates (latest rain,
  active alerts, model improvement) are answered by DuckDB queries over the
  committed real samples listed in `configs/rag.yaml`. The gold code reads
  the same files with plain Python, so the two paths are independent. No
  published snapshot exists yet; these samples stand in and are labelled.
  The extractive fallback shows every retrieved chunk (the plan's top five)
  instead of three. Ranking changes are judged on development questions
  only. Paraphrase misses (Q02, Q23, Q26) remain until the e5 rerank; the
  owner's delegation is not treated as approval for its model download.

- **D89 — English Ask gold set with deferred out-of-phase cases (8 Nov 2026).**
  Split T254 from T181 after T252/T253. Keep all 50 plan questions and the
  10 numeric templates (60 English cases). A question is in the MVP English
  subset only when a committed indexed document contains a verifiable support
  phrase; 15 questions about sources or model cards outside the Karnataka MVP
  stay deferred with reasons. Add `docs/methods.md`, a plan-derived methods
  page, to the corpus; it was written with the question list known, so the
  report states that holdout retrieval is not independent. Numeric gold is
  recomputed from committed real files (S02 ERA5 sample, S09 CAP sample,
  approved M05 release); seven numeric cases require refusal because their
  data is blocked or unpublished. Extractive correctness means the cited
  chunk contains the gold fact. No translation is reviewed, so non-English
  generation stays disabled.

- **D88 — Build the Ask answer contract before any AI binding (8 Nov 2026).**
  Split T253 from T180 after T229/T252. Workers AI needs H05 and the
  free/no-card probe, so this child adds only pure Worker logic: the plan's
  fixed system prompt, evidence serialized as JSON data, the 100/day,
  6/minute and 8000-neuron quotas, and checks that accept generated JSON only
  when every citation names a retrieved chunk and every number appears in
  cited text. Any other case returns quoted excerpts with citations. No
  route, AI binding or account is added; the trusted chunk manifest and the
  `/api/v1/ask` route are a later child. The owner delegated reversible
  choices on 8 Nov; the e5 model download stays deferred because lexical
  recall already passes and drive space is limited.

- **D87 — Build the MVP Ask corpus and lexical retrieval first (8 Nov 2026).**
  Split T252 from T179. A3/A8 move English Ask (C3) into P1; the plan's T179
  dependency on T166 (Delhi gate) belongs to its full multi-state scope, so
  this child indexes only committed project documents listed in
  `configs/rag.yaml`. A document's `available_at` is the commit time of the
  indexed content, so an as-of query never sees a later edit. Words and
  punctuation stand in for e5 tokens until the pinned tokenizer is installed.
  BM25 over SQLite FTS5 runs first; the e5 embedding rerank needs the
  deep-learning lock and a model download, which wait for owner approval.
  At most two chunks come from one document, so long logs cannot crowd out
  a specific report. Plan questions Q41-Q50 are not used for development.

- **D86 — Relay hosted checkpoints by manual dispatch only (8 Nov 2026).**
  Split T251 from T043 after T249/T250. Add `.github/workflows/feeds.yml`
  with `workflow_dispatch` only, one serial concurrency group, a three-minute
  job limit and read-only `contents`/`actions` scopes. A run continues its
  immediate verified predecessor through the pinned download action (by
  artifact ID, extraction off) and the T250 importer, then uploads the
  committed bundle for its successor. A new chain needs the explicit manual
  `bootstrap` input; a scheduled run can never bootstrap. Capture stays out
  of the hosted job until the Worker capability gate (H05) passes. The
  schedule stays off: GitHub cancels a pending run in a busy concurrency
  group, and that cancelled run would break the T249 chain. The 20 GB
  free-space reserve is unchanged and fails closed on the hosted runner.

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
