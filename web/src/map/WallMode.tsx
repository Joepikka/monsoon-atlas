// T188: wall display. A large snapshot timestamp, per-source health and the existing pausable alert
// ticker. A snapshot is either current (connected and at most 24 hours old, the
// same limit as the app), stale, or the feed is disconnected, and a disconnected or stale wall
// shows the last timestamps it has, styled as stale, with no alerts. No sound, no animation, no
// flashing; Escape or the exit button leaves. The ticker pauses with its own button and starts
// paused under reduced motion. Strings come from the i18n lookup (D148). Mounted at ?page=wall (D154, D172).
import { useEffect, useRef, useState } from 'react';
import { type Health, type MapRecord, type Snapshot, type SourceHealth, STALE_MS, type ViewState } from '../data';
import EventTicker from '../components/EventTicker';
import { t } from '../i18n';
import { localTime } from '../time';

export type WallState = 'current' | 'stale' | 'disconnected';
export type SourceState = Health | 'disconnected';

export function wallState(asOf: string, nowMs: number, connected: boolean): WallState {
  if (!connected) return 'disconnected';
  const age = nowMs - Date.parse(asOf);
  return Number.isFinite(age) && age >= 0 && age <= STALE_MS ? 'current' : 'stale';
}

/** A source is only available if it says so, succeeded within 24 hours and the feed is connected. */
export function sourceState(source: SourceHealth, nowMs: number, connected: boolean): SourceState {
  if (!connected) return 'disconnected';
  if (source.status !== 'available') return source.status;
  const age = source.last_success_at ? nowMs - Date.parse(source.last_success_at) : Number.NaN;
  return age >= 0 && age <= STALE_MS ? 'available' : 'stale';
}

/** Connected only if the last snapshot load did not fail and the browser reports it is online. */
export const wallConnected = (status: ViewState['status'], online: boolean): boolean => online && status !== 'error';

export const wallKey = (key: string): 'exit' | null => (key === 'Escape' ? 'exit' : null);

/** Source tiles per row, by viewport width: four at 1920 px and wider. */
export const wallColumns = (widthPx: number): number => (widthPx >= 1920 ? 4 : widthPx >= 1280 ? 3 : widthPx >= 800 ? 2 : 1);

export function stateText(state: SourceState): string {
  switch (state) {
    case 'available': return t('wall.status_available');
    case 'stale': return t('wall.status_stale');
    case 'unavailable': return t('wall.status_unavailable');
    case 'partial': return t('wall.status_partial');
    case 'unknown': return t('wall.status_unknown');
    case 'disconnected': return t('wall.status_disconnected');
  }
}

export function wallStateText(state: WallState): string {
  return state === 'current' ? t('wall.state_current') : state === 'stale' ? t('wall.state_stale') : t('wall.state_disconnected');
}

export default function WallMode({ snapshot, records, connected, now, onExit }: {
  snapshot: Pick<Snapshot, 'as_of' | 'sources'>; records: MapRecord[]; connected: boolean; now: number; onExit: () => void;
}) {
  const exit = useRef<HTMLButtonElement>(null);
  const [width, setWidth] = useState(() => globalThis.window?.innerWidth ?? 1920);
  useEffect(() => { exit.current?.focus(); }, []);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (wallKey(event.key) === 'exit') onExit(); };
    const onResize = () => setWidth(window.innerWidth);
    window.addEventListener('keydown', onKey);
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('resize', onResize); };
  }, [onExit]);
  const state = wallState(snapshot.as_of, now, connected);
  return <section className={`wall-mode wall-${state}`} data-state={state} aria-label={t('wall.title')}>
    <header className="wall-head">
      <h1>{t('wall.title')}</h1>
      <button type="button" ref={exit} onClick={onExit}>{t('wall.exit')}</button>
    </header>
    <p className="wall-state" role="status">{wallStateText(state)}</p>
    <p className="wall-time"><span>{t('wall.as_of')}</span>{' '}
      <time dateTime={snapshot.as_of}>{localTime(snapshot.as_of)}</time></p>
    <h2>{t('wall.sources')}</h2>
    <ul className="wall-sources" style={{ gridTemplateColumns: `repeat(${wallColumns(width)}, 1fr)` }}>
      {snapshot.sources.map(source => {
        const s = sourceState(source, now, connected);
        return <li key={source.source_id} className={`wall-source wall-source-${s}`} data-state={s}>
          <strong>{source.source_id}</strong> <span>{stateText(s)}</span>
          <small>{source.last_success_at
            ? <time dateTime={source.last_success_at}>{t('wall.source_success', { time: localTime(source.last_success_at) })}</time>
            : t('wall.source_none')}</small>
        </li>;
      })}
    </ul>
    {state === 'current' ? <div className="wall-ticker"><EventTicker records={records} now={now} /></div>
      : <p className="wall-alerts-hidden">{t('wall.alerts_hidden')}</p>}
    <p className="wall-note">{t('wall.not_emergency')}</p>
  </section>;
}
