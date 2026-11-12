import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { extractive } from '../../worker/src/ask';

// Canonical corpus bytes exported by atlas.rag.manifest from committed documents (T261).
const body = readFileSync(new URL('./fixtures/ask-corpus.json', import.meta.url), 'utf8');
const release = createHash('sha256').update(body).digest('hex');
const chunks = JSON.parse(body).chunks as { chunk_id: string }[];
const pointer = { schema_version: 1, release, url: `/data/ask/${release}.json` };
const question = 'Does it cover groundwater, crop yield or household water?';

async function publish(page: Page) {
  await page.route('**/data/ask/latest.json', route => route.fulfill({ json: pointer }));
  await page.route(`**/data/ask/${release}.json`, route => route.fulfill({ body, contentType: 'application/json' }));
}

async function ask(page: Page) {
  await page.goto('/?page=ask');
  await expect(page.getByRole('status')).toHaveText('10 document sections loaded.');
  await page.getByLabel('Question').fill(question);
  await page.getByRole('button', { name: 'Ask' }).click();
}

test('without a published corpus the page says so and keeps Ask disabled', async ({ page }) => {
  await page.goto('/?page=ask');
  await expect(page.getByRole('heading', { name: 'Ask the project documents' })).toBeVisible();
  await expect(page.getByText('Ask has not been published yet.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ask' })).toBeDisabled();
  await expect(page.getByRole('link', { name: /official warnings/ })).toHaveAttribute('href', 'https://sachet.ndma.gov.in/');
  await expect(page.getByText(/Research-only:/)).toBeVisible(); // D101
});

test('the Worker answer shows citation cards with path and evidence age', async ({ page }) => {
  await publish(page);
  let sent: { chunk_ids: string[]; as_of: string } | undefined;
  await page.route('**/api/v1/ask', async route => {
    sent = route.request().postDataJSON();
    // The real Worker extractive format (worker/src/ask.ts) over the requested trusted chunks.
    const evidence = sent!.chunk_ids.map(id => JSON.parse(body).chunks.find((item: { chunk_id: string }) => item.chunk_id === id));
    await route.fulfill({ json: { schema_version: 1, release, as_of: sent!.as_of, ...extractive(evidence) } });
  });
  await ask(page);
  await expect(page.getByRole('heading', { name: 'Search results' })).toBeVisible();
  expect(sent!.chunk_ids[0]).toBe('M05#limits-claims-this-result-does-not-support:0');
  expect(sent!.chunk_ids.every(id => chunks.some(item => item.chunk_id === id))).toBe(true);
  await expect(page.getByText(/not groundwater, crop yield loss or household water/).first()).toBeVisible();
  const cards = page.getByRole('list', { name: 'Citations' }).getByRole('listitem');
  await expect(cards).toHaveCount(sent!.chunk_ids.length);
  await expect(cards.first()).toContainText('reports/models/m05.md');
  await expect(cards.first().getByRole('link')).toHaveAttribute('href', /^https:\/\/github\.com\/Joepikka\/monsoon-atlas\/blob\/main\/reports\/models\/m05\.md$/);
  await expect(cards.first()).toContainText(/Committed 2026-11-05 17:48:40 UTC, \d+ days before this answer/);
  await page.getByRole('link', { name: 'Back to the map' }).focus();
  for (let step = 0; step < 4 && !(await page.getByRole('button', { name: 'Ask' }).evaluate(node => node === document.activeElement)); step++) {
    await page.keyboard.press('Tab');
  }
  await expect(page.getByRole('button', { name: 'Ask' })).toBeFocused();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
});

test('an unavailable Worker shows labelled local results, and a tampered corpus is refused', async ({ page }) => {
  await publish(page);
  await page.route('**/api/v1/ask', route => route.fulfill({ status: 503, json: { status: 'unavailable' } }));
  await ask(page);
  await expect(page.getByText('The answer service is unavailable, so these are the local search results.')).toBeVisible();
  await expect(page.locator('blockquote').first()).toContainText('not groundwater');
  await page.unroute(`**/data/ask/${release}.json`);
  await page.route(`**/data/ask/${release}.json`, route => route.fulfill({ body: body.replace('groundwater', 'rainwater') }));
  await page.reload();
  await expect(page.getByText('Ask corpus integrity check failed.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ask' })).toBeDisabled();
});

test('the map header links to the Ask page', async ({ page }) => {
  await page.route('https://tiles.openfreemap.org/**', route => route.abort());
  await page.goto('/');
  await page.getByRole('link', { name: 'Ask', exact: true }).click();
  await expect(page).toHaveURL(/page=ask/);
  await expect(page.getByRole('heading', { name: 'Ask the project documents' })).toBeVisible();
});

test('the microphone is untouched until the voice button is pressed, and text input keeps working', async ({ page }) => {
  await publish(page);
  // Hand-built stand-in for the browser recognition: counts calls, then answers with fixed text.
  await page.addInitScript(() => {
    const w = window as unknown as { micCalls: number; SpeechRecognition: unknown; webkitSpeechRecognition: unknown };
    w.micCalls = 0;
    w.SpeechRecognition = w.webkitSpeechRecognition = class {
      onresult: ((event: unknown) => void) | null = null;
      onend: (() => void) | null = null;
      constructor() { w.micCalls++; }
      start() { w.micCalls++; this.onresult?.({ results: [[{ transcript: 'groundwater cover' }]] }); this.onend?.(); }
      stop() {}
    };
  });
  await page.goto('/?page=ask');
  await expect(page.getByRole('status')).toHaveText('10 document sections loaded.');
  expect(await page.evaluate(() => (window as unknown as { micCalls: number }).micCalls)).toBe(0);
  await page.getByLabel('Question').fill('typed question');
  await expect(page.getByLabel('Question')).toHaveValue('typed question');
  await page.getByRole('button', { name: 'Speak your question' }).click();
  await expect(page.getByLabel('Question')).toHaveValue('groundwater cover');
  expect(await page.evaluate(() => (window as unknown as { micCalls: number }).micCalls)).toBe(2);
});
