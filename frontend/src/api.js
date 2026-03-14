const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  runTask: (task) =>
    request('/tasks', { method: 'POST', body: JSON.stringify({ task }) }),

  listTasks: (limit = 50) =>
    request(`/tasks?limit=${limit}`),

  getTask: (id) =>
    request(`/tasks/${id}`),

  deleteTask: (id) =>
    request(`/tasks/${id}`, { method: 'DELETE' }),

  listTools: () =>
    request('/tools'),

  health: () =>
    request('/health'),
}
