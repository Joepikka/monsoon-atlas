import { describe, expect, it } from 'vitest';
import data from '../transit-coverage.json';
import { BANDS, cellsGeoJson, type Coverage } from './BusAccess';

describe('Bengaluru bus access cells (D191)', () => {
  it('draws each populated cell as a square in the right colour band', () => {
    const coverage = data as unknown as Coverage;
    const geo = cellsGeoJson(coverage);
    expect(geo.features.length).toBe(coverage.cells.filter(c => c[2] > 0).length);
    const [f] = geo.features;
    const ring = f.geometry.coordinates[0];
    expect(ring).toHaveLength(5);
    expect(ring[2][0] - ring[0][0]).toBeCloseTo(coverage.cell_deg, 6);
    const band = BANDS.find(([max]) => f.properties.frac < max)!;
    expect(f.properties.color).toBe(band[1]);
    expect(coverage.population.covered_share).toBeCloseTo(0.6534, 4);
  });
});
