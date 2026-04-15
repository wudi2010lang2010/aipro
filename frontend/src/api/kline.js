import http from './http'

export const getKline = (ts_code, period = 'daily', limit = 250) =>
  http.get(`/kline/${ts_code}`, { params: { period, limit } })

export const searchStock = (q) => http.get('/kline/search', { params: { q } })
