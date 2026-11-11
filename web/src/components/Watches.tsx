// T183: place watches kept only in this browser's IndexedDB (D149). No account, no network call, no
// location lookup: the page passes in the place list and the signals, and a watch never leaves the
// device. A cancelled, superseded or expired signal never triggers. Mounted in the main app (D172).
import { useEffect, useState, type FormEvent } from 'react';
import type { MapRecord } from '../data';
import { t } from '../i18n';

export interface Watch { id: string; placeId: string; label: string; alerts: boolean; rainMm: number | null }
export interface Signal {
  kind: 'alert' | 'forecast'; placeId: string; status: 'actual' | 'cancelled' | 'superseded';
  rainMm: number | null; validUntil: string | null; sourceUrl: string; text: string;
}

export function parseWatch(value: unknown): Watch {
  const w = value as Partial<Watch> | null;
  if (!w || typeof w.id !== 'string' || !w.id || typeof w.placeId !== 'string' || !w.placeId ||
      typeof w.label !== 'string' || typeof w.alerts !== 'boolean' ||
      !(w.rainMm === null || (typeof w.rainMm === 'number' && Number.isFinite(w.rainMm) && w.rainMm >= 0))) {
    throw new Error('Invalid watch.');
  }
  return { id: w.id, placeId: w.placeId, label: w.label, alerts: w.alerts, rainMm: w.rainMm };
}

/** An alert with no end time stays active; a forecast needs a valid end time; an unreadable one never triggers. */
export function triggered(watch: Watch, signal: Signal, now: number): boolean {
  if (watch.placeId !== signal.placeId || signal.status !== 'actual') return false;
  const live = signal.validUntil === null ? signal.kind === 'alert' : Date.parse(signal.validUntil) > now;
  if (!live) return false;
  if (signal.kind === 'alert') return watch.alerts;
  return watch.rainMm !== null && signal.rainMm !== null && signal.rainMm >= watch.rainMm;
}

const DB = 'monsoon-atlas-watches';
const STORE = 'watches';
const open = (): Promise<IDBDatabase> => new Promise((resolve, reject) => {
  const request = indexedDB.open(DB, 1);
  request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: 'id' });
  request.onsuccess = () => resolve(request.result);
  request.onerror = () => reject(request.error);
});
async function run<T>(mode: IDBTransactionMode, act: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await open();
  return new Promise<T>((resolve, reject) => {
    const request = act(db.transaction(STORE, mode).objectStore(STORE));
    request.onsuccess = () => { db.close(); resolve(request.result); };
    request.onerror = () => { db.close(); reject(request.error); };
  });
}
export const listWatches = async (): Promise<Watch[]> => (await run('readonly', s => s.getAll())).map(parseWatch);
export const saveWatch = (watch: Watch) => run('readwrite', s => s.put(parseWatch(watch)));
export const deleteWatch = (id: string) => run('readwrite', s => s.delete(id));

export default function Watches({ places, signals }: { places: { id: string; label: string }[]; signals: Signal[] }) {
  const [watches, setWatches] = useState<Watch[]>([]);
  const [placeId, setPlaceId] = useState(places[0]?.id ?? '');
  const [alerts, setAlerts] = useState(true);
  const [rain, setRain] = useState('');
  const [error, setError] = useState('');
  const refresh = () => listWatches().then(setWatches, () => setError(t('watches.err_read')));
  useEffect(() => { refresh(); }, []);

  async function add(event: FormEvent) {
    event.preventDefault();
    const place = places.find(item => item.id === placeId);
    if (!place) return;
    try {
      await saveWatch({ id: crypto.randomUUID(), placeId, label: place.label, alerts, rainMm: rain === '' ? null : Number(rain) });
      setError('');
      await refresh();
    } catch { setError(t('watches.err_save')); }
  }
  const now = Date.now();
  const hits = watches.flatMap(watch => signals.filter(signal => triggered(watch, signal, now)).map(signal => ({ watch, signal })));

  return <section aria-labelledby="watch-heading">
    <h2 id="watch-heading">{t('watches.heading')}</h2>
    <p>{t('watches.intro')}</p>
    {error && <p role="alert">{error}</p>}
    <form onSubmit={add}>
      <label htmlFor="watch-place">{t('watches.place')}</label>
      <select id="watch-place" value={placeId} onChange={event => setPlaceId(event.target.value)}>
        {places.map(place => <option key={place.id} value={place.id}>{place.label}</option>)}
      </select>
      <label><input type="checkbox" checked={alerts} onChange={event => setAlerts(event.target.checked)} /> {t('watches.alerts')}</label>
      <label htmlFor="watch-rain">{t('watches.rain')}</label>
      <input id="watch-rain" type="number" min="0" step="any" value={rain} onChange={event => setRain(event.target.value)} />
      <button type="submit" disabled={!places.length}>{t('watches.add')}</button>
    </form>
    <ul aria-label={t('watches.list')}>
      {watches.map(watch => <li key={watch.id}>{watch.label}
        <button type="button" onClick={() => deleteWatch(watch.id).then(refresh)}>{t('watches.remove')}</button></li>)}
    </ul>
    <ul aria-label={t('watches.notifications')}>
      {hits.map(({ watch, signal }) => <li key={`${watch.id}|${signal.sourceUrl}|${signal.kind}`}>
        {watch.label}: {signal.text} <a href={signal.sourceUrl} target="_blank" rel="noopener noreferrer">{t('watches.source')}</a></li>)}
    </ul>
  </section>;
}

/** Live signals from snapshot records that name a place: official alerts, and mm forecasts. Nothing is inferred. */
export function signalsFrom(records: MapRecord[]): Signal[] {
  return records.flatMap((r): Signal[] => {
    if (!r.place_id) return [];
    const base = { placeId: r.place_id, status: 'actual' as const, validUntil: r.expires_at, sourceUrl: r.source_url, text: r.title };
    if (r.kind === 'alert' && r.provenance === 'official') return [{ ...base, kind: 'alert' as const, rainMm: null }];
    if (r.kind === 'weather' && r.evidence === 'forecast' && r.unit === 'mm' && r.value !== null) return [{ ...base, kind: 'forecast' as const, rainMm: r.value }];
    return [];
  });
}
