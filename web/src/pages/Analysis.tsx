// T217: index of committed analysis reports with their sources and licence note.
import { data, href } from '../dashboards';
import { t } from '../i18n';

export default function Analysis() {
  return <main className="dashboard" aria-labelledby="analysis-heading">
    <h1 id="analysis-heading">{t('an.heading')}</h1>
    <p>{t('an.intro')}</p>
    <ul className="dash-cards">{data.analyses.map(report => <li key={report.link} className="dash-card" data-testid={`analysis-${report.link}`}>
      <h2><a href={href(report.link)} rel="noopener noreferrer">{report.title}</a></h2>
      <p>{t('an.sources', { sources: report.sources.join(', ') })}</p>
      <p>{report.restricted.length ? t('an.restricted', { sources: report.restricted.join(', ') }) : t('an.no_restricted')}</p>
      <p>{report.sources.map(id => <a key={id} href={href(`configs/sources/${id.toLowerCase()}.yaml`)} rel="noopener noreferrer">{id} {t('dash.source_record')}{' '}</a>)}</p>
    </li>)}</ul>
  </main>;
}
