// T165: Delhi bus markers. Scheduled, live and predicted are different things and stay labelled so.
// A GPS position aged STALE_SECONDS or more (or in the future, or without a clock) is never live and
// never animates as current. With the position feed blocked (H04) the view is "unavailable" and the
// ETA model is "blocked", so no number shows (D142). Built, not mounted pending H11.
import { type Card, parseCard, ScoreCardView } from './ScoreCard';

export const STALE_SECONDS = 120; // equals the Worker rule; tests/test_delhi_product.py checks both
export const KIND_LABEL = {
  scheduled: 'Scheduled position (timetable estimate), not live',
  live: 'Live GPS position',
  predicted: 'Predicted position (model estimate), not observed',
} as const;

export type Eta = { p10: number; p50: number; p90: number; source: string; release: string };
export type Marker = {
  id: string; kind: 'scheduled' | 'gps' | 'predicted'; lat: number; lon: number; at: string; eta?: Eta;
};
export type TransitView = { card: Card } & (
  | { state: 'unavailable'; source_id: string; reason: string; retry_condition: string }
  | { state: 'available'; as_of: string; markers: Marker[] }
);
export type ShownKind = keyof typeof KIND_LABEL | 'aged_out';

export function isFresh(positionMs: number, nowMs: number): boolean {
  const age = (nowMs - positionMs) / 1000;
  return Number.isFinite(age) && age >= 0 && age < STALE_SECONDS;
}

export function shownKind(m: Marker, nowMs: number): ShownKind {
  if (m.kind !== 'gps') return m.kind;
  return /(Z|[+-]\d{2}:\d{2})$/.test(m.at) && isFresh(Date.parse(m.at), nowMs) ? 'live' : 'aged_out';
}

export const animates = (m: Marker, nowMs: number): boolean => shownKind(m, nowMs) === 'live';

export function parseEta(e: Eta | undefined): void {
  if (!e || ![e.p10, e.p50, e.p90].every(Number.isFinite) || !(e.p10 <= e.p50 && e.p50 <= e.p90)) {
    throw new Error('eta needs ordered p10, p50 and p90');
  }
  if (!e.source || !e.release) throw new Error('eta without a source and release');
}

export function parseTransitView(value: unknown): TransitView {
  const v = value as TransitView;
  const card = parseCard(v?.card);
  if (v.state === 'unavailable') {
    if (!v.reason || !v.retry_condition || 'markers' in v) throw new Error('unavailable view needs a reason, a retry and no markers');
    return v;
  }
  if (v.state !== 'available' || !Array.isArray(v.markers)) throw new Error('unknown transit state');
  for (const m of v.markers) {
    if (m.eta || m.kind === 'predicted') {
      if (card.status !== 'available') throw new Error('eta without a released model');
      parseEta(m.eta);
    }
  }
  return v;
}

export function transitFeatures(view: TransitView, nowMs: number) {
  if (view.state !== 'available') return { type: 'FeatureCollection' as const, features: [] };
  const features = view.markers.flatMap(m => {
    const kind = shownKind(m, nowMs);
    return kind === 'aged_out' ? [] : [{
      type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [m.lon, m.lat] },
      properties: { kind, label: KIND_LABEL[kind], animate: kind === 'live', id: m.id, eta: m.eta ?? null },
    }];
  });
  return { type: 'FeatureCollection' as const, features };
}

export default function Transit({ view, nowMs }: { view: TransitView; nowMs: number }) {
  const v = parseTransitView(view);
  const shown = v.state === 'available' ? v.markers.map(m => shownKind(m, nowMs)) : [];
  const count = (k: ShownKind) => shown.filter(s => s === k).length;
  return <section className="transit" aria-label="Delhi buses">
    {v.state === 'unavailable'
      ? <p>Unavailable: {v.reason}. Retry when: {v.retry_condition}</p>
      : <ul>
        {(Object.keys(KIND_LABEL) as (keyof typeof KIND_LABEL)[]).map(k => <li key={k}>{KIND_LABEL[k]}: {count(k)}</li>)}
        <li>GPS positions aged {STALE_SECONDS} s or more (hidden): {count('aged_out')}</li>
      </ul>}
    <ScoreCardView card={v.card} />
  </section>;
}
