# Local CAP capture (T234)

Run one bounded, public-source-only capture from the repository:

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 --max-documents 30
```

The parent kills and reaps its HTTP-only child after 120 seconds. Process startup
and cleanup add overhead; this is not certification of a three-minute cloud job.
The child must not spawn descendants. Maximum admission is 30 CAP documents,
with one second before every HTTP attempt, a shared request budget, conditional
GET and the existing host/TLS/byte protections. Polygon requests are omitted.

`.cache/feeds/control.sqlite` holds local elapsed-cadence admission (15 minutes
for S09), provider Retry-After cooldown and per-document work. Duplicate local
processes share that file. Keep the whole directory, including raw evidence and
its ledger: copying the SQLite file alone is insufficient. Do not delete it to
bypass throttling. A lost or aborted run consumes its admission slot. This local
guard cannot replace the T233 D1 guard across independent cloud runners.
Retry-After is saved from retryable response headers even on the final allowed
attempt, before reading the body. It does not depend on another retry remaining.

New/changed item fingerprints and oldest attempts share bounded admission;
failures rotate rather than monopolizing the queue. Linked CAPs become eligible
for revalidation after 15 minutes, even with an unchanged RSS item. This age is
an engineering revisit target, not a provider freshness promise. RSS 304 does
not check linked documents. A successful CAP 304 advances only that document's
check clock; content origin, source issue time and original bytes remain retained.
Checkpoints advance only after header/content validation. Malformed downloaded
evidence stays in the raw ledger while the last good checkpoint survives.

Every result is **partial**. The all-India feed is a limited rolling window;
bounded work, failures and CAP-only text matching cannot certify complete
Karnataka coverage or absence of hazards. Disappearing items remain stored and
do not imply cancellation. Header-only control messages retain their actual
identity/references without fabricated warning fields. Their eventual application
to retained warnings belongs to the normalization/producer task.

No reviewed snapshot, browser polling, cloud upload, resource or recurring
workflow is created. Full T043 remains pending producer/projection, durable
runner restoration/backoff integration, bounded workflow tests and H05.

## Local snapshot preparation (T235)

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 prepare
```

This reads retained CAP evidence without provider calls. If S09 is disabled,
preparation stops before reading the ledger. Every input hash/path is checked.
A 304 check retains the original content's first retrieval clock.
Only Actual/Public messages with issue times at or before the cutoff enter
control handling. Exact sender/identifier/sent references apply even for
header-only Updates and Cancels; these contribute no invented warning rows.
Ack/Error and non-public controls cannot remove a
warning. Expired messages stay in raw history and leave the current projection.
Malformed documents retain dated last-good warnings and explicitly partial
health; their downloads cannot refresh the successful validation clock.

The `s09-prepared-v2` projection uses the selected CAP info block's original
headline as warning text. It falls back to that block's description and then its
event. The adapter selects the first English info block when present and the
first info block otherwise. Existing v1 prepared files remain immutable.

`.cache/feeds/prepared/` contains content-addressed envelopes and input manifests.
Their local `prepared.json` pointer is **prepared_only**, without publication
approval. Payload and input hashes are distinct and cover their exact bytes.
Both raw and compressed transport sizes must fit one MiB. The pointer moves
atomically after the immutable files exist; concurrent/older preparations cannot
roll it back, and different bytes at the same cutoff conflict. Corruption or a
failed preparation preserves the previous pointer. No files are purged.
Preparation reads the ledger strictly. A damaged entry, even one the collector's
tolerant reader can skip, stops preparation. Known input identities and their
content clocks cannot disappear or move between later preparations; deleting or
retargeting a completed control entry cannot resurrect its warning. Restore
damaged evidence from retained originals rather than bypassing these checks.
The report cutoff stays separate from the actual preparation time stored in
`published_at`; repeated identical preparation preserves that first creation
time and byte identity. This field does not grant public publication approval.

All prepared S09 results remain partial, including empty/expired-state results.
The Worker validator can carry partial health with its actual validation clock;
it does not relabel that source available. Python-produced bytes are checked
against the actual Worker validator in the optional local integration test.
Preparation performs no upload or public release. Full T043 still needs the
bounded scheduling/upload integration, with H05/H11 before cloud/public
activation.

