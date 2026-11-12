import { describe, expect, it } from 'vitest';
import { parseAirView } from './AirQuality';

// Hand-built UI contract values (test inputs, not Delhi data): both Delhi layers are unavailable (D142).
const card = { model_id: 'M14', status: 'blocked' as const, reason: 'M14 blocked: S24 blocked',
  coverage: { status: 'planned, not started' as const, test_period: ['2028-04-27', '2028-05-26'] as [string, string], months: [1, 2, 3, 4, 5] } };
const down = (layer: 'station' | 'model', source_id: string) => ({ layer, state: 'unavailable' as const, source_id,
  reason: `${source_id} unavailable`, retry_condition: 'see record' });
const up = (layer: 'station' | 'model', over: object = {}) => ({ layer, state: 'available' as const,
  provenance: layer === 'station' ? 'observation' as const : 'model' as const, source_id: layer === 'station' ? 'S24' : 'S04',
  pollutant: 'pm2_5', unit: 'ug/m3', interval_minutes: 60, as_of: '2026-11-10T04:00:00Z', ...over });
const view = { station: down('station', 'S24'), model: down('model', 'S04'),
  comparison: { status: 'unavailable' as const, reason: 'no station basis' }, card };

describe('air quality contract', () => {
  it('shows both layers unavailable with a reason and no comparison', () => {
    expect(parseAirView(view).comparison.status).toBe('unavailable');
    expect(() => parseAirView({ ...view, station: { ...view.station, reason: '' } })).toThrow('reason');
    expect(() => parseAirView({ ...view, comparison: { status: 'unavailable', reason: '' } })).toThrow('two available');
  });
  it('keeps station and model layers distinct', () => {
    expect(() => parseAirView({ ...view, station: down('model', 'S04') })).toThrow('distinct');
    expect(() => parseAirView({ ...view, station: up('station', { provenance: 'model' }) })).toThrow('provenance');
    expect(() => parseAirView({ ...view, model: up('model', { provenance: 'observation' }) })).toThrow('provenance');
  });
  it('compares only identical pollutant, unit and averaging', () => {
    const same = { status: 'comparable' as const, pollutant: 'pm2_5', unit: 'ug/m3', interval_minutes: 60 };
    const ok = { ...view, station: up('station'), model: up('model'), comparison: same };
    expect(parseAirView(ok).comparison.status).toBe('comparable');
    for (const other of [{ unit: 'ppb' }, { interval_minutes: 1440 }, { pollutant: 'no2' }]) {
      expect(() => parseAirView({ ...ok, model: up('model', other) })).toThrow('differ');
    }
    expect(() => parseAirView({ ...ok, station: down('station', 'S24') })).toThrow('two available');
  });
});
