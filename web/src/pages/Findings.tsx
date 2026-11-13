// D199: Karnataka data findings — the analyses behind the site, drawn from committed results only
// (web/src/findings.json, written by scripts/findings_product.py). Rain is an index, never mm (D129);
// bus access is derived shares only (D191). Charts are plain SVG with a data table beside each one.
import type { ReactNode } from 'react';
import raw from '../findings.json';
import { href } from '../dashboards';

export type Findings = typeof raw;
export const data = raw as Findings;

const pct = (v: number, digits = 1) => `${(v * 100).toFixed(digits)}%`;
const fixed = (digits: number) => (v: number) => v.toFixed(digits);
const signed = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`;
const people = (v: number) => v.toLocaleString('en-IN');

/** Value range for a chart axis, always including 0 so bar lengths stay honest. */
export function extent(values: number[]): [number, number] {
  const lo = Math.min(0, ...values), hi = Math.max(0, ...values);
  return hi === lo ? [lo, lo + 1] : [lo, hi];
}

export type Bar = { label: string; value: number; strong?: boolean };

const LABEL_W = 190, PLOT_W = 430, ROW_H = 22, W = LABEL_W + PLOT_W + 80;

function Bars({ rows, format, note }: { rows: Bar[]; format: (v: number) => string; note?: string }) {
  const [lo, hi] = extent(rows.map(r => r.value));
  const x = (v: number) => LABEL_W + ((v - lo) / (hi - lo)) * PLOT_W;
  const h = rows.length * ROW_H + 8;
  return <svg className="find-chart" viewBox={`0 0 ${W} ${h}`} role="img" aria-label={note}>
    <line x1={x(0)} x2={x(0)} y1={0} y2={h} className="find-axis" />
    {rows.map((r, i) => {
      const y = i * ROW_H + 4, a = x(Math.min(0, r.value)), b = x(Math.max(0, r.value));
      return <g key={r.label}>
        <text x={LABEL_W - 8} y={y + 14} textAnchor="end" className="find-label">{r.label}</text>
        <rect x={a} y={y + 3} width={Math.max(1, b - a)} height={ROW_H - 7}
          className={r.strong === false ? 'find-bar weak' : 'find-bar'} />
        <text x={b + 6} y={y + 14} className="find-value">{format(r.value)}</text>
      </g>;
    })}
  </svg>;
}

export type Series = { name: string; points: [number, number][]; dashed?: boolean };

function Line({ series, xLabel, yLabel, yFormat, xTick, zero = false }: {
  series: Series[]; xLabel: string; yLabel: string; yFormat: (v: number) => string;
  xTick: (v: number) => string; zero?: boolean;
}) {
  const all = series.flatMap(s => s.points);
  const xs = all.map(p => p[0]), ys = all.map(p => p[1]);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  const [y0, y1] = zero ? extent(ys) : [Math.min(...ys), Math.max(...ys)];
  const L = 56, R = 16, T = 12, B = 44, Wd = 700, Ht = 280;
  const sx = (v: number) => L + ((v - x0) / (x1 - x0 || 1)) * (Wd - L - R);
  const sy = (v: number) => Ht - B - ((v - y0) / (y1 - y0 || 1)) * (Ht - T - B);
  const yTicks = [y0, (y0 + y1) / 2, y1];
  const xTicks = [x0, x0 + (x1 - x0) / 2, x1];
  return <svg className="find-chart" viewBox={`0 0 ${Wd} ${Ht}`} role="img" aria-label={`${yLabel} by ${xLabel}`}>
    {yTicks.map(v => <g key={`y${v}`}>
      <line x1={L} x2={Wd - R} y1={sy(v)} y2={sy(v)} className="find-grid" />
      <text x={L - 6} y={sy(v) + 4} textAnchor="end" className="find-value">{yFormat(v)}</text>
    </g>)}
    {xTicks.map((v, i) => <text key={`x${v}`} x={sx(v)} y={Ht - B + 18} textAnchor={i === 0 ? 'start' : i === 2 ? 'end' : 'middle'} className="find-value">{xTick(v)}</text>)}
    <text x={(L + Wd - R) / 2} y={Ht - 6} textAnchor="middle" className="find-label">{xLabel}</text>
    {series.map((s, i) => <polyline key={s.name} fill="none" className={`find-line s${i}${s.dashed ? ' dashed' : ''}`}
      points={s.points.map(([a, b]) => `${sx(a).toFixed(1)},${sy(b).toFixed(1)}`).join(' ')} />)}
  </svg>;
}

function Figure({ title, chart, legend, table }: { title: string; chart: ReactNode; legend?: ReactNode; table: ReactNode }) {
  return <figure className="find-figure">
    <figcaption>{title}</figcaption>
    {chart}
    {legend}
    <details><summary>Data table</summary><div className="find-table" tabIndex={0} role="region" aria-label={`${title}, data`}>{table}</div></details>
  </figure>;
}

function Kpis({ items }: { items: [string, string][] }) {
  return <dl className="find-kpis">{items.map(([label, value]) =>
    <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function Table({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return <table><thead><tr>{head.map(h => <th key={h} scope="col">{h}</th>)}</tr></thead>
    <tbody>{rows.map(r => <tr key={String(r[0]) + String(r[1])}>{r.map((c, i) => i === 0
      ? <th key={i} scope="row">{c}</th> : <td key={i}>{c}</td>)}</tr>)}</tbody></table>;
}

function Section({ id, title, lead, source, children }: { id: string; title: string; lead: string; source: string; children: ReactNode }) {
  return <section className="find-section" aria-labelledby={`${id}-h`}>
    <h2 id={`${id}-h`}>{title}</h2>
    <p className="find-lead">{lead}</p>
    {children}
    <p className="find-source">Full method and checks: <a href={href(source)} rel="noopener noreferrer">{source}</a></p>
  </section>;
}

export function trendBars(d: Findings = data): Bar[] {
  return [...d.trends.rows].sort((a, b) => b.sen_pct_per_decade - a.sen_pct_per_decade)
    .map(r => ({ label: r.district, value: r.sen_pct_per_decade, strong: r.fdr_q < 0.05 }));
}

export function hospitalBars(d: Findings = data): Bar[] {
  return [...d.hospital.districts].sort((a, b) => b.share_beyond_10km - a.share_beyond_10km)
    .map(r => ({ label: r.district, value: r.share_beyond_10km }));
}

export default function Findings() {
  const h = data.hospital, s = h.statewide, tr = data.trends, bus = data.bus, m = data.model;
  const locked = m.mae.filter(r => r.period.startsWith('2020'));
  const months = data.spatial.moran;
  return <main className="dashboard findings" aria-labelledby="findings-heading">
    <h1 id="findings-heading">Karnataka data findings</h1>
    <p>What the open data says about Karnataka, with the method and the limits of each result. Every number
      comes from a committed, tested analysis; nothing here is an official statement or an emergency service.
      The same results are in a 10-page Power BI report (<a href={href('powerbi/')} rel="noopener noreferrer">powerbi/</a>).</p>
    <nav aria-label="Findings"><ul className="find-toc">
      <li><a href="#hospital-h">Hospital access</a></li><li><a href="#trends-h">Rain trends</a></li>
      <li><a href="#bus-h">Bus access</a></li><li><a href="#model-h">Drought model</a></li>
      <li><a href="#intervals-h">Forecast ranges</a></li><li><a href="#spatial-h">Spatial errors</a></li>
    </ul></nav>

    <Section id="hospital" title="1. How far people live from a hospital" source={h.report}
      lead={`Half of Karnataka's ${(s.people / 1e6).toFixed(1)} million people live within ${s.median_km} km of a mapped hospital, but ${pct(s.share_beyond_10km)} live more than 10 km away. WorldPop 2025 1 km cells to ${people(h.hospitals)} OpenStreetMap hospitals, exact great-circle distance, people-weighted.`}>
      <Kpis items={[['Median distance', `${s.median_km} km`], ['90th percentile', `${s.p90_km} km`],
        ['More than 10 km away', pct(s.share_beyond_10km)], ['Gini of distance', s.gini.toFixed(2)]]} />
      <div className="find-grid2">
        <Figure title="Share of people more than 10 km from a hospital, by district" chart={<Bars rows={hospitalBars()} format={v => pct(v)} note="Share beyond 10 km by district" />}
          table={<Table head={['District', 'People', 'Mean km', 'Over 10 km']} rows={h.districts.map(r => [r.district, people(r.people), r.mean_km, pct(r.share_beyond_10km)])} />} />
        <Figure title="Lorenz curve: share of all distance travelled, people sorted closest first"
          chart={<Line series={[{ name: 'Karnataka', points: h.lorenz.map(([a, b]) => [a, b]) }, { name: 'Equal access', points: [[0, 0], [1, 1]], dashed: true }]}
            xLabel="share of people, closest first" yLabel="share of total distance" yFormat={v => pct(v, 0)} xTick={v => pct(v, 0)} />}
          legend={<p className="find-legend"><span className="key s0" /> Karnataka <span className="key s1 dashed" /> equal access (Gini 0)</p>}
          table={<Table head={['Share of people', 'Share of distance']} rows={h.lorenz.map(([a, b]) => [pct(a, 0), pct(b, 1)])} />} />
      </div>
      <ul className="find-limits">{h.limits.map(l => <li key={l}>{l}</li>)}</ul>
    </Section>

    <Section id="trends" title="2. Has annual rain changed since 1981?" source={tr.report}
      lead={`Annual rain rose in ${tr.significant} of ${tr.tested} districts after correcting for ${tr.tested} tests (Benjamini-Hochberg q below 0.05). Rain is an index, % of the 1981-2010 mean per decade (Sen slope), never mm; the Mann-Kendall test does not assume a straight line.`}>
      <Figure title="Sen slope, % of the 1981-2010 mean per decade (dark: significant after correction)"
        chart={<Bars rows={trendBars()} format={signed} note="Sen slope by district" />}
        legend={<p className="find-legend"><span className="key bar" /> significant (q &lt; 0.05) <span className="key bar weak" /> not significant</p>}
        table={<Table head={['District', 'Sen, %/decade', 'BH q', 'Result']} rows={tr.rows.map(r => [r.district, signed(r.sen_pct_per_decade), r.fdr_q.toFixed(3), r.significance])} />} />
    </Section>

    <Section id="bus" title="3. Who can walk to a bus in Bengaluru?" source={bus.report}
      lead={`${pct(bus.covered_share)} of ${people(bus.people)} people in ${bus.district} district live within a 500 m walk, along mapped paths, of a stop with scheduled BMTC service (${bus.service_date}). Derived shares only; no stops, routes or times are shown.`}>
      <div className="find-grid2">
        <Figure title="People by share of their 1 km cell within the walk"
          chart={<Bars rows={bus.bands.map(b => ({ label: b.band, value: b.people }))} format={v => `${(v / 1e6).toFixed(2)} M`} note="People by band" />}
          table={<Table head={['Band', '1 km cells', 'People']} rows={bus.bands.map(b => [b.band, b.cells, people(b.people)])} />} />
        <div><p>See every cell on the map: <a href="?page=transit">Bus access</a>.</p>
          <ul className="find-limits">{bus.limits.map(l => <li key={l}>{l}</li>)}</ul></div>
      </div>
    </Section>

    <Section id="model" title="4. Does the drought outlook beat simple rules?" source={m.report}
      lead="M05 forecasts each district's 3-month drought index (SPI-3). On the locked 2020-2024 test it beats the strongest simple rule, persistence, and the lower 95% bound of its gain (paired block bootstrap) is above zero. A LightGBM challenger scored close but was not promoted: its gain over ridge was not clearly above zero on the tuning years. This is a hindcast, because IMD publishes the grid yearly.">
      <div className="find-grid2">
        <Figure title="Mean absolute error, 2020-2024, SPI units (lower is better; dark: the promoted model)"
          chart={<Bars rows={locked.map(r => ({ label: r.model, value: r.mae, strong: r.model === 'M05 ridge' }))} format={fixed(3)} note="MAE by model" />}
          table={<Table head={['Period', 'Model', 'MAE']} rows={m.mae.map(r => [r.period, r.model, r.mae.toFixed(3)])} />} />
        <Figure title="Promotion gates (every one must pass)" chart={<ul className="find-gates">{m.gates.map(g =>
          <li key={g.check} className={g.passed === 'yes' ? 'pass' : 'fail'}><strong>{g.passed === 'yes' ? 'Pass' : 'Fail'}</strong> {g.check}: {g.value} against {g.reference}</li>)}</ul>}
          table={<Table head={['Period', 'Mean gain', 'Lower 95%', 'Upper 95%']} rows={m.gain.map(g => [g.period, g.mean.toFixed(3), g.lower95.toFixed(3), g.upper95.toFixed(3)])} />} />
      </div>
    </Section>

    <Section id="intervals" title="5. Can the outlook give a range?" source="models/registry/M05/v1.intervals.json"
      lead={`Not yet. An 80% range is published only if it holds the outcome 75-85% of the time. M05's range missed that band at every look, so the site shows the outlook without a range. The rule was chosen on 2010-2019 before any test year was used.`}>
      <Figure title="80% interval coverage at each look (target band 75% to 85%)"
        chart={<Bars rows={data.intervals.looks.map(l => ({ label: l.stage, value: l.coverage, strong: l.result.startsWith('inside') }))} format={v => pct(v)} note="Interval coverage" />}
        legend={<p className="find-legend"><span className="key bar" /> inside the band <span className="key bar weak" /> outside</p>}
        table={<Table head={['Look', 'Coverage', 'Result']} rows={data.intervals.looks.map(l => [l.stage, pct(l.coverage), l.result])} />} />
    </Section>

    <Section id="spatial" title="6. Do the model's errors cluster on the map?" source={data.spatial.report}
      lead={`Yes: in ${data.spatial.significant} of ${data.spatial.months} months, neighbouring districts' errors were more alike than chance (Moran's I, 999 permutations, Benjamini-Hochberg). The model tends to miss whole regions at once, not single districts.`}>
      <Figure title="Moran's I of forecast errors by issue month, 2020-2024 (0 = no clustering)"
        chart={<Line series={[{ name: "Moran's I", points: months.map((r, i) => [i, r.moran_i]) }]} zero
          xLabel="issue month" yLabel="Moran's I" yFormat={fixed(2)} xTick={v => months[Math.round(v)]?.month ?? ''} />}
        table={<Table head={['Month', "Moran's I", 'Significant']} rows={months.map(r => [r.month, r.moran_i.toFixed(2), r.significant])} />} />
    </Section>
  </main>;
}
