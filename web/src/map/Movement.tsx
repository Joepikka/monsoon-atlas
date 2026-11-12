// T187: aircraft, satellite, earthquake and ship overlays. A layer renders only when its source
// contract says so (enabled, available, licence open; web/tests/fixtures/movement-layers.json is
// written by atlas.spatial.orbits.movement_status() and a Python test keeps it equal). Aircraft
// older than AIRCRAFT_MAX_AGE_S are hidden and carry no callsign, registration or owner. Satellite
// positions exist only as predictions from dated orbit elements. Earthquakes show the USGS
// revision time and a source link. Ships stay hidden while S26 is blocked. This file makes no
// network request, so there is one upstream poll per region, made server side. Built, not
// mounted: S12 and S20 wait for the owner's licence review (H11) and propagation is unavailable
// (D153).
import { localTime } from '../time';

export const AIRCRAFT_MAX_AGE_S = 300; // equals atlas.ingest.s10.MAX_AGE_S; a Python test checks both
export const ELEMENT_MAX_AGE_S = 7 * 86400; // equals atlas.ingest.s12.MAX_AGE
export const PREDICTED_LABEL = 'Predicted position (propagated from orbit elements), not observed';
export const USGS_HOST = 'earthquake.usgs.gov';
export const AIRCRAFT_FIELDS = ['aircraft_id', 'position_at', 'lat', 'lon', 'altitude_m', 'speed_ms', 'on_ground', 'position_type'];
export const LAYERS = ['aircraft', 'satellite', 'earthquake', 'vessel'] as const;

export type MovementLayer = {
  layer: (typeof LAYERS)[number]; source_id: string; title: string; note: string;
  available: boolean; reason: string | null; evidence: string; landing_url: string;
};
export type Aircraft = {
  aircraft_id: string; position_at: string; lat: number; lon: number; altitude_m: number | null;
  speed_ms: number | null; on_ground: boolean; position_type: string;
};
export type Satellite = { norad_id: number; name: string; epoch_at: string; lat: number | null; lon: number | null };
export type Quake = {
  event_id: string; origin_at: string; lat: number; lon: number; depth_km: number | null; magnitude: number | null;
  mag_type: string | null; review_status: 'automatic' | 'reviewed' | 'deleted'; updated_at: string; source_url: string;
};
export type MovementData = { aircraft: Aircraft[]; satellites: Satellite[]; earthquakes: Quake[] };

