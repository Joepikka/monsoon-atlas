import { useEffect, useRef, useState } from 'react';
import { Map, Marker, NavigationControl, setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { MapRecord } from './data';

setWorkerUrl(workerUrl);

interface Props { records: MapRecord[]; selected: string | null; onSelect: (id: string) => void }

export default function MapView({ records, selected, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<Map | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!container.current) return;
    try {
      const instance = new Map({ container: container.current,
        style: 'https://tiles.openfreemap.org/styles/liberty',
        center: [76.2, 14.5], zoom: 6, attributionControl: { compact: true } });
      instance.addControl(new NavigationControl({ showCompass: false }), 'top-right');
      instance.on('error', () => setFailed(true));
      instance.on('load', () => setFailed(false));
      instance.getCanvas().setAttribute('aria-label', 'Karnataka basemap; records are also listed');
      instance.getCanvas().setAttribute('role', 'img');
      map.current = instance;
      return () => { map.current = null; instance.remove(); };
    } catch { setFailed(true); }
  }, []);
  useEffect(() => {
    if (!map.current) return;
    const markers = records.map(record => {
      const element = document.createElement('button');
      element.type = 'button'; element.className = `map-pin ${record.provenance}`;
      element.setAttribute('aria-label', `View ${record.title}`);
      element.setAttribute('aria-pressed', String(record.id === selected));
      element.textContent = '•';
      element.addEventListener('click', () => onSelect(record.id));
      return new Marker({ element }).setLngLat([record.longitude, record.latitude]).addTo(map.current!);
    });
    return () => markers.forEach(marker => marker.remove());
  }, [records, selected, onSelect]);
  useEffect(() => {
    const record = records.find(row => row.id === selected);
    if (record && map.current) map.current.flyTo({ center: [record.longitude, record.latitude],
      zoom: Math.max(map.current.getZoom(), 8), duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 500 });
  }, [selected, records]);
  return <><div className="map-container" ref={container} />
    {failed && <p className="map-message">Map tiles unavailable. Dated records remain available in the list.</p>}
  </>;
}
