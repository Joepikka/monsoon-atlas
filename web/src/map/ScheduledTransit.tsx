// T104: scheduled transit layer. Every marker is a timetable estimate (S30), never live GPS;
// the S21 railway layer is a 2016 historical reference with no times as ETAs.
export const SCHEDULED_LABEL = 'Scheduled position (timetable estimate), not live';
export const RAIL_LABEL = '2016 timetable (historical reference), not a current schedule or ETA';

export type TransitMarker = {
  feed_id: string; source_revision: string; service_date: string; trip_id: string; route_id: string;
  status: 'moving' | 'at_stop' | 'paused'; pause_reason: string | null; lat: number | null; lon: number | null;
  label: string; live: false; approximate: boolean; uncertainty: string;
};
export type TransitStation = { id: string; name?: string; lat: number; lon: number; kind: string; feed_id?: string };
export type TransitFeed = { feed_id: string; source_revision: string; uncertainty: string; service_dates: string[] };
export type TransitSnapshot = {
  as_of: string; label: string; feeds: TransitFeed[]; markers: TransitMarker[]; stations: TransitStation[];
  rail: { label: string; mode: 'historical_reference' } | null;
};

export function parseTransit(value: unknown): TransitSnapshot {
  const data = value as TransitSnapshot;
  if (!data || data.label !== SCHEDULED_LABEL || !Array.isArray(data.markers) || !Array.isArray(data.feeds)) {
    throw new Error('not a scheduled-transit snapshot');
  }
  for (const m of data.markers) {
    if (m.live !== false || m.label !== SCHEDULED_LABEL) throw new Error('a transit marker claims to be live');
    if ((m.status === 'paused') !== (m.lat === null || m.lon === null)) throw new Error('a paused trip has a position');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(m.service_date)) throw new Error('marker without a service date');
  }
  if (data.rail && (data.rail.mode !== 'historical_reference' || data.rail.label !== RAIL_LABEL)) {
    throw new Error('railway layer must be historical reference only');
  }
  return data;
}

export function transitFeatures(snapshot: TransitSnapshot) {
  const markers = snapshot.markers.filter(m => m.status !== 'paused').map(m => ({
    type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [m.lon!, m.lat!] },
    properties: { kind: 'scheduled_vehicle', label: m.label, feed_id: m.feed_id, trip_id: m.trip_id,
      service_date: m.service_date, source_revision: m.source_revision, approximate: m.approximate },
  }));
  const stations = snapshot.stations.map(s => ({
    type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [s.lon, s.lat] },
    properties: { kind: s.kind, label: s.kind === 'railway_station' ? RAIL_LABEL : s.name ?? s.id, id: s.id },
  }));
  return { type: 'FeatureCollection' as const, features: [...markers, ...stations] };
}

export function feedCounts(snapshot: TransitSnapshot, feedId: string) {
  const own = snapshot.markers.filter(m => m.feed_id === feedId);
  return { moving: own.filter(m => m.status === 'moving').length, atStop: own.filter(m => m.status === 'at_stop').length,
    paused: own.filter(m => m.status === 'paused').length };
}

export default function ScheduledTransit({ snapshot }: { snapshot: TransitSnapshot }) {
  return <section className="scheduled-transit" aria-label="Scheduled transit">
    <h2>Scheduled transit <span className="badge">not live</span></h2>
    <p>{SCHEDULED_LABEL}. Times shown for {new Date(snapshot.as_of).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST.</p>
    <ul>{snapshot.feeds.map(feed => {
      const n = feedCounts(snapshot, feed.feed_id);
      return <li key={feed.feed_id} data-testid={`transit-${feed.feed_id}`}>
        <strong>{feed.feed_id.toUpperCase()}</strong> · revision {feed.source_revision.slice(0, 7)} · service date{' '}
        {feed.service_dates.join(', ') || 'none running'} · {n.moving} moving, {n.atStop} at a stop, {n.paused} paused
        (no shape or timetable gap)<br /><small>{feed.uncertainty}</small>
      </li>;
    })}</ul>
    <p>{snapshot.stations.length} stations shown{snapshot.rail ? `; railway stations: ${RAIL_LABEL}` : ''}.</p>
  </section>;
}
