# T229: hot-data Worker (child of T042)

**Deployed 12 Nov 2026 (D180):** `https://monsoon-atlas-hot.monsoon-atlas.workers.dev`
with D1 `monsoon-atlas-hot` (schema from `worker/schema.sql`) and the server-side
`ATLAS_INGEST_HMAC_KEY` secret. The owner confirmed the free plan with no card.
`scripts/deploy_worker.py` builds the git-ignored `worker/wrangler.deploy.toml`
from `.env` (database ID, workers.dev on, `CAPABILITY_GATE = "verified_free_no_card"`)
and deploys with the pinned Wrangler; the committed `wrangler.toml` stays disabled
(no database ID, workers.dev off, gate blocked). The store is empty: GET current
returns 503 with `fallback: static_daily`, and unsigned uploads get 401.
Feeds run from `.github/workflows/feeds.yml` (T043, D182, D183).

**Export (T044, D184):** signed, read-only `POST /internal/export` with JSON
`{"after_ms": -1, "after_id": ""}` returns stored rows after that cursor in
`(as_of_ms, id)` order: exact gzip payload (base64), stored SHA-256, at most 200
rows or about 2.8 MB of payload per page, plus `capacity` (reserved bytes, D1
`size_after`, the 400 MB cap). It writes nothing. No purge or delete exists.
An unavailable capability/binding returns HTTP 503 with `fallback: static_daily`;
it does not advertise a working current feed. The browser retains the dated
approved static snapshot or shows the unavailable view.

T233 adds `POST /internal/feed-check` using the same HMAC message and headers,
with a bounded `application/json` body containing only `state` and `source_id`.
Only KA S01/S09 are allowed. The server supplies the admission clock; a client
cannot supply a bucket or timestamp in the JSON body. An atomic D1 trigger
requires six elapsed hours for S01 and fifteen elapsed minutes for S09, so a
late job cannot burst across a UTC bucket or midnight boundary. Duplicate jobs
receive `admitted: false`; only `admitted: true` authorizes the future producer
to call a provider. A lost response consumes its slot. Missing capability,
authentication, database, storage or write budget never authorizes a call.

Each successful admission reserves 20 row/index writes and 16 KiB within the
same shared caps as snapshots. The 24-hour simulation includes duplicate jobs
with no runner memory and a late start, and permits exactly 4 weather and 96
alert admissions. Actual D1 concurrency/cap tests run in Ubuntu CI. This is an
offline protocol implementation; collection and cron activation remain separate
T043 work. The new table/index/triggers are part of the fresh
bootstrap schema; no existing remote database was migrated or created.

The owned transport accepts `POST /internal/ingest` with `application/gzip`:
gzip-compressed UTF-8 JSON `{source_id, snapshot}`. The snapshot uses the shared
browser validator in `web/src/data.ts`; only KA S01 weather and S09 official CAP
records are accepted. Sources must already be enabled and publicly reusable.
The snapshot contains exactly its own successful health entry, no unrelated
places/facilities, original source clocks and a cutoff not in the future.
An S09 row without a polygon retains its actual area text and an explicit
geometry-unavailable note (T230). Both coordinates are null; it remains in the
record list, report and ticker without a fabricated marker or distance. The
producer must preserve it rather than silently omit the warning.

The server requires `ATLAS_INGEST_HMAC_KEY` (at least 32 characters). Its value
is a separate pipeline secret, never a browser variable or an account API token.
`X-Atlas-Timestamp` is Unix seconds; `X-Atlas-Signature` is lowercase hex HMAC
SHA256 of this UTF-8 message, without a final newline:

```text
timestamp\nPOST\n/internal/ingest\nsha256(exact compressed request body)
```

Five minutes is the maximum past/future clock skew. Verification uses native
Web Crypto. Query parameters on uploads are rejected. Compressed, decompressed,
canonical and combined response sizes are each bounded to 1 MiB. Unknown input
fields are discarded before canonical JSON is hashed/compressed/stored. No source
credential, supplied instruction or arbitrary remote URL becomes code authority.

