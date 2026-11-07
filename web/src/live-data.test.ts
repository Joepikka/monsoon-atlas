import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { parseSnapshot } from './data';
import { currentView, pollCurrentSources, readCurrentSource, type CurrentSource } from './live-data';

const fixture = (name: string) => JSON.parse(readFileSync(new URL(`../tests/fixtures/${name}.json`, import.meta.url), 'utf8'));
const cap = fixture('sachet-ka-point');
const weather = fixture('openmeteo-temperature-point');
const place = fixture('bangalore-place');
const now = Date.parse('2026-11-06T00:00:00Z');
const minute = 60_000;
const cutoff = '2026-11-05T20:00:00Z';
const success = '2026-11-05T19:55:00Z';
const encoder = new TextEncoder();
const maxBytes = 1024 * 1024;
const payload = (source_id: CurrentSource = 'S09') => parseSnapshot({
  schema_version: 1, state: 'ka', release_id: 'normalized-live-contract', data_revision: 'c'.repeat(64),
  as_of: cutoff, published_at: cutoff, places: [], facilities: [], records: [source_id === 'S09' ? cap : weather],
  sources: [{ source_id, last_success_at: success, status: 'partial', detail: 'Limited captured source coverage.' }],
}, 'ka');

function envelope(snapshot: unknown = payload(), source_id: CurrentSource = 'S09') {
  const sha256 = createHash('sha256').update(JSON.stringify({ source_id, snapshot })).digest('hex');
  return { schema_version: 1, state: 'ka', sources: [{ source_id, snapshot, sha256, age_seconds: 1, snapshot_age_seconds: 2 }] };
}

