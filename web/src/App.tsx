import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { hasCoordinates, loadSnapshot, stateNames, type LayerKind, type Snapshot, type StateId, type ViewState } from './data';
import { currentSources, currentView, pollCurrentSources, type SourceUpdates } from './live-data';
import Layers, { layerConfigs, visibleRecords, type Coordinates } from './map/Layers';
import SourceBadge from './components/SourceBadge';
import EventTicker from './components/EventTicker';
import PlaceLens, { type NearbyFacility } from './components/PlaceLens';
import Watches, { signalsFrom } from './components/Watches';
import type { Want } from './map/Terrain';
import { t } from './i18n';
import { readShare, sourceNames } from './report';
import { localTime } from './time';
import './styles.css';

const MapView = lazy(() => import('./MapView').catch(() => ({ default: () =>
  <p className="map-message">The map could not load. The record list remains available.</p> })));

function CurrentStatus({ sources }: { sources: SourceUpdates }) {
  return <section className="data-status current-status" aria-labelledby="current-heading">
    <div><h3 id="current-heading">Active source updates</h3>
      <div role="status" aria-live="polite" aria-atomic="false"><ul>{currentSources.map(id => {
        const update = sources[id];
        return <li key={id} data-testid={`current-${id}`}>
          <strong>{id} · {sourceNames[id]}</strong>
          {update ? <>
            <p>Cutoff <time dateTime={update.asOf}>{localTime(update.asOf)}</time></p>
            <p>Last successful check <time dateTime={update.health.last_success_at}>{localTime(update.health.last_success_at)}</time></p>
            <p>Coverage · {update.health.status}. {update.health.detail}</p>
          </> : <p>{update === null ? 'Active update unavailable. Showing dated daily data where available.' : 'Awaiting first active check.'}</p>}
        </li>;
      })}</ul></div>
      <p>A limited warning feed cannot establish absence of hazards. Weather coverage is limited to the reported model grid points.</p>
    </div>
  </section>;
}

