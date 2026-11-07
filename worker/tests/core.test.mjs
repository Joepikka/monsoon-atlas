import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { gzipSync, gunzipSync } from 'node:zlib';
import { authenticate, decodeUpload, restoreUpload, uploadMessage, MAX_BLOB } from '../src/ingest.ts';
import worker from '../src/index.ts';
import { runtime, runtimeOptions } from './runtime-config.mjs';

const cap = JSON.parse(readFileSync(new URL('../../web/tests/fixtures/sachet-ka-point.json', import.meta.url), 'utf8'));
const now = Date.parse(cap.fetched_at) + 1000;
const snapshot = {schema_version:1,state:'ka',release_id:'worker-contract',data_revision:'a'.repeat(64),
  as_of:cap.fetched_at,published_at:cap.fetched_at,records:[cap],sources:[{
    source_id:'S09',status:'available',last_success_at:cap.fetched_at,detail:'Actual captured CAP sample',
  }]};
const payload = () => gzipSync(JSON.stringify({source_id:'S09',snapshot}));
const key = 'ephemeral-test-secret-not-an-account-token';
const hex = bytes => Buffer.from(bytes).toString('hex');

function getCurrent(source_id, bytes, sha256) {
  const env={CAPABILITY_GATE:'verified_free_no_card',DB:{prepare(){return {bind(){return this;},async all(){return {results:[{
    source_id,payload:Array.from(bytes),sha256,
  }]};}};}}};
  return worker.fetch(new Request(`https://atlas.invalid/api/v1/current?state=ka&source=${source_id}`),env);
}