## One bounded local refresh (T236)

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 refresh --max-documents 30
```

The parent gives the entire capture/preparation child 150 seconds. Neither phase
launches another process. Completed raw/checkpoint writes and atomic prepared
files survive a deadline. Startup/cleanup overhead is additional; this is not
certification of a three-minute GitHub job.

The JSON result reports both collection and preparation. A not-due/deferred or
failed provider check can still prepare already retained evidence, including a
completed control captured before an interruption. Its actual validation clock
stays dated; preparing again does not make the source newly validated. Identical
replay at one cutoff keeps its byte identity. Missing/corrupt evidence fails
preparation and retains the previous head; absence of evidence cannot generate
a fake empty feed. The public command exits unsuccessfully on failed preparation
or a deadline.
Recoverable capture I/O failures are retained in `collection` diagnostics while
usable dated evidence is still prepared. Explicit source-disable and invalid
input errors stop the command before preparation.

This runner is local S09 preparation. Authenticated cloud admission/upload,
durable cloud restoration and scheduling remain in T043. No credential,
account, recurring job or public release is used.

## Paired local weather capture (T237)

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 weather
```

The verified profile queries Bengaluru (12.97,77.59) using named model
`ecmwf_ifs025`; the source returns grid centre (13.0,77.5). This is one model grid
point, with partial coverage. It establishes no statewide weather coverage.

Capture retains metadata-before, forecast and metadata-after together, including
their exact hashes and HTTP validation clocks. A changed model run, pre-settling
forecast response, unexpected grid or absence of a quality-passed future
temperature cannot replace the validated-pair pointer. Waiting after an early
capture does not certify its model vintage. Raw body bytes and every completed
attempt receipt remain stored under `.cache/feeds/weather/`; later revalidation
does not overwrite original receipts. The pointer also rejects older model runs
and regressing capture clocks. Offline weather preparation is described below.
Each newly completed receipt is saved before the previous head is checked. If
that head or its old receipt is damaged, advancement fails and the result still
includes the new immutable receipt's path/hash; the grouping is not lost.

Shared local admission allows at most four six-hour checks per UTC day. Each
weather run admits at most five HTTP attempts, including retries/redirects, so
the initial 20/source/day weather cap is respected. Every underlying attempt
waits five seconds; a normal metadata/forecast/metadata capture uses three calls.
Retry-After is durable and source-specific. A 120-second parent deadline bounds
the child, with startup/cleanup overhead additional. Both local source producers
check enabled-source flags before any provider call. No account, upload,
projection, recurring job or deployment is created.

## Offline weather preparation (T238)

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 weather-prepare
```

This command reads `.cache/feeds/weather/pairs/` and `weather/raw/` without
network requests. `--root` accepts the common feed root. Only complete validated
receipts for the verified Bengaluru `ecmwf_ifs025` request can supply the single
temperature record. Receipt completion and all three HTTP clocks must precede
the report cutoff. The newest eligible model initialization, then newest capture,
supplies the first quality-passed finite temperature at or after the cutoff.
The original value, unit and returned grid centre (13.0,77.5) are preserved;
this is a model-grid forecast, with partial single-point coverage.

For each model/run/forecast-content cohort, `fetched_at` remains its earliest
qualified forecast HTTP retrieval and `available_at` waits for its earliest
complete validated receipt. Revalidation advances only the selected cohort's
actual `last_success_at`; preparing again cannot imply a provider check.
Settling is verified at retrieval, so waiting cannot certify an early attempt.

The shared immutable writer stores prepared-only envelopes and input manifests
in `weather/prepared/`, with the same one-MiB canonical/compressed body bounds,
quota, atomic monotonic pointer, same-cutoff conflicts and idempotent replay as
CAP preparation. `published_at` is the actual local creation time. Receipt/raw
corruption, missing known evidence, disabled source, or no eligible future row
preserves the previous output. A missing latest-pair pointer may recover a fully
qualified archived receipt; a present damaged pointer stops preparation.
Keep all receipts and raw bytes. Nothing is purged, uploaded, scheduled,
approved for publication or activated by this command.

## Signed local Worker upload (T239)

With a local Worker already running and `ATLAS_INGEST_HMAC_KEY` set in the
environment to the same value (at least 32 characters), run:

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 upload-local --source S09 --origin http://127.0.0.1:8787
```

