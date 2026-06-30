import api from './api'

export const keysService = {
  getKeys: () => api.get('/keys'),
  createKey: (payload) => api.post('/keys', payload),
  deleteKey: (id) => api.delete(`/keys/${id}`),
}
