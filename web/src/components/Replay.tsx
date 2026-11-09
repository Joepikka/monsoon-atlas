// T142: Kerala 2018 descriptive replay (D127). "as_known" records had a dated publisher issue on or
// before the window end and show only from that date; "reconstructed" ones (later analyses) never
// show in the as-known view. No forecast vintage exists for 2018, so the replay accepts none.
export const REPLAY_LABEL = 'Descriptive replay of the 2018 Kerala floods, not a forecast. No historical forecast '
  + 'vintage is held, so none is shown; reconstructed records are later analyses.';

export type ReplayMode = 'as_known' | 'reconstructed';
export type ReplayRecord = {
  id: string; source_id: string; source: string; vintage: string; kind: string; district: string | null;
  date: string | null; period_start: string | null; period_end: string | null; value: number; unit: string;
  climatology: number | null; known_from: string | null; mode: ReplayMode;
};
export type Replay = {
  schema_version: 1; title: string; label: string; window: { start: string; end: string };
  forecast_vintages: unknown[]; records: ReplayRecord[];
};

export function parseReplay(value: unknown): Replay {
  const data = value as Replay;
  if (!data || data.label !== REPLAY_LABEL || !Array.isArray(data.records)) throw new Error('not a replay snapshot');
  if (!Array.isArray(data.forecast_vintages) || data.forecast_vintages.length) throw new Error('replay must not carry forecast vintages');
  for (const r of data.records) {
    if (!r.source || !r.vintage) throw new Error(`${r.id}: record without source or vintage`);
    const known = r.known_from !== null && r.known_from <= data.window.end;
    if (r.mode !== (known ? 'as_known' : 'reconstructed')) throw new Error(`${r.id}: mode does not follow its publication date`);
  }
  return data;
}

/** Records a reader could have seen on `cursor` (YYYY-MM-DD): never a reconstructed one. */
export function visibleRecords(replay: Replay, view: 'as_known' | 'all', cursor: string): ReplayRecord[] {
  if (view === 'all') return replay.records;
  return replay.records.filter(r => r.mode === 'as_known' && r.known_from !== null && r.known_from <= cursor);
}

export default function Replay({ replay, view, cursor }: { replay: Replay; view: 'as_known' | 'all'; cursor: string }) {
  const shown = visibleRecords(replay, view, cursor);
  return <section className="replay" aria-label="2018 replay">
    <h2>{replay.title} <span className="badge">{view === 'as_known' ? `as known on ${cursor}` : 'all records'}</span></h2>
    <p>{replay.label}</p>
    {shown.length === 0 && <p>No record had been published by {cursor}.</p>}
    <ul>{shown.map(r => <li key={r.id} data-testid={`replay-${r.id}`}>
      <span className={`mode ${r.mode}`}>{r.mode === 'as_known' ? 'Known at the time' : 'Reconstructed later'}</span>{' '}
      {r.district ?? 'Kerala'} · {r.kind.replaceAll('_', ' ')}: {r.value} {r.unit}
      {r.date ? ` on ${r.date}` : ` for ${r.period_start} to ${r.period_end}`}
      <br /><small>Source: {r.source} · Vintage: {r.vintage}</small>
    </li>)}</ul>
  </section>;
}
