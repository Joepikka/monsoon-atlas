import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { parseClimate, PROJECTION_LABEL } from './Climate';

const product = () => ({
  ndvi: { status: 'unavailable', reason: 'S42 blocked', wording: 'vegetation greenness' },
  tracker: { year: 2025, reference: '1981-2010', checkpoints: [] },
  onset: { official_onset: null, reason: 'no source', inferred: { onset: '2025-05-13', label: 'inferred', method: 'm' } },
  trend: [], projection: { label: PROJECTION_LABEL, baseline: '1981-2010', window: '2021-2050', by_point: {} },
  limits: ['x'],
});

describe('climate product contract', () => {
  it('accepts a labelled product', () => {
    expect(parseClimate(product()).tracker.year).toBe(2025);
  });
  it('refuses an unlabelled projection, a wrong climatology, a bare missing onset or an unlabelled heuristic', () => {
    const p = product();
    expect(() => parseClimate({ ...p, projection: { ...p.projection, label: 'Forecast' } })).toThrow('label');
    expect(() => parseClimate({ ...p, tracker: { ...p.tracker, reference: '1991-2020' } })).toThrow('1981-2010');
    expect(() => parseClimate({ ...p, onset: { ...p.onset, reason: null } })).toThrow('reason');
    expect(() => parseClimate({ ...p, onset: { ...p.onset, inferred: { ...p.onset.inferred, label: 'official' } } })).toThrow('inferred');
    expect(() => parseClimate({ ...p, ndvi: { status: 'unavailable', reason: null, wording: 'x' } })).toThrow('NDVI');
  });
  it('accepts the real export', () => {
    const real = JSON.parse(readFileSync(new URL('../../../reports/eda/08_climate_product/climate.json', import.meta.url), 'utf8'));
    expect(parseClimate(real).onset.official_onset).toBeNull();
  });
});

describe('mounted page data (D166, D167)', () => {
  const file = (p: string) => readFileSync(new URL(p, import.meta.url), 'utf8');
  it('serves the exported product unchanged', () => {
    expect(file('../climate.json')).toBe(file('../../../reports/eda/08_climate_product/climate.json'));
  });
  it('shows no rainfall in mm: every number is a percent, a rank, a year or a model change', () => {
    const real = parseClimate(JSON.parse(file('../climate.json')));
    const keys = [...Object.keys(real.trend[0]), ...Object.keys(real.tracker.checkpoints[0])];
    expect(keys.filter(k => /mm|cumulative|total/.test(k))).toEqual([]);
    expect(real.limits.join(' ')).toContain('not as mm');
  });
});
