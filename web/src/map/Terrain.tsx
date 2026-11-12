// T186: terrain and satellite imagery for the map, from the attributed S14 (AWS Terrarium) and S13
// (NASA GIBS) records. Terrain exaggeration defaults to 1. The imagery date is the date S13 reported
// for the newest non-blank tile, never "today". WebGL loss or low memory falls back to the 2D map,
// or to the accessible record list. Tiles are only requested by the viewer's map; nothing is stored
// for later use. Mounted as an opt-in map view, off by default (D172); no S13 row is fed yet, so imagery says so.
import { useEffect } from 'react';
import { t } from '../i18n';

export const TERRAIN_EXAGGERATION = 1;
export const TERRAIN_SOURCE_ID = 'atlas-terrain-dem';
export const IMAGERY_SOURCE_ID = 'atlas-imagery';
export const TERRAIN_TILES = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'; // S14 BUCKET
export const TERRAIN_MAX_ZOOM = 15; // the S14 adapter rejects tiles above zoom 15
export const TERRAIN_ATTRIBUTION = 'Terrain: Mapzen, USGS (SRTM, GMTED2010), NOAA (ETOPO1)';
export const IMAGERY_MATRIX_SET = 'GoogleMapsCompatible_Level9'; // S13 MATRIX_SET
export const IMAGERY_HOST = 'gibs.earthdata.nasa.gov';
export const IMAGERY_ATTRIBUTION = 'Imagery: NASA GIBS (VIIRS on NOAA-20)';
export const LOW_MEMORY_GB = 2;

/** The slice of a MapLibre map these layers use; the pinned Map type is checked against it in tests. */
export interface MapLike {
  addSource(id: string, source: object): unknown;
  getSource(id: string): unknown;
  removeSource(id: string): unknown;
  addLayer(layer: object): unknown;
  getLayer(id: string): unknown;
  removeLayer(id: string): unknown;
  setTerrain(terrain: { source: string; exaggeration: number } | null): unknown;
  setProjection(projection: { type: 'globe' | 'mercator' }): unknown;
}

export type ViewEnv = { webgl: boolean; contextLost: boolean; deviceMemoryGb: number | null; reducedMotion: boolean };
export type Want = 'globe' | 'terrain' | 'flat';
export type View = { mode: Want | 'list'; reason: string | null };
export type ImageryRow = { layer_id: string; imagery_date: string; tile_template: string };
export type Imagery =
  | { state: 'available'; date: string; tiles: string; maxzoom: number; attribution: string; label: string }
  | { state: 'unavailable'; reason: string };

export function exaggeration(value?: number): number {
  if (value === undefined) return TERRAIN_EXAGGERATION;
  if (!Number.isFinite(value) || value <= 0) throw new Error('terrain exaggeration must be a positive number');
  return value;
}

