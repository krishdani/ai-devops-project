import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const dashboardService = {
  getHealth: () => api.get('/health'),
  getStatus: () => api.get('/status'),
  getDashboardData: () => api.get('/dashboard'),
};

export const logsService = {
  getLogs: (type = 'application', limit = 100, level = '') => 
    api.get(`/logs?type=${type}&limit=${limit}&level=${level}`),
  getLogStream: (lines = 20) => api.get(`/logs/stream?lines=${lines}`),
};

export const alertsService = {
  getAlerts: (limit = 50, severity = '', acknowledged = null) => {
    let url = `/alerts?limit=${limit}`;
    if (severity) url += `&severity=${severity}`;
    if (acknowledged !== null) url += `&acknowledged=${acknowledged}`;
    return api.get(url);
  },
  acknowledgeAlert: (alertId) => api.post(`/alerts/${alertId}/acknowledge`),
  getStats: () => api.get('/alerts/stats'),
};

export const analysisService = {
  getLatest: () => api.get('/analysis/latest'),
  getHistory: (limit = 20) => api.get(`/analysis/history?limit=${limit}`),
  triggerAnalysis: (logType = 'application', lines = 50) => 
    api.post('/analysis/trigger', { log_type: logType, lines }),
};

export default api;
