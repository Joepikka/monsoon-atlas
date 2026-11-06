import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { loadSnapshot, stateNames, type MapRecord, type Snapshot, type StateId, type ViewState } from './data';
import './styles.css';

const MapView = lazy(() => import('./MapView').catch(() => ({ default: () =>
  <p className="map-message">The map could not load. The record list remains available.</p> })));
const EMPTY: MapRecord[] = [];

export function localTime(value: string): string {
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata' }).format(new Date(value)) + ' IST';
}

export default function App() {
  const [state, setState] = useState<StateId>('ka');
  const [radius, setRadius] = useState('25');
  const [attempt, setAttempt] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<ViewState>({ status: 'loading', snapshot: null, message: '' });
  const cache = useRef<Partial<Record<StateId, Snapshot>>>({});
  useEffect(() => {
    const controller = new AbortController();
    const previous = cache.current[state] ?? null;
    setView({ status: 'loading', snapshot: previous, message: '' });
    loadSnapshot(state, previous, { signal: controller.signal }).then(result => {
      if (controller.signal.aborted) return;
      if (result.snapshot) cache.current[state] = result.snapshot;
      setView(result);
    });
    return () => controller.abort();
  }, [state, attempt]);
  const snapshot = view.snapshot;
  const records = snapshot?.records ?? EMPTY;
  const headline = view.status === 'loading' ? 'Loading snapshot'
    : view.status === 'empty' ? 'No released snapshot yet'
    : view.status === 'error' ? snapshot ? 'Refresh failed' : 'Snapshot unavailable'
    : view.status === 'stale' ? 'Dated snapshot' : 'Snapshot ready';

  return <>
    <a className="skip-link" href="#records">Skip to the record list</a>
    <header className="masthead">
      <div className="brand">
        <svg className="brand-mark" width="36" height="36" viewBox="0 0 36 36" aria-hidden="true">
          <circle cx="18" cy="18" r="15" fill="none" stroke="currentColor" />
          <path d="M18 5v7m0 12v7M5 18h7m12 0h7M18 11l5 12-5-3-5 3z" fill="currentColor" />
        </svg>
        <div><h1>Monsoon Atlas</h1><p>Weather, place &amp; evidence</p></div>
      </div>
      <a className="official-link" href="https://sachet.ndma.gov.in/" target="_blank" rel="noopener noreferrer">
        Official warnings <span aria-hidden="true">↗</span>
      </a>
    </header>

    <main className="atlas" aria-label="Atlas workspace">
      <div className="toolbar">
        <label>State<select aria-label="State" value={state} onChange={e => { setState(e.target.value as StateId); setSelected(null); }}>
          <option value="ka">Karnataka</option><option value="kl" disabled>Kerala · not released</option>
          <option value="dl" disabled>Delhi · not released</option>
        </select></label>
        <label>Radius<select aria-label="Radius" value={radius} onChange={e => setRadius(e.target.value)}>
          <option value="5">5 km</option><option value="10">10 km</option><option value="25">25 km</option><option value="50">50 km</option>
        </select></label>
        <label className="snapshot-select">Snapshot<select aria-label="Snapshot" value={snapshot?.as_of ?? ''} disabled>
          <option value={snapshot?.as_of ?? ''}>{snapshot ? localTime(snapshot.as_of) : 'No release available'}</option>
        </select></label>
        <button className="refresh" onClick={() => setAttempt(n => n + 1)} disabled={view.status === 'loading'}>
          <span aria-hidden="true">↻</span> Refresh data
        </button>
      </div>

      <div className="workspace">
        <section className="record-panel" aria-labelledby="region-heading">
          <div className="region-heading"><p className="eyebrow">STATE ATLAS / 01</p>
            <h2 id="region-heading">{stateNames[state]}</h2><p>Read the place. Check the source.</p></div>
          <div className={`data-status ${view.status}`} role="status" aria-live="polite">
            <span className="status-dot" aria-hidden="true" /><div><h3>{headline}</h3>
              {view.message && <p>{view.message}</p>}
              {snapshot && view.status === 'error' && <p>Showing the last approved snapshot.</p>}
              {snapshot && <p className="asof">As of <time data-testid="snapshot-time" dateTime={snapshot.as_of}>{localTime(snapshot.as_of)}</time></p>}
            </div>
          </div>
          <section id="records" className="records" tabIndex={-1} aria-labelledby="records-heading">
            <div className="section-title"><h3 id="records-heading">In this view</h3><span>{records.length} records</span></div>
            {records.length === 0 ? <div className="empty-records">
              <svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true"><path d="M6 32V12l10-4 12 4 10-4v24l-10 4-12-4-10 4zm10-24v24m12-20v24" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>
              <p>{snapshot ? 'No mapped records in this snapshot.' : 'Dated records will appear with their sources when a reviewed snapshot is released.'}</p>
              <p className="muted">An unavailable feed does not mean there are no hazards.</p>
            </div> : <ol className="record-list" data-testid="record-list">{records.map(record => <li key={record.id}>
              <span className={`provenance ${record.provenance}`}>{record.provenance}</span>
              <button className="record-title" aria-pressed={selected === record.id} onClick={() => setSelected(record.id)}>{record.title}</button>
              <time dateTime={record.valid_at}>{localTime(record.valid_at)}</time>
              {record.location_note && <p className="location-note">{record.location_note}</p>}
              <a href={record.source_url} target="_blank" rel="noopener noreferrer">{record.source_id} · Original source ↗</a>
            </li>)}</ol>}
          </section>
          <div className="reading-key"><h3>How to read the atlas</h3><p>Official reports, model outputs, inferred and reconstructed items stay separately labelled. Dates belong to the source snapshot.</p></div>
        </section>

        <section className="map-panel" aria-label="Karnataka map">
          <div className="map-caption"><span className="map-cross" aria-hidden="true">⊕</span><span>{stateNames[state]}<small>Map &amp; matching record list</small></span></div>
          <Suspense fallback={<p className="map-message">Loading map…</p>}>
            <MapView records={records} selected={selected} onSelect={setSelected} />
          </Suspense>
          <div className="map-note">{snapshot ? 'Records belong to the dated snapshot' : 'Basemap only · no released observations'}</div>
        </section>
      </div>
    </main>
    <footer className="site-footer"><span>Independent research · Not an emergency service</span><span>Monsoon Atlas / Karnataka first</span></footer>
  </>;
}
