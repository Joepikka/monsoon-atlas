import { describe, expect, it } from 'vitest';
import { districtFacts } from './PlaceLens';
import type { Tracker } from '../pages/Monsoon';

const tracker: Tracker = { year: 2026, built_on: '2026-11-13', reference: '2001-2025', label: 'ERA5',
  rows: [{ district: 'Bangalore', season: 'southwest', through: '2026-09-30', complete: true, rain_mm: 400,
    pct_of_median: 70.2, band: 'below normal', reference_years: 25 }] };

describe('district profile in the Place Lens (D205)', () => {
  it('shows season, hospital access, rain trend and, for Bangalore only, bus access', () => {
    const facts = districtFacts('Bangalore', tracker);
    expect(facts.map(f => f.label)).toEqual(['Southwest monsoon 2026', 'Hospital access', 'Annual rain trend since 1981', 'Bus access']);
    expect(facts[0].value).toBe('70.2% of normal (below normal)');
    expect(districtFacts('Yadgir', null).map(f => f.label)).toEqual(['Hospital access', 'Annual rain trend since 1981']);
    expect(districtFacts('Yadgir', null)[0].note).toContain('rank 1 of 30');
  });
  it('shows nothing for an unknown place', () => {
    expect(districtFacts('Nowhere', tracker)).toEqual([]);
  });
});
