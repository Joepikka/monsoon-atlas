// T218 (D162): export only licence-cleared rows, as static shards with a manifest.
// The licence and outcome come from the source records in dashboards.json (the same discovery
// records the Python gate reads); a source that is not available and open is refused.
import { sha256 } from './data';
import { data } from './dashboards';

export const MAX_ROWS = 10_000;
export const MAX_BYTES = 10 * 1024 * 1024;

export interface ExportManifest {
  schema_version: 1; source_id: string; licence: string; rows: number; content_sha256: string;
  shards: { path: string; rows: number; bytes: number; sha256: string }[];
}
export class ExportRefused extends Error {}

export function exportAllowed(sourceId: string): boolean {
  const source = data.sources.find(s => s.id === sourceId);
  return !!source && source.outcome === 'available' && source.licence === 'open';
}

const hex = (bytes: Uint8Array) => sha256(bytes);
const join = (parts: Uint8Array[]): Uint8Array => {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const part of parts) { out.set(part, at); at += part.length; }
  return out;
};

export async function exportRows(
  sourceId: string, rows: readonly Record<string, unknown>[], limits = { rows: MAX_ROWS, bytes: MAX_BYTES },
): Promise<{ manifest: ExportManifest; shards: Uint8Array[] }> {
  if (!exportAllowed(sourceId)) throw new ExportRefused(`${sourceId} cannot be exported: its licence is not open or it is unavailable`);
  const encoder = new TextEncoder();
  const shards: Uint8Array[][] = [];
  let size = 0;
  for (const row of rows) {
    const line = encoder.encode(JSON.stringify(row) + '\n');
    if (line.length > limits.bytes) throw new ExportRefused('One row exceeds the shard size limit.');
    if (!shards.length || shards.at(-1)!.length >= limits.rows || size + line.length > limits.bytes) {
      shards.push([]);
      size = 0;
    }
    shards.at(-1)!.push(line);
    size += line.length;
  }
  const bodies = shards.map(join);
  const source = data.sources.find(s => s.id === sourceId)!;
  return {
    shards: bodies,
    manifest: {
      schema_version: 1, source_id: sourceId, licence: source.licence, rows: rows.length,
      content_sha256: await hex(join(bodies)),
      shards: await Promise.all(bodies.map(async (body, i) => ({
        path: `shard-${String(i + 1).padStart(4, '0')}.ndjson`, rows: shards[i].length, bytes: body.length, sha256: await hex(body),
      }))),
    },
  };
}
