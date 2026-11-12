// T182: flat-key UI strings, no i18n library (D148). en.json is authoritative; kn, ml and hi are
// unreviewed machine drafts, present for key parity but not selectable (A7).
import en from './en.json';
import hi from './hi.json';
import kn from './kn.json';
import ml from './ml.json';

export const LOCALES = { en, kn, ml, hi } as const;
export type Locale = keyof typeof LOCALES;
export type Key = Exclude<keyof typeof en, '_review_status'>;
export const SELECTABLE: readonly Locale[] = ['en'];

/** A missing key throws, so a gap fails a test instead of showing English or a raw key. */
export function t(key: Key, vars: Record<string, string | number> = {}, locale: Locale = 'en'): string {
  const text = (LOCALES[locale] as Record<string, string>)[key];
  if (typeof text !== 'string') throw new Error(`Missing UI string ${locale}:${key}`);
  return text.replace(/\{(\w+)\}/g, (_, name: string) => {
    if (!(name in vars)) throw new Error(`Missing value ${name} for ${locale}:${key}`);
    return String(vars[name]);
  });
}
