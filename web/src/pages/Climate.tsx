// T145: monsoon tracker, rainfall trend and climate projections from derived statistics (D130).
// Rain is shown as indices only (S08 licence, D129); NDVI is unavailable while S42 is blocked.
// Not mounted: it waits for the H11 decision on the S08 licence finding.
import { useEffect, useState } from 'react';

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

const num = (v: number | null, unit = '') => v === null ? 'Unavailable' : `${v}${unit}`;

export default function Climate({ fetcher = fetch }: { fetcher?: typeof fetch }) {
  const [state, setState] = useState<{ product?: ClimateProduct; error?: string }>({});
  useEffect(() => {
    fetcher('./climate.json').then(r => r.json()).then(v => setState({ product: parseClimate(v) }))
      .catch(e => setState({ error: String(e.message ?? e) }));
  }, [fetcher]);
  const p = state.product;
  if (!p) return <main className="climate"><h1>Monsoon and climate</h1>
    <p role="status">{state.error ?? 'Loading the climate statistics…'}</p></main>;
  return <main className="climate" aria-labelledby="climate-heading">
    <p><a href="./">Back to the map</a></p>
    <h1 id="climate-heading">Monsoon and climate</h1>
    <p role="note">Past years and model projections only. Nothing here is a forecast, a warning or an emergency service.</p>

    <h2>Monsoon rain so far, {p.tracker.year} (past year, not live)</h2>
    <p>Rain since 1 June against the {p.tracker.reference} distribution, as percent of the median.</p>
    <table><thead><tr><th scope="col">Date</th><th scope="col">Percent of median</th><th scope="col">Percentile rank</th>
      <th scope="col">Normal range (10th to 90th percentile)</th></tr></thead>
      <tbody>{p.tracker.checkpoints.map(c => <tr key={c.date}><th scope="row">{c.date}</th>
        <td>{num(c.value_pct_of_median, '%')}</td><td>{num(c.rank_percentile)}</td>
        <td>{c.band_p10_pct_of_median === null ? 'Unavailable' : `${c.band_p10_pct_of_median}% to ${c.band_p90_pct_of_median}%`}</td></tr>)}</tbody></table>
    <p>Official onset: {p.onset.official_onset ?? `none (${p.onset.reason})`}.
      Inferred onset ({p.onset.inferred.label}, not an official date): {p.onset.inferred.onset ?? 'not found'}; {p.onset.inferred.method}.</p>

    <h2>Annual rain trend</h2>
    <table><thead><tr><th scope="col">Area</th><th scope="col">Years held</th><th scope="col">Trend, percent of normal per decade</th></tr></thead>
      <tbody>{p.trend.map(t => <tr key={t.area}><th scope="row">{t.area}</th>
        <td>{t.first_year} to {t.last_year} ({t.n_years})</td><td>{t.slope_pct_per_decade}</td></tr>)}</tbody></table>

    <h2>Model projections for 2021 to 2050 ({PROJECTION_LABEL})</h2>
    <p>Change in mean annual rain against {p.projection.baseline}, per climate model. The spread between models is not forecast confidence.</p>
    {Object.entries(p.projection.by_point).map(([point, models]) => <table key={point}>
      <caption>{point}</caption><thead><tr><th scope="col">Model</th><th scope="col">Change, percent</th></tr></thead>
      <tbody>{Object.entries(models).map(([m, v]) => <tr key={m}><th scope="row">{m}</th><td>{v}</td></tr>)}</tbody></table>)}

    <h2>Vegetation greenness</h2>
    <p>{p.ndvi.status === 'ready' ? `Showing ${p.ndvi.wording}.` : `Unavailable: ${p.ndvi.reason}. No ${p.ndvi.wording} is shown.`}</p>

    <h2>Limits</h2>
    <ul>{p.limits.map(l => <li key={l}>{l}</li>)}</ul>
  </main>;
}
