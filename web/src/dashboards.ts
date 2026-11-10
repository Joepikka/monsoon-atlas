// T217 (D161): data and rules shared by the accuracy, quality, analysis and comparison pages.
// The data file is built by atlas.models.accuracy from the registry and source records; a Python
// test regenerates it, so these pages cannot drift from the evidence.
import raw from './dashboards.json';
import { SOURCE_BASE } from './ask';
import { t } from './i18n';

export interface Series {
  state: string; name: string; level: string; unit: string; span: [string, string];
  normalisation: string | null; coverage: number | null; link: string;
}
export const data = raw as unknown as Omit<typeof raw, 'series'> & { series: Series[] };

export const href = (path: string): string => SOURCE_BASE + path;

/** Undefined denominators (null, zero, NaN) give null, never 0 or NaN. */
export function ratio(numerator: number | null, denominator: number | null): number | null {
  if (numerator === null || denominator === null || !Number.isFinite(numerator)) return null;
  if (!Number.isFinite(denominator) || denominator === 0) return null;
  return numerator / denominator;
}

export const num = (value: number | null | undefined, digits = 3): string =>
  value === null || value === undefined || !Number.isFinite(value) ? t('dash.unavailable') : value.toFixed(digits);

export type Reason = 'none' | 'level' | 'span' | 'unit' | 'norm' | 'coverage';
export type Comparison = { ok: true; span: [string, string] } | { ok: false; reason: Reason };

const NORMALISATIONS = ['per_capita', 'per_area', 'climate_reference'];

/** Two series may be compared only on the same level and unit, an overlapping span, a stated normalisation and coverage. */
export function comparable(a: Series | null, b: Series | null): Comparison {
  if (!a || !b) return { ok: false, reason: 'none' };
  if (a.level !== b.level) return { ok: false, reason: 'level' };
  if (a.unit !== b.unit) return { ok: false, reason: 'unit' };
  const from = a.span[0] > b.span[0] ? a.span[0] : b.span[0];
  const to = a.span[1] < b.span[1] ? a.span[1] : b.span[1];
  if (from > to) return { ok: false, reason: 'span' };
  if (![a, b].every(s => s.normalisation !== null && NORMALISATIONS.includes(s.normalisation))) {
    return { ok: false, reason: 'norm' };
  }
  if (![a, b].every(s => s.coverage !== null && Number.isFinite(s.coverage) && s.coverage > 0 && s.coverage <= 1)) {
    return { ok: false, reason: 'coverage' };
  }
  return { ok: true, span: [from, to] };
}

export const reasonText = (reason: Reason): string => ({
  none: () => t('cmp.r_none'), level: () => t('cmp.r_level'), span: () => t('cmp.r_span'),
  unit: () => t('cmp.r_unit'), norm: () => t('cmp.r_norm'), coverage: () => t('cmp.r_cov'),
})[reason]();
