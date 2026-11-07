import { parseSnapshot, sha256, type MapRecord, type Snapshot, type SourceHealth } from './data';

export type CurrentSource = 'S09' | 'S01';
interface SourceUpdate {
  sha256: string;
  asOf: string;
  health: SourceHealth & { last_success_at: string };
  records: MapRecord[];
}
export type SourceUpdates = Partial<Record<CurrentSource, SourceUpdate | null>>;

export const currentSources = ['S09', 'S01'] as const;
const intervals = { S09: 15 * 60_000, S01: 6 * 60 * 60_000 };
const maxBytes = 1024 * 1024;
const deadlineMs = 5000;

function compareTimes(left: string, right: string): number {
  const milliseconds = Date.parse(left) - Date.parse(right);
  if (milliseconds) return milliseconds;
  // Capture timestamps can carry more precision than Date.parse preserves.
  const fraction = (time: string) => (/\.(\d+)Z$/.exec(time)?.[1] ?? '').replace(/0+$/, '');
  const a = fraction(left);
  const b = fraction(right);
  return a < b ? -1 : a > b ? 1 : 0;
}

async function readBody(body: ReadableStream<Uint8Array>, signal: AbortSignal): Promise<string> {
  const reader = body.getReader();
  const cancel = () => { void reader.cancel().catch(() => undefined); };
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let size = 0;
  let result = '';
  signal.addEventListener('abort', cancel, { once: true });
  try {
    signal.throwIfAborted();
    while (true) {
      const { done, value } = await reader.read();
      signal.throwIfAborted();
      if (done) return result + decoder.decode();
      size += value.byteLength;
      if (size > maxBytes) throw new Error('The current response exceeds one MiB.');
      result += decoder.decode(value, { stream: true });
    }
  } catch (error) {
    cancel();
    throw error;
  } finally {
    signal.removeEventListener('abort', cancel);
    reader.releaseLock();
  }
}

export async function readCurrentSource(source_id: CurrentSource, signal: AbortSignal): Promise<SourceUpdate> {
  const response = await fetch(`/api/v1/current?state=ka&source=${source_id}`, {
    mode: 'same-origin', redirect: 'error', credentials: 'omit', cache: 'no-store', signal,
    headers: { Accept: 'application/json' },
  });
  if (!response.ok || !response.body) {
    void response.body?.cancel().catch(() => undefined);
    throw new Error('The current source could not be reached.');
  }
  const packet = JSON.parse(await readBody(response.body, signal));
  if (packet?.schema_version !== 1 || packet.state !== 'ka' || !Array.isArray(packet.sources) || packet.sources.length !== 1) {
    throw new Error('Invalid current response schema.');
  }
  const entry = packet.sources[0];
  if (entry?.source_id !== source_id || typeof entry.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(entry.sha256) ||
      await sha256(new TextEncoder().encode(JSON.stringify({ source_id, snapshot: entry.snapshot }))) !== entry.sha256) {
    throw new Error('The current source or its digest does not match.');
  }
  signal.throwIfAborted();
  const snapshot = parseSnapshot(entry.snapshot, 'ka');
  const { as_of: asOf, published_at: published, records, sources, places, facilities } = snapshot;
  const now = new Date().toISOString();
  if (compareTimes(published, asOf) < 0 || compareTimes(published, now) > 0 || compareTimes(asOf, now) > 0) {
    throw new Error('Invalid current source cutoff or publication time.');
  }
  const [health] = sources;
  if (places.length || facilities.length || sources.length !== 1 || health.source_id !== source_id ||
      (health.status !== 'available' && health.status !== 'partial') || !health.last_success_at ||
      compareTimes(health.last_success_at, asOf) > 0 || records.some(record => record.source_id !== source_id ||
        record.kind !== (source_id === 'S09' ? 'alert' : 'weather') || compareTimes(record.fetched_at, asOf) > 0)) {
    throw new Error('The current response includes invalid source data.');
  }
  return { sha256: entry.sha256, asOf, health: { ...health, last_success_at: health.last_success_at }, records };
}

export function pollCurrentSources(onResult: (source: CurrentSource, update: SourceUpdate | null) => void): () => void {
  const due = { S09: 0, S01: 0 };
  const highWater: Partial<Record<CurrentSource, { asOf: string; checkedAt: string; sha256: string }>> = {};
  let nextTimer: ReturnType<typeof setTimeout> | undefined;
  let active: { controller: AbortController; deadline: ReturnType<typeof setTimeout> } | undefined;
  let stopped = false;

  function cancelActive() {
    if (!active) return;
    const { controller, deadline } = active;
    active = undefined;
    clearTimeout(deadline);
    controller.abort();
  }

  function schedule() {
    clearTimeout(nextTimer);
    if (stopped || active || document.visibilityState !== 'visible') return;
    const nextDue = Math.min(due.S09, due.S01);
    nextTimer = setTimeout(checkDue, Math.max(0, nextDue - performance.now()));
  }

  function checkDue() {
    if (stopped || active || document.visibilityState !== 'visible') return;
    const attemptedAt = performance.now();
    const source = currentSources.find(id => due[id] <= attemptedAt);
    if (!source) { schedule(); return; }
    due[source] = attemptedAt + intervals[source];
    const controller = new AbortController();

    const finish = (update: SourceUpdate | null) => {
      if (active?.controller !== controller) return;
      if (performance.now() - attemptedAt >= deadlineMs) update = null;
      if (update) {
        clearTimeout(deadline);
        active = undefined;
      } else cancelActive();
      if (stopped || document.visibilityState !== 'visible') return;
      const previous = highWater[source];
      if (update && previous) {
        const cutoff = compareTimes(update.asOf, previous.asOf);
        if (cutoff < 0 || (cutoff === 0 && update.sha256 !== previous.sha256) ||
            compareTimes(update.health.last_success_at, previous.checkedAt) < 0) update = null;
      }
      if (update) highWater[source] = { asOf: update.asOf, checkedAt: update.health.last_success_at, sha256: update.sha256 };
      onResult(source, update);
      schedule();
    };

    const deadline = setTimeout(() => finish(null), deadlineMs);
    active = { controller, deadline };
    void readCurrentSource(source, controller.signal).then(finish, () => finish(null));
  }

  function visibilityChanged() {
    if (document.visibilityState !== 'visible') cancelActive();
    schedule();
  }

  document.addEventListener('visibilitychange', visibilityChanged);
  schedule();
  return () => {
    stopped = true;
    document.removeEventListener('visibilitychange', visibilityChanged);
    clearTimeout(nextTimer);
    cancelActive();
  };
}

export function currentView(daily: Snapshot | null, updates: SourceUpdates) {
  const current = { ...updates };
  const replacements = new Map<string, SourceUpdate>();
  for (const id of currentSources) {
    const update = current[id];
    if (!update || !daily) continue;
    const dailyCheck = daily.sources.find(source => source.source_id === id)?.last_success_at;
    if (compareTimes(update.asOf, daily.as_of) < 0 || (dailyCheck && compareTimes(update.health.last_success_at, dailyCheck) < 0)) {
      current[id] = null;
    } else replacements.set(id, update);
  }
  const records = daily?.records ?? [];
  const sources = daily?.sources ?? [];
  if (!replacements.size) return { current, records, sources };
  return { current,
    records: [...records.filter(record => !replacements.has(record.source_id)), ...Array.from(replacements.values()).flatMap(update => update.records)],
    sources: [...sources.filter(source => !replacements.has(source.source_id)), ...Array.from(replacements.values(), update => update.health)],
  };
}
