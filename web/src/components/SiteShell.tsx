// Redesign step 1 (D208): one header, grouped navigation and footer on every page.
import type { ReactNode } from 'react';
import { t } from '../i18n';

type Item = { id: string; label: string; href: string };
export const NAV: { group: string; items: Item[] }[] = [
  { group: 'Explore', items: [
    { id: 'map', label: 'Map', href: './' },
    { id: 'monsoon', label: t('nav.monsoon'), href: '?page=monsoon' },
    { id: 'transit', label: t('nav.transit'), href: '?page=transit' },
    { id: 'warnings', label: t('nav.warnings'), href: '?page=warnings' },
  ] },
  { group: 'Analysis', items: [
    { id: 'findings', label: t('nav.findings'), href: '?page=findings' },
    { id: 'accuracy', label: 'Model accuracy', href: '?page=accuracy' },
    { id: 'climate', label: t('nav.climate'), href: '?page=climate' },
  ] },
  { group: 'Tools', items: [
    { id: 'ask', label: 'Ask', href: '?page=ask' },
    { id: 'wall', label: t('wall.title'), href: '?page=wall' },
  ] },
];

export const REPO = 'https://github.com/Joepikka/monsoon-atlas';

export function SiteHeader({ current }: { current: string }) {
  return <header className="site-header">
    <a className="site-brand" href="./">
      <svg className="site-mark" width="34" height="34" viewBox="0 0 36 36" aria-hidden="true">
        <circle cx="18" cy="18" r="15" fill="none" stroke="currentColor" />
        <path d="M18 5v7m0 12v7M5 18h7m12 0h7M18 11l5 12-5-3-5 3z" fill="currentColor" />
      </svg>
      <span>{current === 'map' ? <h1>Monsoon Atlas</h1> : <strong>Monsoon Atlas</strong>}
        <small>Karnataka · open data · tested methods</small></span>
    </a>
    <nav className="site-nav" aria-label="Site">
      {NAV.map(({ group, items }) => <div className="site-nav-group" key={group}>
        <span className="site-nav-label" aria-hidden="true">{group}</span>
        {items.map(item => <a key={item.id} href={item.href} aria-current={item.id === current ? 'page' : undefined}>{item.label}</a>)}
      </div>)}
      <a className="site-official" href="https://sachet.ndma.gov.in/" target="_blank" rel="noopener noreferrer">
        Official warnings <span aria-hidden="true">↗</span>
      </a>
    </nav>
  </header>;
}

export function SiteFooter() {
  return <footer className="site-foot">
    <p><strong>Not an emergency service.</strong> In an emergency call 112 and follow official warnings.</p>
    <p>Monsoon Atlas is a Rs 0 open-data project. Every figure comes from committed, licensed data with its
      method and limits stated. <a href={REPO} rel="noopener noreferrer">Code, data sources and decisions on GitHub</a>.</p>
  </footer>;
}

/** Shell for every page except the map (which keeps its full-height workspace) and wall/widget modes. */
export default function SiteShell({ current, children }: { current: string; children: ReactNode }) {
  return <div className="site-page">
    <SiteHeader current={current} />
    <nav className="site-crumb" aria-label="Breadcrumb"><a href="./">Back to the map</a></nav>
    {children}
    <SiteFooter />
  </div>;
}
