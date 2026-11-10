import { describe, expect, it } from 'vitest';
import { pushStatus } from './push';

// Hand-built fake browsers (test inputs).
const full = { serviceWorker: {}, PushManager: class {}, Notification: class {} };

describe('background push capability', () => {
  it('is disabled with the explicit reason even where the browser could support it', () => {
    expect(pushStatus(full)).toEqual({ enabled: false, supported: true,
      reason: 'disabled: privacy_mode=no_personal_data', localWatchNotifications: true });
  });
  it('reports missing parts as unsupported and is still disabled', () => {
    expect(pushStatus({})).toMatchObject({ enabled: false, supported: false });
    expect(pushStatus({ serviceWorker: {}, Notification: class {} }).supported).toBe(false);
  });
  it('stays disabled under any other mode name until the policy is revised', () => {
    expect(pushStatus(full, 'consented_push')).toMatchObject({ enabled: false, reason: 'disabled: privacy_mode=consented_push' });
  });
});
