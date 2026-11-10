// T165: Delhi air quality. Station observations and gridded model estimates (CAMS) are separate
// layers and are compared only on identical pollutant, unit and averaging interval. Both are
// unavailable today (the station source is blocked; the model source is not configured for Delhi),
// so no value shows (D142). Built, not mounted pending H11.
import { type Card, parseCard, ScoreCardView } from './ScoreCard';

export const STATION_LABEL = 'Station measurement (observation)';
export const MODEL_LABEL = 'Gridded model estimate (CAMS), not a measurement';

export type LayerView =
  | { layer: 'station' | 'model'; state: 'unavailable'; source_id: string; reason: string; retry_condition: string }
  | {
    layer: 'station' | 'model'; state: 'available'; provenance: 'observation' | 'model'; source_id: string;
    pollutant: string; unit: string; interval_minutes: number; as_of: string;
  };
export type Comparison =
  | { status: 'unavailable'; reason: string }
  | { status: 'comparable'; pollutant: string; unit: string; interval_minutes: number };
export type AirView = { station: LayerView; model: LayerView; comparison: Comparison; card: Card };

function parseLayer(l: LayerView | undefined, layer: 'station' | 'model'): LayerView {
  if (!l || l.layer !== layer) throw new Error(`${layer} layers must stay distinct`);
  if (l.state === 'unavailable') {
    if (!l.reason || !l.retry_condition) throw new Error('unavailable layer needs a reason and a retry');
    return l;
  }
  if (l.provenance !== (layer === 'station' ? 'observation' : 'model')) throw new Error(`${layer} layer with the wrong provenance`);
  if (!l.unit || !l.pollutant || !(l.interval_minutes >= 0)) throw new Error('layer without pollutant, unit and averaging');
  return l;
}

export function parseAirView(value: unknown): AirView {
  const v = value as AirView;
  const station = parseLayer(v?.station, 'station');
  const model = parseLayer(v?.model, 'model');
  parseCard(v.card);
  const c = v.comparison;
  if (c?.status === 'unavailable' && c.reason) return v;
  if (c?.status !== 'comparable' || station.state !== 'available' || model.state !== 'available') {
    throw new Error('comparison needs two available layers');
  }
  for (const l of [station, model]) {
    if (l.pollutant !== c.pollutant || l.unit !== c.unit || l.interval_minutes !== c.interval_minutes) {
      throw new Error('compared layers differ in pollutant, unit or averaging');
    }
  }
  return v;
}

const describe = (l: LayerView, label: string) => l.state === 'available'
  ? `${label}: ${l.pollutant} in ${l.unit}, ${l.interval_minutes} min average, as of ${l.as_of}`
  : `${label}: unavailable. ${l.reason}. Retry when: ${l.retry_condition}`;

export default function AirQuality({ view }: { view: AirView }) {
  const v = parseAirView(view);
  return <section className="air-quality" aria-label="Delhi air quality">
    <p>{describe(v.station, STATION_LABEL)}</p>
    <p>{describe(v.model, MODEL_LABEL)}</p>
    <p>{v.comparison.status === 'comparable'
      ? `Compared in ${v.comparison.unit}, ${v.comparison.interval_minutes} min averaging.`
      : `Comparison unavailable: ${v.comparison.reason}`}</p>
    <ScoreCardView card={v.card} />
  </section>;
}
