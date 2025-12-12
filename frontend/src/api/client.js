import axios from 'axios'
import { getToken, clearSession } from './session'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  withCredentials: false,
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  console.info(`[API REQUEST] ${config.method?.toUpperCase()} ${config.url}`)
  return config
})

api.interceptors.response.use(
  (response) => {
    console.info(`[API RESPONSE] ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    if (error.response) {
      console.error(`[API ERROR] ${error.response.status} ${error.config?.url}`)
      if (error.response.status === 401) {
        clearSession()
      }
    }
    return Promise.reject(error)
  }
)

export default api
