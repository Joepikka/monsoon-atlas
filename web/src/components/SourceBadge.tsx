import type { MapRecord, SourceHealth } from '../data';
import { localTime } from '../time';

export default function SourceBadge({ record, health, now }: { record: MapRecord; health?: SourceHealth; now: number }) {
  const expired = record.expires_at && Date.parse(record.expires_at) <= now;
  return <div className="source-details">
    <div className="source-badges">
      <span className={`provenance ${record.provenance}`}>{record.provenance}</span>
      {record.evidence && <span className="evidence-label">{record.evidence}</span>}
      <span className={`health ${health?.status ?? 'unknown'}`}>{health?.status ?? 'Health not reported'}</span>
      {record.kind === 'alert' && record.severity && <span className="severity" title="Severity reported by the CAP provider">{record.severity}</span>}
      {expired && <span className="expired">Expired</span>}
    </div>
    {record.value !== null && <p className="measure">{record.value} {record.unit}{record.market && ` · ${record.market}`}</p>}
    {record.value === null && record.missing_reason && <p className="missing-value">Not reported · {record.missing_reason.replaceAll('_', ' ')}</p>}
    <dl className="source-times">
      <div><dt>Issued</dt><dd>{record.issued_at ? <time data-testid="issued-time" dateTime={record.issued_at}>{localTime(record.issued_at)}</time> : 'Not reported'}</dd></div>
      <div><dt>Valid</dt><dd><time data-testid="valid-time" dateTime={record.valid_at}>{localTime(record.valid_at)}</time></dd></div>
      <div><dt>Fetched</dt><dd><time data-testid="fetched-time" dateTime={record.fetched_at}>{localTime(record.fetched_at)}</time></dd></div>
      {record.expires_at && <div><dt>Expires</dt><dd><time dateTime={record.expires_at}>{localTime(record.expires_at)}</time></dd></div>}
    </dl>
    {health && <p className="source-health-detail">{health.detail}</p>}
  </div>;
}
