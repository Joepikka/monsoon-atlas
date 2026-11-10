import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { comparable, data, num, ratio, type Series } from './dashboards';
import Analysis from './pages/Analysis';
import Compare from './pages/Compare';
import { ModelCards } from './pages/Accuracy';
import Quality from './pages/Quality';

const series = (over: Partial<Series> = {}): Series => ({
  state: 'ka', name: 'x', level: 'district', unit: 'SPI-3', span: ['2020-01-01', '2024-12-31'],
  normalisation: 'climate_reference', coverage: 1, link: 'a', ...over,
});
const html = (page: () => ReturnType<typeof createElement>) => renderToStaticMarkup(page());

describe('dashboard rules', () => {
  it('shows an undefined denominator as unavailable, never 0 or NaN', () => {
    expect(ratio(3, 0)).toBeNull();
    expect(ratio(3, null)).toBeNull();
    expect(ratio(null, 4)).toBeNull();
    expect(ratio(Number.NaN, 4)).toBeNull();
    expect(ratio(1, 4)).toBe(0.25);
    expect(num(ratio(3, 0))).toBe('Unavailable');
    expect(num(Number.NaN)).toBe('Unavailable');
  });
  it('rejects a comparison that differs in level, unit, span, normalisation or coverage', () => {
    expect(comparable(series(), series({ state: 'kl' }))).toEqual({ ok: true, span: ['2020-01-01', '2024-12-31'] });
    expect(comparable(series(), null)).toEqual({ ok: false, reason: 'none' });
    expect(comparable(series(), series({ level: 'state' }))).toEqual({ ok: false, reason: 'level' });
    expect(comparable(series(), series({ unit: 'mm' }))).toEqual({ ok: false, reason: 'unit' });
    expect(comparable(series(), series({ span: ['2025-01-01', '2025-12-31'] }))).toEqual({ ok: false, reason: 'span' });
    expect(comparable(series(), series({ normalisation: null }))).toEqual({ ok: false, reason: 'norm' });
    expect(comparable(series(), series({ coverage: null }))).toEqual({ ok: false, reason: 'coverage' });
    expect(comparable(series(), series({ coverage: 0 }))).toEqual({ ok: false, reason: 'coverage' });
  });
});

describe('dashboard pages render the committed data', () => {
  it('shows only M05 with a score, its interval and denominator, and every card links its report', () => {
    const out = html(() => createElement(ModelCards));
    for (const model of data.models) expect(out).toContain(`data-testid="model-${model.id}"`);
    expect(out).toContain('95% CI 0.003 to 0.150');
    expect(out).toContain('Over 60 months, 1800 district-months');
    expect(out).toContain('Vintage: hindcast');
    expect(out.match(/No score\./g)?.length).toBe(data.models.length - 1);
    expect(out.match(/href="https:\/\/github\.com\/[^"]+reports\/models\/m\d\d(-card)?\.md"/g)?.length).toBe(data.models.length + 1);
    expect(out).not.toContain('NaN');
  });
  it('keeps the review queue apart from hazards and links each source record', () => {
    const out = html(() => createElement(Quality));
    expect(out).toContain('unadjudicated rule output, not incidents');
    expect(out).toContain('Of 100 flags needed, 0 are adjudicated');
    expect(out).toContain('Hazard extremes');
    expect(out).toContain('unavailable, because no live issue-time predictions exist');
    expect(out.match(/data-testid="source-/g)?.length).toBe(data.sources.length);
    expect(out.match(/configs\/sources\/s\d\d\.yaml/g)?.length).toBe(data.sources.length);
  });
  it('indexes the analysis reports with a licence note and no rainfall values', () => {
    const out = html(() => createElement(Analysis));
    expect(out).toContain('Restricted licence: S08');
    expect(out.match(/data-testid="analysis-/g)?.length).toBe(data.analyses.length);
  });
  it('compares nothing it cannot compare and ranks no state', () => {
    const out = html(() => createElement(Compare));
    expect(out).toContain('KA and KL: unavailable. At least one of the two states has no released metric.');
    expect(out).toContain('(coverage 0.697)');
    expect(out).not.toMatch(/rank(ed)? (first|1)|best state/i);
  });
});
