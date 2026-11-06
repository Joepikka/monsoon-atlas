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
