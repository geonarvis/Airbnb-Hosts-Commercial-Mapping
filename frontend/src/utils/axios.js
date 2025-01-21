import axios from 'axios'
import apiConfig from '../config/api'

const instance = axios.create({
    baseURL: apiConfig.baseURL,
    timeout: 15000,
    headers: {
        'Content-Type': 'application/json'
    }
})

// 请求拦截器
instance.interceptors.request.use(
    config => {
        // 添加任何请求头等配置
        return config
    },
    error => {
        return Promise.reject(error)
    }
)

// 响应拦截器
instance.interceptors.response.use(
    response => response.data,
    error => {
        // 统一错误处理
        console.error('API Error:', error)
        return Promise.reject(error)
    }
)

export default instance 