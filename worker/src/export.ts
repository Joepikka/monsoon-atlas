// T044 (D184): signed, read-only export of stored hot snapshots for the daily archive.
// Same HMAC message and headers as /internal/ingest; JSON body {after_ms, after_id} is a cursor.
// Rows come back in (as_of_ms, id) order with the exact stored gzip payload (base64) and its
// stored SHA-256, so the archiver can verify every byte before it trusts the copy. No write,
// counter or reservation happens here; deletion is not offered (archive durability first).
import { authenticate, boundedBytes, UploadError } from './ingest.ts';
import { reply, fallback } from './responses.ts';
import type { Env } from './index.ts';

export const EXPORT_PATH = '/internal/export';
export const EXPORT_PAGE_BYTES = 4 * 1024 * 1024;
export const EXPORT_PAGE_ROWS = 200;
const CAP_BYTES = 400000000;

function base64(bytes: Uint8Array): string {
  let text = '';
  for (let i = 0; i < bytes.length; i += 0x8000) text += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(text);
}

export async function exportSnapshots(request: Request, env: Env, now: number): Promise<Response> {
  const bytes = await boundedBytes(request.body, 1024);
  if (!await authenticate(request, bytes, env.ATLAS_INGEST_HMAC_KEY, now)) return reply({ error: 'Untrusted export request.' }, 401);
  if (request.headers.get('Content-Type') !== 'application/json') throw new UploadError('Use application/json.');
  let value: unknown;
  try { value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); }
  catch { throw new UploadError('Invalid export JSON.'); }
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new UploadError('Invalid export structure.');
  const data = value as Record<string, unknown>;
  const afterMs = data.after_ms, afterId = data.after_id;
  if (Object.keys(data).some(key => !['after_ms', 'after_id'].includes(key)) ||
      typeof afterMs !== 'number' || !Number.isSafeInteger(afterMs) || afterMs < -1 ||
      typeof afterId !== 'string' || !/^([a-f0-9]{64})?$/.test(afterId)) throw new UploadError('Invalid export cursor.');
  const db = env.DB!;
  const usage = await db.prepare('SELECT allocated_bytes FROM capacity WHERE id=1').all<{ allocated_bytes: number }>();
  if (usage.results.length !== 1) return fallback('Storage usage could not be verified.');
  const rows = await db.prepare(
    "SELECT id,source_id,as_of_ms,sha256,payload FROM hot_snapshots WHERE state='ka' AND (as_of_ms>? OR (as_of_ms=? AND id>?)) ORDER BY as_of_ms,id LIMIT ?",
  ).bind(afterMs, afterMs, afterId, EXPORT_PAGE_ROWS + 1).all<{ id: string; source_id: string; as_of_ms: number; sha256: string; payload: number[] }>();
  const out = [];
  let size = 0;
  for (const row of rows.results.slice(0, EXPORT_PAGE_ROWS)) {
    const payload = Uint8Array.from(row.payload);
    if (out.length && size + payload.length > EXPORT_PAGE_BYTES * 0.7) break; // base64 grows 4/3
    size += payload.length;
    out.push({ id: row.id, source_id: row.source_id, as_of_ms: row.as_of_ms, sha256: row.sha256, payload_gzip_base64: base64(payload) });
  }
  const last = out.at(-1);
  return reply({
    schema_version: 1, state: 'ka', rows: out, more: out.length < rows.results.length,
    next: last ? { after_ms: last.as_of_ms, after_id: last.id } : { after_ms: afterMs, after_id: afterId },
    capacity: { allocated_bytes: usage.results[0].allocated_bytes, size_after: usage.meta.size_after ?? null, cap_bytes: CAP_BYTES },
  });
}
