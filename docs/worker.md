# T229: local hot-data Worker (child of T042)

Full T042 is pending H05 and an actual free/no-card capability probe. The owner
has signed into Cloudflare in regular Chrome, but no cloud token, remote D1
binding or service probe is configured here. No Worker or database was deployed.
`wrangler.toml` disables workers.dev and keeps `CAPABILITY_GATE = "blocked"`.
An unavailable capability/binding returns HTTP 503 with `fallback: static_daily`;
it does not advertise a working current feed. The future browser integration
must retain the dated approved static snapshot, or its existing unavailable view.

The owned transport accepts `POST /internal/ingest` with `application/gzip`:
gzip-compressed UTF-8 JSON `{source_id, snapshot}`. The snapshot uses the shared
browser validator in `web/src/data.ts`; only KA S01 weather and S09 official CAP
records are accepted. Sources must already be enabled and publicly reusable.
The snapshot contains exactly its own successful health entry, no unrelated
places/facilities, original source clocks and a cutoff not in the future.
An S09 row without a verified map location cannot be given an invented point;
the producer must fail/retain last-good rather than silently omit that warning.
T043 must handle that source-coverage limit explicitly before enabling polling.

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

Canonical SHA256 provides idempotency. An unchanged upload consumes no new write
reservation. A conflicting snapshot at the same source/state/millisecond cutoff
returns 409, preserving the prior head; the original as-of string remains in the
payload. Newer successful cutoffs advance the head atomically. Stored corruption
returns 503. `GET /api/v1/current?state=ka[&source=S01|S09]` returns each available
source's canonical snapshot, SHA256 and age in seconds from its actual cutoff.
An empty store is unavailable, not evidence of no hazards. S01 and S09 remain
separate source entries, not a claim of complete source coverage.

The SQLite transaction guards 400,000,000 bytes and 10,000 reserved D1 row/index
writes per UTC day. Each new snapshot reserves its compressed length plus 64 KiB
for table/index/page growth and 20 writes, including head/counter changes. The
storage basis is the greater of the existing reservation and D1's actual observed
`meta.size_after`. This intentionally stops before filling a free 500 MB database.
The trigger and D1 batch make cap failures roll back the snapshot and head changes.
No purge/delete endpoint exists. T044 must prove archive durability before adding
deletion. Public read budgets, export and polling are later tasks.

Wrangler is exactly 4.157.0 (Node 22+, MIT OR Apache-2.0), bringing Miniflare
5.20261103.0-beta and workerd 1.20261103.1. TypeScript is exactly 7.0.2. npm lock
integrities are committed. Windows 10 is outside Wrangler's official OS support;
local checks use Node's type erasure and SQLite. Actual Worker/D1 checks run on
Ubuntu 24.04 CI with the bundled Miniflare, no account, remote binding or secret.
Local npm/temp caches remain on D via `scripts/worker.ps1`. Runtime tests use
ephemeral keys and genuine S01/S09 projections, including corrupt copies.

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
