import { authenticate, boundedBytes, decodeUpload, HOT_SOURCES, restoreUpload, UploadError } from './ingest.ts';

interface Result<T> { results: T[]; meta: { size_after?: number; rows_written?: number } }
interface Statement {
  bind(...values: unknown[]): Statement;
  first<T = Record<string, unknown>>(): Promise<T | null>;
  all<T = Record<string, unknown>>(): Promise<Result<T>>;
}
export interface Database { prepare(sql: string): Statement; batch(statements: Statement[]): Promise<Result<unknown>[]> }
export interface Env { CAPABILITY_GATE?: string; ATLAS_INGEST_HMAC_KEY?: string; DB?: Database }
const reply = (data: unknown, status = 200) => Response.json(data, { status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
const fallback = (message: string, status = 503) => reply({ status: 'unavailable', fallback: 'static_daily', message }, status);

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
  for (const row of result.results) {
    const upload = await restoreUpload(Uint8Array.from(row.payload), row.sha256, now);
    if (upload.source_id !== row.source_id) return fallback('Stored source identity mismatch.');
    sources.push({ source_id: upload.source_id, sha256: upload.sha256,
      age_seconds: Math.floor((now - Date.parse(upload.snapshot.as_of)) / 1000), snapshot: upload.snapshot });
  }
  const resultBody = JSON.stringify({ schema_version: 1, state: 'ka', sources });
  if (new TextEncoder().encode(resultBody).byteLength > 1024 * 1024) return fallback('Combined hot response exceeds the byte cap.');
  return new Response(resultBody, { headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public,max-age=60', 'X-Content-Type-Options': 'nosniff' } });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (!['/internal/ingest', '/api/v1/current'].includes(url.pathname)) return reply({ error: 'Not found.' }, 404);
    if (env.CAPABILITY_GATE !== 'verified_free_no_card' || !env.DB) return fallback('Free/no-card capability or database binding has not been verified.');
    try {
      if (url.pathname === '/internal/ingest' && request.method === 'POST' && !url.search) return await ingest(request, env, Date.now());
      if (url.pathname === '/api/v1/current' && request.method === 'GET') return await current(url, env.DB, Date.now());
      return reply({ error: 'Unsupported method or query.' }, 405);
    } catch (error) {
      if (error instanceof UploadError) return reply({ error: error.message }, error.status);
      return fallback('Hot storage is unavailable; retain the dated static snapshot.');
    }
  },
};
