import { authenticate, boundedBytes, HOT_SOURCES, UploadError } from './ingest.ts';
import { reply, fallback } from './responses.ts';
import type { Env } from './index.ts';

const periods: Record<string, number> = { S01: 21600000, S09: 900000 };

export async function claimFeedCheck(request: Request, env: Env, now: number): Promise<Response> {
  const bytes = await boundedBytes(request.body, 1024);
  if (!await authenticate(request, bytes, env.ATLAS_INGEST_HMAC_KEY, now)) return reply({ error: 'Untrusted admission request.' }, 401);
  if (request.headers.get('Content-Type') !== 'application/json') throw new UploadError('Use application/json.');
  let value: unknown;
  try { value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); }
  catch { throw new UploadError('Invalid admission JSON.'); }
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new UploadError('Invalid admission structure.');
  const data = value as Record<string, unknown>;
  if (data.state !== 'ka' || typeof data.source_id !== 'string' || !(HOT_SOURCES as readonly string[]).includes(data.source_id) ||
      Object.keys(data).some(key => !['state', 'source_id'].includes(key))) throw new UploadError('Unknown state, source or admission field.');
  const source = data.source_id; const db = env.DB!;
  const usage = await db.prepare('SELECT allocated_bytes FROM capacity WHERE id=1').all<{ allocated_bytes: number }>();
  if (usage.results.length !== 1 || !Number.isFinite(usage.meta.size_after)) return fallback('Admission storage usage could not be verified.');
  const day = new Date(now).toISOString().slice(0, 10);
  try {
    const result = await db.batch([
      db.prepare('INSERT OR IGNORE INTO daily_usage(day,writes_reserved) VALUES (?,0)').bind(day),
      db.prepare('INSERT INTO feed_checks(state,source_id,period_index,admitted_ms,budget_day,database_bytes) VALUES (?,?,?,?,?,?)')
        .bind('ka', source, Math.floor(now / periods[source]), now, day, usage.meta.size_after),
    ]);
    if (result.reduce((sum, item) => sum + (item.meta.rows_written ?? 0), 0) > 20) return fallback('Admission write accounting requires review.');
    return reply({ admitted: true, state: 'ka', source_id: source }, 201);
  } catch (error) {
    const message = String(error);
    if (message.includes('check_not_due') || message.includes('UNIQUE constraint')) return reply({ admitted: false, state: 'ka', source_id: source, reason: 'not_due' });
    if (message.includes('storage_cap')) return fallback('Admission storage cap reached.', 507);
    if (message.includes('write_cap')) return fallback('Admission daily write cap reached.', 429);
    throw error;
  }
}
