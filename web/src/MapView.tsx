import { useEffect, useMemo, useRef, useState } from 'react';
import { Map, Marker, NavigationControl, setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';
import { hasCoordinates, type MapRecord } from './data';
import type { Coordinates } from './map/Layers';
import { hideInternationalBorders } from './map/Borders';
import Terrain, { browserEnv, chooseView, imageryFor, type MapLike, type Want } from './map/Terrain';
import Globe from './map/Globe';

setWorkerUrl(workerUrl);

interface NearbyPin { facility_id: string; kind: string; name: string; longitude: number; latitude: number; distance_km: number }
interface Props { records: MapRecord[]; selected: string | null; onSelect: (id: string) => void;
  center: Coordinates | null; onCenter: (center: Coordinates) => void; want?: Want; facilities?: NearbyPin[] | null }
const FACILITY_SYMBOL: Record<string, [string, string]> = { hospital: ['H', 'Hospital'], police: ['P', 'Police station'], fire_station: ['F', 'Fire station'] };

export default function MapView({ records, selected, onSelect, center, onCenter, want = 'flat', facilities = null }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<Map | null>(null);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState<Map | null>(null);
  const env = useMemo(browserEnv, []);
  const view = chooseView(env, want);
  useEffect(() => {
    if (!container.current) return;
    try {
      const instance = new Map({ container: container.current,
        style: 'https://tiles.openfreemap.org/styles/liberty',
        center: [76.2, 14.5], zoom: 6, attributionControl: { compact: true } });
      instance.addControl(new NavigationControl({ showCompass: false }), 'top-right');
      instance.on('style.load', () => hideInternationalBorders(instance));
      instance.on('error', () => setFailed(true));
      instance.on('load', () => { setFailed(false); setLoaded(instance); });
      instance.getCanvas().setAttribute('aria-label', 'Karnataka basemap; records are also listed');
      instance.getCanvas().setAttribute('role', 'img');
      instance.getCanvas().setAttribute('aria-description', 'Use arrow keys to pan. Press Enter to set the radius centre.');
      instance.on('click', event => onCenter([event.lngLat.lng, event.lngLat.lat]));
      instance.getCanvas().addEventListener('keydown', event => {
        if (event.key === 'Enter') {
          event.preventDefault();
          const point = instance.getCenter();
          onCenter([point.lng, point.lat]);
        }
      });
      map.current = instance;
      return () => { map.current = null; setLoaded(null); instance.remove(); };
    } catch { setFailed(true); }
  }, [onCenter]);
  useEffect(() => {
    if (!map.current) return;
    const markers = records.filter(hasCoordinates).map(record => {
      const element = document.createElement('button');
      element.type = 'button'; element.className = `map-pin ${record.provenance}`;
      element.setAttribute('aria-label', `View ${record.title}`);
      element.setAttribute('aria-pressed', String(record.id === selected));
      element.textContent = '•';
      element.addEventListener('click', event => { event.stopPropagation(); onSelect(record.id); });
      return new Marker({ element }).setLngLat([record.longitude, record.latitude]).addTo(map.current!);
    });
    return () => markers.forEach(marker => marker.remove());
  }, [records, selected, onSelect]);
  useEffect(() => {
    const record = records.find(row => row.id === selected);
    if (record && hasCoordinates(record) && map.current) map.current.flyTo({ center: [record.longitude, record.latitude],
      zoom: Math.max(map.current.getZoom(), 8), duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 500 });
  }, [selected, records]);
  useEffect(() => {
    if (!center || !map.current) return;
    const element = document.createElement('span');
    element.className = 'radius-centre'; element.textContent = '+';
    element.setAttribute('aria-label', 'Selected radius centre');
    element.setAttribute('role', 'img');
    const marker = new Marker({ element }).setLngLat(center).addTo(map.current);
    return () => { marker.remove(); };
  }, [center]);
  useEffect(() => {
    if (!facilities?.length || !map.current) return;
    const pins = facilities.map(item => {
      const [symbol, label] = FACILITY_SYMBOL[item.kind] ?? ['?', 'Facility'];
      const element = document.createElement('span');
      element.className = `facility-pin ${item.kind}`; element.textContent = symbol;
      element.setAttribute('role', 'img');
      element.setAttribute('aria-label', `${label}: ${item.name}, ${item.distance_km.toFixed(1)} km`);
      element.title = `${label}: ${item.name} (${item.distance_km.toFixed(1)} km, straight line)`;
      return new Marker({ element }).setLngLat([item.longitude, item.latitude]).addTo(map.current!);
    });
    const lons = facilities.map(f => f.longitude), lats = facilities.map(f => f.latitude);
    map.current.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
      { padding: 60, maxZoom: 14, duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 500 });
    return () => pins.forEach(pin => pin.remove());
  }, [facilities]);
  // S13 imagery stays off until a row with a reported date is fed in; no date is assumed.
  const imagery = useMemo(() => imageryFor(null), []);
  return <><div className="map-container" ref={container} />
    {want !== 'flat' && <>
      <Terrain map={loaded as MapLike | null} view={view} imagery={imagery} />
      <Globe map={loaded as MapLike | null} view={view} env={env} />
    </>}
    {failed && <p className="map-message">Map tiles unavailable. Dated records remain available in the list.</p>}
  </>;
}
