// D209: landing page. Karnataka's 30 districts raised in 3D by a chosen measure (MapLibre
// fill-extrusion, no extra library), headline numbers and the way into each analysis. Every
// value comes from committed results (findings.json) or the tracker (/data/ka/monsoon.json).
import { useEffect, useMemo, useRef, useState } from 'react';
import { Map, NavigationControl, setWorkerUrl, type GeoJSONSource } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';
import districts from '../ka-districts.json';
import { data as findings } from './Findings';
import { parseTracker, type Tracker } from './Monsoon';
import { districtFacts } from '../components/PlaceLens';

setWorkerUrl(workerUrl);

export type Metric = 'monsoon' | 'hospital' | 'trend';
type Spec = { label: string; unit: string; note: string; colors: [number, string][]; height: number };
export const METRICS: Record<Metric, Spec> = {
  monsoon: { label: 'Monsoon so far', unit: '% of normal', note: 'Southwest season rain as % of the 2001-2025 ERA5 normal (model, not gauges).',
    colors: [[40, '#b3261e'], [80, '#e07b39'], [100, '#e8e3c9'], [125, '#5fa8c7'], [160, '#1f4e8c']], height: 900 },
  hospital: { label: 'Far from a hospital', unit: '% of people over 10 km', note: 'Share of people more than 10 km in a straight line from an OpenStreetMap hospital.',
    colors: [[0, '#e8f1ec'], [10, '#a9d0b5'], [20, '#e0a458'], [40, '#9c2f1f']], height: 2600 },
  trend: { label: 'Rain trend since 1981', unit: '% of normal per decade', note: 'Sen slope of annual rain (IMD grid, as an index). Dark outline: significant after Benjamini-Hochberg.',
    colors: [[-4, '#b3261e'], [0, '#e8e3c9'], [6, '#5fa8c7'], [12, '#1f4e8c']], height: 9000 },
};

/** Value per district name for one measure; districts without a value are left out, never zero. */
export function values(metric: Metric, tracker: Tracker | null): globalThis.Map<string, number> {
  const out = new globalThis.Map<string, number>();
  if (metric === 'monsoon') for (const r of tracker?.rows ?? []) {
    if (r.season === 'southwest' && r.pct_of_median != null) out.set(r.district, r.pct_of_median);
  }
  if (metric === 'hospital') for (const d of findings.hospital.districts) out.set(d.district, +(d.share_beyond_10km * 100).toFixed(1));
  if (metric === 'trend') for (const r of findings.trends.rows) out.set(r.district, r.sen_pct_per_decade);
  return out;
}

const significant = new Set(findings.trends.rows.filter(r => r.fdr_q < 0.05).map(r => r.district));

function shapes(metric: Metric, tracker: Tracker | null) {
  const v = values(metric, tracker);
  return { ...districts, features: districts.features.map(f => ({ ...f,
    properties: { ...f.properties, value: v.get(f.properties.name) ?? null, sig: significant.has(f.properties.name) } })) };
}

const fetchTracker = () => fetch('/data/ka/monsoon.json', { cache: 'no-store' }).then(r => r.json());

