import http from './http'

export const getPresets = () => http.get('/screener/presets')

export const runScreener = (preset = 'trend_breakout', cond = {}, limit = 100) =>
  http.post(`/screener/run?preset=${encodeURIComponent(preset)}&limit=${limit}`, cond)
