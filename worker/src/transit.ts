// T151: fail-closed transit rules. No poller, upstream URL or key binding exists: S38 is blocked on
// owner step H04 (D135, D138). Enable only after T148 re-runs with a real feed.
export const POLL_SECONDS = 60;
export const STUDY_HOURS = 16;
export const MAX_POLLS_PER_DAY = STUDY_HOURS * 3600 / POLL_SECONDS;
export const STALE_SECONDS = 120;
export const TRANSIT_LIVE = { available: false, reason: 'transit live mode unavailable: S38 blocked (H04)' } as const;

export function isFresh(positionMs: number, nowMs: number): boolean {
  const age = (nowMs - positionMs) / 1000;
  return Number.isFinite(age) && age >= 0 && age < STALE_SECONDS;
}

export const liveMarker = (positionMs: number, nowMs: number): boolean => TRANSIT_LIVE.available && isFresh(positionMs, nowMs);
