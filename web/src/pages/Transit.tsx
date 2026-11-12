// D191: ?page=transit, Bengaluru bus access (T041). Derived numbers only: per 1 km cell, the share of
// people within a 500 m walk of a BMTC stop with scheduled service. The restricted S30 timetable is
// never shown (no stops, routes or times). Owner approved publishing these derived shares.
import { useEffect, useRef, useState } from 'react';
import { Map, NavigationControl, setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';
import { hideInternationalBorders } from '../map/Borders';
import { t } from '../i18n';
import '../styles.css';

setWorkerUrl(workerUrl);

export interface Coverage {
  district: string; service_date: string; radius_m: number; cell_deg: number;
  population: { total: number; covered: number; covered_share: number };
  limits: string[]; credit: string; cells: [number, number, number, number][];
}

export const BANDS: [number, string, string][] = [
  [0.25, '#b3261e', 'under 25%'], [0.5, '#e07b39', '25 to 50%'], [0.75, '#e8c547', '50 to 75%'], [1.01, '#2e8b57', '75% or more'],
];

export function cellsGeoJson(data: Coverage) {
  const h = data.cell_deg / 2;
  return {
    type: 'FeatureCollection' as const,
    features: data.cells.filter(([, , pop]) => pop > 0).map(([lon, lat, pop, frac]) => ({
      type: 'Feature' as const,
      properties: { pop, frac, color: BANDS.find(([max]) => frac < max)![1] },
      geometry: { type: 'Polygon' as const, coordinates: [[[lon - h, lat - h], [lon + h, lat - h], [lon + h, lat + h], [lon - h, lat + h], [lon - h, lat - h]]] },
    })),
  };
}

const loadCoverage = () => import('../transit-coverage.json').then(m => m.default as unknown as Coverage);

export default function Transit({ load = loadCoverage }: { load?: () => Promise<Coverage> }) {
  const [data, setData] = useState<Coverage | null>(null);
  const [failed, setFailed] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => { load().then(setData, () => setFailed(true)); }, [load]);
  useEffect(() => {
    if (!data || !box.current) return;
    try {
      const map = new Map({ container: box.current, style: 'https://tiles.openfreemap.org/styles/liberty',
        center: [77.59, 12.97], zoom: 9.5, attributionControl: { compact: true } });
      map.addControl(new NavigationControl({ showCompass: false }), 'top-right');
      map.getCanvas().setAttribute('aria-label', 'Bengaluru 1 km cells coloured by bus access; numbers are also listed');
      map.on('style.load', () => hideInternationalBorders(map));
      map.on('load', () => {
        map.addSource('cells', { type: 'geojson', data: cellsGeoJson(data) });
        map.addLayer({ id: 'cells', type: 'fill', source: 'cells', paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.55 } });
      });
      map.on('error', () => setFailed(true));
      return () => map.remove();
    } catch { setFailed(true); }
  }, [data]);
  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
  return <main className="dashboard" aria-labelledby="transit-heading">
    <p><a href="./">{t('ask.back')}</a></p>
    <h1 id="transit-heading">{t('transit.title')}</h1>
    {data && <>
      <p className="headline">{t('transit.headline', { share: pct(data.population.covered_share),
        total: (data.population.total / 1e6).toFixed(2), radius: data.radius_m })}</p>
      <p>{t('transit.date', { date: data.service_date })}</p>
      <ul className="legend" aria-label={t('transit.legend')}>{BANDS.map(([, color, label]) =>
        <li key={label}><span className="swatch" style={{ background: color }} aria-hidden="true" /> {label}</li>)}</ul>
      <div className="map-container transit-map" ref={box} />
      {failed && <p className="map-message">{t('transit.mapfailed')}</p>}
      <h2>{t('transit.limits')}</h2>
      <ul>{data.limits.map(l => <li key={l}>{l}</li>)}</ul>
      <p className="credit">{data.credit}</p>
    </>}
  </main>;
}
