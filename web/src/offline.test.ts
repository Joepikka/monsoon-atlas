import { readFileSync } from 'node:fs';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { exportAllowed, exportRows, ExportRefused } from './export';
import Widget, { APP_FRAME_ANCESTORS, frameAncestors, WIDGET_ORIGINS } from './pages/Widget';
import { BUDGET_BYTES, CACHED_AT, offlineBanner, planCache, stamp } from './sw';

const NOW = '2026-11-11T06:00:00Z';

describe('offline cache plan', () => {
  it('caches only allowlisted files, stamps each, and stops at the 20 MB budget', () => {
    const plan = planCache([
      { url: './', bytes: 1000 }, { url: './assets/index-abc.js', bytes: 5000 },
      { url: './data/ka/summary.json', bytes: 10 }, { url: 'https://evil.example/x.js', bytes: 10 },
      { url: './assets/big.js', bytes: BUDGET_BYTES },
    ], NOW);
    expect(plan.entries.map(e => e.url)).toEqual(['./', './assets/index-abc.js']);
    expect(plan.entries.every(e => e.cachedAt === NOW)).toBe(true);
    expect(plan.rejected).toEqual([
      { url: './data/ka/summary.json', reason: 'not_allowlisted' },
      { url: 'https://evil.example/x.js', reason: 'not_allowlisted' },
      { url: './assets/big.js', reason: 'over_budget' },
    ]);
    expect(plan.bytes).toBeLessThanOrEqual(BUDGET_BYTES);
  });
  it('accepts a state summary only when it is explicitly permitted', () => {
    const summary = { url: './data/ka/summary.json', bytes: 10 };
    expect(planCache([summary], NOW).entries).toEqual([]);
    expect(planCache([summary], NOW, ['./data/ka/summary.json']).entries).toHaveLength(1);
  });
  it('records the fetch time on every cached response', async () => {
    const stamped = stamp(new Response('x', { status: 200 }), NOW);
    expect(stamped.headers.get(CACHED_AT)).toBe(NOW);
    expect(await stamped.text()).toBe('x');
  });
});

describe('offline banner', () => {
  it('always shows the cache date and never calls cached risk current', () => {
    for (const now of [NOW, '2026-11-11T06:00:01Z', '2026-11-20T06:00:00Z']) {
      const text = offlineBanner('2026-11-11T06:00:00Z', now);
      expect(text).toContain('2026-11-11 06:00 UTC');
      expect(text).toContain('not current');
      expect(text).toContain('not an emergency service');
    }
    expect(offlineBanner('2026-11-11T06:00:00Z', '2026-11-13T06:00:00Z')).toContain('2 days old');
    expect(offlineBanner('2026-11-11T00:00:00Z', NOW)).toContain('6 hours old');
  });
  it('treats a missing, invalid or future cache date as unknown', () => {
    for (const bad of [null, 'yesterday', '2027-01-01T00:00:00Z']) {
      expect(offlineBanner(bad, NOW)).toContain('unknown date');
    }
  });
});

describe('widget', () => {
  it('is a read-only summary with source links, no controls and no parent access', () => {
    const html = renderToStaticMarkup(createElement(Widget, { search: '?state=ka' }));
    expect(html).not.toMatch(/<(button|input|form|select|textarea|iframe|script)/);
    expect(html).toContain('target="_blank"');
    expect(html).toContain('configs/states/ka.yaml');
    expect(html).toContain('not current conditions');
    const code = readFileSync(new URL('./pages/Widget.tsx', import.meta.url), 'utf8');
    expect(code).not.toMatch(/window\.(parent|top|opener)|document\.referrer|postMessage|\bparent\.|\btop\./);
  });
  it('keeps the app frame policy at self and allows no embedding origin by default', () => {
    expect(APP_FRAME_ANCESTORS).toBe("frame-ancestors 'self'");
    expect(WIDGET_ORIGINS).toEqual([]);
    expect(frameAncestors()).toBe("frame-ancestors 'self'");
    expect(frameAncestors(['https://partner.example'])).toBe("frame-ancestors 'self' https://partner.example");
    expect(() => frameAncestors(['http://partner.example'])).toThrow();
    expect(() => frameAncestors(['https://partner.example/path'])).toThrow();
    expect(() => frameAncestors(['*'])).toThrow();
  });
});

describe('export', () => {
  const rows = Array.from({ length: 5 }, (_, i) => ({ date: `2024-07-0${i + 1}`, precipitation_sum_mm: i }));
  it('refuses S08, S30 and S34 and any unknown source', async () => {
    for (const id of ['S08', 'S30', 'S34', 'S99']) {
      expect(exportAllowed(id)).toBe(false);
      await expect(exportRows(id, rows)).rejects.toThrow(ExportRefused);
    }
  });
  it('exports an open source with licence, source ID and content hash, in shards under the limits', async () => {
    expect(exportAllowed('S02')).toBe(true);
    const { manifest, shards } = await exportRows('S02', rows, { rows: 2, bytes: 10 * 1024 * 1024 });
    expect(manifest).toMatchObject({ source_id: 'S02', licence: 'open', rows: 5 });
    expect(manifest.content_sha256).toMatch(/^[0-9a-f]{64}$/);
    expect(manifest.shards.map(s => s.rows)).toEqual([2, 2, 1]);
    expect(shards).toHaveLength(3);
    const small = await exportRows('S02', rows, { rows: 100, bytes: 60 });
    expect(small.shards.every(s => s.length <= 60)).toBe(true);
    await expect(exportRows('S02', rows, { rows: 100, bytes: 10 })).rejects.toThrow('exceeds');
  });
});
