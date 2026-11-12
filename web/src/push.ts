// T184: capability detection only (D150). Background Web Push needs retained subscription endpoints
// and keys, which the strict no-personal-data rule forbids, so the feature is off and the reason is
// explicit. This file never asks for notification permission, registers a service worker or
// creates a subscription; watch notifications stay inside the open page (Watches.tsx).
export const PRIVACY_MODE = 'no_personal_data';

export interface PushStatus {
  enabled: false; // stays false until the owner revises the privacy policy (docs/decisions/web-push.md)
  supported: boolean; // the browser has the parts background push would need; informational only
  reason: string;
  localWatchNotifications: true;
}

export function pushStatus(host: object, privacyMode: string = PRIVACY_MODE): PushStatus {
  const supported = ['serviceWorker', 'PushManager', 'Notification'].every(name => name in host);
  return { enabled: false, supported, reason: `disabled: privacy_mode=${privacyMode}`, localWatchNotifications: true };
}