const zoned = (value: unknown): value is string => typeof value === 'string' && /(Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
const inRange = (lat: unknown, lon: unknown) => typeof lat === 'number' && typeof lon === 'number' && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;

export function parseMovementLayers(value: unknown): MovementLayer[] {
  if (!Array.isArray(value)) throw new Error('movement layers must be a list');
  for (const l of value as MovementLayer[]) {
    if (!LAYERS.includes(l.layer)) throw new Error(`unknown movement layer ${l.layer}`);
    if (l.available !== (l.reason === null)) throw new Error(`${l.layer}: an unavailable layer needs a reason`);
    if (!/^docs\/sources\/s\d{2}\.md$/.test(l.evidence) || !l.landing_url.startsWith('https://')) throw new Error(`${l.layer}: evidence link missing`);
  }
  return value as MovementLayer[];
}

export function parseAircraft(value: unknown): Aircraft[] {
  if (!Array.isArray(value)) throw new Error('aircraft must be a list');
  for (const row of value as Record<string, unknown>[]) {
    const extra = Object.keys(row).filter(key => !AIRCRAFT_FIELDS.includes(key));
    if (extra.length) throw new Error(`aircraft record has fields outside the allowlist: ${extra.join(', ')}`);
    if (!zoned(row.position_at) || !inRange(row.lat, row.lon)) throw new Error('aircraft needs a zoned time and a position');
  }
  return value as Aircraft[];
}

export function parseQuake(row: Quake): Quake {
  if (!['automatic', 'reviewed', 'deleted'].includes(row.review_status)) throw new Error('unknown USGS review status');
  if (!zoned(row.origin_at) || !zoned(row.updated_at) || !inRange(row.lat, row.lon)) throw new Error('event needs origin and revision times and a position');
  if (Date.parse(row.updated_at) < Date.parse(row.origin_at)) throw new Error('revision time is before the origin time');
  const url = new URL(row.source_url);
  if (url.protocol !== 'https:' || url.hostname !== USGS_HOST) throw new Error('source link must be an https USGS address');
  return row;
}

export const aircraftAge = (row: Aircraft, nowMs: number) => (nowMs - Date.parse(row.position_at)) / 1000;
export const aircraftVisible = (row: Aircraft, nowMs: number) => { const age = aircraftAge(row, nowMs); return age >= 0 && age <= AIRCRAFT_MAX_AGE_S; };

export function satelliteVisible(row: Satellite, nowMs: number): boolean {
  const age = (nowMs - Date.parse(row.epoch_at)) / 1000;
  return zoned(row.epoch_at) && age >= 0 && age <= ELEMENT_MAX_AGE_S && inRange(row.lat, row.lon);
}
export const satelliteLabel = (row: Satellite) => `${PREDICTED_LABEL}; elements dated ${localTime(row.epoch_at)}`;

/** What each layer may draw now: nothing for a layer whose source contract is not available. */
export function shown(layers: MovementLayer[], data: MovementData, nowMs: number) {
  const on = (name: MovementLayer['layer']) => layers.find(l => l.layer === name)?.available === true;
  return {
    aircraft: on('aircraft') ? data.aircraft.filter(row => aircraftVisible(row, nowMs)) : [],
    satellite: on('satellite') ? data.satellites.filter(row => satelliteVisible(row, nowMs)) : [],
    earthquake: on('earthquake') ? data.earthquakes.map(parseQuake).filter(row => row.review_status !== 'deleted') : [],
    vessel: [] as never[], // no ship position is ever drawn while S26 is blocked
  };
}

export default function Movement({ layers, data, now, active, onToggle }: {
  layers: MovementLayer[]; data: MovementData; now: number; active: Set<string>; onToggle: (layer: string) => void;
}) {
  const items = shown(layers, data, now);
  return <fieldset className="movement-layers"><legend>Movement</legend>
    {layers.map(l => <div className="layer-control" key={l.layer} data-testid={`movement-${l.layer}`}>
      <label><input type="checkbox" disabled={!l.available} checked={l.available && active.has(l.layer)}
        aria-describedby={`movement-${l.layer}-note`} onChange={() => onToggle(l.layer)} />{l.title}</label>
      <small id={`movement-${l.layer}-note`}>{l.available ? l.note : <>Unavailable: {l.reason}{' '}
        <a href={l.landing_url} rel="noreferrer">Source</a> · evidence {l.evidence}</>}</small>
    </div>)}
    {active.has('aircraft') && items.aircraft.length > 0 && <ul aria-label="Aircraft positions">{items.aircraft.map(row =>
      <li key={row.aircraft_id}>Aircraft position, {Math.round(aircraftAge(row, now))} s old
        {row.altitude_m !== null && ` · ${Math.round(row.altitude_m)} m`} · <time dateTime={row.position_at}>{localTime(row.position_at)}</time></li>)}</ul>}
    {active.has('satellite') && items.satellite.length > 0 && <ul aria-label="Predicted satellite positions">{items.satellite.map(row =>
      <li key={row.norad_id}>{row.name} · {satelliteLabel(row)}</li>)}</ul>}
    {active.has('earthquake') && items.earthquake.length > 0 && <ul aria-label="Earthquakes">{items.earthquake.map(q =>
      <li key={q.event_id}>{q.magnitude !== null ? `M ${q.magnitude}` : 'Magnitude not reported'}{q.mag_type && ` ${q.mag_type}`} · {q.review_status} ·
        origin <time dateTime={q.origin_at}>{localTime(q.origin_at)}</time> · revised <time dateTime={q.updated_at}>{localTime(q.updated_at)}</time> ·{' '}
        <a href={q.source_url} target="_blank" rel="noopener noreferrer">USGS source</a></li>)}</ul>}
  </fieldset>;
}
