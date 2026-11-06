import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { loadSnapshot, parseSnapshot, sha256 } from './data';

// Contract metadata only. No synthetic observations are served or committed.
const snapshot = {
  schema_version: 1, state: 'ka', release_id: 'contract-test',
  data_revision: 'a'.repeat(64), as_of: '2026-11-05T00:00:00Z',
  published_at: '2026-11-05T01:00:00Z', records: [],
};
const bytes = new TextEncoder().encode(JSON.stringify(snapshot));
const now = Date.parse('2026-11-05T02:00:00Z');

async function responses(approved = true, body = bytes) {
  const digest = await sha256(bytes);
  const pointer = { schema_version: 1, state: 'ka', approval: approved ? 'approved' : 'pending',
    manifest_url: `/data/ka/releases/${digest}.json`, sha256: digest };
  const fetcher = (async (url: string) => url.endsWith('latest.json')
    ? new Response(JSON.stringify(pointer)) : new Response(body)) as typeof fetch;
  return fetcher;
}

describe('immutable snapshot loading', () => {
  it('preserves the real CAP sample provenance and source times', () => {
    const record = JSON.parse(readFileSync(new URL('../tests/fixtures/sachet-ka-point.json', import.meta.url), 'utf8'));
    const parsed = parseSnapshot({ ...snapshot, as_of: record.fetched_at, published_at: record.fetched_at, records: [record] }, 'ka');
    expect(parsed.records[0].provenance).toBe('official');
    expect(parsed.records[0].valid_at).toBe(record.valid_at);
    expect(parsed.records[0].fetched_at).toBe(record.fetched_at);
  });
  it.each(['official', 'model', 'inferred'])('rejects availability before retrieval for %s records', provenance => {
    const record = JSON.parse(readFileSync(new URL('../tests/fixtures/openmeteo-temperature-point.json', import.meta.url), 'utf8'));
    const cutoff = record.available_at;
    // Test-only clock mutation; the captured observation is unchanged.
    record.fetched_at = '2099-01-01T00:00:00Z';
    record.provenance = provenance;
    expect(() => parseSnapshot({ ...snapshot, as_of: cutoff, records: [record] }, 'ka')).toThrow(/available.*fetched|retrieval/i);
  });
  it('preserves the explicit reconstructed availability exception', () => {
    const record = JSON.parse(readFileSync(new URL('../tests/fixtures/openmeteo-temperature-point.json', import.meta.url), 'utf8'));
    const cutoff = record.available_at;
    record.fetched_at = new Date(Date.parse(cutoff) + 86400000).toISOString();
    record.provenance = 'reconstructed'; // Test-only envelope metadata.
    expect(parseSnapshot({ ...snapshot, as_of: cutoff, records: [record] }, 'ka').records[0].provenance).toBe('reconstructed');
  });
  it('accepts an approved hash-matching snapshot without changing its timestamps', async () => {
    const result = await loadSnapshot('ka', null, { fetcher: await responses(), now });
    expect(result.status).toBe('ready');
    expect(result.snapshot?.as_of).toBe(snapshot.as_of);
  });
  it('distinguishes no release from a failed request', async () => {
    const result = await loadSnapshot('ka', null, { fetcher: (async () => new Response(null, { status: 404 })) as typeof fetch, now });
    expect(result.status).toBe('empty');
    expect(result.snapshot).toBeNull();
  });
  it('rejects pending publication approval', async () => {
    const result = await loadSnapshot('ka', null, { fetcher: await responses(false), now });
    expect(result.status).toBe('error');
    expect(result.snapshot).toBeNull();
  });
  it('rejects changed bytes even if they still parse as JSON', async () => {
    const result = await loadSnapshot('ka', null, { fetcher: await responses(true, new TextEncoder().encode('{}')), now });
    expect(result.status).toBe('error');
    expect(result.message).toMatch(/integrity/i);
  });
  it('keeps dated last-good data on network failure, restricted to the same state', async () => {
    const previous = parseSnapshot(snapshot, 'ka');
    const fetcher = (async () => { throw new Error('Network unavailable'); }) as typeof fetch;
    const result = await loadSnapshot('ka', previous, { fetcher, now });
    expect(result.status).toBe('error');
    expect(result.snapshot?.as_of).toBe(snapshot.as_of);
    expect((await loadSnapshot('kl', previous, { fetcher, now })).snapshot).toBeNull();
  });
  it('marks an old snapshot stale without rewriting its dates', async () => {
    const result = await loadSnapshot('ka', null, { fetcher: await responses(), now: now + 86400000 });
    expect(result.status).toBe('stale');
    expect(result.snapshot?.published_at).toBe(snapshot.published_at);
  });
  it('rejects mismatched state, missing provenance and invalid locations', () => {
    expect(() => parseSnapshot(snapshot, 'kl')).toThrow(/state/i);
    expect(() => parseSnapshot({ ...snapshot, records: [{}] }, 'ka')).toThrow();
    expect(() => parseSnapshot({ ...snapshot, as_of: 'not a timestamp' }, 'ka')).toThrow();
  });
  it('rejects off-origin and non-immutable snapshot paths before requesting them', async () => {
    let calls = 0;
    const fetcher = (async () => { calls++; return new Response(JSON.stringify({ schema_version: 1,
      state: 'ka', approval: 'approved', sha256: 'a'.repeat(64), manifest_url: 'https://example.com/data.json' })); }) as typeof fetch;
    expect((await loadSnapshot('ka', null, { fetcher, now })).status).toBe('error');
    expect(calls).toBe(1);
  });
});
