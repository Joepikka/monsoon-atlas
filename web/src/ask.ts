// T261 (child of T182): hash-checked public Ask corpus and the Worker answer call (D96).
import { sha256 } from './data';
import type { CorpusChunk } from './ask-search';

export type CorpusView =
  | { status: 'loading' | 'empty' | 'error'; message: string }
  | { status: 'ready'; message: string; release: string; chunks: CorpusChunk[] };
export interface AskResult {
  source: 'worker' | 'local'; mode: 'generated' | 'extractive'; status: string;
  answer: string; cited: CorpusChunk[]; asOf: string; notice: string;
}

const HASH = /^[0-9a-f]{64}$/;
const MAX_BYTES = 2 * 1024 * 1024;
const FIELDS = ['chunk_id', 'doc_id', 'path', 'heading', 'text', 'available_at', 'states', 'sha256'] as const;

export function parseCorpus(value: unknown): CorpusChunk[] {
  const data = value as { schema_version?: unknown; chunks?: unknown } | null;
  if (!data || data.schema_version !== 1 || !Array.isArray(data.chunks) || !data.chunks.length) throw new Error('Invalid Ask corpus.');
  return data.chunks.map(raw => {
    const item = raw as Record<string, unknown>;
    if (!item || FIELDS.some(key => typeof item[key] !== 'string') || !(item.expires_at === null || typeof item.expires_at === 'string')) {
      throw new Error('Invalid Ask corpus.');
    }
    return item as unknown as CorpusChunk;
  });
}

export async function loadCorpus(fetcher: typeof fetch = fetch): Promise<CorpusView> {
  try {
    const response = await fetcher('/data/ask/latest.json', { cache: 'no-store', headers: { Accept: 'application/json' } });
    if (response.status === 404) return { status: 'empty', message: 'Ask has not been published yet.' };
    if (!response.ok) throw new Error('The Ask corpus could not be reached.');
    const pointer = (await response.json()) as Record<string, unknown>;
    if (pointer.schema_version !== 1 || typeof pointer.release !== 'string' || !HASH.test(pointer.release) ||
        pointer.url !== `/data/ask/${pointer.release}.json`) throw new Error('The Ask corpus URL is not an immutable release.');
    const file = await fetcher(pointer.url, { headers: { Accept: 'application/json' } });
    if (!file.ok) throw new Error('The Ask corpus could not be loaded.');
    const bytes = new Uint8Array(await file.arrayBuffer());
    if (bytes.byteLength > MAX_BYTES) throw new Error('The Ask corpus exceeds the two-megabyte limit.');
    // The release ID is the SHA-256 of these exact bytes (D95), so the Worker serves the same chunks.
    if (await sha256(bytes) !== pointer.release) throw new Error('Ask corpus integrity check failed.');
    const chunks = parseCorpus(JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)));
    return { status: 'ready', message: `${chunks.length} document sections loaded.`, release: pointer.release, chunks };
  } catch (error) {
    return { status: 'error', message: error instanceof Error ? error.message : 'The Ask corpus could not be loaded.' };
  }
}

export const utcSecond = (date: Date): string => date.toISOString().slice(0, 19) + 'Z';

const local = (found: CorpusChunk[], asOf: string, notice: string): AskResult => ({
  source: 'local', mode: 'extractive', status: found.length ? 'local_results' : 'insufficient_evidence',
  answer: found.length ? 'Matching sections from the project documents (not a generated answer):'
    : 'No project document matches this question. Check the linked official sources.',
  cited: found, asOf, notice,
});

/** Ask the Worker about the chosen chunks; any failure or mismatch shows the local results instead. */
export async function askWorker(question: string, found: CorpusChunk[], release: string, asOf: string,
  fetcher: typeof fetch = fetch): Promise<AskResult> {
  if (!found.length) return local(found, asOf, '');
  try {
    const response = await fetcher('/api/v1/ask', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ query: question, language: 'en', place_id: 'in:ka', as_of: asOf, chunk_ids: found.map(item => item.chunk_id) }) });
    if (!response.ok) throw new Error('unavailable');
    const data = (await response.json()) as Record<string, unknown>;
    const byId = new Map(found.map(item => [item.chunk_id, item]));
    const citations = Array.isArray(data.citations) ? data.citations as { chunk_id?: unknown }[] : null;
    if (data.release !== release || data.as_of !== asOf || typeof data.answer !== 'string' || typeof data.status !== 'string' ||
        (data.mode !== 'extractive' && data.mode !== 'generated') || !citations ||
        citations.some(item => typeof item?.chunk_id !== 'string' || !byId.has(item.chunk_id))) throw new Error('mismatch');
    const cited = [...new Set(citations.map(item => item.chunk_id as string))].map(id => byId.get(id)!);
    return { source: 'worker', mode: data.mode, status: data.status, answer: data.answer, cited, asOf, notice: '' };
  } catch {
    return local(found, asOf, 'The answer service is unavailable, so these are the local search results.');
  }
}

/** Whole days from the commit time to the as-of time, for the evidence-age label. */
export function ageDays(availableAt: string, asOf: string): number {
  return Math.max(0, Math.floor((Date.parse(asOf) - Date.parse(availableAt)) / 86_400_000));
}
