import { describe, expect, it } from 'vitest';
import { parseTracker, seasonRows } from './Monsoon';

const body = {
  schema_version: 1, state: 'ka', source_id: 'S02', year: 2026, built_on: '2026-11-12', reference: '2001-2025',
  label: 'ERA5 reanalysis (model)',
  rows: [
    { district: 'Kodagu', season: 'northeast', through: '2026-11-04', complete: false, rain_mm: 80, median_mm: 160, pct_of_median: 50, rank_percentile: 8, band: 'far below normal', reference_years: 25 },
    { district: 'Udupi', season: 'northeast', through: '2026-11-04', complete: false, rain_mm: 300, median_mm: 250, pct_of_median: 120, rank_percentile: 70, band: 'near normal', reference_years: 25 },
    { district: 'Kodagu', season: 'southwest', through: '2026-09-30', complete: true, rain_mm: 2000, median_mm: 2100, pct_of_median: 95.2, rank_percentile: 44, band: 'near normal', reference_years: 25 },
  ],
};

describe('district monsoon tracker (D192)', () => {
  it('keeps one season, driest first', () => {
    const t = parseTracker(body);
    expect(seasonRows(t, 'northeast').map(r => r.district)).toEqual(['Kodagu', 'Udupi']);
    expect(seasonRows(t, 'southwest')).toHaveLength(1);
  });
  it('refuses another state or source', () => {
    expect(() => parseTracker({ ...body, state: 'kl' })).toThrow('Invalid monsoon tracker.');
    expect(() => parseTracker({ ...body, source_id: 'S08' })).toThrow('Invalid monsoon tracker.');
  });
});
