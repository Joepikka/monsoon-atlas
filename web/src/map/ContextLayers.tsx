// T105: context layer controls. A layer whose source contract is blocked or whose licence is not
// open stays a disabled control with the recorded reason and evidence; FIRMS hotspots are thermal
// anomalies, never confirmed fires; crime is district-year registered cases, listed, not mapped.
export type ContextLayer = {
  layer: 'fire' | 'rera' | 'buildings' | 'crime'; source_id: string; title: string; note: string;
  available: boolean; reason: string | null; evidence: string; landing_url: string;
};
export const BUILDING_MIN_CONFIDENCE = 0.75;

export function parseContextLayers(value: unknown): ContextLayer[] {
  if (!Array.isArray(value)) throw new Error('context layers must be a list');
  const layers = value as ContextLayer[];
  for (const l of layers) {
    if (l.available !== (l.reason === null)) throw new Error(`${l.layer}: an unavailable layer needs a reason`);
    if (!/^docs\/sources\/s\d{2}\.md$/.test(l.evidence) || !l.landing_url.startsWith('https://')) {
      throw new Error(`${l.layer}: evidence link missing`);
    }
    if (l.layer === 'fire' && !l.note.includes('not a confirmed fire')) throw new Error('fire hotspots must not read as confirmed fires');
    if (l.layer === 'crime' && !l.note.includes('under-reporting')) throw new Error('crime needs the under-reporting note');
  }
  return layers;
}

export const buildingShown = (confidence: number, min = BUILDING_MIN_CONFIDENCE) => confidence >= min;

export default function ContextLayers({ layers, active, onToggle }: {
  layers: ContextLayer[]; active: Set<string>; onToggle: (layer: string) => void;
}) {
  return <fieldset className="context-layers"><legend>Context</legend>{layers.map(l =>
    <div className="layer-control" key={l.layer} data-testid={`context-${l.layer}`}>
      <label><input type="checkbox" disabled={!l.available} checked={l.available && active.has(l.layer)}
        aria-describedby={`context-${l.layer}-note`} onChange={() => onToggle(l.layer)} />{l.title}</label>
      <small id={`context-${l.layer}-note`}>{l.available ? l.note : <>Unavailable: {l.reason}{' '}
        <a href={l.landing_url} rel="noreferrer">Source</a> · evidence {l.evidence}</>}</small>
    </div>)}
  </fieldset>;
}