function read(body: BodyInit | null, init?: ResponseInit) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, init)));
  return readCurrentSource('S09', new AbortController().signal);
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('bounded Worker GET reader', () => {
  it('uses the normalized Worker digest, source clocks and an abortable same-origin GET', async () => {
    vi.setSystemTime(now);
    const { sources } = envelope();
    const fetcher = vi.fn().mockResolvedValue(Response.json(envelope()));
    vi.stubGlobal('fetch', fetcher);
    const { signal } = new AbortController();
    const result = await readCurrentSource('S09', signal);
    expect(fetcher).toHaveBeenCalledExactlyOnceWith('/api/v1/current?state=ka&source=S09', expect.objectContaining({
      signal, mode: 'same-origin', redirect: 'error', credentials: 'omit',
    }));
    expect(result).toMatchObject({ sha256: sources[0].sha256, asOf: cutoff, health: { last_success_at: success }, records: [{ id: cap.id }] });
  });

  it('verifies the wire snapshot before discarding fields or changing their order', async () => {
    vi.setSystemTime(now);
    const { schema_version, ...rest } = payload();
    const wire = { ...rest, schema_version };
    const response = envelope(wire);
    await expect(read(JSON.stringify(response))).resolves.toMatchObject({ sha256: response.sources[0].sha256 });
    response.sources[0].sha256 = envelope().sources[0].sha256;
    await expect(read(JSON.stringify(response))).rejects.toThrow();
  });

  it('reads current and older stored snapshots through actual Worker GET and preserves stored identity', async () => {
    vi.setSystemTime(now);
    const { default: worker } = await vi.importActual<{ default: { fetch(request: Request, env: unknown): Promise<Response> } }>(
      '../../worker/src/index.ts',
    );
    const current = payload();
    // Simulate the earlier canonical schema with the original captured CAP point.
    const { area_text, ...legacyRecord } = current.records[0];
    const legacy = { ...current, records: [legacyRecord] };
    for (const snapshot of [current, legacy]) {
      const canonical = JSON.stringify({ source_id: 'S09', snapshot });
      const sha256 = createHash('sha256').update(canonical).digest('hex');
      const row = { source_id: 'S09', payload: Array.from(gzipSync(canonical)), sha256 };
      vi.stubGlobal('fetch', (path: string) => worker.fetch(new Request(new URL(path, 'https://atlas.invalid')), {
        CAPABILITY_GATE: 'verified_free_no_card',
        DB: { prepare() { return { bind() { return this; }, async all() { return { results: [row] }; } }; } },
      }));
      const result = await readCurrentSource('S09', new AbortController().signal);
      expect(result).toMatchObject({ sha256, records: [{ id: cap.id, area_text: snapshot === current ? area_text : null }] });
    }
  });

  it('rejects a malformed stored or wire digest and a changed wire body without downgrading to the stored digest', async () => {
    vi.setSystemTime(now);
    const response = envelope();
    const source = response.sources[0];
    for (const invalid of [
      { ...source, wire_sha256: null }, { ...source, wire_sha256: source.sha256.toUpperCase() },
      { ...source, wire_sha256: '0'.repeat(64) },
      { ...source, wire_sha256: source.sha256, sha256: source.sha256.toUpperCase() },
      { ...source, wire_sha256: source.sha256, snapshot: { ...payload(), unchecked: 'changed wire field' } },
    ]) await expect(read(JSON.stringify({ ...response, sources: [invalid] }))).rejects.toThrow();
  });

  it('streams exactly one MiB and rejects oversized or invalid UTF-8 responses', async () => {
    vi.setSystemTime(now);
    const body = JSON.stringify(envelope());
    const bytes = encoder.encode(body + ' '.repeat(maxBytes - encoder.encode(body).byteLength));
    const split = bytes.indexOf(0xe2) + 1; // The original warning title contains an em dash.
    const stream = new ReadableStream<Uint8Array>({ start(controller) {
      controller.enqueue(bytes.slice(0, split));
      controller.enqueue(bytes.slice(split));
      controller.close();
    } });
    await expect(read(stream)).resolves.toMatchObject({ asOf: cutoff });
    await expect(read(new Blob([Uint8Array.from(bytes).buffer, ' ']))).rejects.toThrow();
    const invalid = Uint8Array.from(encoder.encode(body));
    invalid[split] = 0xff;
    await expect(read(invalid.buffer)).rejects.toThrow();
  });

  it('rejects errors, missing bodies, malformed JSON and a response for another source', async () => {
    await expect(read(JSON.stringify(envelope()), { status: 503 })).rejects.toThrow();
    await expect(read(null)).rejects.toThrow();
    await expect(read('<html>')).rejects.toThrow();
    await expect(read(JSON.stringify(envelope(payload('S01'), 'S01')))).rejects.toThrow();
  });

  it('rejects the wrong outer state, schema, count and uppercase digest', async () => {
    vi.setSystemTime(now);
    const response = envelope();
    for (const invalid of [
      { ...response, schema_version: 2 }, { ...response, state: 'kl' },
      { ...response, sources: [...response.sources, ...response.sources] },
      { ...response, sources: [{ ...response.sources[0], sha256: response.sources[0].sha256.toUpperCase() }] },
    ]) await expect(read(JSON.stringify(invalid))).rejects.toThrow();
  });

  it('rejects rehashed bodies with wrong source shape or impossible times', async () => {
    vi.setSystemTime(now);
    const snapshot = payload();
    for (const changes of [
      { records: [weather] }, { records: [{ ...cap, kind: 'weather' }] }, { places: [place] },
      { sources: [{ ...snapshot.sources[0], source_id: 'S01' }] },
      { sources: [{ ...snapshot.sources[0], status: 'stale' }] },
      { sources: [{ ...snapshot.sources[0], last_success_at: null }] },
      { sources: [{ ...snapshot.sources[0], last_success_at: '2026-11-05T20:01:00Z' }] },
      { as_of: '2026-11-05T13:05:40.408123Z', sources: [{ ...snapshot.sources[0], last_success_at: '2026-11-05T13:05:40.408123Z' }] },
      { records: [{ ...weather, provenance: 'reconstructed', fetched_at: '2026-11-05T20:01:00Z' }],
        sources: payload('S01').sources, source: 'S01' as const },
      { published_at: '2026-11-05T19:59:59Z' }, { published_at: '2026-11-06T00:01:00Z' },
      { as_of: '2026-11-06T00:01:00Z', published_at: '2026-11-06T00:01:00Z' },
    ]) {
      const { source = 'S09', ...fields } = changes;
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(envelope({ ...snapshot, ...fields }, source))));
      await expect(readCurrentSource(source, new AbortController().signal)).rejects.toThrow();
    }
  });
});

