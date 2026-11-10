// T218 (D162): read-only summary for embedding. It reads nothing from the embedding page (not its
// location, not its referrer), posts nothing and has no control except links that open in a new
// tab. Which origins may frame it is a response header, not code: see frameAncestors.
import { data, href, num, ratio } from '../dashboards';
import { t } from '../i18n';

/** Origins allowed to embed the widget. Empty: no partner exists. */
export const WIDGET_ORIGINS: readonly string[] = [];
export const APP_FRAME_ANCESTORS = "frame-ancestors 'self'";

/** The widget response's CSP value: self plus exact https origins; anything else is refused. */
export function frameAncestors(origins: readonly string[] = WIDGET_ORIGINS): string {
  for (const origin of origins) {
    if (new URL(origin).protocol !== 'https:' || new URL(origin).origin !== origin) throw new Error(`Not an https origin: ${origin}`);
  }
  return ['frame-ancestors', "'self'", ...origins].join(' ');
}

export default function Widget({ search = window.location.search }: { search?: string }) {
  const asked = new URLSearchParams(search).get('state');
  const state = (asked !== null && Object.hasOwn(data.states, asked) ? asked : 'ka') as keyof typeof data.states;
  const s = data.states[state];
  return <section className="widget" aria-labelledby="widget-heading" data-testid="widget">
    <h2 id="widget-heading">{t('widget.heading', { state: state.toUpperCase() })}</h2>
    <p>{t('widget.summary', { enabled: s.enabled, sources: s.sources, coverage: num(ratio(s.enabled, s.sources)), models_blocked: s.models_blocked, models: s.models })}</p>
    <p>{t('widget.note')}</p>
    <p><a href={href(s.link)} target="_blank" rel="noopener noreferrer">{t('dash.source_record')}</a>{' '}
      <a href={href(s.page)} target="_blank" rel="noopener noreferrer">{t('dash.report')}</a></p>
  </section>;
}
