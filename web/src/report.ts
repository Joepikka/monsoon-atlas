import { hasCoordinates, type Facility, type MapRecord, type Place, type Snapshot, type StateId } from './data';
import { distanceKm, type Coordinates } from './map/Layers';

export interface ShareIdentity { state: StateId; place: string; boundary: string; asOf: string; release: string }
export interface PlaceReport {
  state: StateId; place: Place; as_of: string; release_hash: string; release_id: string;
  records: MapRecord[]; modelOutputs: MapRecord[]; forecasts: MapRecord[];
  facilities: (Facility & { distance_km: number })[]; sources: { id: string; url: string }[];
}

export const sourceNames: Record<string, string> = {
  S01: 'Open-Meteo / ECMWF', S02: 'Open-Meteo / ERA5', S08: 'IMD gridded rainfall',
  S09: 'NDMA Sachet / Karnataka SNDMC', S17: 'geoBoundaries / wmgeolab contributors',
  S18: 'OpenStreetMap via Geofabrik', S22: 'India Data Portal', S23: 'data.gov.in',
  S32: 'KSEB', S33: 'KSEB monthly statistics', S34: 'KSDMA dam reports',
};

export function rankByDistance<T extends { longitude: number; latitude: number }>(origin: Coordinates, items: T[]): (T & { distance_km: number })[] {
  return items.map(item => ({ ...item, distance_km: distanceKm(origin, [item.longitude, item.latitude]) }))
    .sort((a, b) => a.distance_km - b.distance_km);
}

export function buildReport(snapshot: Snapshot, placeId: string, boundary: string): PlaceReport {
  const place = snapshot.places.find(item => item.place_id === placeId && item.boundary_version === boundary);
  if (!place) throw new Error('This place or boundary version is not present in the snapshot.');
  if (!snapshot.release_hash) throw new Error('The report has no verified immutable release hash.');
  const records = snapshot.records.filter(record => {
    if (record.place_id) return record.place_id === placeId && record.boundary_version === boundary;
    if (record.kind === 'model') return false; // A model score needs an explicit versioned place association.
    return record.spatial_scope === 'area' || (hasCoordinates(record) && distanceKm([place.longitude, place.latitude], [record.longitude, record.latitude]) <= 25);
  });
  const facilities = rankByDistance([place.longitude, place.latitude], snapshot.facilities).filter(item => item.distance_km <= 25).slice(0, 10);
  const sourceMap = new Map<string, { id: string; url: string }>();
  for (const source of [{ source_id: place.source_id, source_url: place.source_url }, ...records, ...facilities]) {
    sourceMap.set(source.source_id + '|' + source.source_url, { id: source.source_id, url: source.source_url });
  }
  return { state: snapshot.state, place, as_of: snapshot.as_of, release_hash: snapshot.release_hash,
    release_id: snapshot.release_id, records,
    modelOutputs: records.filter(record => record.kind === 'model' && record.model_id && record.model_status),
    forecasts: records.filter(record => record.evidence === 'forecast' && Date.parse(record.valid_at) >= Date.parse(snapshot.as_of)),
    facilities, sources: Array.from(sourceMap.values()) };
}

export function readShare(search: string): ShareIdentity | null {
  const query = new URLSearchParams(search);
  if (!query.has('release') && !query.has('place') && !query.has('asof') && !query.has('boundary')) return null;
  const state = query.get('state'); const place = query.get('place');
  const boundary = query.get('boundary'); const asOf = query.get('asof'); const release = query.get('release');
  if (!state || !['ka', 'kl', 'dl'].includes(state) || !place || !boundary || !asOf || !release ||
      !/^[a-f0-9]{64}$/.test(release) || !asOf.endsWith('Z') || !Number.isFinite(Date.parse(asOf)) ||
      place.length > 2000 || boundary.length > 2000) throw new Error('The shared report identity is incomplete or invalid.');
  return { state: state as StateId, place, boundary, asOf, release };
}

export function shareUrl(base: string, report: PlaceReport): string {
  const original = new URL(base);
  const result = new URL(original.pathname, original.origin);
  result.search = new URLSearchParams({ state: report.state, place: report.place.place_id,
    boundary: report.place.boundary_version, asof: report.as_of, release: report.release_hash }).toString();
  return result.toString();
}
