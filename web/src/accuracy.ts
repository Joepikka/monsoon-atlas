// T259 (child of T046): approved accuracy release loader. Unavailable is never zero (D94).
import { sha256 } from './data';

export interface AccuracyRow {
  model: string; core: string; target: string; baseline: string | null; test: string | null;
  metric: string | null; candidate: number | null; baseline_value: number | null;
  improvement: number | null; ci95: [number, number] | null; status: string; report: string;
}
export type AccuracyView =
  | { status: 'loading'; rows: null; message: string }
  | { status: 'empty' | 'error'; rows: null; message: string }
  | { status: 'ready'; rows: AccuracyRow[]; message: string; releaseHash: string };

const HASH = /^[0-9a-f]{64}$/;
const MAX_BYTES = 1024 * 1024;
const POINTER = '/data/ka/accuracy/latest.json';

const text = (value: unknown, name: string): string => {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`Accuracy row has no ${name}.`);
  return value;
};
const optionalText = (value: unknown, name: string): string | null => value === null ? null : text(value, name);
const optionalNumber = (value: unknown): number | null => {
  // Blocked models carry null (or an empty legacy list); never coerce either to 0.
  if (value === null || (Array.isArray(value) && value.length === 0)) return null;
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error('Accuracy values must be finite numbers or null.');
  return value;
};

export function parseAccuracy(value: unknown): AccuracyRow[] {
  if (!value || typeof value !== 'object') throw new Error('Invalid accuracy release.');
  const data = value as Record<string, unknown>;
  if (data.schema_version !== 1 || data.state !== 'ka' || !Array.isArray(data.rows)) {
    throw new Error('Invalid accuracy release.');
  }
  return data.rows.map(raw => {
    const row = raw as Record<string, unknown>;
    let ci95: [number, number] | null = null;
    if (row.ci95 !== null && row.ci95 !== undefined) {
      const pair = row.ci95 as unknown[];
      const [low, high] = Array.isArray(pair) && pair.length === 2 ? pair.map(optionalNumber) : [null, null];
      if (low === null || high === null || low > high) throw new Error('Accuracy interval is invalid.');
      ci95 = [low, high];
    }
    return {
      model: text(row.model, 'model'), core: text(row.core, 'core'), target: text(row.target, 'target'),
      baseline: optionalText(row.baseline, 'baseline'), test: optionalText(row.test, 'test period'),
      metric: optionalText(row.metric, 'metric'), candidate: optionalNumber(row.candidate),
      baseline_value: optionalNumber(row.baseline_value), improvement: optionalNumber(row.improvement),
      ci95, status: text(row.status, 'status'), report: text(row.report, 'report'),
    };
  });
}

export async function loadAccuracy(fetcher: typeof fetch = fetch): Promise<AccuracyView> {
  try {
    const response = await fetcher(POINTER, { cache: 'no-store', headers: { Accept: 'application/json' } });
    if (response.status === 404) return { status: 'empty', rows: null, message: 'No approved accuracy table has been released yet.' };
    if (!response.ok) throw new Error('The accuracy release could not be reached.');
    const pointer = (await response.json()) as Record<string, unknown>;
    if (pointer.schema_version !== 1 || pointer.state !== 'ka') throw new Error('Invalid accuracy pointer.');
    if (pointer.approval !== 'approved') throw new Error('Accuracy publication approval is pending.');
    if (typeof pointer.sha256 !== 'string' || !HASH.test(pointer.sha256) ||
        pointer.manifest_url !== `/data/ka/accuracy/${pointer.sha256}.json`) {
      throw new Error('The accuracy URL is not an immutable release.');
    }
    const manifest = await fetcher(pointer.manifest_url, { headers: { Accept: 'application/json' } });
    if (!manifest.ok) throw new Error('The accuracy release could not be loaded.');
    const bytes = new Uint8Array(await manifest.arrayBuffer());
    if (bytes.byteLength > MAX_BYTES) throw new Error('The accuracy release exceeds the one-megabyte limit.');
    if (await sha256(bytes) !== pointer.sha256) throw new Error('Accuracy integrity check failed.');
    const rows = parseAccuracy(JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)));
    return { status: 'ready', rows, message: 'Approved accuracy table loaded.', releaseHash: pointer.sha256 };
  } catch (error) {
    return { status: 'error', rows: null, message: error instanceof Error ? error.message : 'The accuracy table could not be loaded.' };
  }
}

export const show = (value: number | null): string => value === null ? 'Unavailable' : value.toFixed(3);
