import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { loadAccuracy, parseAccuracy, show } from './accuracy';

const body = readFileSync(new URL('../tests/fixtures/accuracy-ka.json', import.meta.url), 'utf8');
const digest = createHash('sha256').update(body).digest('hex');
const pointer = { schema_version: 1, state: 'ka', approval: 'approved', sha256: digest,
  manifest_url: `/data/ka/accuracy/${digest}.json` };

function server(routes: Record<string, () => Response>): typeof fetch {
  return (async (url: string | URL | Request) => (routes[String(url)] ?? (() => new Response('', { status: 404 })))()) as typeof fetch;
}
const ok = (bytes: string) => () => new Response(bytes, { status: 200, headers: { 'Content-Type': 'application/json' } });

describe('accuracy release', () => {
  it('keeps blocked values unavailable and approved values exact', () => {
    const rows = parseAccuracy(JSON.parse(body));
    expect(rows.map(row => row.model)).toEqual(['M07', 'M05', 'M06']);
    const m06 = rows[2];
    expect([m06.candidate, m06.improvement, m06.ci95]).toEqual([null, null, null]);
    expect(show(m06.candidate)).toBe('Unavailable');
    expect(show(rows[1].candidate)).toBe('0.732');
    expect(rows[1].ci95?.map(show)).toEqual(['0.003', '0.150']);
  });

  it('loads only an approved release whose bytes match the pointer', async () => {
    const ready = await loadAccuracy(server({ '/data/ka/accuracy/latest.json': ok(JSON.stringify(pointer)),
      [pointer.manifest_url]: ok(body) }));
    expect(ready.status).toBe('ready');
    expect((await loadAccuracy(server({}))).status).toBe('empty');
    const pending = await loadAccuracy(server({ '/data/ka/accuracy/latest.json': ok(JSON.stringify({ ...pointer, approval: 'pending' })) }));
    expect(pending).toMatchObject({ status: 'error', message: 'Accuracy publication approval is pending.' });
    const tampered = await loadAccuracy(server({ '/data/ka/accuracy/latest.json': ok(JSON.stringify(pointer)),
      [pointer.manifest_url]: ok(body.replace('0.7320467345749282', '0.5')) }));
    expect(tampered).toMatchObject({ status: 'error', message: 'Accuracy integrity check failed.' });
    const mutable = await loadAccuracy(server({ '/data/ka/accuracy/latest.json': ok(JSON.stringify({ ...pointer, manifest_url: '/data/ka/accuracy/latest-table.json' })) }));
    expect(mutable.status).toBe('error');
  });

  it('rejects zero-filled or malformed values', () => {
    const data = JSON.parse(body);
    expect(() => parseAccuracy({ ...data, rows: [{ ...data.rows[1], candidate: '0.7' }] })).toThrow();
    expect(() => parseAccuracy({ ...data, rows: [{ ...data.rows[1], ci95: [0.2, 0.1] }] })).toThrow();
    expect(() => parseAccuracy({ ...data, state: 'kl' })).toThrow();
  });
});
