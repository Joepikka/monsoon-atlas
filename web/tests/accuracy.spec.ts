import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

// The fixture is generated from committed release records by atlas.models.accuracy (T259).
const body = readFileSync(new URL('./fixtures/accuracy-ka.json', import.meta.url), 'utf8');
const digest = createHash('sha256').update(body).digest('hex');
const pointer = { schema_version: 1, state: 'ka', approval: 'approved', sha256: digest,
  manifest_url: `/data/ka/accuracy/${digest}.json` };

test('without a release the page says so and offers the map', async ({ page }) => {
  await page.goto('/?page=accuracy');
  await expect(page.getByRole('heading', { name: 'Model accuracy' })).toBeVisible();
  await expect(page.getByText('No approved accuracy table has been released yet.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Back to the map' })).toBeVisible();
});

test('an approved release shows C1, C2 and M06 with unavailable not zero', async ({ page }) => {
  await page.route('**/data/ka/accuracy/latest.json', route => route.fulfill({ json: pointer }));
  await page.route(`**/data/ka/accuracy/${digest}.json`, route => route.fulfill({ body, contentType: 'application/json' }));
  await page.goto('/?page=accuracy');
  const table = page.getByRole('table');
  await expect(table.getByRole('rowheader', { name: 'M05' })).toBeVisible();
  const m05 = table.getByRole('row').filter({ has: page.getByRole('rowheader', { name: 'M05' }) });
  await expect(m05).toContainText('0.732');
  await expect(m05).toContainText('0.003 to 0.150');
  for (const blocked of ['M07', 'M06']) {
    const row = table.getByRole('row').filter({ has: page.getByRole('rowheader', { name: blocked }) });
    await expect(row).toContainText('Unavailable');
    await expect(row).not.toContainText('0.000');
  }
  const region = page.getByRole('region', { name: 'Accuracy table, scrolls sideways' });
  await region.focus();
  await expect(region).toBeFocused();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test('a tampered or unapproved release is refused', async ({ page }) => {
  await page.route('**/data/ka/accuracy/latest.json', route => route.fulfill({ json: { ...pointer, approval: 'pending' } }));
  await page.goto('/?page=accuracy');
  await expect(page.getByText('Accuracy publication approval is pending.')).toBeVisible();
  await expect(page.getByRole('table')).toHaveCount(0);
});

test('the map header links to the accuracy page', async ({ page }) => {
  await page.route('https://tiles.openfreemap.org/**', route => route.abort());
  await page.goto('/');
  await page.getByRole('link', { name: 'Model accuracy' }).click();
  await expect(page).toHaveURL(/page=accuracy/);
  await expect(page.getByRole('heading', { name: 'Model accuracy' })).toBeVisible();
});
