// D192: ?page=monsoon, the Karnataka district monsoon tracker. ERA5 reanalysis rain (S02) to date
// vs the same window in 2001-2025, per district and season. Model reanalysis, about 6 days behind,
// one grid point per district: never called observed rain.
import { useEffect, useMemo, useState } from 'react';
import { t } from '../i18n';
import '../styles.css';

export interface MonsoonRow {
  district: string; season: 'southwest' | 'northeast'; through: string; complete: boolean;
  rain_mm: number | null; median_mm?: number; pct_of_median?: number | null; rank_percentile?: number; band?: string | null;
  reference_years: number;
}
export interface Tracker { year: number; built_on: string; reference: string; label: string; rows: MonsoonRow[] }

const BAND_COLOR: Record<string, string> = {
  'far below normal': '#b3261e', 'below normal': '#e07b39', 'near normal': '#6b7280',
  'above normal': '#2e7db5', 'far above normal': '#1f4e8c',
};

export function parseTracker(value: unknown): Tracker {
  const d = value as Record<string, unknown>;
  if (!d || d.schema_version !== 1 || d.state !== 'ka' || d.source_id !== 'S02' || !Array.isArray(d.rows)) throw new Error('Invalid monsoon tracker.');
  const rows = (d.rows as MonsoonRow[]).filter(r => typeof r.district === 'string' && (r.season === 'southwest' || r.season === 'northeast'));
  return { year: Number(d.year), built_on: String(d.built_on), reference: String(d.reference), label: String(d.label), rows };
}

export function seasonRows(tracker: Tracker, season: MonsoonRow['season']): MonsoonRow[] {
  return tracker.rows.filter(r => r.season === season)
    .sort((a, b) => (a.pct_of_median ?? Infinity) - (b.pct_of_median ?? Infinity) || a.district.localeCompare(b.district));
}

const fetchTracker = () => fetch('/data/ka/monsoon.json', { cache: 'no-store' }).then(r => r.json());

export default function Monsoon({ load = fetchTracker }: { load?: () => Promise<unknown> }) {
  const [tracker, setTracker] = useState<Tracker | null>(null);
  const [failed, setFailed] = useState(false);
  const [season, setSeason] = useState<MonsoonRow['season']>('northeast');
  useEffect(() => { load().then(v => setTracker(parseTracker(v)), () => setFailed(true)); }, [load]);
  const rows = useMemo(() => tracker ? seasonRows(tracker, season) : [], [tracker, season]);
  return <main className="dashboard" aria-labelledby="monsoon-heading">
    <p><a href="./">{t('ask.back')}</a></p>
    <h1 id="monsoon-heading">{t('monsoon.title')}</h1>
    <p>{t('monsoon.intro')}</p>
    {failed && <p role="alert">{t('monsoon.unavailable')}</p>}
    {tracker && <>
      <p className="notice">{tracker.label}. {t('monsoon.reference', { reference: tracker.reference })}</p>
      <label>{t('monsoon.season')} <select value={season} onChange={e => setSeason(e.target.value as MonsoonRow['season'])}>
        <option value="southwest">{t('monsoon.southwest')}</option><option value="northeast">{t('monsoon.northeast')}</option></select></label>
      {rows.length ? <table className="monsoon-table"><thead><tr>
        <th scope="col">{t('monsoon.district')}</th><th scope="col">{t('monsoon.through')}</th>
        <th scope="col">{t('monsoon.rain')}</th><th scope="col">{t('monsoon.median')}</th>
        <th scope="col">{t('monsoon.pct')}</th><th scope="col">{t('monsoon.rank')}</th><th scope="col">{t('monsoon.status')}</th>
      </tr></thead><tbody>{rows.map(r => <tr key={r.district}>
        <th scope="row">{r.district}</th>
        <td>{r.through}{r.complete ? ` (${t('monsoon.complete')})` : ''}</td>
        <td>{r.rain_mm ?? '—'}</td><td>{r.median_mm ?? '—'}</td>
        <td>{r.pct_of_median != null ? `${r.pct_of_median}%` : '—'}</td>
        <td>{r.rank_percentile != null ? r.rank_percentile : '—'}</td>
        <td>{r.band ? <span className="band-chip" style={{ background: BAND_COLOR[r.band] }}>{r.band}</span> : '—'}</td>
      </tr>)}</tbody></table> : <p>{t('monsoon.empty')}</p>}
    </>}
  </main>;
}