test('runtime harness uses options accepted by the actually installed Miniflare version',()=>{
  assert.doesNotThrow(()=>runtime.MiniflareOptionsSchema.parse(runtimeOptions('export default {}',key)));
});
async function signed(bytes=payload(), timestamp=String(Math.floor(now/1000)), path='/internal/ingest', contentType='application/gzip') {
  const cryptoKey = await crypto.subtle.importKey('raw',new TextEncoder().encode(key),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const message = await uploadMessage(timestamp,'POST',path,bytes);
  const signature = hex(await crypto.subtle.sign('HMAC',cryptoKey,message));
  return new Request('https://atlas.invalid'+path,{method:'POST',body:bytes,headers:{
    'Content-Type':contentType,'X-Atlas-Timestamp':timestamp,'X-Atlas-Signature':signature,
  }});
}

test('authentication binds exact bytes, timestamp, method and path before storage',async()=>{
  const bytes=payload();
  assert.equal(await authenticate(await signed(bytes),bytes,key,now),true);
  assert.equal(await authenticate(await signed(bytes),gzipSync('{}'),key,now),false);
  assert.equal(await authenticate(await signed(bytes,String(Math.floor(now/1000)-301)),bytes,key,now),false);
  assert.equal(await authenticate(await signed(bytes,String(Math.floor(now/1000)+301)),bytes,key,now),false);
  assert.equal(await authenticate(await signed(bytes),bytes,undefined,now),false);
  const changed = await signed(bytes);
  assert.equal(await authenticate(new Request('https://atlas.invalid/other',changed),bytes,key,now),false);
});

test('source-check admission rejects unsigned, unknown and client-clock requests before storage',async()=>{
  let touched=false;
  const env={CAPABILITY_GATE:'verified_free_no_card',ATLAS_INGEST_HMAC_KEY:key,DB:{prepare(){touched=true;throw Error('must not query');}}};
  const path='/internal/feed-check';
  assert.equal((await worker.fetch(new Request('https://atlas.invalid'+path,{method:'POST',body:'{}'}),env)).status,401);
  for(const value of [{state:'kl',source_id:'S09'},{state:'ka',source_id:'S23'},{state:'ka',source_id:'S09',now:0}]){
    const bytes=new TextEncoder().encode(JSON.stringify(value));
    const request=await signed(bytes,String(Math.floor(Date.now()/1000)),path,'application/json');
    assert.equal((await worker.fetch(request,env)).status,400);
  }
  assert.equal(touched,false);
});

test('canonical upload keeps original source clocks and discards unknown fields',async()=>{
  const clean = await decodeUpload(gzipSync(JSON.stringify({source_id:'S09',snapshot:{...snapshot,unchecked:'discard-this-field'}})),now);
  assert.equal(clean.source_id,'S09');
  assert.equal(clean.snapshot.as_of,cap.fetched_at);
  assert.equal(clean.snapshot.records[0].expires_at,cap.expires_at);
  assert.equal(clean.sha256.length,64);
  assert.ok(clean.compressed.byteLength<=MAX_BLOB);
  assert.equal('unchecked' in clean.snapshot,false);
});

test('area-only official CAP text survives hot validation without invented coordinates',async()=>{
  const area=JSON.parse(readFileSync(new URL('../../web/tests/fixtures/sachet-ka-area.json',import.meta.url),'utf8'));
  const clean=await decodeUpload(gzipSync(JSON.stringify({source_id:'S09',snapshot:{...snapshot,records:[area]}})),now);
  assert.equal(clean.snapshot.records[0].longitude,null);
  assert.equal(clean.snapshot.records[0].area_text,area.area_text);
});

test('partial CAP coverage survives transport with its actual validation clock',async()=>{
  const partial={...snapshot,sources:[{...snapshot.sources[0],status:'partial',detail:'CAP-only subset; coverage incomplete'}]};
  const clean=await decodeUpload(gzipSync(JSON.stringify({source_id:'S09',snapshot:partial})),now);
  assert.equal(clean.snapshot.sources[0].status,'partial');
  assert.equal(clean.snapshot.sources[0].last_success_at,cap.fetched_at);
  assert.equal(clean.snapshot.records[0].fetched_at,cap.fetched_at);
});

test('corrupt stored data is a server availability failure, never a client input error',async()=>{
  await assert.rejects(()=>restoreUpload(new Uint8Array([1,2,3]),'a'.repeat(64),now),error=>error.status===503);
});

test('storage integrity covers exact bytes, including changes to ignored fields',async()=>{
  const clean=await decodeUpload(payload(),now);
  const changed=JSON.parse(gunzipSync(clean.compressed).toString('utf8'));
  changed.unchecked='corrupt-copy';
  await assert.rejects(()=>restoreUpload(gzipSync(JSON.stringify(changed)),clean.sha256,now),error=>error.status===503);
});

test('GET retains the older stored hash and separately hashes the normalized wire snapshot',async()=>{
  const clean=await decodeUpload(payload(),now);
  const old=JSON.parse(gunzipSync(clean.compressed).toString('utf8'));
  // Simulate an earlier canonical schema using the captured CAP point.
  delete old.snapshot.records[0].area_text;
  const original=new TextEncoder().encode(JSON.stringify(old));
  const hash=hex(await crypto.subtle.digest('SHA-256',original));
  const stored=gzipSync(original);
  const restored=await restoreUpload(stored,hash,now);
  assert.equal(restored.sha256,hash);
  assert.equal(restored.snapshot.records[0].issued_at,cap.issued_at);

  const response=await getCurrent('S09',stored,hash);
  assert.equal(response.status,200);
  const [source]=(await response.json()).sources;
  assert.equal(source.sha256,hash);
  assert.equal(source.snapshot.records[0].area_text,null);
  const wire=new TextEncoder().encode(JSON.stringify({source_id:source.source_id,snapshot:source.snapshot}));
  assert.equal(source.wire_sha256,hex(await crypto.subtle.digest('SHA-256',wire)));
  assert.notEqual(source.wire_sha256,source.sha256);

  const corrupt=await getCurrent('S09',stored,clean.sha256);
  assert.equal(corrupt.status,503);
  assert.deepEqual(await corrupt.json(),{error:'Stored snapshot integrity failure.'});
});

test('unknown sources, future cutoffs and malformed or oversized compression fail closed',async()=>{
  await assert.rejects(()=>decodeUpload(gzipSync(JSON.stringify({source_id:'S23',snapshot})),now));
  await assert.rejects(()=>decodeUpload(payload(),now-86400000));
  await assert.rejects(()=>decodeUpload(new Uint8Array([1,2,3]),now));
  await assert.rejects(()=>decodeUpload(gzipSync('x'.repeat(MAX_BLOB+1)),now));
  await assert.rejects(()=>decodeUpload(new Uint8Array(MAX_BLOB+1),now));
});

test('capability/binding failure gives static fallback and never invokes storage',async()=>{
  const response=await worker.fetch(new Request('https://atlas.invalid/api/v1/current?state=ka'),{});
  assert.equal(response.status,503);
  assert.equal((await response.json()).fallback,'static_daily');
});

test('unsigned uploads and unknown state/query parameters are rejected without storage',async()=>{
  let touched=false;
  const env={CAPABILITY_GATE:'verified_free_no_card',ATLAS_INGEST_HMAC_KEY:key,DB:{prepare(){touched=true;throw Error('must not query');}}};
  assert.equal((await worker.fetch(new Request('https://atlas.invalid/internal/ingest',{method:'POST',body:payload()}),env)).status,401);
  assert.equal((await worker.fetch(new Request('https://atlas.invalid/api/v1/current?state=dl'),env)).status,400);
  assert.equal((await worker.fetch(new Request('https://atlas.invalid/api/v1/current?state=ka&url=https://elsewhere.invalid'),env)).status,400);
  assert.equal(touched,false);
});

test('source age uses the actual successful fetch, not a later report cutoff',async()=>{
  const weather=JSON.parse(readFileSync(new URL('../../web/tests/fixtures/openmeteo-temperature-point.json',import.meta.url),'utf8'));
  const packet=await decodeUpload(gzipSync(JSON.stringify({source_id:'S01',snapshot:{...snapshot,records:[weather],sources:[{
    source_id:'S01',status:'available',last_success_at:weather.fetched_at,detail:'Actual captured forecast',
  }]}})),Date.now());
  const before=Date.now();
  const response=await getCurrent('S01',packet.compressed,packet.sha256);
  assert.equal(response.status,200);
  const source=(await response.json()).sources[0];
  assert.equal(source.sha256,packet.sha256);
  assert.equal(source.wire_sha256,packet.sha256);
  assert.ok(Math.abs(source.age_seconds-Math.floor((before-Date.parse(weather.fetched_at))/1000))<=1);
});
