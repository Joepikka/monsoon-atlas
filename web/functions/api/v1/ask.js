import { forward } from '../../../pages-proxy.js';

export const onRequestPost = ({ request }) => forward(request, '/api/v1/ask');
