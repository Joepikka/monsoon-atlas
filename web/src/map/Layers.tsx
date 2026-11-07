import { hasCoordinates, type Health, type LayerKind, type MapRecord, type Snapshot } from '../data';

export type Coordinates = [number, number]; // longitude, latitude
export const layerConfigs: { kind: LayerKind; label: string; sources: string[] }[] = [
  { kind: 'weather', label: 'Weather', sources: ['S01', 'S02'] },
  { kind: 'alert', label: 'Official warnings', sources: ['S09'] },
  { kind: 'price', label: 'Market prices', sources: ['S22', 'S23'] },
  { kind: 'model', label: 'Research models', sources: ['S08', 'S32', 'S34'] },
];

export function distanceKm(a: Coordinates, b: Coordinates): number {
  const rad = Math.PI / 180;
  const dLat = (b[1] - a[1]) * rad;
  const dLon = (b[0] - a[0]) * rad;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * rad) * Math.cos(b[1] * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * 6371.0088 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, h))));
}

export function visibleRecords(records: MapRecord[], kinds: Set<string>, center: Coordinates | null, radius: number): MapRecord[] {
  return records.filter(record => kinds.has(record.kind) && (record.spatial_scope === 'area' || !center ||
    (hasCoordinates(record) && distanceKm(center, [record.longitude, record.latitude]) <= radius)));
}

export function layerHealth(kind: LayerKind, sourceData: Pick<Snapshot, 'sources'> | null): Health {
  const config = layerConfigs.find(layer => layer.kind === kind)!;
  const statuses = sourceData?.sources.filter(source => config.sources.includes(source.source_id)).map(source => source.status) ?? [];
  if (!statuses.length) return 'unknown';
  if (statuses.every(status => status === 'unavailable')) return 'unavailable';
  if (statuses.some(status => status === 'unavailable' || status === 'partial')) return 'partial';
  if (statuses.some(status => status === 'stale')) return 'stale';
  if (statuses.length < config.sources.length || statuses.some(status => status === 'unknown')) return statuses.includes('available') ? 'partial' : 'unknown';
  return 'available';
}

export default function Layers({ sourceData, active, onToggle, center, onClear }: {
  sourceData: Pick<Snapshot, 'sources'>; active: Set<LayerKind>; onToggle: (kind: LayerKind) => void; center: Coordinates | null; onClear: () => void;
}) {
  return <fieldset className="layer-controls"><legend>Layers</legend>{layerConfigs.map(layer => {
    const health = layerHealth(layer.kind, sourceData);
    return <div className="layer-control" key={layer.kind} data-testid={`layer-${layer.kind}`}>
      <label><input type="checkbox" checked={active.has(layer.kind)} onChange={() => onToggle(layer.kind)} />{layer.label}</label>
      <span className={`health ${health}`}>{health === 'unknown' ? 'Unavailable · no status' : health}</span>
    </div>;
  })}<p className="layer-help">{center ? `Radius centre: ${center[1].toFixed(3)}° N, ${center[0].toFixed(3)}° E.` : 'Choose a point on the map to apply the radius.'} Official area warnings stay in state context.</p>
    {center && <button className="clear-radius" onClick={onClear}>Clear radius centre</button>}
  </fieldset>;
}
