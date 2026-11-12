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
import Transit from './pages/Transit';
import Monsoon from './pages/Monsoon';
import Widget from './pages/Widget';

// T259: a query switch keeps the single-page build without a router dependency (D94).
const name = new URLSearchParams(window.location.search).get('page');
const PAGES: Record<string, () => ReactElement> = {
  accuracy: () => <Accuracy />, ask: () => <Ask />, quality: () => <Quality />,
  analysis: () => <Analysis />, compare: () => <Compare />, widget: () => <Widget />,
  climate: () => <Climate />, wall: () => <Wall />, warnings: () => <Warnings />, transit: () => <Transit />, monsoon: () => <Monsoon />,
};
const page = (name !== null && Object.hasOwn(PAGES, name) ? PAGES[name] : () => <App />)();
createRoot(document.getElementById('root')!).render(<StrictMode>{page}</StrictMode>);
