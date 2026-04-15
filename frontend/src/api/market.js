import http from './http'

export const getIndices = () => http.get('/market/indices')
export const getTopGainers = (n = 20) => http.get('/market/top-gainers', { params: { n } })
export const getSectors = () => http.get('/market/sectors')
export const getMarketStatus = () => http.get('/market/status')
export const getWatchlist = () => http.get('/market/watchlist')
export const addWatchlist = (ts_code, note = '') => http.post('/market/watchlist', { ts_code, note })
export const removeWatchlist = (ts_code) => http.delete(`/market/watchlist/${ts_code}`)
export const getQuote = (ts_code) => http.get(`/market/quote/${ts_code}`)
