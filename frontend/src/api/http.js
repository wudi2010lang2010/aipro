import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

http.interceptors.response.use(
  res => res.data,
  err => {
    console.error('API Error:', err.message)
    return Promise.reject(err)
  }
)

export default http
