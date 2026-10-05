import axios from 'axios'
import { token } from './session'

export const API_URL = (import.meta.env.VITE_API_URL || 'https://frog02-20689.wykr.es/api').replace(/\/+$/, '')

const http = axios.create({ baseURL: API_URL, timeout: 15000 })

http.interceptors.request.use((config) => {
  if (token.value && config.url.startsWith('/admin')) {
    config.headers.Authorization = `Bearer ${token.value}`
  }
  return config
})

export function errorMessage(error, fallback = 'Coś poszło nie tak') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (!error?.response) return 'Brak połączenia z serwerem'
  return fallback
}

export function isUnauthorized(error) {
  return error?.response?.status === 401
}

const data = (promise) => promise.then((r) => r.data)

export const api = {
  search: (query) => data(http.get('/search', { params: { query } })),
  live: () => data(http.get('/live')),
  submit: (videoId) => data(http.post('/requests', { videoId })),
  lookup: (items) => data(http.post('/requests/lookup', { items })),
  cancel: (id, ticket) => data(http.delete(`/requests/${id}`, { params: { ticket } })),

  login: (username, password) => data(http.post('/login', { username, password })),
  me: () => data(http.get('/admin/me')),
  submissions: (status = 'pending') => data(http.get('/admin/submissions', { params: { status } })),
  accept: (ids) => data(http.post('/admin/submissions/accept', { ids })),
  reject: (ids) => data(http.post('/admin/submissions/reject', { ids })),
  queue: () => data(http.get('/admin/queue')),
  reorder: (ids) => data(http.post('/admin/queue/order', { ids })),
  played: (id) => data(http.post(`/admin/queue/${id}/played`)),
  remove: (id) => data(http.delete(`/admin/queue/${id}`)),
  clear: () => data(http.delete('/admin/queue')),
  player: (payload) => data(http.post('/admin/player', payload)),
}

// Przy zamykaniu karty axios nie zdąży, fetch z keepalive tak.
export function reportPlayerOnExit(payload) {
  if (!token.value) return
  try {
    fetch(`${API_URL}/admin/player`, {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token.value}` },
      body: JSON.stringify(payload),
    })
  } catch {
    // trudno, serwer sam uzna radio za wyłączone po chwili
  }
}
