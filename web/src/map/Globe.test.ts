import { describe, expect, it } from 'vitest';
import { applyGlobe, flyDuration, GLOBE_FLY_MS, wrapLongitude, wrapPoint } from './Globe';

describe('globe', () => {
  it('wraps longitudes into [-180, 180) across world copies', () => {
    expect(wrapLongitude(0)).toBe(0);
    expect(wrapLongitude(190)).toBe(-170);
    expect(wrapLongitude(-190)).toBe(170);
    expect(wrapLongitude(180)).toBe(-180);
    expect(wrapLongitude(-180)).toBe(-180);
    expect(wrapLongitude(540)).toBe(-180);
    expect(wrapLongitude(76.2 + 360)).toBeCloseTo(76.2, 9);
    expect(wrapPoint(-283.8, 14.5)[0]).toBeCloseTo(76.2, 9);
  });

  it('switches projection when the map can, and says so when it cannot', () => {
    const seen: unknown[] = [];
    expect(applyGlobe({ setProjection: p => seen.push(p) }, true)).toBe(true);
    expect(applyGlobe({ setProjection: p => seen.push(p) }, false)).toBe(true);
    expect(seen).toEqual([{ type: 'globe' }, { type: 'mercator' }]);
    expect(applyGlobe({}, true)).toBe(false);
  });

  it('has no animation under reduced motion', () => {
    const env = { webgl: true, contextLost: false, deviceMemoryGb: 8, reducedMotion: false };
    expect(flyDuration(env)).toBe(GLOBE_FLY_MS);
    expect(flyDuration({ ...env, reducedMotion: true })).toBe(0);
  });
});
