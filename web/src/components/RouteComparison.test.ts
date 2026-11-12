import { describe, expect, it } from 'vitest';
import { parseRoute, ROUTE_LABEL } from './RouteComparison';

const guide = 'https://sdma.kerala.gov.in/disaster-memoranda/';
const unavailable = { label: ROUTE_LABEL, guidance_url: guide, status: 'unavailable', reason: 'no verified road network' };

describe('route comparison contract', () => {
  it('shows the unavailable and disabled states with their reason', () => {
    expect(parseRoute(unavailable).status).toBe('unavailable');
    expect(parseRoute({ ...unavailable, status: 'disabled' }).status).toBe('disabled');
  });
  it('refuses a route without the label, the guidance link, a reason or a known status', () => {
    expect(() => parseRoute({ ...unavailable, label: 'Safe route' })).toThrow('label');
    expect(() => parseRoute({ ...unavailable, guidance_url: '' })).toThrow('guidance');
    expect(() => parseRoute({ ...unavailable, reason: '' })).toThrow('status');
    expect(() => parseRoute({ ...unavailable, status: 'safe' })).toThrow('status');
  });
  it('accepts an experimental comparison', () => {
    const leg = { length_m: 1200, path: ['a', 'b'] };
    const r = { label: ROUTE_LABEL, guidance_url: guide, status: 'experimental', avoiding: leg,
      shortest: { ...leg, high_risk_edges: 1 } };
    expect(parseRoute(r).status).toBe('experimental');
  });
});