export default function App() {
  const [share] = useState(() => {
    try {
      const identity = readShare(window.location.search);
      if (identity && identity.state !== 'ka') throw new Error('This state has no released atlas yet.');
      return { identity, error: '' };
    } catch (error) {
      return { identity: null, error: error instanceof Error ? error.message : 'Invalid shared report.' };
    }
  });
  const [state, setState] = useState<StateId>('ka');
  const [radius, setRadius] = useState('25');
  const [want, setWant] = useState<Want>('flat'); // 2D stays the default; terrain and globe are opt-in
  const [attempt, setAttempt] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [active, setActive] = useState<Set<LayerKind>>(() => new Set(layerConfigs.map(layer => layer.kind)));
  const [center, setCenter] = useState<Coordinates | null>(null);
  const [nearby, setNearby] = useState<NearbyFacility[] | null>(null);
  const [clock, setClock] = useState(Date.now);
  const [view, setView] = useState<ViewState>({ status: 'loading', snapshot: null, message: '' });
  const [updates, setUpdates] = useState<SourceUpdates>({});
  const cache = useRef<Partial<Record<StateId, Snapshot>>>({});
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 60000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (share.error) { setView({ status: 'error', snapshot: null, message: share.error }); return; }
    const controller = new AbortController();
    const previous = cache.current[state] ?? null;
    setView({ status: 'loading', snapshot: previous, message: '' });
    loadSnapshot(state, previous, { signal: controller.signal, releaseHash: share.identity?.release, asOf: share.identity?.asOf }).then(result => {
      if (controller.signal.aborted) return;
      if (result.snapshot) cache.current[state] = result.snapshot;
      setView(result);
    });
    return () => controller.abort();
  }, [state, attempt, share]);
  const snapshot = view.snapshot;
  const pollingEnabled = state === 'ka' && snapshot?.state === state && !!snapshot.release_hash && !share.identity && !share.error;
  useEffect(() => {
    if (!pollingEnabled) { setUpdates({}); return; }
    return pollCurrentSources((source, update) => setUpdates(previous => ({ ...previous, [source]: update })));
  }, [pollingEnabled]);
  const display = useMemo(() => currentView(snapshot, pollingEnabled ? updates : {}), [snapshot, pollingEnabled, updates]);
  const records = useMemo(() => visibleRecords(display.records, active, center, Number(radius)), [display.records, active, center, radius]);
  const hasCurrent = currentSources.some(id => display.current[id]);
  const toggle = (kind: LayerKind) => setActive(previous => {
    const next = new Set(previous);
    if (next.has(kind)) next.delete(kind); else next.add(kind);
    return next;
  });
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
      <nav className="masthead-links" aria-label="Site">
        <a className="official-link" href="?page=ask">Ask</a>
        <a className="official-link" href="?page=findings">{t('nav.findings')}</a>
        <a className="official-link" href="?page=accuracy">Model accuracy</a>
        <a className="official-link" href="?page=climate">{t('nav.climate')}</a>
        <a className="official-link" href="?page=wall">{t('wall.title')}</a>
        <a className="official-link" href="?page=warnings">{t('nav.warnings')}</a>
        <a className="official-link" href="?page=transit">{t('nav.transit')}</a>
        <a className="official-link" href="?page=monsoon">{t('nav.monsoon')}</a>
        <a className="official-link" href="https://sachet.ndma.gov.in/" target="_blank" rel="noopener noreferrer">
          Official warnings <span aria-hidden="true">↗</span>
        </a>
      </nav>
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
        <label>{t('map.view')}<select aria-label={t('map.view')} value={want} onChange={e => setWant(e.target.value as Want)}>
          <option value="flat">{t('map.view_flat')}</option><option value="terrain">{t('map.view_terrain')}</option>
          <option value="globe">{t('map.view_globe')}</option>
        </select></label>
        <label className="snapshot-select">Snapshot<select aria-label="Snapshot" value={snapshot?.as_of ?? ''} disabled>
          <option value={snapshot?.as_of ?? ''}>{snapshot ? localTime(snapshot.as_of) : 'No release available'}</option>
        </select></label>
        <button className="refresh" onClick={() => setAttempt(n => n + 1)} disabled={view.status === 'loading'}>
          <span aria-hidden="true">↻</span> Refresh data
        </button>
      </div>

      <EventTicker records={records} now={clock} />
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
          {pollingEnabled && <CurrentStatus sources={display.current} />}
          <Layers sourceData={display} active={active} onToggle={toggle} center={center} onClear={() => setCenter(null)} />
          <section id="records" className="records" tabIndex={-1} aria-labelledby="records-heading">
            <div className="section-title"><h3 id="records-heading">In this view</h3><span>{records.length} records</span></div>
            {records.some(record => !hasCoordinates(record)) && <p className="location-note">Area-only warnings remain in this list. Their map geometry is unavailable.</p>}
            {records.length === 0 ? <div className="empty-records">
              <svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true"><path d="M6 32V12l10-4 12 4 10-4v24l-10 4-12-4-10 4zm10-24v24m12-20v24" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>
              <p>{snapshot ? hasCurrent ? 'No records match this view.' : 'No mapped records in this snapshot.' : 'Dated records will appear with their sources when a reviewed snapshot is released.'}</p>
              <p className="muted">An unavailable feed does not mean there are no hazards.</p>
            </div> : <ol className="record-list" data-testid="record-list">{records.map(record => <li key={record.id}>
              <button className="record-title" aria-pressed={selected === record.id} onClick={() => setSelected(record.id)}>{record.title}</button>
              {record.warning_text && <p className="location-note">{record.warning_text}</p>}
              {record.instruction && <p className="location-note">{record.instruction}</p>}
              {record.area_text && <p className="location-note">{record.area_text}</p>}
              <SourceBadge record={record} health={display.sources.find(source => source.source_id === record.source_id)} now={clock} />
              {record.location_note && <p className="location-note">{record.location_note}</p>}
              <a href={record.source_url} target="_blank" rel="noopener noreferrer">{record.source_id} · {sourceNames[record.source_id] ?? 'Original source'} ↗</a>
            </li>)}</ol>}
          </section>
          <PlaceLens snapshot={snapshot} shared={share.identity} now={clock} onNearby={setNearby} />
          {snapshot && <Watches places={snapshot.places.map(p => ({ id: p.place_id, label: p.name }))} signals={signalsFrom(display.records)} />}
          <div className="reading-key"><h3>How to read the atlas</h3><p>Official reports, model outputs, inferred and reconstructed items stay separately labelled. Dates belong to the source snapshot.</p></div>
        </section>

        <section className="map-panel" aria-label="Karnataka map">
          <div className="map-caption"><span className="map-cross" aria-hidden="true">⊕</span><span>{stateNames[state]}<small>{records.some(record => !hasCoordinates(record)) ? 'Mapped points & area warning list' : 'Map & matching record list'}</small></span></div>
          <Suspense fallback={<p className="map-message">Loading map…</p>}>
            <MapView records={records} selected={selected} onSelect={setSelected} center={center} onCenter={setCenter} want={want} facilities={nearby} />
          </Suspense>
          <div className="map-note">{snapshot ? hasCurrent ? 'Active source updates and dated daily records' : 'Records belong to the dated snapshot' : 'Basemap only · no released observations'}
            <small className="map-disclaimer">{t('map.disclaimer')}</small></div>
        </section>
      </div>
    </main>
    <footer className="site-footer"><span>Independent research · Not an emergency service</span><span>Monsoon Atlas / Karnataka first</span></footer>
  </>;
}
