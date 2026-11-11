// T186: globe projection for the map (MapLibre setProjection, present in the pinned maplibre-gl
// 6.16.0; the build type-checks the call). A build or browser without it reports "Globe unavailable
// in this build" and keeps the flat map. The globe has no world copies, so any longitude read from
// a click is wrapped into [-180, 180) before it is used. Reduced motion removes animation.
// Mounted as an opt-in map view (D172).
import { useEffect } from 'react';
import { t } from '../i18n';
import { type MapLike, motionMs, type View, type ViewEnv } from './Terrain';

export const GLOBE_FLY_MS = 800;

export const wrapLongitude = (lon: number): number => ((((lon + 180) % 360) + 360) % 360) - 180;
export const wrapPoint = (lon: number, lat: number): [number, number] => [wrapLongitude(lon), lat];

/** True when the projection was changed; false when this map cannot do it. */
export function applyGlobe(map: Partial<MapLike>, on: boolean): boolean {
  if (typeof map.setProjection !== 'function') return false;
  map.setProjection({ type: on ? 'globe' : 'mercator' });
  return true;
}

export const flyDuration = (env: ViewEnv): number => motionMs(env, GLOBE_FLY_MS);

export default function Globe({ map, view, env }: { map: MapLike | null; view: View; env: ViewEnv }) {
  const wanted = view.mode === 'globe';
  useEffect(() => {
    if (!map) return;
    applyGlobe(map, wanted);
    return () => { applyGlobe(map, false); };
  }, [map, wanted]);
  const missing = wanted && map !== null && typeof map.setProjection !== 'function';
  return <p className="globe-note" role="status">
    {missing ? t('globe.unavailable') : wanted ? (env.reducedMotion ? t('globe.on_reduced', { ms: flyDuration(env) })
      : t('globe.on', { ms: flyDuration(env) })) : ''}
  </p>;
}
