import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import AxeBuilder from '@axe-core/playwright';

const place = JSON.parse(readFileSync(new URL('./fixtures/bangalore-place.json', import.meta.url), 'utf8'));
const cap = JSON.parse(readFileSync(new URL('./fixtures/sachet-ka-point.json', import.meta.url), 'utf8'));
const weather = JSON.parse(readFileSync(new URL('./fixtures/openmeteo-temperature-point.json', import.meta.url), 'utf8'));
const release = { schema_version: 1, state: 'ka', release_id: 'lens-contract', data_revision: 'c'.repeat(64),
  as_of: cap.fetched_at, published_at: cap.fetched_at, records: [cap, weather], places: [place], facilities: [] };
const body = JSON.stringify(release);
const hash = createHash('sha256').update(body).digest('hex');
const pointer = { schema_version: 1, state: 'ka', approval: 'approved', sha256: hash,
  manifest_url: `/data/ka/releases/${hash}.json` };

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-11-06T00:00:00Z'));
  await page.route('https://tiles.openfreemap.org/**', route => route.abort());
  await page.route('**/data/ka/latest.json', route => route.fulfill({ json: pointer }));
  await page.route(`**/data/ka/releases/${hash}.approval.json`, route => route.fulfill({ json: pointer }));
  await page.route(`**/data/ka/releases/${hash}.json`, route => route.fulfill({ body, contentType: 'application/json' }));
});

test('place tabs keep the boundary and report cutoff, without unavailable scores or facilities', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Place', { exact: true }).selectOption({ label: 'Bangalore · district' });
  const lens = page.getByRole('region', { name: 'Place Lens' });
  await expect(lens.getByTestId('report-cutoff')).toHaveAttribute('datetime', release.as_of);
  await expect(lens.getByText(place.boundary_version, { exact: true })).toBeVisible();
  for (const name of ['Now', 'Risk', 'Forecast', 'History', 'Nearby', 'Sources']) {
    await lens.getByRole('tab', { name, exact: true }).click();
    await expect(lens.getByRole('tab', { name, exact: true })).toHaveAttribute('aria-selected', 'true');
  }
  await lens.getByRole('tab', { name: 'Risk', exact: true }).click();
  await expect(lens.getByText('No released risk score for this place.')).toBeVisible();
  await lens.getByRole('tab', { name: 'Nearby', exact: true }).click();
  await expect(lens.getByText('Facility data is unavailable.')).toBeVisible();
});

test('shared URL reopens the frozen release even when latest is unavailable', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Place', { exact: true }).selectOption({ label: 'Bangalore · district' });
  const link = page.getByRole('link', { name: 'Open frozen report' });
  const href = await link.getAttribute('href');
  expect(href).toContain(`release=${hash}`);
  await page.route('**/data/ka/latest.json', route => route.abort());
  await page.goto(href!);
  await expect(page.getByRole('region', { name: 'Place Lens' }).getByTestId('report-cutoff')).toHaveAttribute('datetime', release.as_of);
  await expect(page.getByLabel('Place', { exact: true })).toHaveValue('0');
});

test('print view contains all report sections, source attribution and original warning text', async ({ page }, testInfo) => {
  await page.goto('/');
  await page.getByLabel('Place', { exact: true }).selectOption({ label: 'Bangalore · district' });
  await page.emulateMedia({ media: 'print' });
  const report = page.getByTestId('print-report');
  await expect(report.getByText(cap.title, { exact: true }).first()).toBeVisible();
  await expect(report.getByText(cap.warning_text, { exact: true }).first()).toBeVisible();
  await expect(report.getByText(cap.instruction, { exact: true }).first()).toBeVisible();
  await expect(report.getByText('Open-Meteo / ECMWF', { exact: true })).toBeVisible();
  await expect(report.getByText(place.boundary_version, { exact: true })).toBeVisible();
  await expect(report.getByText('Not an emergency service.', { exact: true })).toBeVisible();
  await page.pdf({ path: testInfo.outputPath('place-report.pdf'), format: 'A4', printBackground: true });
});

test('an incomplete shared identity never silently substitutes the latest report', async ({ page }) => {
  await page.goto('/?state=ka&release=invalid&place=missing');
  await expect(page.getByRole('status')).toContainText('The shared report identity is incomplete or invalid.');
  await expect(page.getByTestId('snapshot-time')).toHaveCount(0);
});

test('place tabs support keyboard navigation and accessible report content', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Place', { exact: true }).selectOption({ label: 'Bangalore · district' });
  const lens = page.getByRole('region', { name: 'Place Lens' });
  await lens.getByRole('tab', { name: 'Now', exact: true }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(lens.getByRole('tab', { name: 'Risk', exact: true })).toBeFocused();
  const audit = await new AxeBuilder({ page }).include('.place-lens').analyze();
  expect(audit.violations).toEqual([]);
});

test('Nearby lists real S18 facilities with kind, distance and an OSM link, no opening claim', async ({ page }) => {
  const facilities = JSON.parse(readFileSync(new URL('./fixtures/s18-facilities-bengaluru.json', import.meta.url), 'utf8'));
  const asOf = facilities[0].fetched_at;
  const withFacilities = JSON.stringify({ ...release, release_id: 'lens-facilities', as_of: asOf, published_at: asOf, facilities });
  const digest = createHash('sha256').update(withFacilities).digest('hex');
  const current = { ...pointer, sha256: digest, manifest_url: `/data/ka/releases/${digest}.json` };
  await page.clock.setFixedTime(new Date('2026-11-12T06:00:00Z'));
  await page.route('**/data/ka/latest.json', route => route.fulfill({ json: current }));
  await page.route(`**/data/ka/releases/${digest}.json`, route => route.fulfill({ body: withFacilities, contentType: 'application/json' }));
  await page.goto('/');
  await page.getByLabel('Place', { exact: true }).selectOption({ label: 'Bangalore · district' });
  const lens = page.getByRole('region', { name: 'Place Lens' });
  await lens.getByRole('tab', { name: 'Nearby', exact: true }).click();
  await expect(lens.getByText('Opening hours and current operation are not verified.', { exact: false })).toBeVisible();
  await expect(lens.getByRole('heading', { name: 'Hebbal Fire Station' })).toBeVisible();
  await expect(lens.getByText(/^Fire station · \d+\.\d km · source checked$/)).toBeVisible();
  await expect(lens.getByText(/^Hospital · /)).toHaveCount(3);
  await expect(lens.getByRole('link', { name: 'OpenStreetMap · Original source' }).first()).toHaveAttribute('href', /^https:\/\/www\.openstreetmap\.org\/node\/\d+$/);
  expect((await new AxeBuilder({ page }).include('[aria-label="Place Lens"]').analyze()).violations).toEqual([]);
});
