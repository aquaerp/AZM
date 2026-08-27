import axios from 'axios'

const desktopApiBaseUrl = typeof window !== 'undefined' ? window.azmDesktop?.apiBaseUrl : ''

const api = axios.create({
  baseURL: desktopApiBaseUrl || import.meta.env.VITE_API_BASE_URL || '/api',
})

const deviceStorageKey = 'azm_device_id'
let deviceId = localStorage.getItem(deviceStorageKey)
if (!deviceId) {
  deviceId = crypto.randomUUID()
  localStorage.setItem(deviceStorageKey, deviceId)
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('azm_access_token')
  config.headers['Accept-Language'] = localStorage.getItem('azm_language') || 'ar'
  config.headers['X-Azm-Device-Id'] = deviceId
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise = null
const refreshPath = '/auth/token/refresh/'

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const refreshToken = localStorage.getItem('azm_refresh_token')
    const isAuthRequest = originalRequest?.url?.includes('/auth/login/') || originalRequest?.url?.includes(refreshPath)
    if (error.response?.status !== 401 || !refreshToken || originalRequest?._azmRetried || isAuthRequest) {
      return Promise.reject(error)
    }
    originalRequest._azmRetried = true
    try {
      refreshPromise ||= axios.post(`${api.defaults.baseURL}${refreshPath}`, { refresh: refreshToken })
      const { data } = await refreshPromise
      localStorage.setItem('azm_access_token', data.access)
      if (data.refresh) localStorage.setItem('azm_refresh_token', data.refresh)
      originalRequest.headers.Authorization = `Bearer ${data.access}`
      return api(originalRequest)
    } catch (refreshError) {
      localStorage.removeItem('azm_access_token')
      localStorage.removeItem('azm_refresh_token')
      window.dispatchEvent(new CustomEvent('azm:session-expired'))
      return Promise.reject(refreshError)
    } finally {
      refreshPromise = null
    }
  },
)

export default api
