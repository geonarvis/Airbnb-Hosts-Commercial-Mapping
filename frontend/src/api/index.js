import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/airbnb-hosts-visualization/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 添加请求拦截器
api.interceptors.request.use(config => {
  console.log('API Request:', config.url)
  return config
})

// 添加响应拦截器
api.interceptors.response.use(response => {
  console.log('API Response:', {
    url: response.config.url,
    status: response.status,
    duration: Date.now() - response.config.requestStartTime
  })
  return response
}, error => {
  console.error('API Error:', error)
  return Promise.reject(error)
})

export default api
