// T217: source health (data problems) kept apart from the M16 review queue and from hazards.
import { data, href, num } from '../dashboards';
import { t } from '../i18n';

const yesNo = (value: boolean): string => value ? t('dash.yes') : t('dash.no');

export default function Quality() {
  const { anomaly_queue: queue, drift } = data;
  return <main className="dashboard" aria-labelledby="quality-heading">
    <p><a href="./">{t('ask.back')}</a></p>
    <h1 id="quality-heading">{t('q.heading')}</h1>
    <p>{t('q.intro')}</p>
    <section aria-labelledby="source-health-heading">
      <h2 id="source-health-heading">{t('q.sources_heading')}</h2>
      <div className="accuracy-table" tabIndex={0} role="region" aria-label={t('q.sources_heading')}>
        <table>
          <thead><tr>
            <th scope="col">{t('q.col_state')}</th><th scope="col">{t('q.col_source')}</th>
            <th scope="col">{t('q.col_enabled')}</th><th scope="col">{t('q.col_outcome')}</th>
            <th scope="col">{t('q.col_licence')}</th><th scope="col">{t('q.col_retry')}</th>
          </tr></thead>
          <tbody>{data.sources.map(source => <tr key={`${source.state}-${source.id}`} data-testid={`source-${source.state}-${source.id}`}>
            <td>{source.state.toUpperCase()}</td>
            <th scope="row"><a href={href(source.link)} rel="noopener noreferrer">{source.id}</a> {source.name}</th>
            <td>{yesNo(source.enabled)}</td><td>{source.outcome}</td><td>{source.licence}</td>
            <td>{source.retry ?? t('q.no_retry')}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </section>
    <section aria-labelledby="queue-heading" data-testid="review-queue">
      <h2 id="queue-heading">{t('q.queue_heading')}</h2>
      <p>{t('q.queue_note', { model: queue.model, label: queue.label, adjudicated: queue.adjudicated, required: queue.required })}</p>
      <ul>{Object.entries(queue.states).map(([state, counts]) => <li key={state}>
        {t('q.queue_state', { state: state.toUpperCase(), flags: counts.flags.toLocaleString('en-IN'), evaluated: counts.evaluated.toLocaleString('en-IN') })}</li>)}</ul>
      <p>{queue.links.map(path => <a key={path} href={href(path)} rel="noopener noreferrer">{path} </a>)}</p>
    </section>
    <section aria-labelledby="extremes-heading">
      <h2 id="extremes-heading">{t('q.extremes_heading')}</h2>
      <p>{t('q.extremes_body')}</p>
    </section>
    <section aria-labelledby="drift-heading" data-testid="drift">
      <h2 id="drift-heading">{t('q.drift_heading')}</h2>
      <p>{t('q.drift_body', {
        model: drift.model, period: drift.period.replace('/', ' to '), rows: drift.rows, ratio: num(drift.mae_ratio),
        low: num(drift.ci95[0]), high: num(drift.ci95[1]), flag: drift.flag, label: drift.label,
      })} <a href={href(drift.link)} rel="noopener noreferrer">{t('dash.report')}</a></p>
      <p>{t('q.drift_none')}</p>
    </section>
  </main>;
}
