// T145: monsoon tracker, rainfall trend and climate projections from derived statistics (D130).
// Rain is shown as indices only (S08 licence, D129); NDVI is unavailable while S42 is blocked.
// Mounted at ?page=climate after H11: the data holds no S08 value in mm (D166, D167).
import { useEffect, useState } from 'react';
import data from '../climate.json';
import { t } from '../i18n';

export const PROJECTION_LABEL = 'climate projection, not a forecast';
type Checkpoint = { date: string; reference_years: number; value_pct_of_median: number | null;
  rank_percentile: number | null; band_p10_pct_of_median: number | null; band_p90_pct_of_median: number | null };
export interface ClimateProduct {
  ndvi: { status: string; reason: string | null; wording: string };
  tracker: { year: number; reference: string; checkpoints: Checkpoint[] };
  onset: { official_onset: string | null; reason: string | null; inferred: { onset: string | null; label: string; method: string } };
  trend: { area: string; first_year: number; last_year: number; n_years: number; slope_pct_per_decade: number }[];
  projection: { label: string; baseline: string; window: string; by_point: Record<string, Record<string, number>> };
  limits: string[];
}

export function parseClimate(value: unknown): ClimateProduct {
  const p = value as ClimateProduct;
  if (!p || p.projection?.label !== PROJECTION_LABEL) throw new Error('projection without its label');
  if (p.tracker?.reference !== '1981-2010') throw new Error('climatology must be 1981-2010');
  if (p.onset?.official_onset === null && !p.onset.reason) throw new Error('missing onset without a reason');
  if (p.onset?.inferred?.label !== 'inferred') throw new Error('heuristic onset must be labelled inferred');
  if (p.ndvi?.status !== 'ready' && !p.ndvi?.reason) throw new Error('unavailable NDVI without a reason');
  if (!Array.isArray(p.trend) || !Array.isArray(p.limits)) throw new Error('invalid climate product');
  return p;
}

const num = (v: number | null, unit = '') => v === null ? t('climate.unavailable') : `${v}${unit}`;

// Bundled like dashboards.json: web/public holds no data (D162, D172).
export default function Climate({ load = () => Promise.resolve<unknown>(data) }: { load?: () => Promise<unknown> }) {
  const [state, setState] = useState<{ product?: ClimateProduct; error?: string }>({});
  useEffect(() => {
    load().then(v => setState({ product: parseClimate(v) }))
      .catch(e => setState({ error: String(e.message ?? e) }));
  }, [load]);
  const p = state.product;
  if (!p) return <main className="climate"><h1>{t('climate.title')}</h1>
    <p role="status">{state.error ?? t('climate.loading')}</p></main>;
  return <main className="climate" aria-labelledby="climate-heading">
    <h1 id="climate-heading">{t('climate.title')}</h1>
    <p role="note">{t('climate.note')}</p>

    <h2>{t('climate.tracker_h', { year: p.tracker.year })}</h2>
    <p>{t('climate.tracker_intro', { reference: p.tracker.reference })}</p>
    <table tabIndex={0}><thead><tr><th scope="col">{t('climate.col_date')}</th><th scope="col">{t('climate.col_pct')}</th><th scope="col">{t('climate.col_rank')}</th>
      <th scope="col">{t('climate.col_range')}</th></tr></thead>
      <tbody>{p.tracker.checkpoints.map(c => <tr key={c.date}><th scope="row">{c.date}</th>
        <td>{num(c.value_pct_of_median, '%')}</td><td>{num(c.rank_percentile)}</td>
        <td>{c.band_p10_pct_of_median === null ? t('climate.unavailable') : t('climate.range', { lo: c.band_p10_pct_of_median, hi: c.band_p90_pct_of_median ?? '' })}</td></tr>)}</tbody></table>
    <p>{t('climate.onset', { official: p.onset.official_onset ?? t('climate.onset_none', { reason: p.onset.reason ?? '' }),
      label: p.onset.inferred.label, inferred: p.onset.inferred.onset ?? t('climate.onset_notfound'), method: p.onset.inferred.method })}</p>

    <h2>{t('climate.trend_h')}</h2>
    <table tabIndex={0}><thead><tr><th scope="col">{t('climate.col_area')}</th><th scope="col">{t('climate.col_years')}</th><th scope="col">{t('climate.col_trend')}</th></tr></thead>
      <tbody>{p.trend.map(r => <tr key={r.area}><th scope="row">{r.area}</th>
        <td>{t('climate.years', { first: r.first_year, last: r.last_year, n: r.n_years })}</td><td>{r.slope_pct_per_decade}</td></tr>)}</tbody></table>

    <h2>{t('climate.proj_h', { label: t('climate.proj_label') })}</h2>
    <p>{t('climate.proj_intro', { baseline: p.projection.baseline })}</p>
    {Object.entries(p.projection.by_point).map(([point, models]) => <table key={point} tabIndex={0}>
      <caption>{point}</caption><thead><tr><th scope="col">{t('climate.col_model')}</th><th scope="col">{t('climate.col_change')}</th></tr></thead>
      <tbody>{Object.entries(models).map(([m, v]) => <tr key={m}><th scope="row">{m}</th><td>{v}</td></tr>)}</tbody></table>)}

    <h2>{t('climate.ndvi_h')}</h2>
    <p>{p.ndvi.status === 'ready' ? t('climate.ndvi_ready', { wording: p.ndvi.wording })
      : t('climate.ndvi_unavailable', { reason: p.ndvi.reason ?? '', wording: p.ndvi.wording })}</p>

    <h2>{t('climate.limits_h')}</h2>
    <ul>{p.limits.map(l => <li key={l}>{l}</li>)}</ul>
  </main>;
}
