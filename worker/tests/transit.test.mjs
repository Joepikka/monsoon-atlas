import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MAX_POLLS_PER_DAY, TRANSIT_LIVE, isFresh, liveMarker } from '../src/transit.ts';

test('poll budget is 16 h at one call per 60 s', () => assert.equal(MAX_POLLS_PER_DAY, 960));

test('a position aged 120 s or more is never fresh, nor is a future or invalid one', () => {
  const now = 1_000_000_000;
  assert.equal(isFresh(now - 119_999, now), true);
  assert.equal(isFresh(now - 120_000, now), false);
  assert.equal(isFresh(now + 1, now), false);
  assert.equal(isFresh(Number.NaN, now), false);
});

test('live mode is unavailable while S38 is blocked, even for a fresh position', () => {
  assert.equal(TRANSIT_LIVE.available, false);
  assert.match(TRANSIT_LIVE.reason, /S38 blocked \(H04\)/);
  assert.equal(liveMarker(1_000, 1_000), false);
});
