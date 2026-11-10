// T184: background Web Push registration is refused (D150). Under privacy_mode=no_personal_data the
// project keeps no subscription endpoints or keys, so this handler never reads, parses or stores the
// request body. The conditional design for a later policy revision is docs/decisions/web-push.md.
import { reply } from './responses.ts';

export const PRIVACY_MODE = 'no_personal_data';
export const PUSH_PATH = '/api/v1/push/subscription';
export const PUSH_DISABLED = `disabled: privacy_mode=${PRIVACY_MODE}`;

/** Any method on the push path: 403 now; 501 for any other mode, because no storage design is built. */
export function pushRegistration(_request: Request, privacyMode: string = PRIVACY_MODE): Response {
  return privacyMode === PRIVACY_MODE
    ? reply({ error: PUSH_DISABLED }, 403)
    : reply({ error: 'Not implemented: background push needs a revised privacy policy.' }, 501);
}
