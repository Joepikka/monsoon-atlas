import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { authenticate, decodeUpload, restoreUpload, uploadMessage, MAX_BLOB } from '../src/ingest.ts';
import worker from '../src/index.ts';

const cap = JSON.parse(readFileSync(new URL('../../web/tests/fixtures/sachet-ka-point.json', import.meta.url), 'utf8'));
const now = Date.parse(cap.fetched_at) + 1000;
const snapshot = {schema_version:1,state:'ka',release_id:'worker-contract',data_revision:'a'.repeat(64),
  as_of:cap.fetched_at,published_at:cap.fetched_at,records:[cap],sources:[{
    source_id:'S09',status:'available',last_success_at:cap.fetched_at,detail:'Actual captured CAP sample',
  }]};
const payload = () => gzipSync(JSON.stringify({source_id:'S09',snapshot}));
const key = 'ephemeral-test-secret-not-an-account-token';
const hex = bytes => Buffer.from(bytes).toString('hex');
async function signed(bytes=payload(), timestamp=String(Math.floor(now/1000))) {
  const cryptoKey = await crypto.subtle.importKey('raw',new TextEncoder().encode(key),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const message = await uploadMessage(timestamp,'POST','/internal/ingest',bytes);
  const signature = hex(await crypto.subtle.sign('HMAC',cryptoKey,message));
  return new Request('https://atlas.invalid/internal/ingest',{method:'POST',body:bytes,headers:{
    'Content-Type':'application/gzip','X-Atlas-Timestamp':timestamp,'X-Atlas-Signature':signature,
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

test('canonical upload keeps original source clocks and discards unknown fields',async()=>{
  const clean = await decodeUpload(gzipSync(JSON.stringify({source_id:'S09',snapshot:{...snapshot,unchecked:'discard-this-field'}})),now);
  assert.equal(clean.source_id,'S09');
  assert.equal(clean.snapshot.as_of,cap.fetched_at);
  assert.equal(clean.snapshot.records[0].expires_at,cap.expires_at);
  assert.equal(clean.sha256.length,64);
  assert.ok(clean.compressed.byteLength<=MAX_BLOB);
  assert.equal('unchecked' in clean.snapshot,false);
});

test('corrupt stored data is a server availability failure, never a client input error',async()=>{
  await assert.rejects(()=>restoreUpload(new Uint8Array([1,2,3]),'a'.repeat(64),now),error=>error.status===503);
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
