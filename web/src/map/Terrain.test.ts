import { describe, expect, it } from 'vitest';
import type { Map as MapLibre } from 'maplibre-gl';
import {
  applyTerrain, chooseView, detectEnv, imageryFor, IMAGERY_SOURCE_ID, motionMs, removeTerrain, terrainSpec,
  TERRAIN_EXAGGERATION, TERRAIN_SOURCE_ID, type MapLike, type ViewEnv,
} from './Terrain';

// Compile-time proof that the pinned MapLibre Map has every method these layers call.
export const pinnedMapFits = (map: MapLibre): MapLike => map;

const env = (over: Partial<ViewEnv> = {}): ViewEnv => ({ webgl: true, contextLost: false, deviceMemoryGb: 8, reducedMotion: false, ...over });
const template = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_NOAA20_CorrectedReflectance_TrueColor/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpeg';
const row = { layer_id: 'VIIRS_NOAA20_CorrectedReflectance_TrueColor', imagery_date: '2026-11-09', tile_template: template };

function fakeMap() {
  const sources = new Set<string>(); const layers = new Set<string>(); const calls: unknown[] = [];
  const map: MapLike = {
    addSource: id => sources.add(id), getSource: id => (sources.has(id) ? {} : undefined), removeSource: id => sources.delete(id),
    addLayer: l => layers.add((l as { id: string }).id), getLayer: id => (layers.has(id) ? {} : undefined), removeLayer: id => layers.delete(id),
    setTerrain: t => calls.push(t), setProjection: p => calls.push(p),
  };
  return { map, sources, layers, calls };
}

describe('terrain', () => {
  it('defaults exaggeration to 1 and rejects nonsense', () => {
    expect(TERRAIN_EXAGGERATION).toBe(1);
    expect(terrainSpec().terrain).toEqual({ source: TERRAIN_SOURCE_ID, exaggeration: 1 });
    expect(terrainSpec().source).toMatchObject({ type: 'raster-dem', encoding: 'terrarium', maxzoom: 15 });
    expect(terrainSpec(2).terrain.exaggeration).toBe(2);
    for (const bad of [0, -1, Number.NaN, Infinity]) expect(() => terrainSpec(bad)).toThrow();
  });

  it('shows the S13 imagery date and builds a MapLibre tile address', () => {
    const imagery = imageryFor(row);
    expect(imagery).toMatchObject({ state: 'available', date: '2026-11-09', maxzoom: 9 });
    if (imagery.state !== 'available') throw new Error('unreachable');
    expect(imagery.tiles).toBe(template.replace('{Time}', '2026-11-09').replace('{TileMatrixSet}', 'GoogleMapsCompatible_Level9')
      .replace('{TileMatrix}', '{z}').replace('{TileRow}', '{y}').replace('{TileCol}', '{x}'));
    expect(imagery.label).toContain('2026-11-09');
    expect(imagery.attribution).toContain('NASA GIBS');
  });

  it('shows terrain without imagery when tile imagery is missing, never a guessed date', () => {
    expect(imageryFor(null)).toMatchObject({ state: 'unavailable' });
    expect(imageryFor({ ...row, imagery_date: '' })).toMatchObject({ state: 'unavailable' });
    expect(imageryFor({ ...row, imagery_date: 'today' })).toMatchObject({ state: 'unavailable' });
    expect(imageryFor({ ...row, tile_template: 'https://example.org/{Time}.jpeg' })).toMatchObject({ state: 'unavailable' });
    expect(imageryFor({ ...row, tile_template: 'http://gibs.earthdata.nasa.gov/{Time}.jpeg' })).toMatchObject({ state: 'unavailable' });
    expect(imageryFor({ ...row, tile_template: 'not a url' })).toMatchObject({ state: 'unavailable' });
    const { map, sources, calls } = fakeMap();
    applyTerrain(map, { mode: 'terrain', reason: null }, imageryFor(null));
    expect([...sources]).toEqual([TERRAIN_SOURCE_ID]);
    expect(calls).toEqual([{ source: TERRAIN_SOURCE_ID, exaggeration: 1 }]);
  });

  it('adds then removes its sources and layer, and does nothing in 2D or list mode', () => {
    const { map, sources, layers, calls } = fakeMap();
    applyTerrain(map, { mode: 'flat', reason: null }, imageryFor(row));
    applyTerrain(map, { mode: 'list', reason: 'x' }, imageryFor(row));
    expect(sources.size + layers.size + calls.length).toBe(0);
    applyTerrain(map, { mode: 'terrain', reason: null }, imageryFor(row));
    applyTerrain(map, { mode: 'terrain', reason: null }, imageryFor(row)); // idempotent
    expect([...sources].sort()).toEqual([IMAGERY_SOURCE_ID, TERRAIN_SOURCE_ID].sort());
    expect([...layers]).toEqual([IMAGERY_SOURCE_ID]);
    removeTerrain(map);
    expect(sources.size + layers.size).toBe(0);
    expect(calls.at(-1)).toBeNull();
  });
});

describe('view choice', () => {
  it('falls back to the accessible list when WebGL is unavailable or lost', () => {
    const noGl = detectEnv({}, () => ({ getContext: () => null }), false);
    expect(noGl.webgl).toBe(false);
    expect(chooseView(noGl, 'globe')).toMatchObject({ mode: 'list' });
    expect(chooseView(env({ contextLost: true }), 'terrain').mode).toBe('list');
    expect(detectEnv({}, () => { throw new Error('boom'); }, false).webgl).toBe(false);
    expect(detectEnv({}, () => null, false).webgl).toBe(false);
    expect(chooseView(noGl, 'flat').reason).toContain('WebGL');
  });

  it('keeps the flat map on low memory and without a globe in the build', () => {
    expect(detectEnv({ deviceMemory: 1 }, () => ({ getContext: () => ({}) }), false)).toMatchObject({ webgl: true, deviceMemoryGb: 1 });
    expect(chooseView(env({ deviceMemoryGb: 2 }), 'terrain')).toMatchObject({ mode: 'flat' });
    expect(chooseView(env({ deviceMemoryGb: null }), 'terrain')).toEqual({ mode: 'terrain', reason: null });
    expect(chooseView(env(), 'globe')).toEqual({ mode: 'globe', reason: null });
    expect(chooseView(env(), 'globe', false)).toEqual({ mode: 'terrain', reason: 'Globe unavailable in this build; terrain is shown.' });
    expect(chooseView(env({ deviceMemoryGb: 1 }), 'flat').reason).toBeNull();
  });

  it('removes animation under reduced motion', () => {
    expect(motionMs(env({ reducedMotion: true }), 800)).toBe(0);
    expect(motionMs(env(), 800)).toBe(800);
  });
});
