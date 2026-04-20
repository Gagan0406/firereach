import { useState } from 'react'
import { getHistoryItem } from '../utils/api'

export function useHistory() {
  const [selectedSession, setSelectedSession] = useState(null)
  const [historyLoading, setHistoryLoading] = useState(false)

  async function loadSessionFromHistory(sessionId) {
    setHistoryLoading(true)
    try {
      const { data } = await getHistoryItem(sessionId)
      setSelectedSession(data)
      return data
    } catch (error) {
      console.error('Failed to load session:', error)
      return null
    } finally {
      setHistoryLoading(false)
    }
  }

  function clearSelection() {
    setSelectedSession(null)
  }

  return {
    selectedSession,
    historyLoading,
    loadSessionFromHistory,
    clearSelection,
  }
}
