import { authenticate, boundedBytes, decodeUpload, HOT_SOURCES, restoreUpload, UploadError } from './ingest.ts';
import { sha256 } from '../../web/src/data.ts';
import { claimFeedCheck } from './feed-check.ts';
import { reply, fallback } from './responses.ts';
import { answer, LIMITS, type Evidence } from './ask.ts';
import { PUSH_PATH, pushRegistration } from './push.ts';

interface Result<T> { results: T[]; meta: { size_after?: number; rows_written?: number } }
interface Statement {
  bind(...values: unknown[]): Statement;
  first<T = Record<string, unknown>>(): Promise<T | null>;
  all<T = Record<string, unknown>>(): Promise<Result<T>>;
}
export interface Database { prepare(sql: string): Statement; batch(statements: Statement[]): Promise<Result<unknown>[]> }
export interface Env { CAPABILITY_GATE?: string; ATLAS_INGEST_HMAC_KEY?: string; DB?: Database }

async function ingest(request: Request, env: Env, now: number): Promise<Response> {
  const bytes = await boundedBytes(request.body);
  if (!await authenticate(request, bytes, env.ATLAS_INGEST_HMAC_KEY, now)) return reply({ error: 'Untrusted upload.' }, 401);
  if (request.headers.get('Content-Type') !== 'application/gzip') throw new UploadError('Use application/gzip.');
  const upload = await decodeUpload(bytes, now); const db = env.DB!;
  const existing = await db.prepare('SELECT id FROM hot_snapshots WHERE id=?').bind(upload.sha256).first();
  if (existing) return reply({ status: 'unchanged', snapshot_id: upload.sha256 });
  const usage = await db.prepare('SELECT allocated_bytes FROM capacity WHERE id=1').all<{ allocated_bytes: number }>();
  if (usage.results.length !== 1 || !Number.isFinite(usage.meta.size_after)) return fallback('Storage usage could not be verified.');
  const day = new Date(now).toISOString().slice(0, 10);
  try {
    const result = await db.batch([
      db.prepare('INSERT OR IGNORE INTO daily_usage(day,writes_reserved) VALUES (?,0)').bind(day),
      db.prepare('INSERT INTO hot_snapshots(id,state,source_id,as_of_ms,payload,sha256,budget_day,database_bytes) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING')
        .bind(upload.sha256, 'ka', upload.source_id, Date.parse(upload.snapshot.as_of), upload.compressed,
          upload.sha256, day, usage.meta.size_after),
    ]);
    if (result.reduce((sum, item) => sum + (item.meta.rows_written ?? 0), 0) > 20) return fallback('Write accounting requires review.');
    return reply({ status: 'stored', snapshot_id: upload.sha256, as_of: upload.snapshot.as_of }, 201);
  } catch (error) {
    const message = String(error);
    if (message.includes('storage_cap')) return fallback('Hot storage cap reached; previous snapshots retained.', 507);
    if (message.includes('write_cap')) return fallback('Daily write cap reached; previous snapshots retained.', 429);
    if (message.includes('UNIQUE constraint')) return reply({ error: 'A different snapshot already occupies this source cutoff.' }, 409);
    throw error;
  }
}

