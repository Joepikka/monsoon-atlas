import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const area=JSON.parse(readFileSync(new URL('./fixtures/sachet-ka-area.json',import.meta.url),'utf8'));
const place=JSON.parse(readFileSync(new URL('./fixtures/bangalore-place.json',import.meta.url),'utf8'));
const body=JSON.stringify({schema_version:1,state:'ka',release_id:'area-browser-contract',data_revision:'e'.repeat(64),
  as_of:area.fetched_at,published_at:area.fetched_at,records:[area],places:[place]});
const hash=createHash('sha256').update(body).digest('hex');

test('an area-only official warning stays readable without a fake map marker or fly-to point',async({page})=>{
  const errors:string[]=[]; page.on('pageerror',error=>errors.push(error.message));
  await page.route('https://tiles.openfreemap.org/**',route=>route.abort());
  await page.route('**/data/ka/latest.json',route=>route.fulfill({json:{schema_version:1,state:'ka',approval:'approved',sha256:hash,manifest_url:`/data/ka/releases/${hash}.json`}}));
  await page.route(`**/data/ka/releases/${hash}.json`,route=>route.fulfill({body,contentType:'application/json'}));
  await page.goto('/?page=map');
  const list=page.getByTestId('record-list');
  await expect(list.getByText(area.warning_text,{exact:true})).toBeVisible();
  await expect(list.getByText(area.area_text,{exact:true})).toBeVisible();
  await expect(list.getByText(area.location_note,{exact:true})).toBeVisible();
  await expect(page.locator('.maplibregl-canvas')).toBeAttached();
  await expect(page.locator('.map-pin')).toHaveCount(0);
  await list.getByRole('button',{name:area.title,exact:true}).click();
  await page.getByLabel('Radius',{exact:true}).selectOption('5');
  await page.locator('.maplibregl-canvas').focus(); await page.keyboard.press('Enter');
  await expect(list.locator('li')).toHaveCount(1);
  await page.getByLabel('Place',{exact:true}).selectOption('0');
  await expect(page.getByRole('region',{name:'Place Lens'}).getByText(area.area_text,{exact:true})).toBeVisible();
  expect(errors).toEqual([]);
});
