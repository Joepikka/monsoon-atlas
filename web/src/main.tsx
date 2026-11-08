import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import Accuracy from './pages/Accuracy';

// T259: a query switch keeps the single-page build without a router dependency (D94).
const page = new URLSearchParams(window.location.search).get('page') === 'accuracy' ? <Accuracy /> : <App />;
createRoot(document.getElementById('root')!).render(<StrictMode>{page}</StrictMode>);
