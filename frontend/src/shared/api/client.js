const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || '/api'

const readErrorMessage = async (response) => {
  const fallback = `요청을 처리하지 못했습니다. (${response.status})`

  try {
    const data = await response.json()
    return data.message || data.error || fallback
  } catch {
    return fallback
  }
}

const request = async (path, options = {}) => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

export const authApi = {
  signup: (payload) => request('/auth/signup', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  login: (payload) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  logout: () => request('/auth/logout', {
    method: 'POST',
  }),
  me: () => request('/auth/me'),
}

export const startupProfileApi = {
  status: () => request('/profile/status'),
  get: () => request('/profile'),
  save: (payload) => request('/profile', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
}

export const savedResultApi = {
  list: () => request('/saved-results'),
  latest: (sourceFeature) => request(`/saved-results/latest?sourceFeature=${encodeURIComponent(sourceFeature)}`),
  get: (savedResultId) => request(`/saved-results/${savedResultId}`),
  save: (payload) => request('/saved-results', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
}

export const operationFeedbackApi = {
  save: (payload) => request('/operation-feedback', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
}

export const workspaceApi = {
  list: () => request('/workspaces'),
  create: (payload = {}) => request('/workspaces', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  update: (workspaceId, payload) => request(`/workspaces/${workspaceId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }),
}

export const supportProgramApi = {
  recommend: (payload) => request('/support-programs/recommend', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
}

export const threadsApi = {
  account: () => request('/sns/threads/account'),
  connectUrl: () => request('/sns/threads/connect-url'),
  publish: (payload) => request('/sns/threads/publish', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  logs: () => request('/sns/threads/logs'),
}