describe('active polling', () => {
  function setup() {
    vi.useFakeTimers();
    vi.setSystemTime(now);
    const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' });
    vi.stubGlobal('document', doc);
    const onResult = vi.fn();
    const fetcher = vi.fn<typeof fetch>();
    vi.stubGlobal('fetch', fetcher);
    const setVisibility = (value: string) => {
      doc.visibilityState = value;
      doc.dispatchEvent(new Event('visibilitychange'));
    };
    return { fetcher, onResult, setVisibility };
  }

  it('keeps independent monotonic cutoffs, digests and check clocks across fallbacks', async () => {
    const { fetcher, onResult } = setup();
    const capPacket = envelope();
    const weatherPacket = envelope(payload('S01'), 'S01');
    const responses = [
      Response.json(capPacket), Response.json(weatherPacket), new Response(null, { status: 503 }),
      Response.json(envelope({ ...payload(), as_of: '2026-11-05T19:56:00Z' })),
      Response.json(envelope({ ...payload(), records: [] })),
      Response.json(envelope({ ...payload(), as_of: '2026-11-05T20:01:00Z', published_at: '2026-11-05T20:01:00Z',
        sources: [{ ...payload().sources[0], last_success_at: '2026-11-05T19:54:00Z' }] })),
      Response.json(capPacket),
    ];
    fetcher.mockImplementation(async () => responses.shift()!);
    const stop = pollCurrentSources(onResult);
    try {
      await vi.waitFor(() => expect(onResult).toHaveBeenCalledTimes(2));
      expect(onResult).toHaveBeenNthCalledWith(1, 'S09', expect.objectContaining({ sha256: capPacket.sources[0].sha256 }));
      expect(onResult).toHaveBeenNthCalledWith(2, 'S01', expect.objectContaining({ sha256: weatherPacket.sources[0].sha256 }));
      for (let attempt = 3; attempt <= 6; attempt++) {
        await vi.advanceTimersByTimeAsync(15 * minute);
        await vi.waitFor(() => expect(onResult).toHaveBeenCalledTimes(attempt));
        expect(onResult).toHaveBeenLastCalledWith('S09', null);
      }
      await vi.advanceTimersByTimeAsync(15 * minute);
      await vi.waitFor(() => expect(onResult).toHaveBeenCalledTimes(7));
      expect(onResult).toHaveBeenLastCalledWith('S09', expect.objectContaining({ sha256: capPacket.sources[0].sha256 }));
    } finally { stop(); }
  });

  it('cancels while hidden, ignores late settlement after resume, and times out a visible body', async () => {
    const { fetcher, onResult, setVisibility } = setup();
    let rejectLate!: (reason: Error) => void;
    const late = new Promise<Response>((_, reject) => { rejectLate = reject; });
    fetcher.mockResolvedValueOnce(Response.json(envelope()))
      .mockResolvedValueOnce(Response.json(envelope(payload('S01'), 'S01')))
      .mockReturnValueOnce(late)
      .mockResolvedValueOnce(new Response(new ReadableStream<Uint8Array>()));
    const stop = pollCurrentSources(onResult);
    try {
      await vi.waitFor(() => expect(onResult).toHaveBeenCalledTimes(2));
      await vi.advanceTimersByTimeAsync(15 * minute);
      expect(fetcher).toHaveBeenCalledTimes(3);
      const hiddenSignal = fetcher.mock.calls[2][1]!.signal!;
      setVisibility('hidden');
      expect(hiddenSignal.aborted).toBe(true);
      await vi.advanceTimersByTimeAsync(5 * minute);
      setVisibility('visible');
      rejectLate(new Error('Late network failure'));
      await vi.advanceTimersByTimeAsync(100);
      expect(onResult).toHaveBeenCalledTimes(2);
      expect(fetcher).toHaveBeenCalledTimes(3);
      await vi.advanceTimersByTimeAsync(10 * minute);
      const timeoutSignal = fetcher.mock.calls[3][1]!.signal!;
      expect(timeoutSignal.aborted).toBe(false);
      await vi.advanceTimersByTimeAsync(5000);
      expect(timeoutSignal.aborted).toBe(true);
      expect(onResult).toHaveBeenLastCalledWith('S09', null);
      expect(onResult).toHaveBeenCalledTimes(3);
    } finally { stop(); }
  });

  it('falls back when a response settles past the deadline before the timer can run', async () => {
    const { fetcher, onResult } = setup();
    let resolve!: (response: Response) => void;
    fetcher.mockReturnValueOnce(new Promise<Response>(done => { resolve = done; }));
    const now = performance.now.bind(performance);
    let delay = 0;
    const clock = vi.spyOn(performance, 'now').mockImplementation(() => now() + delay);
    const stop = pollCurrentSources(onResult);
    try {
      await vi.advanceTimersByTimeAsync(10);
      delay = 5000;
      resolve(Response.json(envelope()));
      await vi.waitFor(() => expect(onResult).toHaveBeenCalled());
      expect(onResult).toHaveBeenNthCalledWith(1, 'S09', null);
      expect(fetcher.mock.calls[0][1]!.signal!.aborted).toBe(true);
    } finally { stop(); clock.mockRestore(); }
  });

  it('retains the daily data when an empty hot source predates the daily cutoff or check', async () => {
    vi.setSystemTime(now);
    const daily = payload();
    const olderCutoff = await read(JSON.stringify(envelope({ ...daily, as_of: '2026-11-05T19:56:00Z', records: [] })));
    const olderCheck = await read(JSON.stringify(envelope({ ...daily, records: [],
      sources: [{ ...daily.sources[0], last_success_at: '2026-11-05T19:54:00Z' }] })));
    for (const hot of [olderCutoff, olderCheck]) {
      const view = currentView(daily, { S09: hot });
      expect(view.current.S09).toBeNull();
      expect(view.records).toEqual(daily.records);
      expect(view.sources).toEqual(daily.sources);
    }
  });
});
