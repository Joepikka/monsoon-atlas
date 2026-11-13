import { StrictMode, type ReactElement } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import Accuracy from './pages/Accuracy';
import Analysis from './pages/Analysis';
import Ask from './pages/Ask';
import Climate from './pages/Climate';
import Compare from './pages/Compare';
import Quality from './pages/Quality';
import Wall from './pages/Wall';
import Warnings from './pages/Warnings';
import BusAccess from './pages/BusAccess';
import Monsoon from './pages/Monsoon';
import Findings from './pages/Findings';
import SiteShell from './components/SiteShell';
import Overview from './pages/Overview';
import Widget from './pages/Widget';

// T259: a query switch keeps the single-page build without a router dependency (D94).
const name = new URLSearchParams(window.location.search).get('page');
const PAGES: Record<string, () => ReactElement> = {
  accuracy: () => <Accuracy />, ask: () => <Ask />, quality: () => <Quality />,
  analysis: () => <Analysis />, compare: () => <Compare />, widget: () => <Widget />,
  climate: () => <Climate />, wall: () => <Wall />, warnings: () => <Warnings />, transit: () => <BusAccess />, monsoon: () => <Monsoon />, findings: () => <Findings />,
};
const known = name !== null && Object.hasOwn(PAGES, name);
// D209: a bare address opens the Overview; ?page=map and shared place links open the map.
// D208: every page but the map, the wall display and the embeddable widget gets the site shell.
const page = !window.location.search ? <SiteShell current="overview"><Overview /></SiteShell>
  : !known ? <App /> : name === 'wall' || name === 'widget' ? PAGES[name!]()
  : <SiteShell current={name!}>{PAGES[name!]()}</SiteShell>;
createRoot(document.getElementById('root')!).render(<StrictMode>{page}</StrictMode>);
