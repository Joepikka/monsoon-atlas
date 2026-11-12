import { expect, test, type Page, type Route } from '@playwright/test';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { parseSnapshot } from '../src/data';

const fixture = (name: string) => JSON.parse(readFileSync(new URL(`./fixtures/${name}.json`, import.meta.url), 'utf8'));
const cap = fixture('sachet-ka-point');
const area = fixture('sachet-ka-area');
const weather = fixture('openmeteo-temperature-point');
const place = fixture('bangalore-place');
const start = Date.parse('2026-11-06T00:00:00Z');
const minute = 60_000;
const capCutoff = '2026-11-05T20:00:00Z';
const capCheck = '2026-11-05T19:55:00Z';
const weatherCutoff = '2026-11-05T21:00:00Z';
const weatherCheck = '2026-11-05T20:55:00Z';
const release = { schema_version: 1, state: 'ka', release_id: 'daily-live-data-contract', data_revision: 'c'.repeat(64),
  as_of: cap.fetched_at, published_at: cap.fetched_at, records: [cap, weather], places: [place], facilities: [], sources: [
    { source_id: 'S09', status: 'stale', last_success_at: cap.fetched_at, detail: 'Historical warning capture.' },
    { source_id: 'S01', status: 'partial', last_success_at: weather.fetched_at, detail: 'Historical weather grid capture.' },
  ] };
const hash = (body: string) => createHash('sha256').update(body).digest('hex');

function packet(source_id: 'S09' | 'S01', records: unknown[], as_of: string, last_success_at: string) {
  // The Worker hashes and serves the normalized snapshot, including normalized optional fields.
  const snapshot = parseSnapshot({ ...release, release_id: `hot-${source_id}-contract`, as_of, published_at: as_of,
    records, places: [], sources: [{ source_id, status: 'partial', last_success_at,
      detail: source_id === 'S09' ? 'Limited CAP feed coverage.' : 'One Bengaluru model grid point.' }] }, 'ka');
  const sha256 = hash(JSON.stringify({ source_id, snapshot }));
  return { schema_version: 1, state: 'ka', sources: [{ source_id, snapshot, sha256, wire_sha256: sha256,
    age_seconds: 1, snapshot_age_seconds: 2 }] };
}

async function dailyRoutes(page: Page, daily = release) {
  const body = JSON.stringify(daily);
  const sha256 = hash(body);
  const manifest_url = `/data/ka/releases/${sha256}.json`;
  const pointer = { schema_version: 1, state: 'ka', approval: 'approved', sha256, manifest_url };
  await page.route('**/*', route => route.request().url().startsWith('http://127.0.0.1:5173/') ? route.fallback() : route.abort());
  await page.route('**/data/ka/latest.json', route => route.fulfill({ json: pointer }));
  await page.route(`**/data/ka/releases/${sha256}.approval.json`, route => route.fulfill({ json: pointer }));
  await page.route(`**${manifest_url}`, route => route.fulfill({ body, contentType: 'application/json' }));
  return sha256;
}

async function pauseClock(page: Page) {
  await page.clock.install({ time: start - minute });
  await page.clock.pauseAt(start);
}

async function visibility(page: Page, state: 'hidden' | 'visible') {
  await page.evaluate(value => {
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => value });
    document.dispatchEvent(new Event('visibilitychange'));
  }, state);
}

