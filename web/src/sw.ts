// T218 (D162): the offline cache plan as pure functions. NOTHING REGISTERS A SERVICE WORKER:
// there is no public host and no approved public snapshot (H05, H06, H11), and a worker that
// cached an unapproved shell is hard to remove from a user's device. Registration is deferred
// until H11; a test greps that nothing registers one.
import { t } from './i18n';

export const CACHE_NAME = 'monsoon-atlas-shell-v1';
export const BUDGET_BYTES = 20 * 1024 * 1024;
export const CACHED_AT = 'x-atlas-cached-at';
/** App shell files. Hashed build assets are listed by name at build time, never fetched blind. */
export const SHELL = [/^\.\/$/, /^\.\/index\.html$/, /^\.\/manifest\.webmanifest$/, /^\.\/assets\/[\w.-]+\.(?:js|css)$/];
/** State summaries cleared for offline use. Empty: no snapshot is approved for publication. */
export const PERMITTED_SUMMARIES: readonly string[] = [];

export interface Candidate { url: string; bytes: number }
export interface Planned extends Candidate { cachedAt: string }
export interface Plan {
  entries: Planned[]; bytes: number;
  rejected: { url: string; reason: 'not_allowlisted' | 'over_budget' }[];
}

/** Allowlisted candidates in order, each stamped with `now`, until the 20 MB budget is spent. */
export function planCache(
  candidates: readonly Candidate[], now: string, permitted: readonly string[] = PERMITTED_SUMMARIES, budget = BUDGET_BYTES,
): Plan {
  const plan: Plan = { entries: [], bytes: 0, rejected: [] };
  for (const { url, bytes } of candidates) {
    if (!SHELL.some(rule => rule.test(url)) && !permitted.includes(url)) plan.rejected.push({ url, reason: 'not_allowlisted' });
    else if (!Number.isFinite(bytes) || bytes < 0 || plan.bytes + bytes > budget) plan.rejected.push({ url, reason: 'over_budget' });
    else { plan.entries.push({ url, bytes, cachedAt: now }); plan.bytes += bytes; }
  }
  return plan;
}

/** A copy of the response that records when it was fetched. */
export function stamp(response: Response, cachedAt: string): Response {
  const headers = new Headers(response.headers);
  headers.set(CACHED_AT, cachedAt);
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

const age = (ms: number): string => ms >= 86_400_000
  ? t('offline.age_days', { n: Math.floor(ms / 86_400_000) })
  : t('offline.age_hours', { n: Math.floor(ms / 3_600_000) });

/** Always names the cache date and never says cached risk is current, however fresh the copy. */
export function offlineBanner(cachedAt: string | null, now: string): string {
  const saved = cachedAt === null ? Number.NaN : Date.parse(cachedAt);
  const ms = Date.parse(now) - saved;
  if (!Number.isFinite(ms) || ms < 0) return t('offline.unknown');
  return t('offline.banner', { when: new Date(saved).toISOString().slice(0, 16).replace('T', ' ') + ' UTC', age: age(ms) });
}
