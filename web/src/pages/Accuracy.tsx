// T259 (child of T046): F036 model accuracy page from an approved release (D94).
// D210: working models first, blocked models grouped as a roadmap; no model is removed.
import { useEffect, useState } from 'react';
import { loadAccuracy, show, type AccuracyView } from '../accuracy';
import { data, href, num } from '../dashboards';
import { t } from '../i18n';

// What each model would predict, from the first line of its report (reports/models/mNN.md).
const PREDICTS: Record<string, string> = {
  M01: 'Bengaluru ward flood occurrence', M02: 'Karnataka reservoir level and storage', M03: 'Karnataka reservoir inflow',
  M04: 'Rain-gauge gap filling and spatial interpolation', M05: 'Karnataka drought outlook', M06: 'Kolar tomato price-spike warning',
  M07: 'Kerala seven-day dam forecast', M08: 'Kerala flood classifier and 2018 held-out replay', M09: 'Kerala landslide susceptibility',
  M10: 'Rain-to-price statistical effect study', M11: 'Karnataka-to-Kerala flood transfer', M12: 'Delhi bus arrival and delay',
  M13: 'Delhi bunching anomaly', M14: 'Delhi station pollution / AQI forecast', M15: 'Heat exposure and heatwave outlook',
  M16: 'Cross-state sensor and market anomalies', M17: 'Sentinel-1 flood extent U-Net', M18: 'Malayalam/English news event extraction',
  M19: 'GRU reservoir challenger', M20: 'Rain what-if sensitivity explorer',
};
const STATES = [['ka', 'Karnataka'], ['kl', 'Kerala'], ['dl', 'Delhi'], ['all', 'All']] as const;
type Pick = typeof STATES[number][0];
type Model = typeof data.models[number];
const predicts = (m: Model) => PREDICTS[m.id] ?? m.id;
const reportLinks = (m: Model) => m.links.map((path, i) => <a key={path} href={href(path)} rel="noopener noreferrer">
  {i === 0 ? t('dash.report') : t('dash.model_card')}</a>);

function Hero({ model }: { model: Model }) {
  const s = model.score!;
  const [from, to] = s.test.split('/');
  return <article className="acc-hero" data-testid={`model-${model.id}`} aria-labelledby={`hero-${model.id}`}>
    <p className="ov-eyebrow">Promoted model, {s.label}</p>
    <h3 id={`hero-${model.id}`}>{model.id} {predicts(model)}</h3>
    <p className="ov-lead">{s.model} beats the {s.baseline} baseline on {s.rows} district-months of held-out data, {from} to {to}.</p>
    <dl className="ov-kpis">
      <div><dt>{s.metric}, {s.model} (lower is better)</dt><dd>{num(s.model_value)}</dd></div>
      <div><dt>{s.metric}, {s.baseline}</dt><dd>{num(s.baseline_value)}</dd></div>
      <div><dt>Improvement</dt><dd>{num(s.improvement)}</dd></div>
      <div><dt>95% CI of improvement</dt><dd>{num(s.ci95?.[0])} to {num(s.ci95?.[1])}</dd></div>
    </dl>
    <p className="acc-detail">{t('acc.score', {
      metric: s.metric, model: s.model, baseline: s.baseline,
      model_value: num(s.model_value), baseline_value: num(s.baseline_value),
      improvement: num(s.improvement), low: num(s.ci95?.[0]), high: num(s.ci95?.[1]),
      rows: s.rows, months: s.months, from, to, label: s.label,
    })}</p>
    <p className="acc-detail">{model.reason}</p>
    <p className="acc-links">{reportLinks(model)}</p>
  </article>;
}

// T217: every model with its status; scores only where the registry has them (M05).
export function ModelCards({ initial = 'ka' }: { initial?: Pick }) {
  const [pick, setPick] = useState<Pick>(initial);
  const shown = data.models.filter(m => pick === 'all' || m.state === pick || m.state === 'all');
  const scored = shown.filter(m => m.score);
  const research = shown.filter(m => !m.score && m.status === 'research_only');
  const roadmap = shown.filter(m => !m.score && m.status !== 'research_only');
  const name = pick === 'kl' ? 'Kerala' : 'Delhi';
  return <section aria-labelledby="models-heading">
    <h2 id="models-heading">Models that work</h2>
    <p className="acc-frame">A model is shown as working only when it beats the strongest simple baseline on held-out data.
      Models without licensed labels are listed as roadmap, not trained on invented data.</p>
    <div className="ov-switch" role="group" aria-label="State">
      {STATES.map(([id, label]) => <button key={id} type="button" aria-pressed={pick === id} className={pick === id ? 'on' : ''}
        onClick={() => setPick(id)}>{label}</button>)}
    </div>
    {(pick === 'kl' || pick === 'dl') && <p className="ov-note">{name} work has not started yet (Karnataka comes first),
      so no {name} model has been trained.</p>}
    {scored.map(m => <Hero key={m.id} model={m} />)}
    {scored.length === 0 && <p className="ov-note">No model for this selection has passed the baseline test yet.</p>}
    {research.map(m => <article key={m.id} className="acc-research" data-testid={`model-${m.id}`}>
      <p className="ov-eyebrow acc-tag">Research only</p>
      <h3>{m.id} {predicts(m)}</h3>
      <p>{t('acc.no_score', { reason: m.reason })}</p>
      <p className="acc-links">{reportLinks(m)}</p>
    </article>)}
    <details className="acc-roadmap">
      <summary>Roadmap: models waiting for data ({roadmap.length})</summary>
      <p className="ov-note acc-pad">{t('acc.models_intro')}</p>
      <ul aria-label={t('acc.models_heading')}>{roadmap.map(m => <li key={m.id} data-testid={`model-${m.id}`}>
        <strong>{m.id} {predicts(m)}</strong>
        <span className="dash-state">{m.state === 'all' ? 'ALL STATES' : m.state.toUpperCase()}, {m.status.toUpperCase()}</span>
        <span className="acc-why">{t('acc.no_score', { reason: m.reason })}</span>
        <span className="acc-links">{reportLinks(m)}</span>
      </li>)}</ul>
    </details>
  </section>;
}

export default function Accuracy({ fetcher }: { fetcher?: typeof fetch }) {
  const [view, setView] = useState<AccuracyView>({ status: 'loading', rows: null, message: 'Loading the accuracy table…' });
  useEffect(() => { loadAccuracy(fetcher).then(setView); }, [fetcher]);

  return <main className="accuracy" aria-labelledby="accuracy-heading">
    <h1 id="accuracy-heading">Model accuracy</h1>
    <ModelCards />
    <h2>Approved accuracy table</h2>
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
