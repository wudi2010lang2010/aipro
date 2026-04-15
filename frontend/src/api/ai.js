import http from './http'

export const analyzeStock = (ts_code, period = 'daily') =>
  http.post(`/ai/analyze?ts_code=${encodeURIComponent(ts_code)}&period=${encodeURIComponent(period)}`)

export const getAISignals = (limit = 50, ts_code = '') =>
  http.get('/ai/signals', { params: { limit, ts_code } })

export const getAISignalDetail = (id) => http.get(`/ai/signals/${id}`)
