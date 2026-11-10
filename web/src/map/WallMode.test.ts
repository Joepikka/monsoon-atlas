import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import type { MapRecord, SourceHealth } from '../data';
import { LOCALES } from '../i18n';
import WallMode, { sourceState, stateText, wallColumns, wallKey, wallState } from './WallMode';

const alert = JSON.parse(readFileSync(new URL('../../tests/fixtures/sachet-ka-point.json', import.meta.url), 'utf8')) as MapRecord;
const asOf = '2026-11-11T05:00:00Z';
const at = (hoursAfter: number) => Date.parse(asOf) + hoursAfter * 3600_000;
// Hand-built test inputs, not observations.
const sources: SourceHealth[] = [
  { source_id: 'S01', status: 'available', last_success_at: '2026-11-11T04:30:00Z', detail: 'ok' },
  { source_id: 'S09', status: 'partial', last_success_at: '2026-11-11T04:45:00Z', detail: 'partial' },
  { source_id: 'S22', status: 'unavailable', last_success_at: null, detail: 'blocked' },
];
const render = (nowMs: number, connected: boolean) =>
  renderToStaticMarkup(createElement(WallMode, { snapshot: { as_of: asOf, sources }, records: [alert], connected, now: nowMs, onExit: () => {} }));
const stub = (reduced: boolean) => { (globalThis as { matchMedia?: unknown }).matchMedia = () => ({ matches: reduced }); };
afterEach(() => { delete (globalThis as { matchMedia?: unknown }).matchMedia; });

describe('wall state', () => {
  it('is current only when connected and at most 24 hours old', () => {
    expect(wallState(asOf, at(1), true)).toBe('current');
    expect(wallState(asOf, at(24), true)).toBe('current');
    expect(wallState(asOf, at(24.01), true)).toBe('stale');
    expect(wallState(asOf, at(-1), true)).toBe('stale'); // a future timestamp is not trusted
    expect(wallState('not a time', at(1), true)).toBe('stale');
    expect(wallState(asOf, at(1), false)).toBe('disconnected');
  });

  it('never styles a source available when disconnected or its last success is old or missing', () => {
    const [ok, partial, none] = sources;
    expect(sourceState(ok, at(1), true)).toBe('available');
    expect(sourceState(ok, at(30), true)).toBe('stale');
    expect(sourceState({ ...ok, last_success_at: null }, at(1), true)).toBe('stale');
    expect(sourceState(partial, at(1), true)).toBe('partial');
    expect(sourceState(none, at(1), true)).toBe('unavailable');
    for (const s of sources) expect(sourceState(s, at(1), false)).toBe('disconnected');
  });

  it('exits on Escape only and lays out four columns at 1920 px', () => {
    expect(wallKey('Escape')).toBe('exit');
    expect(['Enter', ' ', 'q', 'Esc'].map(wallKey)).toEqual([null, null, null, null]);
    expect([1920, 2560, 1919, 1280, 800, 799].map(wallColumns)).toEqual([4, 4, 3, 3, 2, 1]);
  });
});

describe('wall display', () => {
  it('shows a current snapshot with the ticker, large source timestamps and four columns at 1920 px', () => {
    stub(false);
    const html = render(at(1), true);
    expect(html).toContain('data-state="current"');
    expect(html).toContain(`dateTime="${asOf}"`); // the snapshot timestamp is kept
    expect(html).toContain('dateTime="2026-11-11T04:30:00Z"'); // so is each source's last success
    expect(html).toContain('event-ticker');
    expect(html).toContain('Pause alerts');
    expect(html).toContain('repeat(4, 1fr)');
    expect(html.replace(/<[^>]*>/g, ' ')).not.toMatch(/\blive\b/i); // visible text only
  });

  it('starts the ticker paused under reduced motion', () => {
    stub(true);
    const html = render(at(1), true);
    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain('Resume alerts');
  });

  it('shows a disconnected feed as stale-styled, keeps its timestamps and hides alerts', () => {
    stub(false);
    const html = render(at(1), false);
    expect(html).toContain('data-state="disconnected"');
    expect(html).toContain('Feed disconnected: showing the last snapshot');
    expect(html).toContain(`dateTime="${asOf}"`);
    expect(html).not.toContain('event-ticker');
    expect(html).not.toContain('data-state="available"');
    expect(html).not.toContain('Current snapshot');
    expect(html).toContain('Alerts are not shown');
  });

  it('shows an old snapshot as stale even while connected', () => {
    stub(false);
    const html = render(at(48), true);
    expect(html).toContain('wall-stale');
    expect(html).toContain('Stale snapshot');
    expect(html).not.toContain('Current snapshot');
    expect(html).not.toContain('event-ticker');
    expect(html).not.toContain('data-state="available"');
  });
});

describe('wall strings', () => {
  it('has every status in all four locales', () => {
    for (const locale of Object.keys(LOCALES) as (keyof typeof LOCALES)[]) {
      for (const state of ['available', 'stale', 'unavailable', 'partial', 'unknown', 'disconnected'] as const) {
        expect(Object.keys(LOCALES[locale])).toContain(`wall.status_${state}`);
      }
    }
    expect(stateText('disconnected')).toBe('Disconnected');
  });
});
