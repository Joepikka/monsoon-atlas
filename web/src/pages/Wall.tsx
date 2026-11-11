// F006: ?page=wall. Decides WallMode's `connected` from data the app already has: the last snapshot
// load did not fail and the browser is online (D154, D172). It reloads every 5 minutes, so a failed
// reload keeps the last snapshot but shows it as disconnected, never as current.
import { useEffect, useState } from 'react';
import { loadSnapshot, type ViewState } from '../data';
import WallMode, { wallConnected } from '../map/WallMode';
import { t } from '../i18n';
import '../styles.css';

const RELOAD_MS = 5 * 60 * 1000;
const leave = () => { window.location.href = './'; };

export default function Wall() {
  const [view, setView] = useState<ViewState>({ status: 'loading', snapshot: null, message: '' });
  const [online, setOnline] = useState(() => navigator.onLine);
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    let last: ViewState['snapshot'] = null;
    const load = () => loadSnapshot('ka', last).then(result => { last = result.snapshot; setView(result); });
    load();
    const timers = [setInterval(load, RELOAD_MS), setInterval(() => setNow(Date.now()), 30000)];
    const on = () => setOnline(true), off = () => setOnline(false);
    window.addEventListener('online', on); window.addEventListener('offline', off);
    return () => { timers.forEach(clearInterval); window.removeEventListener('online', on); window.removeEventListener('offline', off); };
  }, []);
  if (!view.snapshot) return <main className="wall-mode" aria-live="polite">
    <p role="status">{view.status === 'loading' ? t('display.loading') : t('display.none')}</p>
    <p><a href="./">{t('ask.back')}</a></p></main>;
  return <WallMode snapshot={view.snapshot} records={view.snapshot.records}
    connected={wallConnected(view.status, online)} now={now} onExit={leave} />;
}
