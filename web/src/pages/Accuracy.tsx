// T259 (child of T046): F036 model accuracy page from an approved release (D94).
import { useEffect, useState } from 'react';
import { loadAccuracy, show, type AccuracyView } from '../accuracy';
import { data, href, num } from '../dashboards';
import { t } from '../i18n';

// T217: every model with its status; scores only where the registry has them (M05).
export function ModelCards() {
  return <section aria-labelledby="models-heading">
    <h2 id="models-heading">{t('acc.models_heading')}</h2>
    <p>{t('acc.models_intro')}</p>
    <ul className="dash-cards">{data.models.map(model => <li key={model.id} className="dash-card" data-testid={`model-${model.id}`}>
      <h3>{model.id} <span className="dash-state">{model.state.toUpperCase()}</span></h3>
      <p><strong>{model.status}</strong></p>
      <p>{model.score ? t('acc.score', {
        metric: model.score.metric, model: model.score.model, baseline: model.score.baseline,
        model_value: num(model.score.model_value), baseline_value: num(model.score.baseline_value),
        improvement: num(model.score.improvement), low: num(model.score.ci95?.[0]), high: num(model.score.ci95?.[1]),
        rows: model.score.rows, months: model.score.months, from: model.score.test.split('/')[0],
        to: model.score.test.split('/')[1], label: model.score.label,
      }) : t('acc.no_score', { reason: model.reason })}</p>
      <p>{model.links.map((path, i) => <a key={path} href={href(path)} rel="noopener noreferrer">
        {i === 0 ? t('dash.report') : t('dash.model_card')}{' '}</a>)}</p>
    </li>)}</ul>
  </section>;
}

export default function Accuracy({ fetcher }: { fetcher?: typeof fetch }) {
  const [view, setView] = useState<AccuracyView>({ status: 'loading', rows: null, message: 'Loading the accuracy table…' });
  useEffect(() => { loadAccuracy(fetcher).then(setView); }, [fetcher]);

  return <main className="accuracy" aria-labelledby="accuracy-heading">
    <p><a href="./">Back to the map</a></p>
    <h1 id="accuracy-heading">Model accuracy</h1>
    <p>Each model is compared with its strongest simple baseline on held-out test dates.
      Unavailable means no evaluated value exists; it is not zero.</p>
    <p role="status" className={`accuracy-status ${view.status}`}>{view.message}</p>
    {view.status === 'ready' && <div className="accuracy-table" tabIndex={0} role="region" aria-label="Accuracy table, scrolls sideways">
      <table>
        <caption>Karnataka MVP models (release {view.releaseHash.slice(0, 12)})</caption>
        <thead><tr>
          {['Model', 'Core', 'Target', 'Baseline', 'Test dates', 'Metric', 'Model value', 'Baseline value',
            'Improvement', '95% CI', 'Status', 'Report'].map(name => <th key={name} scope="col">{name}</th>)}
        </tr></thead>
        <tbody>{view.rows.map(row => <tr key={row.model}>
          <th scope="row">{row.model}</th>
          <td>{row.core}</td><td>{row.target}</td><td>{row.baseline ?? 'Unavailable'}</td>
          <td>{row.test?.replace('/', ' to ') ?? 'Unavailable'}</td><td>{row.metric ?? 'Unavailable'}</td>
          <td>{show(row.candidate)}</td><td>{show(row.baseline_value)}</td><td>{show(row.improvement)}</td>
          <td>{row.ci95 ? `${show(row.ci95[0])} to ${show(row.ci95[1])}` : 'Unavailable'}</td>
          <td>{row.status}</td><td><code>{row.report}</code></td>
        </tr>)}</tbody>
      </table>
    </div>}
    <ModelCards />
  </main>;
}