async function current(url: URL, db: Database, now: number): Promise<Response> {
  if (url.searchParams.get('state') !== 'ka' || Array.from(url.searchParams.keys()).some(key => !['state', 'source'].includes(key)) ||
      (url.searchParams.has('source') && !(HOT_SOURCES as readonly string[]).includes(url.searchParams.get('source')!))) return reply({ error: 'Unknown state or query.' }, 400);
  const result = await db.prepare('SELECT s.source_id,s.payload,s.sha256 FROM hot_current c JOIN hot_snapshots s ON s.id=c.snapshot_id WHERE c.state=? AND (? IS NULL OR c.source_id=?)')
    .bind('ka', url.searchParams.get('source'), url.searchParams.get('source')).all<{ source_id: string; payload: number[]; sha256: string }>();
  if (!result.results.length) return fallback('No successful hot snapshot is stored.');
  const sources = [];
  const encoder = new TextEncoder();
  for (const row of result.results) {
    const { source_id, snapshot, sha256: storedSha256 } = await restoreUpload(Uint8Array.from(row.payload), row.sha256, now);
    if (source_id !== row.source_id) return fallback('Stored source identity mismatch.');
    const wireSha256 = await sha256(encoder.encode(JSON.stringify({ source_id, snapshot })));
    sources.push({ source_id, sha256: storedSha256, wire_sha256: wireSha256,
      age_seconds: Math.floor((now - Date.parse(snapshot.sources[0].last_success_at!)) / 1000),
      snapshot_age_seconds: Math.floor((now - Date.parse(snapshot.as_of)) / 1000), snapshot });
  }
  const resultBody = JSON.stringify({ schema_version: 1, state: 'ka', sources });
  if (encoder.encode(resultBody).byteLength > 1024 * 1024) return fallback('Combined hot response exceeds the byte cap.');
  return new Response(resultBody, { headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public,max-age=60', 'X-Content-Type-Options': 'nosniff' } });
}

const ASK_LANGUAGES = ['en', 'kn', 'ml', 'hi'];
const PLACE = /^in:(ka|kl|dl)(?::[a-z0-9._-]+)*$/;
const UTC_SECOND = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
// Generation, its quota counters and the AI binding wait for H05 and the probe (D95).
const NO_GENERATION = { day_answers: 0, minute_requests: 0, day_neurons: 0 };
type ChunkRow = Evidence & { expires_at: string | null; states: string };

async function ask(request: Request, db: Database, now: number): Promise<Response> {
  if (request.headers.get('Content-Type') !== 'application/json') return reply({ error: 'Use application/json.' }, 415);
  let body: Record<string, unknown>;
  try { body = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(await boundedBytes(request.body, 8192))); }
  catch (error) { if (error instanceof UploadError) throw error; return reply({ error: 'Invalid JSON.' }, 400); }
  const { query, language, place_id, as_of, chunk_ids } = body ?? {};
  const ids = Array.isArray(chunk_ids) ? chunk_ids : [];
  const state = typeof place_id === 'string' && place_id.length <= 200 ? PLACE.exec(place_id)?.[1] : undefined;
  if (!body || typeof body !== 'object' || Object.keys(body).some(key => !['query', 'language', 'place_id', 'as_of', 'chunk_ids'].includes(key)) ||
      typeof query !== 'string' || !query.trim() || query.length > LIMITS.questionChars || !ASK_LANGUAGES.includes(language as string) || !state ||
      typeof as_of !== 'string' || !UTC_SECOND.test(as_of) || !(Date.parse(as_of) <= now + 60_000) ||
      ids.length < 1 || ids.length > 5 || new Set(ids).size !== ids.length || ids.some(id => typeof id !== 'string' || !id || id.length > 200)) {
    return reply({ error: 'Send query, language, place_id, as_of (UTC, not future) and 1 to 5 distinct chunk_ids.' }, 400);
  }
  const current = await db.prepare('SELECT release FROM ask_current WHERE id=1').first<{ release: string }>();
  if (!current) return fallback('No trusted Ask release is loaded.');
  // Evidence text comes only from the trusted release, never from the client (plan T179 step 3).
  const rows = await db.prepare(`SELECT chunk_id,doc_id,path,heading,text,available_at,expires_at,states,sha256 FROM ask_chunks WHERE release=? AND chunk_id IN (${ids.map(() => '?').join(',')})`)
    .bind(current.release, ...ids).all<ChunkRow>();
  if (rows.results.length !== ids.length) return reply({ error: 'Unknown chunk ID for the current Ask release.' }, 400);
  const byId = new Map(rows.results.map(row => [row.chunk_id, row]));
  const evidence: Evidence[] = [];
  for (const id of ids as string[]) {
    const row = byId.get(id)!;
    if (await sha256(new TextEncoder().encode(row.text)) !== row.sha256) return fallback('A trusted Ask chunk failed its integrity check.');
    // Same as-of, expiry and state rules as src/atlas/rag/retrieve.py.
    if (row.available_at > as_of || (row.expires_at !== null && row.expires_at <= as_of) ||
        !(row.states.includes(`,${state},`) || row.states.includes(',all,'))) continue;
    const { chunk_id, doc_id, path, heading, text, available_at, sha256: digest } = row;
    evidence.push({ chunk_id, doc_id, path, heading, text, available_at, sha256: digest });
  }
  const result = await answer(query, evidence, { asOf: as_of, usage: NO_GENERATION });
  return reply({ schema_version: 1, release: current.release, as_of, ...result });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === PUSH_PATH) return pushRegistration(request); // always refused (T184, D150)
    if (!['/internal/ingest', '/internal/feed-check', '/api/v1/current', '/api/v1/ask'].includes(url.pathname)) return reply({ error: 'Not found.' }, 404);
    if (env.CAPABILITY_GATE !== 'verified_free_no_card' || !env.DB) return fallback('Free/no-card capability or database binding has not been verified.');
    try {
      if (url.pathname === '/internal/ingest' && request.method === 'POST' && !url.search) return await ingest(request, env, Date.now());
      if (url.pathname === '/internal/feed-check' && request.method === 'POST' && !url.search) return await claimFeedCheck(request, env, Date.now());
      if (url.pathname === '/api/v1/current' && request.method === 'GET') return await current(url, env.DB, Date.now());
      if (url.pathname === '/api/v1/ask' && request.method === 'POST' && !url.search) return await ask(request, env.DB, Date.now());
      return reply({ error: 'Unsupported method or query.' }, 405);
    } catch (error) {
      if (error instanceof UploadError) return reply({ error: error.message }, error.status);
      return fallback('Hot storage is unavailable; retain the dated static snapshot.');
    }
  },
};
