import http from './http'

export const runBacktest = (payload) => http.post('/backtest/run', payload)

export const getBacktestResult = (result_id) => http.get(`/backtest/results/${result_id}`)

export const getVirtualSimulation = (initial_cash = 100000, limit = 200) =>
  http.get('/backtest/simulate', { params: { initial_cash, limit } })