export function detectEnv(
  nav: { deviceMemory?: number },
  canvas: () => { getContext(kind: string): unknown } | null,
  reducedMotion: boolean,
): ViewEnv {
  let webgl = false;
  try {
    const c = canvas();
    webgl = !!(c && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch { webgl = false; }
  return { webgl, contextLost: false, deviceMemoryGb: typeof nav.deviceMemory === 'number' ? nav.deviceMemory : null, reducedMotion };
}

export const browserEnv = (): ViewEnv => detectEnv(navigator as { deviceMemory?: number },() => document.createElement('canvas'),
  matchMedia('(prefers-reduced-motion: reduce)').matches);

/** Animation length: none when the viewer asked for reduced motion. */
export const motionMs = (env: ViewEnv, ms: number): number => (env.reducedMotion ? 0 : ms);

export function chooseView(env: ViewEnv, want: Want, globeInBuild = true): View {
  if (!env.webgl || env.contextLost) {
    return { mode: 'list', reason: t('terrain.no_webgl') };
  }
  if (want === 'flat') return { mode: 'flat', reason: null };
  if (env.deviceMemoryGb !== null && env.deviceMemoryGb <= LOW_MEMORY_GB) {
    return { mode: 'flat', reason: t('terrain.low_memory') };
  }
  if (want === 'globe' && !globeInBuild) return { mode: 'terrain', reason: t('terrain.globe_fallback') };
  return { mode: want, reason: null };
}

/** S13 row to a MapLibre raster source. A missing or malformed date shows no imagery and says so. */
export function imageryFor(row: ImageryRow | null): Imagery {
  const none = (reason: string): Imagery => ({ state: 'unavailable', reason });
  if (!row) return none(t('terrain.imagery_none'));
  if (!/^\d{4}-\d{2}-\d{2}$/.test(row.imagery_date)) return none(t('terrain.imagery_bad_date'));
  let url: URL;
  try { url = new URL(row.tile_template.replace(/\{(\w+)\}/g, 'x')); } catch { return none(t('terrain.imagery_bad_tile')); }
  if (url.protocol !== 'https:' || url.hostname !== IMAGERY_HOST) return none(t('terrain.imagery_bad_host'));
  const tiles = row.tile_template.replace('{Time}', row.imagery_date).replace('{TileMatrixSet}', IMAGERY_MATRIX_SET)
    .replace('{TileMatrix}', '{z}').replace('{TileRow}', '{y}').replace('{TileCol}', '{x}');
  return { state: 'available', date: row.imagery_date, tiles, maxzoom: Number(/Level(\d+)$/.exec(IMAGERY_MATRIX_SET)![1]),
    attribution: IMAGERY_ATTRIBUTION, label: t('terrain.imagery_label', { date: row.imagery_date }) };
}

export function terrainSpec(value?: number) {
  return {
    source: { type: 'raster-dem', tiles: [TERRAIN_TILES], tileSize: 256, encoding: 'terrarium', maxzoom: TERRAIN_MAX_ZOOM,
      attribution: TERRAIN_ATTRIBUTION },
    terrain: { source: TERRAIN_SOURCE_ID, exaggeration: exaggeration(value) },
  };
}

export function applyTerrain(map: MapLike, view: View, imagery: Imagery, value?: number): void {
  if (view.mode !== 'terrain' && view.mode !== 'globe') return;
  const { source, terrain } = terrainSpec(value);
  if (!map.getSource(TERRAIN_SOURCE_ID)) map.addSource(TERRAIN_SOURCE_ID, source);
  map.setTerrain(terrain);
  if (imagery.state === 'available' && !map.getSource(IMAGERY_SOURCE_ID)) {
    map.addSource(IMAGERY_SOURCE_ID, { type: 'raster', tiles: [imagery.tiles], tileSize: 256, maxzoom: imagery.maxzoom,
      attribution: imagery.attribution });
    map.addLayer({ id: IMAGERY_SOURCE_ID, type: 'raster', source: IMAGERY_SOURCE_ID });
  }
}

export function removeTerrain(map: MapLike): void {
  map.setTerrain(null);
  if (map.getLayer(IMAGERY_SOURCE_ID)) map.removeLayer(IMAGERY_SOURCE_ID);
  for (const id of [IMAGERY_SOURCE_ID, TERRAIN_SOURCE_ID]) if (map.getSource(id)) map.removeSource(id);
}

export function ViewFallback({ view }: { view: View }) {
  if (!view.reason) return null;
  return <p className="map-message" role="status">{view.reason}{view.mode === 'list' && ` ${t('terrain.list_suffix')}`}</p>;
}

export default function Terrain({ map, view, imagery, value }: { map: MapLike | null; view: View; imagery: Imagery; value?: number }) {
  useEffect(() => {
    if (!map) return;
    applyTerrain(map, view, imagery, value);
    return () => removeTerrain(map);
  }, [map, view, imagery, value]);
  return <div className="terrain-note"><ViewFallback view={view} />
    {(view.mode === 'terrain' || view.mode === 'globe') && <>
      <p>{t('terrain.exaggeration', { credit: TERRAIN_ATTRIBUTION, value: exaggeration(value) })}</p>
      {imagery.state === 'available' ? <p>{imagery.attribution}. {imagery.label}.</p> : <p role="status">{imagery.reason}</p>}
    </>}
  </div>;
}
