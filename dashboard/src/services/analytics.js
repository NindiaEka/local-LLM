import api from './api'

export const analyticsService = {
  getSummary: () => api.get('/v1/analytics/summary'),
}
