export type StateId = 'ka' | 'kl' | 'dl';
export const stateNames: Record<StateId, string> = { ka: 'Karnataka', kl: 'Kerala', dl: 'Delhi' };

export interface MapRecord {
  id: string; title: string; longitude: number; latitude: number;
  source_id: string; source_url: string; provenance: 'official' | 'model' | 'inferred' | 'reconstructed';
  valid_at: string; fetched_at: string;
  location_note?: string;
}

export interface Snapshot {
  schema_version: 1; state: StateId; release_id: string; data_revision: string;
  as_of: string; published_at: string; records: MapRecord[];
}

export interface ViewState {
  status: 'loading' | 'empty' | 'ready' | 'stale' | 'error';
  snapshot: Snapshot | null; message: string;
}

interface LoadOptions { fetcher?: typeof fetch; now?: number; signal?: AbortSignal }

const HASH = /^[a-f0-9]{64}$/;
const STALE_MS = 24 * 60 * 60 * 1000;
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

export async function sha256(bytes: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', Uint8Array.from(bytes).buffer);
  return Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2, '0')).join('');
}

export function parseSnapshot(value: unknown, state: StateId): Snapshot {
  const data = object(value);
  if (data.schema_version !== 1) throw new Error('Unsupported snapshot schema.');
  if (data.state !== state) throw new Error('Snapshot state does not match the selected state.');
  const revision = text(data.data_revision, 'data revision');
  if (!HASH.test(revision)) throw new Error('Invalid data revision hash.');
  if (!Array.isArray(data.records)) throw new Error('Snapshot records are missing.');
  const ids = new Set<string>();
  const records = data.records.map(value => {
    const row = object(value);
    const id = text(row.id, 'record ID');
    if (ids.has(id)) throw new Error('Duplicate snapshot record ID.');
    ids.add(id);
    if (typeof row.longitude !== 'number' || !Number.isFinite(row.longitude) || Math.abs(row.longitude) > 180 ||
        typeof row.latitude !== 'number' || !Number.isFinite(row.latitude) || Math.abs(row.latitude) > 90) {
      throw new Error('Invalid record location.');
    }
    if (!['official', 'model', 'inferred', 'reconstructed'].includes(String(row.provenance))) throw new Error('Missing record provenance.');
    const sourceId = text(row.source_id, 'source ID');
    if (!/^S\d{2,}$/.test(sourceId)) throw new Error('Invalid source ID.');
    const sourceUrl = text(row.source_url, 'source URL');
    const url = new URL(sourceUrl);
    if (url.protocol !== 'https:' || url.username || url.password) throw new Error('Invalid public source URL.');
    return {
      id, title: text(row.title, 'record title'), longitude: row.longitude, latitude: row.latitude,
      source_id: sourceId, source_url: sourceUrl, provenance: row.provenance as MapRecord['provenance'],
      valid_at: timestamp(row.valid_at, 'valid_at'), fetched_at: timestamp(row.fetched_at, 'fetched_at'),
      ...(row.location_note === undefined ? {} : { location_note: text(row.location_note, 'location note') }),
    };
  });
  return { schema_version: 1, state, release_id: text(data.release_id, 'release ID'),
    data_revision: revision, as_of: timestamp(data.as_of, 'as_of'),
    published_at: timestamp(data.published_at, 'published_at'), records };
}

export async function loadSnapshot(state: StateId, previous: Snapshot | null, options: LoadOptions = {}): Promise<ViewState> {
  const fetcher = options.fetcher ?? fetch;
  const lastGood = previous?.state === state ? previous : null;
  try {
    const response = await fetcher(`/data/${state}/latest.json`, {
      cache: 'no-store', signal: options.signal, headers: { Accept: 'application/json' },
    });
    if (response.status === 404 && !lastGood) return { status: 'empty', snapshot: null, message: 'No approved snapshot has been released yet.' };
    if (!response.ok) throw new Error('The latest snapshot could not be reached.');
    const pointer = object(await response.json());
    if (pointer.schema_version !== 1 || pointer.state !== state) throw new Error('Invalid release pointer.');
    if (pointer.approval !== 'approved') throw new Error('Publication approval is pending.');
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
