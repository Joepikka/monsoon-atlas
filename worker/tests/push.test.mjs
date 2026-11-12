// T184: background push registration is refused under privacy_mode=no_personal_data (D150).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/index.ts';
import { pushRegistration, PUSH_PATH } from '../src/push.ts';

// A hand-built test subscription, not a real endpoint or key.
const subscription = { endpoint: 'https://push.example.invalid/test', keys: { p256dh: 'test', auth: 'test' } };

test('every method on the push path is refused, even before the capability gate, and the body is never read', async () => {
  for (const method of ['POST', 'PUT', 'DELETE', 'GET']) {
    const init = method === 'GET' ? {} : { method, body: JSON.stringify(subscription) };
    const request = new Request(`https://atlas.invalid${PUSH_PATH}`, { method, ...init });
    const response = await worker.fetch(request, {});
    assert.equal(response.status, 403, method);
    assert.deepEqual(await response.json(), { error: 'disabled: privacy_mode=no_personal_data' });
    assert.equal(request.bodyUsed, false, `${method} body was read`);
  }
});

test('another mode name does not enable storage: it is refused as not implemented', async () => {
  const response = pushRegistration(new Request('https://atlas.invalid/x', { method: 'POST' }), 'consented_push');
  assert.equal(response.status, 501);
});
