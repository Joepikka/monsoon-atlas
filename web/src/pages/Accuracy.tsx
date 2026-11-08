// T259 (child of T046): F036 model accuracy page from an approved release (D94).
import { useEffect, useState } from 'react';
import { loadAccuracy, show, type AccuracyView } from '../accuracy';

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
  </main>;
}
