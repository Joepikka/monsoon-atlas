export type StateId = 'ka' | 'kl' | 'dl';
export const stateNames: Record<StateId, string> = { ka: 'Karnataka', kl: 'Kerala', dl: 'Delhi' };
export type LayerKind = 'weather' | 'alert' | 'price' | 'model';
export type Health = 'available' | 'stale' | 'unavailable' | 'partial' | 'unknown';
export interface SourceHealth {
  source_id: string; status: Health; last_success_at: string | null; detail: string;
}
export interface Place {
  place_id: string; name: string; kind: 'state' | 'district' | 'ward' | 'h3'; state: StateId;
  boundary_version: string; longitude: number; latitude: number;
  source_id: string; source_url: string; licence_id: string; location_note: string;
}
export type FacilityKind = 'hospital' | 'police' | 'fire_station';
export const facilityKinds: readonly FacilityKind[] = ['hospital', 'police', 'fire_station'];
export interface Facility {
  facility_id: string; kind: FacilityKind; name: string; longitude: number; latitude: number;
  source_id: 'S18'; source_url: string; fetched_at: string;
  verification_status: 'unverified' | 'source_checked';
}

export interface MapRecord {
  id: string; title: string; longitude: number | null; latitude: number | null;
  source_id: string; source_url: string; provenance: 'official' | 'model' | 'inferred' | 'reconstructed';
  valid_at: string; fetched_at: string;
  location_note?: string;
  kind: LayerKind; spatial_scope: 'point' | 'area';
  issued_at: string | null; available_at: string; expires_at: string | null;
  severity: string | null; unit: string | null; value: number | null;
  market: string | null; missing_reason: string | null;
  evidence: 'forecast' | 'reanalysis' | 'hindcast' | null;
  place_id: string | null; boundary_version: string | null;
  model_id: string | null; model_status: 'champion' | 'baseline' | 'research_only' | null;
  warning_text: string | null; instruction: string | null;
  area_text: string | null;
}

export interface Snapshot {
  schema_version: 1; state: StateId; release_id: string; data_revision: string;
  as_of: string; published_at: string; records: MapRecord[];
  sources: SourceHealth[];
  places: Place[]; facilities: Facility[];
  release_hash?: string; // Derived from verified bytes by the loader, never trusted from JSON.
}

export interface ViewState {
  status: 'loading' | 'empty' | 'ready' | 'stale' | 'error';
  snapshot: Snapshot | null; message: string;
}

interface LoadOptions { fetcher?: typeof fetch; now?: number; signal?: AbortSignal; releaseHash?: string; asOf?: string }

const HASH = /^[a-f0-9]{64}$/;
export const STALE_MS = 24 * 60 * 60 * 1000;
const MAX_BYTES = 1024 * 1024;

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid snapshot structure.');
  return value as Record<string, unknown>;
}

function text(value: unknown, field: string): string {
  if (typeof value !== 'string' || !value.trim() || value.length > 2000) throw new Error(`Missing or invalid ${field}.`);
  return value;
}

function timestamp(value: unknown, field: string): string {
  const result = text(value, field);
  const parsed = new Date(result);
  if (!result.endsWith('Z') || !result.includes('T') || !Number.isFinite(parsed.getTime()) ||
      parsed.toISOString().slice(0, 10) !== result.slice(0, 10)) throw new Error(`Invalid ${field} timestamp.`);
  return result;
}

function nullableTime(value: unknown, field: string): string | null {
  return value === null || value === undefined ? null : timestamp(value, field);
}

function nullableText(value: unknown, field: string): string | null {
  return value === null || value === undefined ? null : text(value, field);
}

function publicUrl(value: unknown): string {
  const result = text(value, 'source URL');
  const url = new URL(result);
  if (url.protocol !== 'https:' || url.username || url.password ||
      Array.from(url.searchParams.keys()).some(key => /^(api[-_]?key|key|map[-_]?key|access[-_]?token|token|secret|password|authorization)$/i.test(key))) {
    throw new Error('Invalid public source URL or embedded credential.');
  }
  return result;
}

