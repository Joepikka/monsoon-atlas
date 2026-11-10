// T183: place watches kept only in this browser's IndexedDB (D149). No account, no network call, no
// location lookup: the page passes in the place list and the signals, and a watch never leaves the
// device. A cancelled, superseded or expired signal never triggers. Built, not mounted.
import { useEffect, useState, type FormEvent } from 'react';

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
  const refresh = () => listWatches().then(setWatches, () => setError('Watches could not be read in this browser.'));
  useEffect(() => { refresh(); }, []);

  async function add(event: FormEvent) {
    event.preventDefault();
    const place = places.find(item => item.id === placeId);
    if (!place) return;
    try {
      await saveWatch({ id: crypto.randomUUID(), placeId, label: place.label, alerts, rainMm: rain === '' ? null : Number(rain) });
      setError('');
      await refresh();
    } catch { setError('The watch could not be saved in this browser.'); }
  }
  const now = Date.now();
  const hits = watches.flatMap(watch => signals.filter(signal => triggered(watch, signal, now)).map(signal => ({ watch, signal })));

  return <section aria-labelledby="watch-heading">
    <h2 id="watch-heading">Place watches</h2>
    <p>Watches are stored only in this browser. They are never sent anywhere, and there is no account.
      Notifications here appear only while this page is open. This is not an emergency service.</p>
    {error && <p role="alert">{error}</p>}
    <form onSubmit={add}>
      <label htmlFor="watch-place">Place</label>
      <select id="watch-place" value={placeId} onChange={event => setPlaceId(event.target.value)}>
        {places.map(place => <option key={place.id} value={place.id}>{place.label}</option>)}
      </select>
      <label><input type="checkbox" checked={alerts} onChange={event => setAlerts(event.target.checked)} /> Official alerts</label>
      <label htmlFor="watch-rain">Forecast rain at or above (mm, optional)</label>
      <input id="watch-rain" type="number" min="0" step="any" value={rain} onChange={event => setRain(event.target.value)} />
      <button type="submit" disabled={!places.length}>Add watch</button>
    </form>
    <ul aria-label="Your watches">
      {watches.map(watch => <li key={watch.id}>{watch.label}
        <button type="button" onClick={() => deleteWatch(watch.id).then(refresh)}>Remove</button></li>)}
    </ul>
    <ul aria-label="Watch notifications">
      {hits.map(({ watch, signal }) => <li key={`${watch.id}|${signal.sourceUrl}|${signal.kind}`}>
        {watch.label}: {signal.text} <a href={signal.sourceUrl} target="_blank" rel="noopener noreferrer">Source</a></li>)}
    </ul>
  </section>;
}