Choose `S01` for `weather/prepared/` or `S09` for `prepared/`; `--root` accepts
the common feed root. The explicit origin must be `http://127.0.0.1:<port>`
without a trailing slash, path, query, fragment or credentials. Environment
proxies and redirects are disabled. The environment key is never a CLI argument.

The sender verifies the prepared-only pointer, immutable payload and streamed
input-manifest hash, then signs a deterministic gzip of the exact prepared
bytes. One HTTP-only child has a 15-second deadline, finite request timeouts,
one request and a 4096-byte acknowledgement limit. Startup/cleanup add overhead.
Success reports the Worker's normalized `snapshot_id` separately from the local
`prepared_sha256`. A repeat sends identical bytes for Worker idempotency.
Failures preserve preparation and report bounded diagnostics without response
bodies. This local acknowledgement grants no static publication approval.
Remote destinations, durable cloud restoration and scheduled admission remain
T043 work behind the existing activation gates.

## Active Karnataka view (T240)

The normal Karnataka view starts checking `/api/v1/current` after it verifies
an approved daily release. It checks S09 every 15 minutes and S01 every six
hours, with S09 first when both are due. One request runs at a time with a
five-second deadline and a one-MiB response limit. A started check uses its
cadence slot even if it fails or the tab becomes hidden. Returning to the tab
checks due sources. Refreshing the daily release keeps the source cadence.

The map, list and ticker use the verified active source data where available.
Each source shows its cutoff, last successful check and coverage separately.
A partial S09 result can contain zero records while coverage remains limited.
S01 coverage is confined to the reported model grid points. On failure or
when the active source predates the daily cutoff or last successful daily
check, the view uses that source's dated daily data where available. The
fallback label also appears when the daily release contains no rows for the
source. Previously accepted source clocks guard against older or conflicting
responses across failures.

The daily release still provides the cutoff and verified hash for Place Lens,
frozen links and print. Frozen, invalid shared and unreleased views skip the
active checks. Cloud routing, remote upload, durable restoration, archiving
and public activation stay behind their existing gates.

## Local checkpoint and recovery (T241)

1. Stop local capture, refresh and preparation processes. Keep the feed tree,
   bundle and their parent directories idle until each command finishes. Run
   one checkpoint operation at a time.
2. Save to a new directory with an existing parent, outside the feed tree.

   ```powershell
   rtk proxy powershell -NoProfile -File scripts/feeds.ps1 checkpoint-save --bundle .cache/feeds-checkpoint-01
   ```

   Record the reported `manifest_sha256` separately from the bundle. Keep both
   for recovery.
3. When recovery is needed, hold any remaining feed tree aside so the original
   path is absent. Set `$savedManifestSha256` to the separately recorded digest
   and restore to that original path.

   ```powershell
   rtk proxy powershell -NoProfile -File scripts/feeds.ps1 checkpoint-restore --bundle .cache/feeds-checkpoint-01 --expected-sha256 $savedManifestSha256
   ```

Both commands default to `.cache/feeds`. Use `--root` for a different local feed
directory and supply that same canonical absolute location on restore. The
versioned `manifest.json` binds that location and lists each member of `files/`
by relative path, byte length and SHA-256. The separately saved digest is the
integrity check for the manifest and its file list. The archive quota counts
repository data, the current input tree and the incoming copy. Sibling bundles
count toward that quota when they sit within repository data. Save and restore
leave the configured physical free-space reserve on the destination drive.

The bundle requires the shared `control.sqlite` and retains exact SQLite
controls, raw S09 and S01 objects and ledgers,
partial and validated weather receipts, the latest pair pointer, and immutable
prepared history and pointers. Unrelated files, credentials, configuration and
interrupted temporary writes are outside the inventory. The commands refuse
links, reparse points and SQLite sidecars in the inspected layout. A damaged
ledger or missing referenced artifact causes verification to fail.
CAP preparation and control clocks must match their retained ledger events.

Restore copies to staging beside the missing destination, checks the manifest,
bytes, SQLite integrity and references there, then publishes with a single
directory rename. The bundle remains available for another recovery. Restored
collectors and preparers use the retained source bytes, admission, cooldown and
clocks at the original path. The checkpoint commands run entirely offline.

## Capture with local Worker admission (T242)

