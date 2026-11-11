import { useEffect, useMemo, useState } from 'react';
import type { MapRecord } from '../data';
import { t } from '../i18n';
import { localTime } from '../time';

export default function EventTicker({ records, now }: { records: MapRecord[]; now: number }) {
  const alerts = useMemo(() => records.filter(record => record.kind === 'alert' && record.provenance === 'official'), [records]);
  const [paused, setPaused] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [index, setIndex] = useState(0);
  useEffect(() => setIndex(0), [alerts]);
  useEffect(() => {
    if (paused || alerts.length < 2) return;
    const timer = setInterval(() => setIndex(current => (current + 1) % alerts.length), 8000);
    return () => clearInterval(timer);
  }, [alerts, paused]);
  const alert = alerts[index % alerts.length];
  if (!alert) return null;
  return <section className="event-ticker" aria-label={t('ticker.region')}>
    <p aria-live="polite" aria-atomic="true"><span className="ticker-label">{t('ticker.label')}</span>
      <a href={alert.source_url} target="_blank" rel="noopener noreferrer">{alert.title}</a>
      {alert.severity && <span className="ticker-severity">{alert.severity}</span>}
      {alert.expires_at && <><span className="ticker-severity">{Date.parse(alert.expires_at) <= now ? t('ticker.expired') : t('ticker.expires')}</span>
        <time dateTime={alert.expires_at}>{localTime(alert.expires_at)}</time></>}
    </p>
    <button type="button" aria-pressed={paused} onClick={() => setPaused(current => !current)}>{paused ? t('ticker.resume') : t('ticker.pause')}</button>
  </section>;
}