function coordinates(row: Record<string, unknown>): { longitude: number; latitude: number } {
  if (typeof row.longitude !== 'number' || !Number.isFinite(row.longitude) || Math.abs(row.longitude) > 180 ||
      typeof row.latitude !== 'number' || !Number.isFinite(row.latitude) || Math.abs(row.latitude) > 90) throw new Error('Invalid location.');
  return { longitude: row.longitude, latitude: row.latitude };
}

export function hasCoordinates<T extends { longitude: number | null; latitude: number | null }>(point: T): point is T & { longitude: number; latitude: number } {
  return typeof point.longitude === 'number' && Number.isFinite(point.longitude) && typeof point.latitude === 'number' && Number.isFinite(point.latitude);
}

export async function sha256(bytes: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', Uint8Array.from(bytes).buffer);
  return Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2, '0')).join('');
}

export function parseSnapshot(value: unknown, state: StateId): Snapshot {
  const data = object(value);
  if (data.schema_version !== 1) throw new Error('Unsupported snapshot schema.');
  if (data.state !== state) throw new Error('Snapshot state does not match the selected state.');
  const revision = text(data.data_revision, 'data revision');
  const asOf = timestamp(data.as_of, 'as_of');
  if (!HASH.test(revision)) throw new Error('Invalid data revision hash.');
  if (!Array.isArray(data.records)) throw new Error('Snapshot records are missing.');
  const ids = new Set<string>();
  const records = data.records.map(entry => {
    const row = object(entry);
    const id = text(row.id, 'record ID');
    if (ids.has(id)) throw new Error('Duplicate snapshot record ID.');
    ids.add(id);
    const areaText = nullableText(row.area_text, 'original area text');
    const unlocated = row.longitude === null && row.latitude === null;
    if (unlocated && (row.source_id !== 'S09' || row.provenance !== 'official' || row.kind !== 'alert' ||
        row.spatial_scope !== 'area' || !areaText || !row.location_note)) throw new Error('An area-only official warning needs its source area text and location limit.');
    const point = unlocated ? { longitude: null, latitude: null } : coordinates(row);
    if (!['official', 'model', 'inferred', 'reconstructed'].includes(String(row.provenance))) throw new Error('Missing record provenance.');
    const sourceId = text(row.source_id, 'source ID');
    if (!/^S\d{2,}$/.test(sourceId)) throw new Error('Invalid source ID.');
    const sourceUrl = publicUrl(row.source_url);
    if (!['weather', 'alert', 'price', 'model'].includes(String(row.kind))) throw new Error('Invalid record layer.');
    if (!['point', 'area'].includes(String(row.spatial_scope))) throw new Error('Missing spatial scope.');
    const issued = nullableTime(row.issued_at, 'issued_at');
    const available = timestamp(row.available_at, 'available_at');
    const fetched = timestamp(row.fetched_at, 'fetched_at');
    if (row.provenance !== 'reconstructed' && Date.parse(available) < Date.parse(fetched)) {
      throw new Error('available_at before fetched_at requires reconstructed provenance.');
    }
    if (Date.parse(available) > Date.parse(asOf) || (issued && Date.parse(issued) > Date.parse(asOf))) {
      throw new Error('A record was not available at the snapshot cutoff.');
    }
    const unit = nullableText(row.unit, 'unit');
    const market = nullableText(row.market, 'market');
    const value = row.value === undefined || row.value === null ? null : row.value;
    if (value !== null && (typeof value !== 'number' || !Number.isFinite(value))) throw new Error('Invalid numeric measure.');
    if (value !== null && !unit) throw new Error('A numeric measure requires a documented unit.');
    if (value === null && ['weather', 'model'].includes(String(row.kind)) && !row.missing_reason) {
      throw new Error('A missing measure requires a missing reason.');
    }
    if (row.kind === 'price' && (!unit || !market || value === null || value <= 0)) {
      throw new Error('A price requires a verified unit, market and positive value.');
    }
    const evidence = row.evidence ?? null;
    if (evidence !== null && !['forecast', 'reanalysis', 'hindcast'].includes(String(evidence))) throw new Error('Invalid model evidence label.');
    if (row.kind === 'alert' && (sourceId !== 'S09' || row.provenance !== 'official')) {
      throw new Error('An inferred or model item cannot enter the official CAP alert layer.');
    }
    const placeId = nullableText(row.place_id, 'place ID');
    const boundary = nullableText(row.boundary_version, 'boundary version');
    if (placeId && !boundary) throw new Error('A place association requires a boundary version.');
    const modelId = nullableText(row.model_id, 'model ID');
    const modelStatus = row.model_status ?? null;
    if (modelId && !/^M\d{2,}$/.test(modelId)) throw new Error('Invalid model ID.');
    if (modelStatus !== null && !['champion', 'baseline', 'research_only'].includes(String(modelStatus))) throw new Error('Invalid model status.');
    return {
      id, title: text(row.title, 'record title'), ...point,
      source_id: sourceId, source_url: sourceUrl, provenance: row.provenance as MapRecord['provenance'],
      valid_at: timestamp(row.valid_at, 'valid_at'), fetched_at: fetched,
      ...(row.location_note === undefined ? {} : { location_note: text(row.location_note, 'location note') }),
      kind: row.kind as LayerKind, spatial_scope: row.spatial_scope as MapRecord['spatial_scope'],
      issued_at: issued, available_at: available, expires_at: nullableTime(row.expires_at, 'expires_at'),
      severity: nullableText(row.severity, 'provider severity'), unit, value,
      market, missing_reason: nullableText(row.missing_reason, 'missing reason'),
      evidence: evidence as MapRecord['evidence'],
      place_id: placeId, boundary_version: boundary, model_id: modelId, model_status: modelStatus as MapRecord['model_status'],
      warning_text: nullableText(row.warning_text, 'original warning'), instruction: nullableText(row.instruction, 'source instruction'),
      area_text: areaText,
    };
  });
  if (data.sources !== undefined && !Array.isArray(data.sources)) throw new Error('Invalid source health metadata.');
  const sources: SourceHealth[] = ((data.sources ?? []) as unknown[]).map(value => {
    const source = object(value);
    const sourceId = text(source.source_id, 'source ID');
    if (!/^S\d{2,}$/.test(sourceId) || !['available', 'stale', 'unavailable', 'partial', 'unknown'].includes(String(source.status))) {
      throw new Error('Invalid source health.');
    }
    const lastSuccess = nullableTime(source.last_success_at, 'last success');
    if ((source.status === 'available' && !lastSuccess) || (lastSuccess && Date.parse(lastSuccess) > Date.parse(asOf))) {
      throw new Error('Source health has no valid success time at this cutoff.');
    }
    return { source_id: sourceId, status: source.status as Health,
      last_success_at: lastSuccess, detail: text(source.detail, 'source health detail') };
  });
  if (new Set(sources.map(source => source.source_id)).size !== sources.length) throw new Error('Duplicate source health entry.');
  if (data.places !== undefined && !Array.isArray(data.places)) throw new Error('Invalid places.');
  const places: Place[] = ((data.places ?? []) as unknown[]).map(value => {
    const place = object(value);
    if (place.state !== state || !['state', 'district', 'ward', 'h3'].includes(String(place.kind))) throw new Error('Invalid place state or kind.');
    const placeId = text(place.place_id, 'place ID');
    if ((place.kind === 'h3') !== placeId.startsWith('h3:')) throw new Error('H3 cells cannot be labelled as administrative places.');
    return { place_id: placeId, name: text(place.name, 'place name'), kind: place.kind as Place['kind'], state,
      boundary_version: text(place.boundary_version, 'boundary version'), ...coordinates(place),
      source_id: text(place.source_id, 'place source'), source_url: publicUrl(place.source_url),
      licence_id: text(place.licence_id, 'place licence'), location_note: text(place.location_note, 'place location note') };
  });
  if (new Set(places.map(place => place.place_id + '\0' + place.boundary_version)).size !== places.length) throw new Error('Duplicate place version.');
  if (data.facilities !== undefined && !Array.isArray(data.facilities)) throw new Error('Invalid facilities.');
  const facilities: Facility[] = ((data.facilities ?? []) as unknown[]).map(value => {
    const facility = object(value);
    if (facility.source_id !== 'S18' || !['unverified', 'source_checked'].includes(String(facility.verification_status))) throw new Error('Invalid facility source or verification.');
    if (!facilityKinds.includes(facility.kind as FacilityKind)) throw new Error('Invalid facility kind.');
    const fetched = timestamp(facility.fetched_at, 'facility fetched_at');
    if (Date.parse(fetched) > Date.parse(asOf)) throw new Error('Facility was not known at this cutoff.');
    return { facility_id: text(facility.facility_id, 'facility ID'), kind: facility.kind as FacilityKind, name: text(facility.name, 'facility name'),
      ...coordinates(facility), source_id: 'S18', source_url: publicUrl(facility.source_url), fetched_at: fetched,
      verification_status: facility.verification_status as Facility['verification_status'] };
  });
  if (new Set(facilities.map(facility => facility.facility_id)).size !== facilities.length) throw new Error('Duplicate facility ID.');
  return { schema_version: 1, state, release_id: text(data.release_id, 'release ID'),
    data_revision: revision, as_of: asOf,
    published_at: timestamp(data.published_at, 'published_at'), records, sources, places, facilities };
}

