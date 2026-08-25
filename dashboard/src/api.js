import axios from 'axios';

const BASE = 'http://localhost:8000';

const api = axios.create({ baseURL: BASE });

export const getTransactions = (limit = 50)  => api.get(`/api/transactions?limit=${limit}`);
export const getStats        = ()            => api.get('/api/stats');
export const getDrift        = ()            => api.get('/api/drift');
export const getGraph        = (type, id)    => api.get(`/api/graph/${type}/${id}`);
export const scoreTransaction = (tx)         => api.post('/api/score', tx);
export const simulate         = (payload)    => api.post('/api/simulate', payload);
export const submitFeedback   = (fb)         => api.post('/api/feedback', fb);
export const startStream      = (opts = {})  => api.post('/api/stream/start', null, { params: opts });
export const stopStream       = ()           => api.post('/api/stream/stop');

export default api;
