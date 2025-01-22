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
    // 在发送请求之前，确保 loading 状态被正确触发
    if (config.url.includes('/city/') && !config.url.includes('/cities')) {
      // 这里我们需要一个方法来触发 loading 状态
      // 可以通过 Vuex 或者 event bus 来实现
      window.dispatchEvent(new CustomEvent('api-loading-start'))
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 添加响应拦截器
api.interceptors.response.use(
  response => {
    // 请求完成后，确保 loading 状态被正确关闭
    if (response.config.url.includes('/city/') && !response.config.url.includes('/cities')) {
      window.dispatchEvent(new CustomEvent('api-loading-end'))
    }
    return response
  },
  error => {
    window.dispatchEvent(new CustomEvent('api-loading-end'))
    return Promise.reject(error)
  }
)

export default api