export async function loadSnapshot(state: StateId, previous: Snapshot | null, options: LoadOptions = {}): Promise<ViewState> {
  const fetcher = options.fetcher ?? fetch;
  const lastGood = previous?.state === state && (!options.releaseHash || previous.release_hash === options.releaseHash) &&
    (!options.asOf || previous.as_of === options.asOf) ? previous : null;
  try {
    if (options.releaseHash && !HASH.test(options.releaseHash)) throw new Error('Invalid frozen release hash.');
    const pointerUrl = options.releaseHash ? `/data/${state}/releases/${options.releaseHash}.approval.json` : `/data/${state}/latest.json`;
    const response = await fetcher(pointerUrl, {
      cache: 'no-store', signal: options.signal, headers: { Accept: 'application/json' },
    });
    if (response.status === 404 && !lastGood && !options.releaseHash) return { status: 'empty', snapshot: null, message: 'No approved snapshot has been released yet.' };
    if (!response.ok) throw new Error('The latest snapshot could not be reached.');
    const pointer = object(await response.json());
    if (pointer.schema_version !== 1 || pointer.state !== state) throw new Error('Invalid release pointer.');
    if (pointer.approval !== 'approved') throw new Error('Publication approval is pending.');
    if (options.releaseHash && pointer.sha256 !== options.releaseHash) throw new Error('Frozen release approval does not match the requested hash.');
    if (typeof pointer.sha256 !== 'string' || !HASH.test(pointer.sha256) ||
        pointer.manifest_url !== `/data/${state}/releases/${pointer.sha256}.json`) {
      throw new Error('The snapshot URL is not an immutable release for this state.');
    }
    const manifest = await fetcher(pointer.manifest_url as string, {
      signal: options.signal, headers: { Accept: 'application/json' },
    });
    if (!manifest.ok) throw new Error('The released snapshot could not be loaded.');
    const bytes = new Uint8Array(await manifest.arrayBuffer());
    if (bytes.byteLength > MAX_BYTES) throw new Error('The snapshot exceeds the one-megabyte limit.');
    if (await sha256(bytes) !== pointer.sha256) throw new Error('Snapshot integrity check failed.');
    const snapshot = parseSnapshot(JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), state);
    snapshot.release_hash = pointer.sha256;
    if (options.asOf && snapshot.as_of !== options.asOf) throw new Error('Snapshot as-of time does not match the shared report.');
    const now = options.now ?? Date.now();
    if (Date.parse(snapshot.as_of) > now) throw new Error('The snapshot as-of time is in the future.');
    const stale = now - Date.parse(snapshot.as_of) > STALE_MS;
    return { status: stale ? 'stale' : 'ready', snapshot,
      message: stale ? 'This snapshot is more than 24 hours old.' : 'Approved snapshot loaded.' };
  } catch (error) {
    return { status: 'error', snapshot: lastGood,
      message: error instanceof Error ? error.message : 'The snapshot could not be loaded.' };
  }
}
