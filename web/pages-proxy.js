// D187: the site calls its own /api/v1/current and /api/v1/ask; these Pages Functions forward to
// the hot Worker (no credentials, no caching of answers). The Worker validates every request.
export const WORKER = 'https://monsoon-atlas-hot.monsoon-atlas.workers.dev';

export async function forward(request, path) {
  const url = new URL(request.url);
  const target = new URL(WORKER + path);
  target.search = url.search;
  const init = { method: request.method, headers: { 'User-Agent': 'monsoon-atlas-pages/1' } };
  if (request.method === 'POST') {
    init.headers['Content-Type'] = request.headers.get('Content-Type') ?? 'application/json';
    init.body = await request.arrayBuffer();
  }
  const reply = await fetch(target, init);
  return new Response(reply.body, {
    status: reply.status,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
  });
}
