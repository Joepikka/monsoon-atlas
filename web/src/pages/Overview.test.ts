import { describe, expect, it } from 'vitest';
import { METRICS, values } from './Overview';
import districts from '../ka-districts.json';
import type { Tracker } from './Monsoon';

const tracker: Tracker = { year: 2026, built_on: '2026-11-13', reference: '2001-2025', label: 'ERA5', rows: [
  { district: 'Yadgir', season: 'southwest', through: '2026-09-30', complete: true, rain_mm: 300, pct_of_median: 48.7, band: 'far below normal', reference_years: 25 },
  { district: 'Yadgir', season: 'northeast', through: '2026-11-04', complete: false, rain_mm: 7, pct_of_median: 9.4, band: 'far below normal', reference_years: 25 },
] };

describe('Overview 3D map values (D209)', () => {
  it('covers all 30 district outlines with hospital and trend values', () => {
    const names = districts.features.map(f => f.properties.name);
    expect(names).toHaveLength(30);
    for (const metric of ['hospital', 'trend'] as const) expect([...values(metric, null).keys()].sort()).toEqual([...names].sort());
  });
  it('uses the southwest season only and leaves missing districts out, never zero', () => {
    const v = values('monsoon', tracker);
    expect(v.get('Yadgir')).toBe(48.7);
    expect(v.size).toBe(1);
    expect(values('monsoon', null).size).toBe(0);
  });
  it('gives every measure a unit and a rising colour scale', () => {
    for (const spec of Object.values(METRICS)) {
      expect(spec.unit).toBeTruthy();
      const stops = spec.colors.map(c => c[0]);
      expect(stops).toEqual([...stops].sort((a, b) => a - b));
    }
  });
});
