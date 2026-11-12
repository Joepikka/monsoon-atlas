import { useMemo, useState } from 'react';
import type { FacilityKind, MapRecord, Snapshot } from '../data';
import { buildReport, shareUrl, sourceNames, type PlaceReport, type ShareIdentity } from '../report';
import { localTime } from '../time';
import SourceBadge from './SourceBadge';

const tabs = ['Now', 'Risk', 'Forecast', 'History', 'Nearby', 'Sources'] as const;
type Tab = typeof tabs[number];
const facilityLabel: Record<FacilityKind, string> = { hospital: 'Hospital', police: 'Police station', fire_station: 'Fire station' };

function Records({ records, snapshot, now }: { records: MapRecord[]; snapshot: Snapshot; now: number }) {
  return <ul className="lens-records">{records.map(record => <li key={record.id}>
    <h4>{record.title}</h4>
    {record.warning_text && <p>{record.warning_text}</p>}
    {record.instruction && <p>{record.instruction}</p>}
    {record.area_text && <p>{record.area_text}</p>}
    {record.spatial_scope === 'area' && <p>Statewide area-warning context; inclusion does not establish an incident at this place.</p>}
    {record.model_id && <p>{record.model_id} · {record.model_status?.replaceAll('_', ' ')}</p>}
    <SourceBadge record={record} health={snapshot.sources.find(source => source.source_id === record.source_id)} now={now} />
    {record.location_note && <p>{record.location_note}</p>}
    <a href={record.source_url} target="_blank" rel="noopener noreferrer">{record.source_id} · Original source</a>
  </li>)}</ul>;
}

function ReportSection({ tab, report, snapshot, now }: { tab: Tab; report: PlaceReport; snapshot: Snapshot; now: number }) {
  if (tab === 'Risk') return <>
    <p>Scores are specific to a versioned place and model release. They do not guarantee safety.</p>
    {report.modelOutputs.length ? <Records records={report.modelOutputs} snapshot={snapshot} now={now} /> : <p>No released risk score for this place.</p>}
  </>;
  if (tab === 'Forecast') return <>
    <p>Forecast validity is compared with the report cutoff, not today's date.</p>
    {report.forecasts.length ? <Records records={report.forecasts} snapshot={snapshot} now={now} /> : <p>No future forecast is included at this cutoff.</p>}
  </>;
  if (tab === 'Nearby') return <>
    <p>Approximate straight-line distances from the place representative point, within 25 km. These are not walking distances or safe routes. Opening hours and current operation are not verified.</p>
    {report.facilities.length ? <ul className="lens-records">{report.facilities.map(item => <li key={item.facility_id}>
      <h4>{item.name}</h4><p>{facilityLabel[item.kind]} · {item.distance_km.toFixed(1)} km · {item.verification_status.replaceAll('_', ' ')}</p>
      <p>Fetched <time dateTime={item.fetched_at}>{localTime(item.fetched_at)}</time></p>
      <a href={item.source_url} target="_blank" rel="noopener noreferrer">OpenStreetMap · Original source</a>
    </li>)}</ul> : <p>Facility data is unavailable.</p>}
  </>;
  if (tab === 'Sources') return <>
    <p>Place boundary licence: {report.place.licence_id}. Source names and dates belong to this frozen report.</p>
    <ul className="lens-sources">{report.sources.map(source => <li key={source.id + source.url}>
      <a href={source.url} target="_blank" rel="noopener noreferrer">{sourceNames[source.id] ?? source.id}</a>
      <span>{source.id} · {source.url}</span>
    </li>)}</ul>
  </>;
  const records = tab === 'History' ? report.records.filter(record => Date.parse(record.valid_at) <= Date.parse(report.as_of)) : report.records;
  return <>
    <p>{tab === 'History' ? 'Past validity times included in this snapshot. This is not a complete historical archive.' : 'Known at the report cutoff. This dated view is not a statement of current conditions.'}</p>
    <p>Point records are within 25 km of the place representative point. Area warnings remain statewide context.</p>
    {records.length ? <Records records={records} snapshot={snapshot} now={now} /> : <p>No matching records are included.</p>}
  </>;
}

