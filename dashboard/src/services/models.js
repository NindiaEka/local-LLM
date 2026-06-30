import api from './api'

export const modelsService = {
  getModels: () => api.get('/v1/models'),
}
