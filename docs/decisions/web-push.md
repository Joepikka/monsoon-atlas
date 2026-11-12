# Background Web Push: feasibility and privacy gate (T184, D150)

Status: **disabled** under `privacy_mode=no_personal_data`. Feature F051 in the plan's feature
catalogue: **conditional stretch**. The repository holds no machine-readable feature catalogue
(only `docs/plan.pdf`), so this document is the record of that status.

## The conflict

Background Web Push lets a server wake a browser that has the page closed. To do that the server
must keep, for every subscribed browser, the push **endpoint** (a URL that identifies that browser
profile at the browser vendor's push service) and the **keys** (`p256dh` and `auth`) used to
encrypt each message. Together they are a persistent identifier of a person's device. They are
pseudonymous personal data. The project rule (`AGENTS.md`, Privacy) says: no personal data, no
accounts, no subscriber databases. Storing endpoints and keys is a subscriber database, so
background push cannot be switched on without the owner changing that rule. The agent cannot
resolve this conflict; only the owner can.

## What is built now

| Part | State |
|---|---|
| Local in-app watch notifications | Enabled. `web/src/components/Watches.tsx` keeps watches in the browser's IndexedDB and shows matches while the page is open. Nothing is sent to a server. |
| Capability detection | `web/src/push.ts` reports whether the browser has a service worker, the Push API and notifications, and always returns `enabled: false` with the reason `disabled: privacy_mode=no_personal_data`. |
| Server registration | `worker/src/push.ts` answers every request to `/api/v1/push/subscription` with 403 and the same reason, before the capability gate. It never reads the request body. |
| Subscription | Nothing creates one: no code calls the browser's push subscribe method, asks for notification permission or registers a service worker. `tests/test_push_policy.py` scans for it. |

## Conditional design (not built; only if the owner relaxes the policy)

Do not enable any of this without a written policy revision by the owner (a new decision in
`docs/decisions.md`, an edit of the Privacy rule in `AGENTS.md`, and a changed `privacy_mode`).

1. **Consent.** Off by default. The person turns it on per device, in the page, after a plain
   statement of what is stored (endpoint, keys, chosen place IDs, creation time), why, for how
   long, and how to delete it. The browser's own permission prompt comes after that, never before.
   Declining or ignoring it keeps in-app notifications working.
2. **Private, encrypted subscriptions.** Endpoint and keys are encrypted (AES-GCM, with a key held
   as a Worker secret, never in code or logs) before they are written to a private store that is
   not readable from the public site. Only place IDs and an alert reference are stored beside
   them: no name, no email, no coordinates, no precise location, no analytics identifier.
3. **30-day expiry.** Every record carries an expiry 30 days after creation or the last explicit
   renewal by the person. A scheduled job deletes expired records; a push service answer of
   "gone" deletes the record at once.
4. **Delete endpoint.** The person can delete their subscription from the page at any time. The
   request proves possession by presenting the endpoint, which the Worker matches to the stored
   record by keyed hash. No account is needed.
5. **Batch send.** One send job per alert revision, after the brief's deduplication and
   supersession rules (D149), sent in batches sized to the Worker request limits in force on the
   free plan at that time (to be checked against Cloudflare's documentation then). A cancelled or
   expired alert is never sent. Messages carry the alert title and its source link, not model
   output. No sound is requested by the sender. It is not an emergency service.
6. **No public repository storage.** Subscriptions, keys and the server's VAPID private key
   never enter the repository, its history, CI logs, fixtures or the public static data. The
   VAPID key pair is created by the owner (an owner step like H05 and H08), and code reads only
   the variable names.

Open items before any build: the owner's policy decision; a store that is private and free
(unverified); the VAPID key owner step; a data-protection notice text; and a test that proves
a deleted or expired subscription is unrecoverable.
