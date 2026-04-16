import http from './http'

export const getPortfolio = (include_closed = false) =>
  http.get('/portfolio', { params: { include_closed } })

export const addPosition = (payload) => http.post('/portfolio', payload)

export const updatePosition = (id, payload) => http.put(`/portfolio/${id}`, payload)

export const closePosition = (id, params = {}) =>
  http.delete(`/portfolio/${id}`, { params })

export const getPortfolioReview = (initial_cash = 100000) =>
  http.get('/portfolio/review', { params: { initial_cash } })

export const getEquityCurve = (days = 120, initial_cash = 100000) =>
  http.get('/portfolio/equity', { params: { days, initial_cash } })

export const getTransactions = (limit = 200) =>
  http.get('/portfolio/transactions', { params: { limit } })