export default function Overview({ load = fetchTracker }: { load?: () => Promise<unknown> }) {
  const [tracker, setTracker] = useState<Tracker | null>(null);
  const [metric, setMetric] = useState<Metric>('hospital');
  const [picked, setPicked] = useState('Yadgir');
  const [mapFailed, setMapFailed] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<Map | null>(null);
  const ready = useRef(false);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => { load().then(v => setTracker(parseTracker(v))).catch(() => {}); }, [load]);
  const data = useMemo(() => shapes(metric, tracker), [metric, tracker]);
  const spec = METRICS[metric];
  const ranked = useMemo(() => [...values(metric, tracker)].sort((a, b) => b[1] - a[1]), [metric, tracker]);

  useEffect(() => {
    if (!box.current || map.current) return;
    try {
      const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
      // Plain background, no basemap tiles: districts only, so nothing external can fail or
      // draw an international border (India mapping guidance).
      const m = new Map({ container: box.current,
        style: { version: 8, sources: {}, layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#dfe7e4' } }] },
        bounds: [[74.0, 11.5], [78.6, 18.5]], fitBoundsOptions: { padding: 30 }, pitch: 50, bearing: -14,
        attributionControl: { compact: true } });
      m.addControl(new NavigationControl({ visualizePitch: true }), 'top-right');
      m.on('error', () => { if (!ready.current) setMapFailed(true); });
      m.on('load', () => {
        ready.current = true;
        m.addSource('districts', { type: 'geojson', data: shapes('hospital', null) as never });
        m.addLayer({ id: 'district-3d', type: 'fill-extrusion', source: 'districts', paint: {
          'fill-extrusion-color': '#ccc', 'fill-extrusion-height': 0, 'fill-extrusion-opacity': 0.88 } });
        m.addLayer({ id: 'district-line', type: 'line', source: 'districts', paint: { 'line-color': '#0b2730', 'line-width': 0.6 } });
        m.on('click', 'district-3d', e => {
          const name = e.features?.[0]?.properties?.name; if (typeof name === 'string') setPicked(name);
        });
        m.on('mouseenter', 'district-3d', () => { m.getCanvas().style.cursor = 'pointer'; });
        m.on('mouseleave', 'district-3d', () => { m.getCanvas().style.cursor = ''; });
        if (!still) m.easeTo({ bearing: -24, duration: 2400 });
        setLoaded(true);
      });
      m.getCanvas().setAttribute('aria-label', 'Three-dimensional map of Karnataka districts; the same values are in the table below');
      map.current = m;
    } catch { setMapFailed(true); }
    return () => { map.current?.remove(); map.current = null; ready.current = false; setLoaded(false); };
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m || !loaded) return;
    (m.getSource('districts') as GeoJSONSource).setData(data as never);
    const stops = spec.colors.flatMap(([v, c]) => [v, c]);
    m.setPaintProperty('district-3d', 'fill-extrusion-color', ['case', ['==', ['get', 'name'], picked], '#f2b84b',
      ['==', ['get', 'value'], null], '#d9d9d9', ['interpolate', ['linear'], ['get', 'value'], ...stops]]);
    m.setPaintProperty('district-3d', 'fill-extrusion-height',
      ['case', ['==', ['get', 'value'], null], 0, ['*', ['abs', ['get', 'value']], spec.height]]);
    m.setPaintProperty('district-line', 'line-width', metric === 'trend' ? ['case', ['get', 'sig'], 2.2, 0.5] : 0.6);
  }, [data, spec, metric, loaded, picked]);


  const facts = districtFacts(picked, tracker);
  const s = findings.hospital.statewide;
  return <main className="overview" aria-labelledby="overview-heading">
    <section className="ov-hero">
      <p className="ov-eyebrow">Karnataka · open data · tested methods</p>
      <h1 id="overview-heading">Monsoon, access and risk across Karnataka's 30 districts</h1>
      <p className="ov-lead">An open-data atlas built at Rs 0: rain against normal, how far people live from hospitals and buses,
        and a drought model that has to beat simple rules before it is shown. Every number links to its method and limits.</p>
      <dl className="ov-kpis">
        <div><dt>People covered</dt><dd>{(s.people / 1e6).toFixed(1)} M</dd></div>
        <div><dt>Median km to a hospital</dt><dd>{s.median_km}</dd></div>
        <div><dt>Districts with rising rain</dt><dd>{findings.trends.significant} of {findings.trends.tested}</dd></div>
        <div><dt>Bengaluru within 500 m of a bus</dt><dd>{(findings.bus.covered_share * 100).toFixed(1)}%</dd></div>
      </dl>
    </section>

    <section className="ov-map-wrap" aria-labelledby="ov-map-heading">
      <div className="ov-map-head">
        <h2 id="ov-map-heading">Explore the districts in 3D</h2>
        <div className="ov-switch" role="radiogroup" aria-label="Measure shown on the map">
          {(Object.keys(METRICS) as Metric[]).map(k => <button key={k} type="button" role="radio" aria-checked={metric === k}
            className={metric === k ? 'on' : ''} onClick={() => setMetric(k)}>{METRICS[k].label}</button>)}
        </div>
      </div>
      <p className="ov-note">{spec.note} Height and colour show the value; drag to rotate, scroll to zoom, click a district.</p>
      <div className="ov-grid">
        <div className="ov-map">
          {mapFailed ? <p role="status" className="ov-map-fail">The 3D map could not load here. The values are in the table below.</p>
            : <div ref={box} className="ov-canvas" />}
          <div className="ov-legend" aria-hidden="true">
            <span>{spec.unit}</span>
            <i style={{ background: `linear-gradient(90deg, ${spec.colors.map(c => c[1]).join(',')})` }} />
            <span>{spec.colors[0][0]}</span><span>{spec.colors[spec.colors.length - 1][0]}+</span>
          </div>
        </div>
        <aside className="ov-panel" aria-live="polite">
          <label htmlFor="ov-district">District</label>
          <select id="ov-district" value={picked} onChange={e => setPicked(e.target.value)}>
            {districts.features.map(f => <option key={f.properties.name}>{f.properties.name}</option>)}
          </select>
          <h3>{picked}</h3>
          <ul>{facts.map(f => <li key={f.label}><span>{f.label}</span><strong>{f.value}</strong><small>{f.note}</small></li>)}</ul>
          <a className="ov-cta" href="?page=map">Open the full map</a>
        </aside>
      </div>
      <details className="ov-table"><summary>All 30 districts, {spec.label.toLowerCase()} ({spec.unit})</summary>
        <div tabIndex={0} role="region" aria-label={`${spec.label} by district`}>
          <table><thead><tr><th scope="col">Rank</th><th scope="col">District</th><th scope="col">{spec.unit}</th></tr></thead>
            <tbody>{ranked.map(([name, v], i) => <tr key={name}><td>{i + 1}</td><th scope="row">{name}</th><td>{v}</td></tr>)}</tbody></table>
        </div>
      </details>
      <p className="ov-credit">{districts.attribution}.</p>
    </section>

    <section aria-labelledby="ov-go-heading">
      <h2 id="ov-go-heading">Go deeper</h2>
      <ul className="ov-cards">
        {[
          ['?page=findings', 'Data findings', 'Six analyses with charts: hospital equity, rain trends, bus access, the drought model and its checks.'],
          ['?page=monsoon', 'Monsoon tracker', 'This season in every district against 25 years of normals.'],
          ['?page=accuracy', 'Model accuracy', 'Every model, its baseline and why 18 of 20 are blocked rather than guessed.'],
          ['?page=transit', 'Bus access', 'Bengaluru 1 km squares by the share of people within a 500 m walk of a bus.'],
          ['?page=ask', 'Ask the project', 'Cited answers from the project documents (search-based, research-only).'],
          ['?page=map', 'Map and Place Lens', 'Pick a district: forecast, warnings, nearby hospitals with Google Maps links.'],
        ].map(([href, title, text]) => <li key={href}><a href={href}><strong>{title}</strong><span>{text}</span></a></li>)}
      </ul>
    </section>
  </main>;
}
