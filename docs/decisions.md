# Decisions log

## Continuation review (5 Nov 2026)

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
