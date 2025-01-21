import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// 创建 axios 实例
const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 15000
})

export default api