With the trusted local Worker running and its `ATLAS_INGEST_HMAC_KEY` available
in the command environment, run one capture for `S09` or `S01`.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 capture-admitted --source S09 --origin http://127.0.0.1:8787
```

The command checks source enablement and sends one signed request to
`/internal/feed-check`. A matching HTTP 201 acknowledgement grants admission.
A matching HTTP 200 denial returns `not_due` at the admission stage. Errors,
wrong-source replies and timeouts fail closed before the collector starts.
Use an explicit `http://127.0.0.1:<port>` origin. The signed transport disables
environment proxies and redirects and bounds successful replies to 4096 bytes.

After admission the existing collector still applies its SQLite cadence,
Retry-After cooldown and quota. Its result uses `stage: capture`. A lost Worker
reply or a later local deferral can consume the Worker slot. The command runs
the claim and capture in one child with a 150-second parent deadline. Startup
and cleanup add overhead. Completed capture evidence remains in `--root`,
which defaults to `.cache/feeds`. Use `--max-documents` to bound S09 work.
Preparation, upload, durable runner persistence and scheduling are separate
steps. The cloud capability and release gates apply before activation.

## Runner checkpoint store (T243)

Use a dedicated local directory that survives cleanup of the feed workspace.
Its parent must exist, and the store and feed root must be disjoint. Stop
capture and preparation while saving or restoring. Initialize the store with
one explicit save from the intended feed root.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-save --store .cache/runner-checkpoints --expected-head empty
```

On the next run, when the original feed path is absent, restore from that
same store. Keep the reported `manifest_sha256` in the runner state.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-restore --store .cache/runner-checkpoints
```

After the run, save with `--expected-head $restoredManifestSha256`, using the
digest that run actually restored. A stale value fails before copying. Both
commands default to `.cache/feeds`; `--root` selects the same canonical
absolute feed path used at initialization.

The trusted `catalog.sqlite` serializes store operations. A missing catalogue
requires an empty directory for bootstrap. Save verifies and installs an
immutable bundle under `objects/<manifest_sha256>` before committing the
current digest. It preserves older generations. A process interruption
before the catalogue commits can leave a complete unreferenced bundle. A
retry verifies its bytes before using it. After interruption, restore selects
the last committed digest and verifies it before creating the feed directory.
The quota counts repository data, the feed tree during save, the whole store
and the incoming copy. It includes pending catalogue pages and the temporary
copy used to verify an unchanged save. Physical free-space checks apply on
the destination drive.

The store is a local trust boundary. Keep its catalogue and objects together
on a local filesystem, with access restricted to the operator or runner.
Recovery depends on the catalogue and manifest agreeing. Hosted runner
persistence, cross-path recovery and recurring activation remain later work.

## Bounded runner cycle (T244)

With a committed runner checkpoint, an absent original feed root and a trusted
loopback Worker, run one source through restore, admission, capture and save.
Use the Worker's existing local signing key in the command environment.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-cycle --store .cache/runner-checkpoints --source S09 --origin http://127.0.0.1:8787
```

One child has a 150-second deadline for all three phases. `restored_sha256`
identifies the starting generation. `manifest_sha256` identifies the verified
generation returned after save, or the restored generation if admission
stopped capture. Handled capture failures can still save valid evidence and
provider cooldown. A failed checkpoint reports the starting digest and the
capture result so the working tree can be inspected.

The command leaves the working root in place. After a successful save, hold
it aside before the next cycle so restore can use the original absent path.
After a timeout, keep the root in place and inspect the catalogue and working
tree before resuming. SQLite may have committed just before the child was
stopped. Retain any newer capture evidence and cooldown by sealing the
validated working tree against the current head before another capture.

## Prepare and upload from a runner cycle (T245)

Add `--upload-local` to prepare a successful capture at the current UTC cutoff.
The cycle commits the checkpoint before sending the prepared snapshot from its
immutable generation to the same loopback Worker.

```powershell
rtk proxy powershell -NoProfile -File scripts/feeds.ps1 runner-cycle --store .cache/runner-checkpoints --source S09 --origin http://127.0.0.1:8787 --upload-local
```

The 150-second deadline covers preparation and upload too. A preparation failure
can still save valid capture evidence and cadence. A failed checkpoint stops
before upload. An upload failure reports the saved digest, so the next cycle can
restore the committed snapshot. When the next capture is `not_due`, the option
resends a retained prepared head if present, with its original cutoff and exact
bytes. The Worker reports `stored` or `unchanged` at the upload stage. Recurring
scheduling and hosted persistence remain separate steps.
