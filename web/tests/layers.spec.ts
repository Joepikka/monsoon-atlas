import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import AxeBuilder from '@axe-core/playwright';

const cap = JSON.parse(readFileSync(new URL('./fixtures/sachet-ka-point.json', import.meta.url), 'utf8'));
const weather = JSON.parse(readFileSync(new URL('./fixtures/openmeteo-temperature-point.json', import.meta.url), 'utf8'));
const release = { schema_version: 1, state: 'ka', release_id: 'layer-contract', data_revision: 'd'.repeat(64),
  as_of: cap.fetched_at, published_at: cap.fetched_at, records: [cap, weather], sources: [
    { source_id: 'S09', status: 'stale', last_success_at: cap.fetched_at, detail: 'Historical test capture' },
    { source_id: 'S01', status: 'available', last_success_at: weather.fetched_at, detail: 'Captured model forecast' },
    { source_id: 'S22', status: 'unavailable', last_success_at: null, detail: 'Discovery blocked' },
    { source_id: 'S23', status: 'unavailable', last_success_at: null, detail: 'Price unit unverified' },
  ] };

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-11-06T00:00:00Z'));
  const body = JSON.stringify(release);
  const sha = createHash('sha256').update(body).digest('hex');
  await page.route('https://tiles.openfreemap.org/**', route => route.abort());
  await page.route('**/data/ka/latest.json', route => route.fulfill({ json: {
    schema_version: 1, state: 'ka', approval: 'approved', sha256: sha,
    manifest_url: `/data/ka/releases/${sha}.json`,
  } }));
  await page.route(`**/data/ka/releases/${sha}.json`, route => route.fulfill({ body, contentType: 'application/json' }));
  await page.goto('/?page=map');
});

test('layer toggles update the same map and list while official links remain', async ({ page }) => {
  await expect(page.getByTestId('record-list').locator('li')).toHaveCount(2);
  await page.getByRole('checkbox', { name: 'Weather', exact: true }).uncheck();
  await expect(page.getByTestId('record-list').locator('li')).toHaveCount(1);
  await expect(page.locator('.map-pin')).toHaveCount(1);
  await expect.poll(async () => {
    const canvas = await page.locator('.maplibregl-canvas').boundingBox();
    const panel = await page.locator('.map-panel').boundingBox();
    return Math.abs((canvas?.height ?? 0) - (panel?.height ?? 0));
  }).toBeLessThan(2);
  await expect(page.getByRole('link', { name: 'Official warnings', exact: true })).toHaveAttribute('href', 'https://sachet.ndma.gov.in/');
  await expect(page.getByTestId('layer-price')).toContainText('unavailable');
});

test('provider severity and source clocks remain original on a stale alert', async ({ page }, testInfo) => {
  const alert = page.getByTestId('record-list').locator('li').filter({ hasText: cap.title });
  await expect(alert.getByText('Moderate', { exact: true })).toBeVisible();
  await expect(alert.getByTestId('issued-time')).toHaveAttribute('datetime', cap.issued_at);
  await expect(alert.getByTestId('valid-time')).toHaveAttribute('datetime', cap.valid_at);
  await expect(alert.getByTestId('fetched-time')).toHaveAttribute('datetime', cap.fetched_at);
  await expect(alert.getByText('stale', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath('layers.png'), fullPage: true });
});

test('keyboard radius selection retains area alerts and can be cleared', async ({ page }) => {
  await expect(page.getByTestId('record-list').locator('li')).toHaveCount(2);
  const canvas = page.locator('.maplibregl-canvas');
  await canvas.focus();
  await canvas.press('Enter');
  await expect(page.getByTestId('record-list').locator('li')).toHaveCount(1);
  const clear = page.getByRole('button', { name: 'Clear radius centre' });
  await expect(clear).toBeVisible();
  await clear.click();
  await expect(page.getByTestId('record-list').locator('li')).toHaveCount(2);
});

test('alert updates can be paused and resume through a polite region', async ({ page }) => {
  const ticker = page.getByRole('region', { name: 'Alerts in this snapshot' });
  await expect(ticker.getByText('Expired', { exact: true })).toBeVisible();
  await expect(ticker.locator('time')).toHaveAttribute('datetime', cap.expires_at);
  await expect(ticker.locator('[aria-live=polite]')).toBeVisible();
  await ticker.getByRole('button', { name: 'Pause alerts' }).click();
  await expect(ticker.getByRole('button', { name: 'Resume alerts' })).toHaveAttribute('aria-pressed', 'true');
  await ticker.getByRole('button', { name: 'Resume alerts' }).click();
  await expect(ticker.getByRole('button', { name: 'Pause alerts' })).toHaveAttribute('aria-pressed', 'false');
});
