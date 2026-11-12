import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { parseSnapshot } from './data';
import { buildReport } from './report';

// Written by atlas.publish.build_release (tests/test_publish.py keeps it in sync), D185.
const release = JSON.parse(readFileSync(new URL('../tests/fixtures/release-ka.json', import.meta.url), 'utf8'));

describe('a Python-built Karnataka release', () => {
  it('passes the browser validator and feeds the Place Lens', () => {
    const snapshot = parseSnapshot(release, 'ka');
    expect(snapshot.sources.map(s => s.source_id)).toEqual(['S01', 'S09']);
    expect(snapshot.places).toHaveLength(1);
    const place = snapshot.places[0];
    const report = buildReport({ ...snapshot, release_hash: 'f'.repeat(64) }, place.place_id, place.boundary_version);
    expect(report.facilities.length).toBeGreaterThan(0);
    expect(report.facilities.every(f => f.distance_km <= 25)).toBe(true);
  });
});
