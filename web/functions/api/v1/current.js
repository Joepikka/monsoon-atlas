import { forward } from '../../../pages-proxy.js';

export const onRequestGet = ({ request }) => forward(request, '/api/v1/current');
