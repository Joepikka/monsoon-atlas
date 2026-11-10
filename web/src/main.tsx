import { StrictMode, type ReactElement } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import Accuracy from './pages/Accuracy';
import Analysis from './pages/Analysis';
import Ask from './pages/Ask';
import Compare from './pages/Compare';
import Quality from './pages/Quality';
import Widget from './pages/Widget';

// T259: a query switch keeps the single-page build without a router dependency (D94).
const name = new URLSearchParams(window.location.search).get('page');
const PAGES: Record<string, () => ReactElement> = {
  accuracy: () => <Accuracy />, ask: () => <Ask />, quality: () => <Quality />,
  analysis: () => <Analysis />, compare: () => <Compare />, widget: () => <Widget />,
};
const page = (name !== null && Object.hasOwn(PAGES, name) ? PAGES[name] : () => <App />)();
createRoot(document.getElementById('root')!).render(<StrictMode>{page}</StrictMode>);
