import { parseSnapshot, sha256, type Snapshot } from '../../web/src/data.ts';

export const MAX_BLOB = 1024 * 1024;
export const HOT_SOURCES = ['S01', 'S09'] as const;
export class UploadError extends Error {
  status: number;
  constructor(message: string, status = 400) { super(message); this.status = status; }
}

export async function boundedBytes(stream: ReadableStream<Uint8Array> | null, limit = MAX_BLOB): Promise<Uint8Array> {
  if (!stream) throw new UploadError('Missing body.');
  const reader = stream.getReader(); const chunks: Uint8Array[] = []; let length = 0;
  try {
    while (true) {
      const item = await reader.read(); if (item.done) break;
      length += item.value.byteLength;
      if (length > limit) { await reader.cancel(); throw new UploadError('Snapshot exceeds the byte limit.', 413); }
      chunks.push(item.value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return bytes;
}

export async function uploadMessage(timestamp: string, method: string, path: string, bytes: Uint8Array): Promise<Uint8Array> {
  return new TextEncoder().encode(`${timestamp}\n${method}\n${path}\n${await sha256(bytes)}`);
}

export async function authenticate(request: Request, bytes: Uint8Array, secret: string | undefined, now: number): Promise<boolean> {
  const timestamp = request.headers.get('X-Atlas-Timestamp') ?? '';
  const signature = request.headers.get('X-Atlas-Signature') ?? '';
  if (!secret || secret.length < 32 || !/^\d{10,}$/.test(timestamp) || !/^[a-f0-9]{64}$/.test(signature) ||
      !Number.isSafeInteger(Number(timestamp)) || Math.abs(now - Number(timestamp) * 1000) > 300000) return false;
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['verify']);
  const signed = Uint8Array.from(signature.match(/../g)!, value => parseInt(value, 16));
  const message = await uploadMessage(timestamp, request.method, new URL(request.url).pathname, bytes);
  return crypto.subtle.verify('HMAC', key, signed, Uint8Array.from(message).buffer);
}

async function transform(bytes: Uint8Array, compression: boolean): Promise<Uint8Array> {
  const stream = new Blob([Uint8Array.from(bytes).buffer]).stream();
  return boundedBytes(stream.pipeThrough(compression ? new CompressionStream('gzip') : new DecompressionStream('gzip')));
}

export interface Upload { source_id: string; snapshot: Snapshot; sha256: string; compressed: Uint8Array }
function validateEnvelope(value: unknown, now: number): Pick<Upload, 'source_id' | 'snapshot'> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new UploadError('Invalid hot envelope.');
  const decoded = value as { source_id: unknown; snapshot: unknown };
  if (typeof decoded.source_id !== 'string' || !(HOT_SOURCES as readonly string[]).includes(decoded.source_id)) throw new UploadError('Unknown hot source.');
  const snapshot = parseSnapshot(decoded.snapshot, 'ka');
  const cutoff = Date.parse(snapshot.as_of);
  if (cutoff > now || Date.parse(snapshot.published_at) > now || Date.parse(snapshot.published_at) < cutoff) throw new UploadError('Invalid snapshot cutoff or publication time.');
  if (snapshot.records.some(record => record.source_id !== decoded.source_id || Date.parse(record.fetched_at) > cutoff ||
      record.kind !== (decoded.source_id === 'S09' ? 'alert' : 'weather'))) throw new UploadError('Record source, layer or fetch time does not match the upload.');
  if (snapshot.places.length || snapshot.facilities.length || snapshot.sources.length !== 1 ||
      snapshot.sources[0].source_id !== decoded.source_id || snapshot.sources[0].status !== 'available' || !snapshot.sources[0].last_success_at) {
    throw new UploadError('A hot snapshot needs its own successful source health, without unrelated data.');
  }
  return { source_id: decoded.source_id, snapshot };
}

export async function decodeUpload(bytes: Uint8Array, now: number): Promise<Upload> {
  if (bytes.byteLength > MAX_BLOB) throw new UploadError('Compressed snapshot exceeds the limit.', 413);
  try {
    const decoded = validateEnvelope(JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(await transform(bytes, false))), now);
    const canonical = new TextEncoder().encode(JSON.stringify(decoded));
    if (canonical.byteLength > MAX_BLOB) throw new UploadError('Canonical snapshot exceeds the byte limit.', 413);
    return { ...decoded, sha256: await sha256(canonical), compressed: await transform(canonical, true) };
  } catch (error) {
    if (error instanceof UploadError) throw error;
    throw new UploadError('Invalid compressed snapshot or source schema.');
  }
}

export async function restoreUpload(bytes: Uint8Array, expectedHash: string, now: number): Promise<Upload> {
  try {
    if (bytes.byteLength > MAX_BLOB) throw new Error('Oversized stored blob');
    const canonical = await transform(bytes, false);
    if (await sha256(canonical) !== expectedHash) throw new Error('Hash mismatch');
    const decoded = validateEnvelope(JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(canonical)), now);
    return { ...decoded, sha256: expectedHash, compressed: bytes };
  } catch { throw new UploadError('Stored snapshot integrity failure.', 503); }
}
