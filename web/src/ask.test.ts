import { describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { search, terms, type CorpusChunk } from './ask-search';
import { ageDays, askWorker, loadCorpus, parseCorpus } from './ask';

// Canonical bytes exported by atlas.rag.manifest from the committed AGENTS.md and M05 report (T261).
const body = readFileSync(new URL('../tests/fixtures/ask-corpus.json', import.meta.url), 'utf8');
const release = createHash('sha256').update(body).digest('hex');
const chunks = parseCorpus(JSON.parse(body));
const asOf = '2026-11-08T12:00:00Z';
const pointer = { schema_version: 1, release, url: `/data/ask/${release}.json` };
const ok = (data: unknown) => new Response(typeof data === 'string' ? data : JSON.stringify(data), { status: 200 });
const server = (routes: Record<string, () => Response>) =>
  (async (url: string | URL | Request) => (routes[String(url)] ?? (() => new Response('', { status: 404 })))()) as typeof fetch;

describe('browser Ask search', () => {
  it('ranks the M05 limits section first and keeps the retrieval rules', () => {
    const found = search(chunks, 'Does it cover groundwater, crop yield or household water?', { asOf, state: 'ka' });
    expect(found[0].chunk_id).toBe('M05#limits-claims-this-result-does-not-support:0');
    expect(found.filter(item => item.doc_id === 'M05').length).toBeLessThanOrEqual(2);
    const rules = search(chunks, 'agent task plan amendments decisions commit tests session', { asOf, state: 'ka' });
    expect(rules.filter(item => item.doc_id === 'project/rules').length).toBe(2);
    expect(terms('What is the')).toEqual([]);
    expect(search(chunks, 'What is the', { asOf, state: 'ka' })).toEqual([]);
  });

  it('never returns chunks committed after as-of, expired, for another state or near-duplicate', () => {
    expect(search(chunks, 'SPI groundwater drought', { asOf: '2026-11-05T17:48:39Z', state: 'ka' })
      .some(item => item.doc_id === 'M05')).toBe(false);
    expect(search(chunks, 'SPI groundwater drought', { asOf, state: 'kl' }).some(item => item.doc_id === 'M05')).toBe(false);
    const limits = chunks[0];
    const variants: CorpusChunk[] = [{ ...limits, expires_at: '2026-11-08T00:00:00Z' },
      { ...limits, chunk_id: 'copy#0', doc_id: 'copy' }, { ...limits, chunk_id: 'copy2#0', doc_id: 'copy2' }];
    const found = search([...variants, ...chunks.slice(1)], 'SPI groundwater drought', { asOf, state: 'ka' });
    expect(found.map(item => item.chunk_id)).toContain('copy#0');
    expect(found.map(item => item.chunk_id)).not.toContain('copy2#0');
    expect(found.some(item => item.expires_at !== null)).toBe(false);
  });
});

describe('Ask corpus and Worker reply', () => {
  it('loads only bytes whose SHA-256 is the release ID', async () => {
    const ready = await loadCorpus(server({ '/data/ask/latest.json': () => ok(pointer), [pointer.url]: () => ok(body) }));
    expect(ready).toMatchObject({ status: 'ready', release });
    expect((await loadCorpus(server({}))).status).toBe('empty');
    const tampered = await loadCorpus(server({ '/data/ask/latest.json': () => ok(pointer),
      [pointer.url]: () => ok(body.replace('groundwater', 'rainwater')) }));
    expect(tampered).toMatchObject({ status: 'error', message: 'Ask corpus integrity check failed.' });
    const mutable = await loadCorpus(server({ '/data/ask/latest.json': () => ok({ ...pointer, url: '/data/ask/latest-corpus.json' }) }));
    expect(mutable.status).toBe('error');
    expect(() => parseCorpus({ schema_version: 1, chunks: [{ ...chunks[0], text: 7 }] })).toThrow();
  });

  it('shows the Worker answer only when it matches the request, else local results', async () => {
    const found = search(chunks, 'SPI groundwater drought', { asOf, state: 'ka' });
    const reply = { schema_version: 1, release, as_of: asOf, answer: 'Search results (not a generated answer):\n[1] ...',
      citations: [{ chunk_id: found[0].chunk_id, claim_index: 0 }], status: 'quota_fallback', mode: 'extractive' };
    const worker = vi.fn(async () => ok(reply));
    const result = await askWorker('SPI groundwater?', found, release, asOf, worker as unknown as typeof fetch);
    expect(result).toMatchObject({ source: 'worker', mode: 'extractive', notice: '' });
    expect(result.cited.map(item => item.chunk_id)).toEqual([found[0].chunk_id]);
    const sent = JSON.parse((worker.mock.calls[0] as unknown as [string, RequestInit])[1].body as string);
    expect(sent).toEqual({ query: 'SPI groundwater?', language: 'en', place_id: 'in:ka', as_of: asOf,
      chunk_ids: found.map(item => item.chunk_id) });
    for (const bad of [{ ...reply, release: 'f'.repeat(64) }, { ...reply, citations: [{ chunk_id: 'invented#0', claim_index: 0 }] }]) {
      const fallback = await askWorker('SPI?', found, release, asOf, (async () => ok(bad)) as typeof fetch);
      expect(fallback).toMatchObject({ source: 'local', status: 'local_results' });
      expect(fallback.cited).toEqual(found);
    }
    const down = await askWorker('SPI?', found, release, asOf, (async () => new Response('', { status: 503 })) as typeof fetch);
    expect(down.notice).toMatch(/answer service is unavailable/);
    const unused = vi.fn();
    expect((await askWorker('zzz', [], release, asOf, unused as unknown as typeof fetch)).status).toBe('insufficient_evidence');
    expect(unused).not.toHaveBeenCalled();
    expect(ageDays('2026-11-05T17:48:40Z', asOf)).toBe(2);
  });
});
