import { describe, expect, it } from 'vitest';
import { data, extent, hospitalBars, trendBars } from './Findings';

describe('Karnataka data findings (D199)', () => {
  it('keeps the committed headline numbers', () => {
    expect(data.state).toBe('ka');
    expect(data.trends.significant).toBe(9);
    expect(data.trends.tested).toBe(30);
    expect(data.bus.covered_share).toBeCloseTo(0.6534, 4);
    expect(data.spatial.significant).toBe(57);
    expect(data.model.gates.every(g => g.passed === 'yes')).toBe(true);
  });
  it('sorts bars and marks only significant trends as strong', () => {
    const bars = trendBars();
    expect(bars[0].value).toBeGreaterThanOrEqual(bars[bars.length - 1].value);
    expect(bars.filter(b => b.strong)).toHaveLength(9);
    expect(hospitalBars()[0].label).toBe('Yadgir');
  });
  it('always puts zero on the axis', () => {
    expect(extent([2, 5])).toEqual([0, 5]);
    expect(extent([-3, 4])).toEqual([-3, 4]);
    expect(extent([0, 0])).toEqual([0, 1]);
  });
  it('holds no rain in mm and no bus stop, route or time', () => {
    const text = JSON.stringify(data);
    expect(text).not.toMatch(/gauge_mm|grid_mm|rain_mm|stop_id|route_id|trip_id|departure/);
  });
});
