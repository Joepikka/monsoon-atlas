import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('the bare address opens the Overview with headline numbers, the measure switch and the district panel', async ({ page }) => {
  await page.route('**/data/ka/monsoon.json', route => route.fulfill({ status: 404 }));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1, name: /30 districts/ })).toBeVisible();
  await expect(page.getByText('9 of 30')).toBeVisible();
  await page.getByRole('radio', { name: 'Rain trend since 1981' }).click();
  await expect(page.getByRole('radio', { name: 'Rain trend since 1981' })).toHaveAttribute('aria-checked', 'true');
  await page.getByRole('combobox', { name: 'District', exact: true }).selectOption('Mysore');
  await expect(page.getByRole('heading', { level: 3, name: 'Mysore' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Open the full map' })).toHaveAttribute('href', '?page=map');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  expect(a11y.violations).toEqual([]);
});
