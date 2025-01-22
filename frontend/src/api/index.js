import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.DEV ? '/api' : 'https://api.yoursite.com',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export default api
