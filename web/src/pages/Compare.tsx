// T217: state comparison. Catalogue counts side by side with coverage and no ranking; a metric
// comparison appears only when comparable() accepts it, otherwise it says why it is unavailable.
import { comparable, data, href, num, ratio, reasonText, type Series } from '../dashboards';
import { t } from '../i18n';

const STATES = ['ka', 'kl', 'dl'] as const;
const ofState = (state: string): Series | null => data.series.find(s => s.state === state) ?? null;

export default function Compare() {
  const pairs = STATES.flatMap((a, i) => STATES.slice(i + 1).map(b => ({ a, b, result: comparable(ofState(a), ofState(b)) })));
  return <main className="dashboard" aria-labelledby="compare-heading">
    <h1 id="compare-heading">{t('cmp.heading')}</h1>
    <p>{t('cmp.intro')}</p>
    <section aria-labelledby="counts-heading">
      <h2 id="counts-heading">{t('cmp.counts_heading')}</h2>
      <p>{t('cmp.counts_note')}</p>
      <ul className="dash-cards">{STATES.map(state => {
        const s = data.states[state];
        return <li key={state} className="dash-card" data-testid={`state-${state}`}>
          <h3>{state.toUpperCase()}</h3>
          <p>{t('cmp.row', {
            enabled: s.enabled, sources: s.sources, coverage: num(ratio(s.enabled, s.sources)),
            blocked: s.blocked, models_blocked: s.models_blocked, models: s.models,
          })}</p>
          <p><a href={href(s.link)} rel="noopener noreferrer">{t('dash.source_record')}</a>{' '}
            <a href={href(s.page)} rel="noopener noreferrer">{t('dash.report')}</a></p>
        </li>;
      })}</ul>
    </section>
    <section aria-labelledby="metric-heading">
      <h2 id="metric-heading">{t('cmp.metric_heading')}</h2>
      <ul>{pairs.map(({ a, b, result }) => <li key={`${a}-${b}`} data-testid={`pair-${a}-${b}`}>
        {result.ok ? `${a.toUpperCase()} / ${b.toUpperCase()}: ${result.span.join(' to ')}`
          : t('cmp.pair', { a: a.toUpperCase(), b: b.toUpperCase(), reason: reasonText(result.reason) })}</li>)}</ul>
      <p>{data.series.map(s => <a key={s.state} href={href(s.link)} rel="noopener noreferrer">{s.name} {s.state.toUpperCase()} </a>)}</p>
    </section>
  </main>;
}
