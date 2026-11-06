// Real workerd/D1 runtime check on supported Ubuntu. No remote binding/account.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { webcrypto, randomBytes } from 'node:crypto';
import { runtime, runtimeOptions } from './runtime-config.mjs';

const requireWrangler = createRequire(new URL('../node_modules/wrangler/package.json', import.meta.url));
const { Miniflare } = runtime;
const { build } = requireWrangler('esbuild');
const bundle = await build({entryPoints:[new URL('../src/index.ts',import.meta.url).pathname],bundle:true,format:'esm',platform:'browser',write:false,target:'es2023'});
const key = randomBytes(32).toString('hex');
const mf = new Miniflare(runtimeOptions(bundle.outputFiles[0].text,key));
try {
  const db = await mf.getD1Database('DB');
  // Pinned workerd rejects a comment-only tail after a prepared statement.
  const schema = readFileSync(new URL('../schema.sql',import.meta.url),'utf8').replace(/^\s*--.*$/gm,'');
  for (const statement of schema.split(/\n(?=(?:CREATE TABLE|CREATE TRIGGER|INSERT INTO capacity|PRAGMA)\b)/)) {
    if (statement.trim()) {
      try { await db.prepare(statement).run(); }
      catch (cause) { throw new Error(`Failed schema statement: ${statement.trim().split('\n')[0]}`,{cause}); }
    }
  }
  const fixture = name => JSON.parse(readFileSync(new URL(`../../web/tests/fixtures/${name}.json`,import.meta.url),'utf8'));
  const cap=fixture('sachet-ka-point'); const weather=fixture('openmeteo-temperature-point');
  const envelope = (record,source) => ({source_id:source,snapshot:{schema_version:1,state:'ka',release_id:'actual-runtime-contract',data_revision:'e'.repeat(64),
    as_of:cap.fetched_at,published_at:cap.fetched_at,records:[record],sources:[{source_id:source,status:'available',last_success_at:record.fetched_at,detail:'Captured source sample'}]}});
  const signed=async value=>{
    const bytes=gzipSync(JSON.stringify(value)); const timestamp=String(Math.floor(Date.now()/1000));
    const hash=Buffer.from(await webcrypto.subtle.digest('SHA-256',bytes)).toString('hex');
    const secret=await webcrypto.subtle.importKey('raw',new TextEncoder().encode(key),{name:'HMAC',hash:'SHA-256'},false,['sign']);
    const signature=Buffer.from(await webcrypto.subtle.sign('HMAC',secret,new TextEncoder().encode(`${timestamp}\nPOST\n/internal/ingest\n${hash}`))).toString('hex');
    return {method:'POST',body:bytes,headers:{'Content-Type':'application/gzip','X-Atlas-Timestamp':timestamp,'X-Atlas-Signature':signature}};
  };
  const post=async value=>mf.dispatchFetch('https://atlas.invalid/internal/ingest',await signed(value));
  const get=()=>mf.dispatchFetch('https://atlas.invalid/api/v1/current?state=ka');
  assert.equal((await mf.dispatchFetch('https://atlas.invalid/internal/ingest',{method:'POST',body:'untrusted'})).status,401);
  const good=envelope(cap,'S09');
  const stored=await post(good); assert.equal(stored.status,201,await stored.clone().text());
  const id=(await stored.json()).snapshot_id;
  const first=await get(); assert.equal(first.status,200,await first.clone().text());
  const source=(await first.json()).sources[0];
  assert.equal(source.sha256,id); assert.equal(source.snapshot.records[0].issued_at,cap.issued_at);
  assert.ok(source.age_seconds>=0);
  assert.equal((await post(good)).status,200);
  assert.equal(await db.prepare('SELECT writes_reserved FROM daily_usage').first('writes_reserved'),20);
  const wrong=structuredClone(good); wrong.snapshot.release_id='conflicting-metadata';
  assert.equal((await post(wrong)).status,409);
  const future=structuredClone(good); future.snapshot.as_of=new Date(Date.now()+3600000).toISOString(); future.snapshot.published_at=future.snapshot.as_of;
  assert.equal((await post(future)).status,400);
  const forecast=envelope(weather,'S01');
  const concurrent=await Promise.all([post(forecast),post(forecast)]);
  assert.ok(concurrent.every(result=>[200,201].includes(result.status)), await Promise.all(concurrent.map(r=>r.clone().text())));
  assert.equal(await db.prepare('SELECT COUNT(*) n FROM hot_snapshots').first('n'),2);
  assert.equal(await db.prepare('SELECT writes_reserved FROM daily_usage').first('writes_reserved'),40);
  const old=structuredClone(good); old.snapshot.as_of=cap.fetched_at.replace('408124','408125'); old.snapshot.published_at=old.snapshot.as_of;
  // Same millisecond, different canonical content: rejected, never overwrites head.
  assert.equal((await post(old)).status,409);
  const update=structuredClone(good); update.snapshot.as_of=new Date(Date.parse(cap.fetched_at)+1000).toISOString(); update.snapshot.published_at=update.snapshot.as_of;
  await db.prepare('UPDATE daily_usage SET writes_reserved=10000').run();
  assert.equal((await post(update)).status,429);
  await db.prepare('UPDATE daily_usage SET writes_reserved=40').run();
  await db.prepare('UPDATE capacity SET allocated_bytes=399999999').run();
  assert.equal((await post(update)).status,507);
  const retained=await get(); assert.equal(retained.status,200);
  assert.equal((await retained.json()).sources.find(s=>s.source_id==='S09').sha256,id);
  const original=await db.prepare('SELECT payload FROM hot_snapshots WHERE id=?').bind(id).first('payload');
  await db.prepare('UPDATE hot_snapshots SET payload=? WHERE id=?').bind(new Uint8Array([1,2,3]),id).run();
  assert.equal((await get()).status,503);
  await db.prepare('UPDATE hot_snapshots SET payload=? WHERE id=?').bind(Uint8Array.from(original),id).run();
  assert.equal((await get()).status,200);
  console.log('PASS: actual Miniflare/D1 auth, clocks/hash, duplicate concurrency, conflicting cutoff, storage/write rollback and last-good checks');
} finally { await mf.dispose(); }
