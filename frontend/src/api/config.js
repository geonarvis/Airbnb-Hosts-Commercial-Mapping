import axios from 'axios'

const api = axios.create({
  baseURL: '/airbnb-hosts-visualization/api',
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export default api