export default function PlaceLens({ snapshot, shared, now }: { snapshot: Snapshot | null; shared: ShareIdentity | null; now: number }) {
  const [selection, setSelection] = useState<{ place: string; boundary: string } | null>(shared);
  const [tab, setTab] = useState<Tab>('Now');
  const result = useMemo(() => {
    if (!snapshot || !selection) return { report: null, error: '' };
    try { return { report: buildReport(snapshot, selection.place, selection.boundary), error: '' }; }
    catch (error) { return { report: null, error: error instanceof Error ? error.message : 'The report could not be built.' }; }
  }, [snapshot, selection]);
  const { report, error } = result;
  const selectedIndex = snapshot?.places.findIndex(place => place.place_id === selection?.place && place.boundary_version === selection?.boundary) ?? -1;
  return <>
    <section className="place-lens" aria-label="Place Lens">
      <p className="eyebrow">PLACE LENS</p><h3>One place, dated evidence</h3>
      <label className="place-select">Place<select aria-label="Place" value={selectedIndex < 0 ? '' : String(selectedIndex)} disabled={!snapshot?.places.length}
        onChange={event => { const place = snapshot?.places[Number(event.target.value)]; setSelection(event.target.value && place ? { place: place.place_id, boundary: place.boundary_version } : null); }}>
        <option value="">{snapshot?.places.length ? 'Choose a place' : 'Place boundaries unavailable'}</option>
        {snapshot?.places.map((place, index) => <option key={place.place_id + place.boundary_version} value={index}>{place.name} · {place.kind}</option>)}
      </select></label>
      {error && <p role="alert">{error}</p>}
      {report && <>
        <div className="report-identity"><h4>{report.place.name}</h4>
          <p>Report cutoff <time data-testid="report-cutoff" dateTime={report.as_of}>{localTime(report.as_of)}</time></p>
          <p>Boundary <span>{report.place.boundary_version}</span></p><p>{report.place.location_note}</p>
        </div>
        <div className="lens-tabs" role="tablist" aria-label="Place report sections">
          {tabs.map((name, index) => <button key={name} id={`lens-tab-${name}`} type="button" role="tab" aria-selected={tab === name}
            aria-controls="lens-panel" tabIndex={tab === name ? 0 : -1} onClick={() => setTab(name)}
            onKeyDown={event => {
              const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length
                : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : -1;
              if (next >= 0) { event.preventDefault(); setTab(tabs[next]); document.getElementById(`lens-tab-${tabs[next]}`)?.focus(); }
            }}>{name}</button>)}
        </div>
        <div id="lens-panel" role="tabpanel" aria-labelledby={`lens-tab-${tab}`} tabIndex={0}>
          <ReportSection tab={tab} report={report} snapshot={snapshot!} now={now} />
        </div>
        <div className="report-actions"><a href={shareUrl(window.location.href, report)}>Open frozen report</a>
          <button type="button" onClick={() => window.print()}>Print / Save PDF</button></div>
      </>}
    </section>
    {report && <article className="print-report" data-testid="print-report" aria-label="Printable place report">
      <h1>Monsoon Atlas · {report.place.name}</h1><p>Not an emergency service.</p>
      <p>Report cutoff <time dateTime={report.as_of}>{localTime(report.as_of)}</time></p>
      <p>State: {report.state} · Place ID: {report.place.place_id}</p><p>Boundary: <span>{report.place.boundary_version}</span></p>
      <p>{report.place.location_note}</p><p>Release: {report.release_id}</p><p className="report-hash">SHA256: {report.release_hash}</p>
      {tabs.map(name => <section key={name}><h2>{name}</h2><ReportSection tab={name} report={report} snapshot={snapshot!} now={now} /></section>)}
      <p>Official reports, model outputs, inferred and reconstructed items remain separately labelled. A missing feed does not mean there are no hazards. No routing is promised to be safe.</p>
    </article>}
  </>;
}