test('the visible map and list poll by source, retain a partial empty feed, and fall back on failure', async ({ page }) => {
  await pauseClock(page);
  await dailyRoutes(page);
  const calls: string[] = [];
  let capRequests = 0;
  let finishHeld!: () => void;
  const held = new Promise<void>(resolve => { finishHeld = resolve; });
  await page.route('**/api/v1/current?*', async route => {
    const source = new URL(route.request().url()).searchParams.get('source')!;
    calls.push(source);
    if (source === 'S01') {
      await route.fulfill({ json: packet('S01', [weather], weatherCutoff, weatherCheck) });
    } else if (++capRequests === 1) {
      await route.fulfill({ json: packet('S09', [], capCutoff, capCheck) });
    } else if (capRequests === 2) {
      await held;
      await route.fulfill({ status: 503 }).catch(() => undefined);
    } else {
      await route.fulfill({ status: 503 });
    }
  });
  const list = page.getByTestId('record-list');
  const active = page.getByRole('region', { name: 'Active source updates' });
  const alerts = active.getByTestId('current-S09');
  const forecast = active.getByTestId('current-S01');
  await page.goto('/');
  await expect(page.getByTestId('snapshot-time')).toHaveAttribute('datetime', release.as_of);
  await page.clock.runFor(100);
  await expect(alerts).toContainText('partial');
  await expect(alerts.locator('time').nth(0)).toHaveAttribute('datetime', capCutoff);
  await expect(alerts.locator('time').nth(1)).toHaveAttribute('datetime', capCheck);
  await expect(alerts).toContainText('Limited CAP feed coverage.');
  await expect(list.getByText(cap.title, { exact: true })).toHaveCount(0);
  await expect(list.getByText(weather.title, { exact: true })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Alerts in this snapshot' })).toHaveCount(0);
  await expect(page.getByTestId('layer-alert')).toContainText('partial');
  await page.clock.runFor(100);
  await expect(forecast.locator('time').nth(0)).toHaveAttribute('datetime', weatherCutoff);
  await expect(forecast.locator('time').nth(1)).toHaveAttribute('datetime', weatherCheck);
  await expect(forecast).toContainText('One Bengaluru model grid point.');
  expect(calls).toEqual(['S09', 'S01']);

  await page.getByRole('button', { name: 'Refresh data' }).click();
  await expect(page.getByRole('button', { name: 'Refresh data' })).toBeEnabled();
  await page.clock.fastForward(14 * minute);
  expect(calls).toEqual(['S09', 'S01']);
  await page.clock.fastForward(minute);
  await expect.poll(() => calls).toEqual(['S09', 'S01', 'S09']);
  const aborted = page.waitForEvent('requestfailed', request => request.url().includes('source=S09'));
  await visibility(page, 'hidden');
  await aborted;
  await page.clock.fastForward(10 * minute);
  expect(calls).toHaveLength(3);
  await visibility(page, 'visible');
  finishHeld();
  await page.clock.runFor(100);
  await expect(alerts).toContainText('partial');
  expect(calls).toHaveLength(3);

  await visibility(page, 'hidden');
  await page.clock.fastForward(5 * 60 * minute + 34 * minute);
  expect(calls).toHaveLength(3);
  await visibility(page, 'visible');
  await page.clock.runFor(100);
  await expect(alerts).toContainText('Showing dated daily data');
  await expect(list.getByText(cap.title, { exact: true })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Alerts in this snapshot' })).toBeVisible();
  await expect(page.locator('.map-pin.official')).toHaveCount(1);
  await expect(page.getByTestId('layer-alert')).toContainText('stale');
  expect(calls).toEqual(['S09', 'S01', 'S09', 'S09']);
  await page.clock.fastForward(2 * minute);
  await expect.poll(() => calls).toEqual(['S09', 'S01', 'S09', 'S09', 'S01']);
  await expect(page.getByTestId('snapshot-time')).toHaveAttribute('datetime', release.as_of);
});

test('Place Lens, print and frozen links keep the daily warning and verified release identity', async ({ page }) => {
  await pauseClock(page);
  const sha256 = await dailyRoutes(page);
  let releaseMap!: () => void;
  const deferredMap = new Promise<void>(resolve => { releaseMap = resolve; });
  await page.route('**/src/MapView.tsx*', async route => {
    await deferredMap;
    await route.fallback();
  });
  const calls: string[] = [];
  await page.route('**/api/v1/current?*', route => {
    const source = new URL(route.request().url()).searchParams.get('source')!;
    calls.push(source);
    return route.fulfill({ json: source === 'S09' ? packet('S09', [area], capCutoff, capCheck)
      : packet('S01', [weather], weatherCutoff, weatherCheck) });
  });
  await page.goto('/');
  await expect(page.getByTestId('snapshot-time')).toHaveAttribute('datetime', release.as_of);
  await page.clock.runFor(100);
  await expect(page.getByTestId('record-list').getByText(area.location_note, { exact: true })).toBeVisible();
  await page.clock.runFor(100);
  releaseMap();
  // Lazy map mounting can finish after a single virtual-clock advance.
  await expect.poll(async () => {
    await page.clock.runFor(100);
    return page.locator('.map-pin.model').count();
  }).toBe(1);
  await expect(page.locator('.map-pin.official')).toHaveCount(0);
  await page.clock.runFor(100);
  await expect.poll(() => calls).toEqual(['S09', 'S01']);
  await page.getByLabel('Place', { exact: true }).selectOption({ label: 'Bangalore · district' });
  const lens = page.getByRole('region', { name: 'Place Lens' });
  await expect(lens.getByTestId('report-cutoff')).toHaveAttribute('datetime', release.as_of);
  await expect(lens.getByText(cap.location_note, { exact: true })).toBeVisible();
  const href = await lens.getByRole('link', { name: 'Open frozen report' }).getAttribute('href');
  expect(new URL(href!).searchParams.get('release')).toBe(sha256);
  await page.emulateMedia({ media: 'print' });
  const print = page.getByTestId('print-report');
  await expect(print.getByText(`SHA256: ${sha256}`, { exact: true })).toBeVisible();
  await expect(print.getByText(cap.location_note, { exact: true }).first()).toBeVisible();
  await expect(print.getByText(area.location_note, { exact: true })).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Active source updates' })).toBeHidden();
  await page.emulateMedia({ media: 'screen' });

  calls.length = 0;
  await page.goto(href!);
  await expect(lens.getByTestId('report-cutoff')).toHaveAttribute('datetime', release.as_of);
  await page.clock.fastForward(7 * 60 * minute);
  expect(calls).toEqual([]);
  await expect(page.getByRole('region', { name: 'Active source updates' })).toHaveCount(0);
  await expect(lens.getByText(cap.location_note, { exact: true })).toBeVisible();
});

test('unreleased and invalid shared views never poll, and absent daily warning rows still get a fallback label', async ({ page }) => {
  await pauseClock(page);
  await dailyRoutes(page, { ...release, records: [weather], sources: [release.sources[1]] });
  const calls: string[] = [];
  await page.route('**/api/v1/current?*', route => {
    calls.push(new URL(route.request().url()).searchParams.get('source')!);
    return route.fulfill({ status: 503 });
  });
  await page.goto('/?state=ka&release=invalid');
  await expect(page.getByRole('status')).toContainText('The shared report identity is incomplete or invalid.');
  await page.clock.runFor(100);
  expect(calls).toEqual([]);

  const noRelease = (route: Route) => route.fulfill({ status: 404 });
  await page.route('**/data/ka/latest.json', noRelease);
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('No released snapshot yet');
  await page.clock.runFor(100);
  expect(calls).toEqual([]);
  await page.unroute('**/data/ka/latest.json', noRelease);

  await page.getByRole('button', { name: 'Refresh data' }).click();
  await expect(page.getByTestId('snapshot-time')).toHaveAttribute('datetime', release.as_of);
  await page.clock.runFor(100);
  const alerts = page.getByRole('region', { name: 'Active source updates' }).getByTestId('current-S09');
  await expect(alerts).toContainText('Showing dated daily data');
  await expect(page.getByTestId('record-list').getByText(cap.title, { exact: true })).toHaveCount(0);
  await expect(page.getByTestId('record-list').getByText(weather.title, { exact: true })).toBeVisible();
});
