import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import {
  AIRCRAFT_MAX_AGE_S, ELEMENT_MAX_AGE_S, parseAircraft, parseMovementLayers, parseQuake, satelliteLabel, shown,
  type Aircraft, type MovementData, type MovementLayer, type Quake, type Satellite,
} from './Movement';

// Written by atlas.spatial.orbits.movement_status() from the source contracts (a Python test keeps it equal).
const fixture = JSON.parse(readFileSync(new URL('../../tests/fixtures/movement-layers.json', import.meta.url), 'utf8'));
const now = Date.parse('2026-11-11T06:00:00Z');
const ago = (seconds: number) => new Date(now - seconds * 1000).toISOString();
// Hand-built test inputs, not observations.
const plane = (seconds: number, extra: object = {}): Aircraft => ({ aircraft_id: 'abc123', position_at: ago(seconds), lat: 13, lon: 77.5,
  altitude_m: 3000, speed_ms: 200, on_ground: false, position_type: 'adsb_icao', ...extra });
const sat = (epochSeconds: number, lat: number | null = 10): Satellite => ({ norad_id: 25544, name: 'TEST SAT', epoch_at: ago(epochSeconds), lat, lon: lat === null ? null : 70 });
const quake = (over: Partial<Quake> = {}): Quake => ({ event_id: 'us0001', origin_at: ago(7200), lat: 10, lon: 70, depth_km: 10, magnitude: 4.2, mag_type: 'mb',
  review_status: 'reviewed', updated_at: ago(3600), source_url: 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson', ...over });
const data: MovementData = { aircraft: [plane(10)], satellites: [sat(3600)], earthquakes: [quake()] };
const allOpen: MovementLayer[] = parseMovementLayers(fixture).map(l => ({ ...l, available: l.layer !== 'vessel', reason: l.layer !== 'vessel' ? null : l.reason }));

describe('movement layers', () => {
  it('shows what the source contracts allow and keeps the rest disabled with a reason', () => {
    const layers = parseMovementLayers(fixture);
    expect(layers.filter(l => l.available).map(l => l.layer)).toEqual(['aircraft']);
    expect(layers.find(l => l.layer === 'satellite')?.reason).toContain('sgp4 not in the lock');
    expect(layers.find(l => l.layer === 'earthquake')?.reason).toContain('H11');
    expect(layers.find(l => l.layer === 'vessel')?.reason).toContain('H12');
    expect(() => parseMovementLayers(fixture.map((l: MovementLayer) => (l.layer === 'vessel' ? { ...l, reason: null } : l)))).toThrow('reason');
    const real = shown(layers, data, now);
    expect(real.aircraft).toHaveLength(1);
    expect([real.satellite.length, real.earthquake.length, real.vessel.length]).toEqual([0, 0, 0]);
  });

  it('hides stale, future and unpositioned aircraft', () => {
    const rows = [plane(0), plane(AIRCRAFT_MAX_AGE_S), plane(AIRCRAFT_MAX_AGE_S + 1), plane(-1)];
    expect(shown(allOpen, { ...data, aircraft: rows }, now).aircraft).toHaveLength(2);
  });

  it('accepts no callsign, registration or other field outside the allowlist', () => {
    expect(parseAircraft([plane(1)])).toHaveLength(1);
    expect(() => parseAircraft([plane(1, { callsign: 'X' })])).toThrow('allowlist');
    expect(() => parseAircraft([plane(1, { registration: 'X' })])).toThrow('allowlist');
    expect(() => parseAircraft([{ ...plane(1), position_at: '2026-11-11T06:00:00' }])).toThrow('zoned');
  });

  it('labels satellite positions as predicted, dates the elements and hides old or positionless ones', () => {
    expect(satelliteLabel(sat(3600))).toContain('Predicted position');
    expect(satelliteLabel(sat(3600))).toContain('not observed');
    const rows = [sat(0), sat(ELEMENT_MAX_AGE_S), sat(ELEMENT_MAX_AGE_S + 1), sat(-60), sat(3600, null)];
    expect(shown(allOpen, { ...data, satellites: rows }, now).satellite).toHaveLength(2);
  });

  it('keeps the USGS revision time and source link, refuses other hosts and drops deleted events', () => {
    expect(parseQuake(quake()).updated_at).toBe(quake().updated_at);
    expect(() => parseQuake(quake({ source_url: 'https://example.org/x' }))).toThrow('USGS');
    expect(() => parseQuake(quake({ source_url: 'http://earthquake.usgs.gov/x' }))).toThrow('USGS');
    expect(() => parseQuake(quake({ updated_at: ago(9000) }))).toThrow('before');
    expect(() => parseQuake(quake({ review_status: 'maybe' as never }))).toThrow('status');
    const rows = [quake(), quake({ event_id: 'us0002', review_status: 'deleted' })];
    expect(shown(allOpen, { ...data, earthquakes: rows }, now).earthquake.map(q => q.event_id)).toEqual(['us0001']);
  });

  it('never draws a ship while the feed is blocked, even when ship data is supplied', () => {
    const open = allOpen.map(l => ({ ...l, available: true, reason: null }));
    expect(shown(open, { ...data, aircraft: [], satellites: [], earthquakes: [] }, now).vessel).toEqual([]);
  });
});
