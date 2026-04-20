import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : '/api/v1',
  timeout: 120000, // 2 min – agent can be slow
  headers: { 'Content-Type': 'application/json' },
})

/**
 * Run the full FireReach agent pipeline.
 * @param {{ icp: string, company: string, email: string }} payload
 */
export async function runAgent(payload) {
  const { data } = await api.post('/run-agent', payload)
  return data
}

/**
 * Get session state by ID.
 */
export async function getSession(sessionId) {
  const { data } = await api.get(`/session/${sessionId}`)
  return data
}

/**
 * Get structured logs for a session.
 */
export async function getLogs(sessionId) {
  const { data } = await api.get(`/logs/${sessionId}`)
  return data
}

/**
 * Get all history with pagination.
 * @param {{ limit?: number, offset?: number }} options
 */
export async function getHistory(options = {}) {
  const { limit = 50, offset = 0 } = options
  const { data } = await api.get('/history', { params: { limit, offset } })
  return data
}

/**
 * Get a specific session from history.
 */
export async function getHistoryItem(sessionId) {
  const { data } = await api.get(`/history/${sessionId}`)
  return data
}

/**
 * Search history by company or ICP.
 */
export async function searchHistory(query, limit = 50) {
  const { data } = await api.get('/history/search', { params: { q: query, limit } })
  return data
}

/**
 * Get history statistics.
 */
export async function getHistoryStats() {
  const { data } = await api.get('/history/stats')
  return data
}

/**
 * Delete a session from history.
 */
export async function deleteHistory(sessionId, hard = false) {
  const { data } = await api.delete(`/history/${sessionId}`, { params: { hard } })
  return data
}

export default api
