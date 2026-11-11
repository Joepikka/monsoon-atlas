import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { parseReplay, REPLAY_LABEL, visibleRecords } from './Replay';

const EXPORT = '../reports/eda/05_kl_flood2018/replay2018.json';

// UI contract values only; the real export is checked in the last test.
const base = { source_id: 'S36', source: 'memorandum', vintage: 'submitted 07 Aug 2018', kind: 'human_fatalities',
  district: 'Idukki', date: null, period_start: '2018-05-29', period_end: '2018-07-31', value: 1, unit: 'persons',
  climatology: null };
const replay = () => ({ schema_version: 1 as const, title: 'replay', label: REPLAY_LABEL,
  window: { start: '2018-06-01', end: '2018-09-30' }, forecast_vintages: [],
  records: [
    { ...base, id: 'known', known_from: '2018-08-07', mode: 'as_known' as const },
    { ...base, id: 'grid', source_id: 'S08', known_from: null, mode: 'reconstructed' as const },
  ] });

describe('2018 replay contract', () => {
  it('never shows a reconstructed record in the as-known view, nor one before its publication', () => {
    const data = parseReplay(replay());
    expect(visibleRecords(data, 'as_known', '2018-08-06')).toHaveLength(0);
    expect(visibleRecords(data, 'as_known', '2018-09-30').map(r => r.id)).toEqual(['known']);
    expect(visibleRecords(data, 'all', '2018-06-01')).toHaveLength(2);
  });
  it('rejects mislabelled modes, missing source or vintage and forecast vintages', () => {
    const r = replay();
    expect(() => parseReplay({ ...r, records: [{ ...r.records[1], mode: 'as_known' }] })).toThrow('mode');
    expect(() => parseReplay({ ...r, records: [{ ...r.records[0], known_from: '2019-08-01' }] })).toThrow('mode');
    expect(() => parseReplay({ ...r, records: [{ ...r.records[0], vintage: '' }] })).toThrow('vintage');
    expect(() => parseReplay({ ...r, forecast_vintages: [{ issued: '2018-08-01' }] })).toThrow('forecast');
  });
  // The export holds S08 rain, so it is untracked (D166) and absent in CI; the test runs where it exists.
  it.skipIf(!existsSync(EXPORT))('accepts the exported replay and keeps every S08 grid record out of the as-known view', () => {
    const data = parseReplay(JSON.parse(readFileSync(EXPORT, 'utf-8')));
    const known = visibleRecords(data, 'as_known', data.window.end);
    expect(known.length).toBeGreaterThan(0);
    expect(known.every(r => r.mode === 'as_known' && r.source_id !== 'S08')).toBe(true);
  });
});