Canonical SHA256 provides idempotency. Stored integrity is checked against the
original decompressed canonical bytes before schema normalization, including
changes to otherwise ignored fields. A new optional field cannot rewrite the
identity of an older stored blob. Reads validate without recompressing it.
An unchanged upload consumes no new write
reservation. A conflicting snapshot at the same source/state/millisecond cutoff
returns 409, preserving the prior head; the original as-of string remains in the
payload. Newer successful cutoffs advance the head atomically. Stored corruption
returns 503. `GET /api/v1/current?state=ka[&source=S01|S09]` returns each available
source's normalized snapshot, stored `sha256` and `wire_sha256`. The wire digest
covers UTF-8 `JSON.stringify({source_id, snapshot})` using the returned snapshot.
An older stored snapshot can retain a different `sha256` when the parser adds an
optional field. The browser verifies the wire digest before normalizing the snapshot
and uses the stored digest for source identity. Older GET replies without
`wire_sha256` use `sha256` for both checks.
`age_seconds` measures time since the actual successful source fetch.
`snapshot_age_seconds` separately measures time since the report cutoff.
An empty store is unavailable, not evidence of no hazards. S01 and S09 remain
separate source entries, not a claim of complete source coverage.

The SQLite transaction guards 400,000,000 bytes and 10,000 reserved D1 row/index
writes per UTC day. Each new snapshot reserves its compressed length plus 64 KiB
for table/index/page growth and 20 writes, including head/counter changes. The
storage basis is the greater of the existing reservation and D1's actual observed
`meta.size_after`. This intentionally stops before filling a free 500 MB database.
The trigger and D1 batch make cap failures roll back the snapshot and head changes.
No purge/delete endpoint exists. T044 must prove archive durability before adding
deletion. Public read budgets and export are later tasks.

Wrangler is exactly 4.157.0 (Node 22+, MIT OR Apache-2.0), bringing Miniflare
5.20261103.0-beta and workerd 1.20261103.1. TypeScript is exactly 7.0.2. npm lock
integrities are committed. Windows 10 is outside Wrangler's official OS support;
local checks use Node's type erasure and SQLite. Actual Worker/D1 checks run on
Ubuntu 24.04 CI with the bundled Miniflare, no account, remote binding or secret.
Local npm/temp caches remain on D via `scripts/worker.ps1`. Runtime tests use
ephemeral keys and genuine S01/S09 projections, including corrupt copies.
The harness uses Miniflare 5's exported v4-options converter, verified against
the installed options schema without starting workerd on Windows. It strips
full-line SQL comments before preparing schema statements because the pinned
workerd rejects a comment-only tail. Ubuntu CI exercises the actual engine.

Owner setup remains separate from implementation. Use a scoped Cloudflare API
token for Workers/D1 and later Pages; keep it in ignored `.env` or Actions secrets,
never in chat or the browser bundle. The agent must not create it or accept terms.
Hugging Face H06 needs a write token scoped to the eventual archive repository.
Account tokens do not approve a public deployment; H11 still applies.

Primary references (verified 6 Nov 2026):

- [Wrangler installation and supported OS](https://developers.cloudflare.com/workers/wrangler/install-and-update/)
- [Workers signing example](https://developers.cloudflare.com/workers/examples/signing-requests/)
- [D1 API and atomic batch](https://developers.cloudflare.com/d1/worker-api/)
- [D1 result metadata](https://developers.cloudflare.com/d1/worker-api/return-object/)
- [D1 limits](https://developers.cloudflare.com/d1/platform/limits/)
- [Miniflare D1](https://developers.cloudflare.com/workers/testing/miniflare/storage/d1/)
- [Workers roles](https://developers.cloudflare.com/workers/authorization/)
- [Token permissions](https://developers.cloudflare.com/fundamentals/api/reference/permissions/)
- [HF token scopes](https://huggingface.co/docs/hub/security-tokens)
