// D189: ?page=warnings, the Karnataka official warning archive. Reads /data/ka/alerts/archive.json
// (built from every stored S09 snapshot). Provider text, severity and times are shown as issued;
// nothing is inferred. Not an emergency service.
import { useEffect, useMemo, useState } from 'react';
import { t } from '../i18n';
import { localTime } from '../time';
import '../styles.css';

export interface ArchivedWarning {
  id: string; title: string; severity: string | null; issued_at: string | null; expires_at: string | null;
  area_text: string | null; warning_text: string | null; instruction: string | null; source_url: string;
  first_seen: string; last_seen: string;
}
export interface Archive { archive_since: string | null; built_at: string; count: number; warnings: ArchivedWarning[] }

const text = (v: unknown) => (typeof v === 'string' ? v : null);

export function parseArchive(value: unknown): Archive {
  const data = value as Record<string, unknown>;
  if (!data || data.schema_version !== 1 || data.state !== 'ka' || !Array.isArray(data.warnings)) throw new Error('Invalid warning archive.');
  const warnings = (data.warnings as Record<string, unknown>[]).map(w => {
    const url = text(w.source_url);
    if (!text(w.id) || !text(w.title) || !url || !url.startsWith('https://') || !text(w.first_seen) || !text(w.last_seen)) {
      throw new Error('Invalid archived warning.');
    }
    return { id: w.id as string, title: w.title as string, severity: text(w.severity), issued_at: text(w.issued_at),
      expires_at: text(w.expires_at), area_text: text(w.area_text), warning_text: text(w.warning_text),
      instruction: text(w.instruction), source_url: url, first_seen: w.first_seen as string, last_seen: w.last_seen as string };
  });
  return { archive_since: text(data.archive_since), built_at: String(data.built_at), count: warnings.length, warnings };
}

export function filterWarnings(list: ArchivedWarning[], query: string, severity: string): ArchivedWarning[] {
  const q = query.trim().toLowerCase();
  return list.filter(w => (!severity || w.severity === severity) &&
    (!q || [w.title, w.area_text, w.warning_text].some(s => s?.toLowerCase().includes(q))));
}

const fetchArchive = () => fetch('/data/ka/alerts/archive.json', { cache: 'no-store' }).then(r => r.json());

export default function Warnings({ load = fetchArchive }: { load?: () => Promise<unknown> }) {
  const [state, setState] = useState<{ archive?: Archive; error?: string }>({});
  const [query, setQuery] = useState('');
  const [severity, setSeverity] = useState('');
  useEffect(() => {
    load().then(v => setState({ archive: parseArchive(v) }), () => setState({ error: t('archive.unavailable') }));
  }, [load]);
  const shown = useMemo(() => state.archive ? filterWarnings(state.archive.warnings, query, severity) : [], [state.archive, query, severity]);
  const severities = useMemo(() => Array.from(new Set((state.archive?.warnings ?? [])
    .map(w => w.severity).filter((s): s is string => !!s))), [state.archive]);
  const archive = state.archive;
  return <main className="dashboard" aria-labelledby="archive-heading">
    <p><a href="./">{t('ask.back')}</a></p>
    <h1 id="archive-heading">{t('archive.title')}</h1>
    <p>{t('archive.intro')}</p>
    <p className="notice">{t('archive.emergency')}</p>
    {state.error && <p role="alert">{state.error}</p>}
    {archive && <>
      <p>{archive.archive_since && <>{t('archive.since')} <time dateTime={archive.archive_since}>{localTime(archive.archive_since)}</time> · </>}
        {t('archive.count')}: {archive.count}</p>
      <div className="archive-filters">
        <label>{t('archive.search')} <input type="search" value={query} onChange={e => setQuery(e.target.value)} /></label>
        <label>{t('archive.severity')} <select value={severity} onChange={e => setSeverity(e.target.value)}>
          <option value="">{t('archive.all')}</option>{severities.map(s => <option key={s} value={s}>{s}</option>)}</select></label>
      </div>
      {shown.length ? <ul className="lens-records">{shown.map(w => <li key={w.id}>
        <h4>{w.title}</h4>
        <p>{w.severity ?? '—'} · {t('archive.issued')} {w.issued_at ? <time dateTime={w.issued_at}>{localTime(w.issued_at)}</time> : '—'}
          {' · '}{t('archive.expires')} {w.expires_at ? <time dateTime={w.expires_at}>{localTime(w.expires_at)}</time> : '—'}</p>
        {w.area_text && <p>{w.area_text}</p>}
        {w.warning_text && <blockquote>{w.warning_text}</blockquote>}
        {w.instruction && <p>{w.instruction}</p>}
        <a href={w.source_url} target="_blank" rel="noopener noreferrer">{t('archive.original')}</a>
      </li>)}</ul> : <p>{archive.count ? t('archive.nomatch') : t('archive.empty')}</p>}
    </>}
  </main>;
}
