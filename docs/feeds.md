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

This reads retained CAP evidence without provider calls. Every input hash/path
is checked; 304 checks retain the original content's first retrieval clock.
Only Actual/Public messages with issue times at or before the cutoff enter
control handling. Exact sender/identifier/sent references apply even for
header-only Updates and Cancels; these contribute no invented warning rows.
Ack/Error and non-public controls cannot remove a
warning. Expired messages stay in raw history and leave the current projection.
Malformed documents retain dated last-good warnings and explicitly partial
health; their downloads cannot refresh the successful validation clock.

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
bounded scheduling/upload integration and active-page refresh, with H05/H11
before cloud/public activation.

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

This runner is local S09 preparation. S01 preparation, authenticated cloud
admission/upload, durable cloud restoration, scheduling and active-page polling
remain in T043. No credential, account, recurring job or public release is used.
