import { describe, expect, it } from 'vitest';
import { feedCounts, parseTransit, RAIL_LABEL, SCHEDULED_LABEL, transitFeatures } from './ScheduledTransit';

// UI contract values only (S30 raw feeds are restricted and stay local, D115).
const marker = { feed_id: 'bmrcl', source_revision: 'f402c4c69a5d', service_date: '2026-11-11', trip_id: 'a',
  route_id: 'GREEN', status: 'moving' as const, pause_reason: null, lat: 12.9, lon: 77.5, label: SCHEDULED_LABEL,
  live: false as const, approximate: true, uncertainty: 'approximate' };
const snapshot = () => ({ as_of: '2026-11-12T00:20:00+05:30', label: SCHEDULED_LABEL,
  feeds: [{ feed_id: 'bmrcl', source_revision: 'f402c4c69a5d', uncertainty: 'approximate', service_dates: ['2026-11-11'] }],
  markers: [marker, { ...marker, trip_id: 'b', status: 'paused' as const, pause_reason: 'missing shape', lat: null, lon: null }],
  stations: [{ id: 'SBC', lat: 12.97, lon: 77.57, kind: 'railway_station' }],
  rail: { label: RAIL_LABEL, mode: 'historical_reference' as const } });

describe('scheduled transit contract', () => {
  it('keeps paused trips off the map and labels every vehicle as scheduled', () => {
    const data = parseTransit(snapshot());
    const features = transitFeatures(data).features;
    expect(features.filter(f => f.properties.kind === 'scheduled_vehicle')).toHaveLength(1);
    expect(features.every(f => f.properties.kind !== 'scheduled_vehicle' || f.properties.label === SCHEDULED_LABEL)).toBe(true);
    expect(features.find(f => f.properties.kind === 'railway_station')?.properties.label).toBe(RAIL_LABEL);
    expect(feedCounts(data, 'bmrcl')).toEqual({ moving: 1, atStop: 0, paused: 1 });
  });
  it('rejects live claims, positioned pauses and railway ETAs', () => {
    expect(() => parseTransit({ ...snapshot(), markers: [{ ...marker, live: true }] })).toThrow('live');
    expect(() => parseTransit({ ...snapshot(), markers: [{ ...marker, status: 'paused' }] })).toThrow('paused');
    expect(() => parseTransit({ ...snapshot(), rail: { label: 'ETA', mode: 'current' } })).toThrow('historical');
    expect(() => parseTransit({ ...snapshot(), markers: [{ ...marker, service_date: '' }] })).toThrow('service date');
  });
});
