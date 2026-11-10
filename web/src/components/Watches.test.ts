import { describe, expect, it } from 'vitest';
import { parseWatch, triggered, type Signal, type Watch } from './Watches';

// Hand-built UI contract values (test inputs, not real alerts or forecasts).
const now = Date.parse('2026-11-10T06:00:00Z');
const watch: Watch = { id: 'w1', placeId: 'in:ka:blr', label: 'Test place', alerts: true, rainMm: 20 };
const signal = (over: Partial<Signal> = {}): Signal => ({ kind: 'forecast', placeId: 'in:ka:blr', status: 'actual',
  rainMm: 30, validUntil: '2026-11-10T09:00:00Z', sourceUrl: 'https://example.test/x', text: 'test', ...over });

describe('watch evaluation', () => {
  it('triggers on a live forecast at or above the threshold and on a live alert', () => {
    expect(triggered(watch, signal(), now)).toBe(true);
    expect(triggered(watch, signal({ rainMm: 19.9 }), now)).toBe(false);
    expect(triggered(watch, signal({ kind: 'alert', rainMm: null }), now)).toBe(true);
    expect(triggered({ ...watch, alerts: false }, signal({ kind: 'alert' }), now)).toBe(false);
  });
  it('never triggers on an expired forecast or alert, or a cancelled or superseded one', () => {
    expect(triggered(watch, signal({ validUntil: '2026-11-10T06:00:00Z' }), now)).toBe(false);
    expect(triggered(watch, signal({ kind: 'alert', validUntil: '2026-11-09T00:00:00Z' }), now)).toBe(false);
    for (const status of ['cancelled', 'superseded'] as const) {
      expect(triggered(watch, signal({ kind: 'alert', status }), now)).toBe(false);
    }
  });
  it('fails closed on missing end times, bad dates and other places', () => {
    expect(triggered(watch, signal({ validUntil: null }), now)).toBe(false); // a forecast needs an end time
    expect(triggered(watch, signal({ kind: 'alert', validUntil: null }), now)).toBe(true);
    expect(triggered(watch, signal({ validUntil: 'soon' }), now)).toBe(false);
    expect(triggered(watch, signal({ placeId: 'in:kl:koc' }), now)).toBe(false);
    expect(triggered({ ...watch, rainMm: null }, signal(), now)).toBe(false);
  });
  it('accepts only well-formed stored watches', () => {
    expect(parseWatch(watch)).toEqual(watch);
    for (const bad of [null, { ...watch, id: '' }, { ...watch, rainMm: -1 }, { ...watch, alerts: 'yes' }, { ...watch, rainMm: NaN }]) {
      expect(() => parseWatch(bad)).toThrow('Invalid watch');
    }
  });
});
