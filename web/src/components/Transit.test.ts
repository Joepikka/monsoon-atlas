import { describe, expect, it } from 'vitest';
import { animates, parseTransitView, shownKind, STALE_SECONDS, transitFeatures, type Marker } from './Transit';

// Hand-built UI contract values (test inputs, not Delhi data): the position feed is blocked (D142).
const blocked = { model_id: 'M12', status: 'blocked' as const, reason: 'M12 blocked: S38 blocked on H04',
  coverage: { status: 'planned, not started' as const, test_period: ['2028-04-27', '2028-05-26'] as [string, string], months: [1, 2, 3, 4, 5] } };
const unavailable = { state: 'unavailable' as const, source_id: 'S38', reason: 'S38 blocked', retry_condition: 'owner completes H04', card: blocked };
const released = { ...blocked, status: 'available' as const, release: 'v1', source: 'S38', scores: { mae: 1 },
  coverage: { ...blocked.coverage, status: 'measured' as const } };
const now = Date.parse('2026-11-10T10:00:00+05:30');
const at = (secondsAgo: number) => new Date(now - secondsAgo * 1000).toISOString();
const gps = (secondsAgo: number): Marker => ({ id: 'g', kind: 'gps', lat: 28.6, lon: 77.2, at: at(secondsAgo) });
const eta = { p10: 60, p50: 120, p90: 300, source: 'S38', release: 'v1' };
const available = (markers: Marker[], card: object = blocked) => ({ state: 'available' as const, as_of: at(0), markers, card });

describe('transit markers', () => {
  it('uses the same stale limit as the Worker', () => expect(STALE_SECONDS).toBe(120));
  it('ages GPS out at 120 s and never animates it as current', () => {
    expect(shownKind(gps(119), now)).toBe('live');
    expect(animates(gps(119), now)).toBe(true);
    for (const late of [gps(120), gps(3600), gps(-5), { ...gps(0), at: '' }, { ...gps(0), at: 'soon' }, { ...gps(0), at: '2026-11-10T04:30:00' }]) {
      expect(shownKind(late, now)).toBe('aged_out');
      expect(animates(late, now)).toBe(false);
    }
  });
  it('keeps scheduled and predicted markers off the live path', () => {
    const scheduled: Marker = { ...gps(0), kind: 'scheduled' };
    expect(shownKind(scheduled, now)).toBe('scheduled');
    expect(animates(scheduled, now)).toBe(false);
    expect(animates({ ...gps(0), kind: 'predicted', eta }, now)).toBe(false);
  });
  it('leaves aged-out positions off the map and labels each kind', () => {
    const view = parseTransitView(available([gps(10), gps(500), { ...gps(0), kind: 'predicted', eta }], released));
    const features = transitFeatures(view, now).features;
    expect(features.map(f => f.properties.kind)).toEqual(['live', 'predicted']);
    expect(features.map(f => f.properties.animate)).toEqual([true, false]);
  });
});

describe('transit view and ETA card', () => {
  it('shows unavailable with a reason, a retry condition and a blocked ETA model', () => {
    expect(parseTransitView(unavailable).state).toBe('unavailable');
    expect(transitFeatures(unavailable, now).features).toEqual([]);
    expect(() => parseTransitView({ ...unavailable, retry_condition: '' })).toThrow('retry');
    expect(() => parseTransitView({ ...unavailable, markers: [] })).toThrow('no markers');
  });
  it('refuses any ETA number while the model is blocked', () => {
    expect(() => parseTransitView(available([{ ...gps(0), eta }]))).toThrow('released model');
    expect(() => parseTransitView(available([{ ...gps(0), kind: 'predicted' }]))).toThrow('released model');
    expect(() => parseTransitView({ ...unavailable, card: { ...blocked, scores: { mae: 1 } } })).toThrow('no scores');
  });
  it('needs ordered p10, p50, p90 with a source once a release exists', () => {
    expect(parseTransitView(available([{ ...gps(0), eta }], released)).state).toBe('available');
    expect(() => parseTransitView(available([{ ...gps(0), eta: { ...eta, p10: 400 } }], released))).toThrow('ordered');
    expect(() => parseTransitView(available([{ ...gps(0), eta: { ...eta, source: '' } }], released))).toThrow('source');
  });
  it('shows the test period and months beside scores, and planned coverage only when blocked', () => {
    const planned = { ...blocked.coverage };
    expect(() => parseTransitView({ ...unavailable, card: { ...blocked, coverage: { ...planned, status: 'measured' } } })).toThrow('planned');
    expect(() => parseTransitView({ ...unavailable, card: { ...blocked, coverage: { ...planned, months: [] } } })).toThrow('months');
    expect(() => parseTransitView({ ...unavailable, card: { ...blocked, coverage: { ...planned, test_period: ['', ''] } } })).toThrow('test period');
    expect(() => parseTransitView({ ...unavailable, card: { ...released, coverage: planned } })).toThrow('measured');
  });
});
