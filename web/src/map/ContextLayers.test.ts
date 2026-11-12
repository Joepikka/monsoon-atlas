import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { buildingShown, parseContextLayers } from './ContextLayers';

// Written by atlas.spatial.context.layer_status() from the source contracts (T105 test keeps it in sync).
const fixture = JSON.parse(readFileSync(new URL('../../tests/fixtures/context-layers.json', import.meta.url), 'utf8'));

describe('context layer controls', () => {
  it('disables blocked layers with their reason and evidence', () => {
    const layers = parseContextLayers(fixture);
    expect(layers.filter(l => !l.available).map(l => l.layer)).toEqual(['rera']);
    expect(layers.find(l => l.layer === 'fire')?.note).toContain('not a confirmed fire');
    expect(buildingShown(0.74)).toBe(false);
    expect(buildingShown(0.75)).toBe(true);
  });
  it('refuses confirmed-fire wording, missing reasons and missing notes', () => {
    const edit = (layer: string, change: object) => fixture.map((l: { layer: string }) => l.layer === layer ? { ...l, ...change } : l);
    expect(() => parseContextLayers(edit('fire', { note: 'Confirmed structure fire' }))).toThrow('confirmed');
    expect(() => parseContextLayers(edit('rera', { reason: null }))).toThrow('reason');
    expect(() => parseContextLayers(edit('crime', { note: 'Crime rate' }))).toThrow('under-reporting');
    expect(() => parseContextLayers(edit('buildings', { evidence: '' }))).toThrow('evidence');
  });
});
