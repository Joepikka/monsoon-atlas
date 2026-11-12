import { createRequire } from 'node:module';
const requireWrangler = createRequire(new URL('../node_modules/wrangler/package.json', import.meta.url));
export const runtime = requireWrangler('miniflare');
export function runtimeOptions(script, key) {
  return runtime.convertV4MiniflareOptions({modules:true,script,compatibilityDate:'2026-11-06',cf:false,
    telemetry:{enabled:false},d1Databases:{DB:'local-test-hot'},
    bindings:{CAPABILITY_GATE:'verified_free_no_card',ATLAS_INGEST_HMAC_KEY:key}});
}
