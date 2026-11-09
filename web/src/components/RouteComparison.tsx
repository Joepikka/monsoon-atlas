// T143: experimental route comparison. Not an emergency service and never a safe route: a route is
// shown only with the label below and the official guidance link. No road network or shelter record
// is verified (S18 and S43 blocked), so real data shows the unavailable state (D128).
export const ROUTE_LABEL = 'Experimental route, not a safe route; road closures and flood depth unknown.';

type Leg = { length_m: number; path: string[] };
export type RouteResult = { label: string; guidance_url: string } & (
  | { status: 'unavailable' | 'disabled'; reason: string }
  | { status: 'experimental'; avoiding: Leg; shortest: Leg & { high_risk_edges: number } }
);

export function parseRoute(value: unknown): RouteResult {
  const r = value as RouteResult;
  if (!r || r.label !== ROUTE_LABEL) throw new Error('route without the experimental label');
  if (!r.guidance_url?.startsWith('https://')) throw new Error('route without an official guidance link');
  if (r.status === 'experimental') return r;
  if ((r.status === 'unavailable' || r.status === 'disabled') && r.reason) return r;
  throw new Error('unknown route status');
}

const km = (m: number) => `${(m / 1000).toFixed(1)} km`;

export default function RouteComparison({ route }: { route: RouteResult }) {
  const r = parseRoute(route);
  return <section className="route-comparison" aria-label="Route comparison">
    <p role="note"><strong>{r.label}</strong> <a href={r.guidance_url}>Official guidance</a></p>
    {r.status === 'experimental'
      ? <ul>
        <li>Avoiding high-risk edges: {km(r.avoiding.length_m)}</li>
        <li>Shortest, ignoring risk: {km(r.shortest.length_m)} ({r.shortest.high_risk_edges} high-risk edges)</li>
      </ul>
      : <p>{r.status === 'disabled' ? 'Disabled' : 'Unavailable'}: {r.reason}</p>}
  </section>;
}
