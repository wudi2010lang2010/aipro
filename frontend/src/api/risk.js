import http from './http'

export const getRiskStatus = () => http.get('/risk/status')
