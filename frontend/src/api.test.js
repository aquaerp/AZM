import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => {
  const requestUse = vi.fn()
  const responseUse = vi.fn()
  const apiInstance = vi.fn()
  apiInstance.defaults = { baseURL: '/api' }
  apiInstance.interceptors = {
    request: { use: requestUse },
    response: { use: responseUse },
  }
  return {
    apiInstance,
    axiosCreate: vi.fn(() => apiInstance),
    axiosPost: vi.fn(),
    requestUse,
    responseUse,
  }
})

vi.mock('axios', () => ({
  default: {
    create: mocks.axiosCreate,
    post: mocks.axiosPost,
  },
}))

await import('./api')
const [, onRejected] = mocks.responseUse.mock.calls[0]

describe('API token refresh', () => {
  beforeEach(() => {
    mocks.axiosPost.mockReset()
    mocks.apiInstance.mockReset()
    localStorage.clear()
  })

  it('refreshes an expired access token through the backend token endpoint', async () => {
    localStorage.setItem('azm_refresh_token', 'refresh-token')
    mocks.axiosPost.mockResolvedValue({ data: { access: 'new-access-token' } })
    mocks.apiInstance.mockResolvedValue({ data: { ok: true } })
    const originalRequest = { url: '/workshop/customers/', headers: {} }

    await onRejected({ response: { status: 401 }, config: originalRequest })

    expect(mocks.axiosPost).toHaveBeenCalledWith('/api/auth/token/refresh/', { refresh: 'refresh-token' })
    expect(originalRequest.headers.Authorization).toBe('Bearer new-access-token')
    expect(mocks.apiInstance).toHaveBeenCalledWith(originalRequest)
  })
})
