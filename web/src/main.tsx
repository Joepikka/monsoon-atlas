import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import Accuracy from './pages/Accuracy';
import Ask from './pages/Ask';

// T259: a query switch keeps the single-page build without a router dependency (D94).
const name = new URLSearchParams(window.location.search).get('page');
const page = name === 'accuracy' ? <Accuracy /> : name === 'ask' ? <Ask /> : <App />;
createRoot(document.getElementById('root')!).render(<StrictMode>{page}</StrictMode>);
