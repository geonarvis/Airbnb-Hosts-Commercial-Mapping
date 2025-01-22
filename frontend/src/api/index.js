import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.PROD ? 'https://www.geonarvis.com/airbnb-hosts-visualization/api' : 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 添加请求拦截器
api.interceptors.request.use(
  config => {
    if (config.url.includes('/city/') && !config.url.includes('/cities')) {
      console.log('[API Interceptor] Loading start:', config.url);
      window.dispatchEvent(new CustomEvent('api-loading-start'))
    }
    return config
  },
  error => {
    console.error('[API Interceptor] Request error:', error);
    return Promise.reject(error)
  }
)

// 添加响应拦截器
api.interceptors.response.use(
  response => {
    if (response.config.url.includes('/city/') && !response.config.url.includes('/cities')) {
      console.log('[API Interceptor] Loading end:', response.config.url);
      window.dispatchEvent(new CustomEvent('api-loading-end'))
    }
    return response
  },
  error => {
    console.error('[API Interceptor] Response error:', error);
    window.dispatchEvent(new CustomEvent('api-loading-end'))
    return Promise.reject(error)
  }
)

export default api
