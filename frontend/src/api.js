import axios from 'axios'
import { getCsrfToken } from './csrf'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true, // JWT хранится в httpOnly-куках, а не в localStorage
})

// CSRF для запросов с куками (Django требует X-CSRFToken для POST/PUT/DELETE)
api.interceptors.request.use((config) => {
  const csrf = getCsrfToken()
  if (csrf && ['post', 'put', 'patch', 'delete'].includes((config.method || '').toLowerCase())) {
    config.headers['X-CSRFToken'] = csrf
  }
  return config
})

let refreshing = null

async function refreshAccessToken() {
  if (!refreshing) {
    refreshing = axios.post('/api/auth/refresh', null, { withCredentials: true })
      .finally(() => { refreshing = null })
  }
  await refreshing
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    // access-токен (кука) истёк — пробуем обновить из refresh-куки один раз
    if (error.response && error.response.status === 401 && !original._retry) {
      original._retry = true
      try {
        await refreshAccessToken()
        return api(original)
      } catch (e) {
        if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  }
)

export default api
