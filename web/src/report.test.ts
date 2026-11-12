import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { buildReport, readShare, shareUrl, rankByDistance } from './report';
import { loadSnapshot, parseSnapshot, sha256 } from './data';

const place = JSON.parse(readFileSync(new URL('../tests/fixtures/bangalore-place.json', import.meta.url), 'utf8'));
const cap = JSON.parse(readFileSync(new URL('../tests/fixtures/sachet-ka-point.json', import.meta.url), 'utf8'));
const weather = JSON.parse(readFileSync(new URL('../tests/fixtures/openmeteo-temperature-point.json', import.meta.url), 'utf8'));
const facilities = JSON.parse(readFileSync(new URL('../tests/fixtures/s18-facilities-bengaluru.json', import.meta.url), 'utf8'));
const body = { schema_version: 1, state: 'ka', release_id: 'report-contract', data_revision: 'e'.repeat(64),
  as_of: cap.fetched_at, published_at: cap.fetched_at, places: [place], records: [cap, weather], facilities: [] };
const now = Date.parse(cap.fetched_at) + 3600000;

function snapshot() { return { ...parseSnapshot(body, 'ka'), release_hash: 'f'.repeat(64) }; }

describe('frozen place reports', () => {
  it('lists real S18 facilities by straight-line distance, nearest first, with their kind', () => {
    const asOf = facilities[0].fetched_at;
    const parsed = parseSnapshot({ ...body, as_of: asOf, published_at: asOf, facilities }, 'ka');
    const report = buildReport({ ...parsed, release_hash: 'f'.repeat(64) }, place.place_id, place.boundary_version);
    expect(report.facilities.map(f => f.kind).sort()).toEqual(['fire_station', 'hospital', 'hospital', 'hospital', 'police', 'police']);
    const distances = report.facilities.map(f => f.distance_km);
    expect(distances).toEqual([...distances].sort((a, b) => a - b));
    expect(distances.every(d => d <= 25)).toBe(true);
    expect(report.sources.some(s => s.id === 'S18')).toBe(true);
    expect(() => parseSnapshot({ ...body, as_of: asOf, published_at: asOf, facilities: [{ ...facilities[0], kind: 'shelter' }] }, 'ka')).toThrow('Invalid facility kind.');
  });
  it('keeps the real place version, original cutoff and unavailable outputs', () => {
    const report = buildReport(snapshot(), place.place_id, place.boundary_version);
    expect(report.place.boundary_version).toBe(place.boundary_version);
    expect(report.as_of).toBe(cap.fetched_at);
    expect(report.modelOutputs).toHaveLength(0);
    expect(report.facilities).toHaveLength(0);
    expect(report.records.some(record => record.id === cap.id)).toBe(true);
  });
  it('shares only the frozen identity, without carrying arbitrary URL parameters', () => {
    const report = buildReport(snapshot(), place.place_id, place.boundary_version);
    const url = shareUrl('https://atlas.invalid/?token=do-not-share', report);
    const shared = readShare(new URL(url).search);
    expect(shared?.place).toBe(place.place_id);
    expect(shared?.boundary).toBe(place.boundary_version);
    expect(shared?.asOf).toBe(cap.fetched_at);
    expect(shared?.release).toBe('f'.repeat(64));
    expect(new URL(url).searchParams.has('token')).toBe(false);
  });
  it('rejects unknown places, mismatched versions and incomplete frozen links', () => {
    expect(() => buildReport(snapshot(), place.place_id, 'unmatched-version')).toThrow(/boundary|version/i);
    expect(() => buildReport(snapshot(), 'unknown-place', place.boundary_version)).toThrow(/place/i);
    expect(() => readShare('?release=invalid&state=ka')).toThrow();
  });
  it('rejects source links carrying credential query fields before rendering or sharing', () => {
    for (const key of ['access_token', 'key', 'map_key', 'api-key']) {
      expect(() => parseSnapshot({ ...body, records: [{ ...weather, source_url: weather.source_url + `&${key}=test-only` }] }, 'ka')).toThrow(/credential|URL/i);
    }
  });
  it('ranks actual coordinate references by distance without changing the inputs', () => {
    const references = [weather, place];
    const sorted = rankByDistance([place.longitude, place.latitude], references);
    expect(sorted[0].distance_km).toBe(0);
    expect(sorted[1].distance_km).toBeGreaterThan(0);
    expect(references[0]).toBe(weather);
  });
  it('reopens a hash-bound approved snapshot without requesting latest', async () => {
    const bytes = new TextEncoder().encode(JSON.stringify(body));
    const hash = await sha256(bytes);
    const fetcher = (async (url: string) => {
      if (url.endsWith(`${hash}.approval.json`)) return new Response(JSON.stringify({
        schema_version: 1, state: 'ka', approval: 'approved', sha256: hash,
        manifest_url: `/data/ka/releases/${hash}.json`,
      }));
      if (url.endsWith(`${hash}.json`)) return new Response(bytes);
      throw new Error('Latest must not be used for a frozen view');
    }) as typeof fetch;
    const result = await loadSnapshot('ka', null, { fetcher, now, releaseHash: hash, asOf: cap.fetched_at });
    expect(result.status).toBe('ready');
    expect(result.snapshot?.release_hash).toBe(hash);
  });
  it('does not substitute a different release when historical lookup fails', async () => {
    const fetcher = (async () => new Response(null, { status: 404 })) as typeof fetch;
    const result = await loadSnapshot('ka', snapshot(), { fetcher, now, releaseHash: 'a'.repeat(64), asOf: cap.fetched_at });
    expect(result.status).toBe('error');
    expect(result.snapshot).toBeNull();
  });
});

describe('Nearby keeps every facility kind (D188)', () => {
  it('many near hospitals cannot hide a farther police station', () => {
    const asOf = facilities[0].fetched_at;
    const base = facilities.find((f: { kind: string }) => f.kind === 'hospital');
    const crowd = Array.from({ length: 12 }, (_, i) => ({ ...base, facility_id: `osm:node:${900000 + i}`, name: `H${i}`,
      longitude: place.longitude + 0.001 * (i + 1), latitude: place.latitude }));
    const police = { ...facilities.find((f: { kind: string }) => f.kind === 'police'), facility_id: 'osm:node:999999',
      longitude: place.longitude + 0.1, latitude: place.latitude };
    const parsed = parseSnapshot({ ...body, as_of: asOf, published_at: asOf, facilities: [...crowd, police] }, 'ka');
    const report = buildReport({ ...parsed, release_hash: 'f'.repeat(64) }, place.place_id, place.boundary_version);
    expect(report.facilities.filter(f => f.kind === 'hospital')).toHaveLength(4);
    expect(report.facilities.some(f => f.facility_id === 'osm:node:999999')).toBe(true);
    const d = report.facilities.map(f => f.distance_km);
    expect(d).toEqual([...d].sort((a, b) => a - b));
  });
});
