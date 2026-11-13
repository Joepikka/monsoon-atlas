import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

// Empty release metadata exercises the loader without inventing observations.
const release = { schema_version: 1, state: 'ka', release_id: 'browser-contract',
  data_revision: 'b'.repeat(64), as_of: '2026-11-05T00:00:00Z',
  published_at: '2026-11-05T01:00:00Z', records: [] };
const body = JSON.stringify(release);
const digest = createHash('sha256').update(body).digest('hex');
const pointer = { schema_version: 1, state: 'ka', approval: 'approved',
  sha256: digest, manifest_url: `/data/ka/releases/${digest}.json` };

test.beforeEach(async ({ page }) => {
  // Third-party tiles are irrelevant to deterministic loading tests.
  await page.route('https://tiles.openfreemap.org/**', route => route.abort());
});

test('the real server shows an honest empty state before any release exists', async ({ page }) => {
  await page.goto('/?page=map');
  await expect(page.getByText('No released snapshot yet')).toBeVisible();
});

test('the basemap canvas has usable dimensions', async ({ page }) => {
  await page.goto('/?page=map');
  const canvas = page.locator('.maplibregl-canvas');
  await expect(canvas).toBeAttached();
  const bounds = await canvas.boundingBox();
  const container = await page.locator('.map-container').boundingBox();
  const panel = await page.locator('.map-panel').boundingBox();
  expect(container?.height).toBeGreaterThan(200);
  expect(Math.abs((bounds?.height ?? 0) - (panel?.height ?? 0))).toBeLessThan(2);
  expect(bounds?.height).toBeGreaterThan(200);
  expect(bounds?.width).toBeGreaterThan(250);
});

test('a genuine CAP sample has matching list and map entries with original provenance', async ({ page }) => {
  const record = JSON.parse(readFileSync(new URL('./fixtures/sachet-ka-point.json', import.meta.url), 'utf8'));
  const sample = JSON.stringify({ ...release, as_of: record.fetched_at, published_at: record.fetched_at, records: [record] });
  const sha = createHash('sha256').update(sample).digest('hex');
  await page.route('**/data/ka/latest.json', route => route.fulfill({ json: {
    ...pointer, sha256: sha, manifest_url: `/data/ka/releases/${sha}.json`,
  } }));
  await page.route(`**/data/ka/releases/${sha}.json`, route => route.fulfill({ body: sample, contentType: 'application/json' }));
  await page.goto('/?page=map');
  const list = page.getByTestId('record-list');
  await expect(list.getByRole('button', { name: record.title, exact: true })).toBeVisible();
  await expect(list.getByText('official', { exact: true })).toBeVisible();
  await expect(list.getByRole('link')).toHaveAttribute('href', record.source_url);
  await expect(list.getByTestId('valid-time')).toHaveAttribute('datetime', record.valid_at);
  await expect(list.getByText(record.location_note)).toBeVisible();
  await expect(page.locator('.map-pin')).toHaveCount(1);
});

test('missing data is explicit, controls work, layout fits and keyboard access remains', async ({ page }) => {
  await page.route('**/data/ka/latest.json', route => route.fulfill({ status: 404 }));
  await page.goto('/?page=map');
  await expect(page.getByRole('heading', { name: 'Monsoon Atlas' })).toBeVisible();
  await expect(page.getByText('No released snapshot yet')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Official warnings' })).toHaveAttribute('href', 'https://sachet.ndma.gov.in/');
  await page.getByLabel('Radius').selectOption('50');
  await expect(page.getByLabel('Radius')).toHaveValue('50');
  await page.getByRole('button', { name: 'Refresh data' }).focus();
  await expect(page.getByRole('button', { name: 'Refresh data' })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  expect(a11y.violations).toEqual([]);
});

test('failed refresh retains the exact dated last-good snapshot', async ({ page }) => {
  let failNext = false;
  await page.route('**/data/ka/latest.json', route => {
    return failNext ? route.abort() : route.fulfill({ json: pointer });
  });
  await page.route(`**/data/ka/releases/${digest}.json`, route => route.fulfill({ body, contentType: 'application/json' }));
  await page.goto('/?page=map');
  await expect(page.getByTestId('snapshot-time')).toHaveAttribute('datetime', release.as_of);
  failNext = true;
  await page.getByRole('button', { name: 'Refresh data' }).click();
  await expect(page.getByText('Refresh failed')).toBeVisible();
  await expect(page.getByTestId('snapshot-time')).toHaveAttribute('datetime', release.as_of);
  await expect(page.getByText('Showing the last approved snapshot.')).toBeVisible();
});

test('loading and unapproved data have distinct visible states', async ({ page }) => {
  let finish: () => void = () => {};
  const held = new Promise<void>(resolve => { finish = resolve; });
  await page.route('**/data/ka/latest.json', async route => {
    await held;
    await route.fulfill({ json: { ...pointer, approval: 'pending' } });
  });
  await page.goto('/?page=map');
  await expect(page.getByText('Loading snapshot')).toBeVisible();
  finish();
  await expect(page.getByText('Snapshot unavailable')).toBeVisible();
  await expect(page.getByText('Publication approval is pending.')).toBeVisible();
  await expect(page.getByTestId('snapshot-time')).toHaveCount(0);
});
