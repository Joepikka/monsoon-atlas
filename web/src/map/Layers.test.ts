import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { distanceKm, visibleRecords, layerHealth } from './Layers';
import { parseSnapshot } from '../data';
import { LOCALES, t } from '../i18n';

const cap = JSON.parse(readFileSync(new URL('../../tests/fixtures/sachet-ka-point.json', import.meta.url), 'utf8'));
const weather = JSON.parse(readFileSync(new URL('../../tests/fixtures/openmeteo-temperature-point.json', import.meta.url), 'utf8'));
const metadata = { schema_version: 1, state: 'ka', release_id: 'layer-contract', data_revision: 'c'.repeat(64),
  as_of: cap.fetched_at, published_at: cap.fetched_at, records: [cap] };

describe('layer contracts', () => {
  it('uses geodesic distances, including the antimeridian', () => {
    expect(distanceKm([0, 0], [0, 1])).toBeCloseTo(111.195, 2);
    expect(distanceKm([179.9, 0], [-179.9, 0])).toBeLessThan(23);
    expect(distanceKm([77, 13], [77, 13])).toBe(0);
  });
  it('does not exclude an area alert on the basis of its representative point', () => {
    const snapshot = parseSnapshot(metadata, 'ka');
    expect(visibleRecords(snapshot.records, new Set(['alert']), [74, 16], 5)).toHaveLength(1);
    expect(visibleRecords(snapshot.records, new Set(), null, 5)).toHaveLength(0);
  });
  it('filters an actual forecast grid point by distance and rejects a missing measure unit', () => {
    const records = parseSnapshot({ ...metadata, records: [weather] }, 'ka').records;
    expect(visibleRecords(records, new Set(['weather']), [77.5, 13], 1)).toHaveLength(1);
    expect(visibleRecords(records, new Set(['weather']), [74, 16], 5)).toHaveLength(0);
    expect(() => parseSnapshot({ ...metadata, records: [{ ...weather, unit: null }] }, 'ka')).toThrow(/unit/i);
  });
  it('does not turn missing health metadata or a blocked source into a healthy empty feed', () => {
    expect(layerHealth('alert', parseSnapshot(metadata, 'ka'))).toBe('unknown');
    expect(layerHealth('price', parseSnapshot({ ...metadata, sources: [
      {source_id:'S22',status:'unavailable',last_success_at:null,detail:'Source discovery blocked'},
      {source_id:'S23',status:'unavailable',last_success_at:null,detail:'Price unit unverified'},
    ] }, 'ka'))).toBe('unavailable');
  });
  it('requires a reason for an unavailable weather measure', () => {
    expect(() => parseSnapshot({ ...metadata, records: [{ ...weather, value: null, missing_reason: null }] }, 'ka')).toThrow(/missing|reason/i);
  });
  it('rejects unknown price units and retains the CAP severity and original timestamps', () => {
    expect(() => parseSnapshot({ ...metadata, records: [{ ...cap, kind: 'price', unit: null }] }, 'ka')).toThrow(/unit/i);
    const record = parseSnapshot(metadata, 'ka').records[0];
    expect(record.severity).toBe(cap.severity);
    expect(record.issued_at).toBe(cap.issued_at);
    expect(record.expires_at).toBe(cap.expires_at);
  });
  it('rejects a record not yet available at the snapshot cutoff', () => {
    expect(() => parseSnapshot({ ...metadata, as_of: '2026-11-05T00:00:00Z' }, 'ka')).toThrow(/available|cutoff/i);
  });
  it('puts the boundary disclaimer on the map panel and adds no border layer of its own (H11, D166)', () => {
    const text = 'District boundaries are approximate and not authoritative. For official boundaries see the Survey of India.';
    expect(t('map.disclaimer')).toBe(text);
    for (const locale of Object.values(LOCALES)) expect(locale['map.disclaimer']).toBeTruthy();
    const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8');
    expect(read('../App.tsx')).toMatch(/className="map-disclaimer">\{t\('map\.disclaimer'\)\}/);
    // hiding the basemap's own country lines (D168) is the only border-related code allowed here
    expect(read('../MapView.tsx').replace(/hideInternationalBorders|map\/Borders/g, '')).not.toMatch(/addLayer|addSource|boundar|border/i);
  });
});
