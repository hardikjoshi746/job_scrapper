import axios from 'axios'

// Dev (localhost): use Vite proxy at /api
// Prod (Vercel): call Railway directly
export const baseURL = window.location.hostname === 'localhost'
  ? '/api'
  : 'https://jobscrapper-production-bb25.up.railway.app/api'

const client = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Attach JWT token to every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Redirect to login on 401
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default client
