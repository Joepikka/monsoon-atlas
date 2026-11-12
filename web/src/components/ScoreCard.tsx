// T165: a model card with its test-period and season coverage beside any score (D142). A blocked
// model shows the word "blocked" and the planned (not actual) window; it never shows a number.
export const PLANNED = 'planned, not started';
const DAY = /^\d{4}-\d{2}-\d{2}$/;
const MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export type Coverage = { status: typeof PLANNED | 'measured'; test_period: [string, string]; months: number[] };
export type Card =
  | { status: 'blocked'; model_id: string; reason: string; coverage: Coverage }
  | { status: 'available'; model_id: string; release: string; source: string; scores: Record<string, number>; coverage: Coverage };

export function parseCoverage(value: unknown): Coverage {
  const c = value as Coverage;
  if (!c || (c.status !== PLANNED && c.status !== 'measured')) throw new Error('coverage without a status');
  const [from, to] = c.test_period ?? [];
  if (!DAY.test(from) || !DAY.test(to) || from > to) throw new Error('coverage without a test period');
  if (!c.months?.length || c.months.some(m => !Number.isInteger(m) || m < 1 || m > 12)) {
    throw new Error('coverage without months');
  }
  return c;
}

export function parseCard(value: unknown): Card {
  const c = value as Card;
  if (!c?.model_id) throw new Error('card without a model');
  const coverage = parseCoverage(c.coverage);
  if (c.status === 'blocked') {
    if (!c.reason || 'scores' in c) throw new Error('a blocked card has a reason and no scores');
    if (coverage.status !== PLANNED) throw new Error('a blocked card shows planned coverage only');
    return c;
  }
  const scores = Object.values(c.scores ?? {});
  if (c.status !== 'available' || !c.release || !c.source) throw new Error('score card without a release and source');
  if (!scores.length || !scores.every(Number.isFinite)) throw new Error('score card without finite scores');
  if (coverage.status !== 'measured') throw new Error('scores need measured coverage');
  return c;
}

export function ScoreCardView({ card }: { card: Card }) {
  const c = parseCard(card);
  const { test_period: [from, to], months } = c.coverage;
  return <div className="score-card" data-testid={`card-${c.model_id}`}>
    <p><strong>{c.model_id}</strong>: {c.status === 'blocked'
      ? `blocked. ${c.reason}`
      : Object.entries(c.scores).map(([k, v]) => `${k} ${v}`).join(', ') + ` (release ${c.release}, source ${c.source})`}</p>
    <p>Test period {from} to {to} ({c.coverage.status}); months covered: {months.map(m => MONTH[m - 1]).join(', ')}.</p>
  </div>;
}
