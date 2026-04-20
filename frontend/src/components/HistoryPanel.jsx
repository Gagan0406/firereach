import { useState, useEffect } from 'react'
import { Clock, Trash2, Search, RotateCcw, Mail } from 'lucide-react'
import { getHistory, deleteHistory, searchHistory, runAgent } from '../utils/api'
import clsx from 'clsx'

export default function HistoryPanel({ onSelectSession, selectedSessionId, onRetry }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [retryingId, setRetryingId] = useState(null)
  const [resendingId, setResendingId] = useState(null)

  // Fetch history on mount
  useEffect(() => {
    loadHistory()
  }, [])

  // Search when query changes
  useEffect(() => {
    if (searchQuery.trim()) {
      handleSearch()
    } else {
      loadHistory()
    }
  }, [searchQuery])

  async function loadHistory() {
    setLoading(true)
    try {
      const { data } = await getHistory({ limit: 100 })
      setSessions(data || [])
    } catch (error) {
      console.error('Failed to load history:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleSearch() {
    if (!searchQuery.trim()) {
      loadHistory()
      return
    }
    setLoading(true)
    try {
      const { data } = await searchHistory(searchQuery, 100)
      setSessions(data || [])
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(sessionId, e) {
    e.stopPropagation()
    if (!window.confirm('Delete this session?')) return

    try {
      await deleteHistory(sessionId, false)
      // Update state immediately without refresh
      setSessions(sessions.filter(s => s.session_id !== sessionId))
    } catch (error) {
      console.error('Delete failed:', error)
      alert('Failed to delete session')
    }
  }

  async function handleRetry(session, e) {
    e.stopPropagation()
    if (!window.confirm(`Retry outreach for ${session.company}?`)) return

    setRetryingId(session.session_id)
    try {
      const result = await runAgent({
        icp: session.icp,
        company: session.company,
        email: session.email,
      })

      // Reload history to show updated status
      await loadHistory()

      // Callback to parent to show the new result
      if (onRetry) onRetry(result)
    } catch (error) {
      console.error('Retry failed:', error)
      alert('Retry failed: ' + error.message)
    } finally {
      setRetryingId(null)
    }
  }

  async function handleResendEmail(session, e) {
    e.stopPropagation()
    if (!window.confirm(`Resend email to ${session.email}?`)) return

    setResendingId(session.session_id)
    try {
      const response = await fetch('/api/v1/resend-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: session.session_id,
          email: session.email,
          subject: session.email_subject,
          body: session.email_body,
        }),
      })

      if (!response.ok) throw new Error('Resend failed')
      const result = await response.json()
      alert('Email resent successfully!')
    } catch (error) {
      console.error('Resend failed:', error)
      alert('Failed to resend email: ' + error.message)
    } finally {
      setResendingId(null)
    }
  }

  const formatStatus = (status) => {
    if (!status) return 'Unknown'
    return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()
  }

  const getStatusColor = (status) => {
    const s = status?.toLowerCase() || ''
    switch (s) {
      case 'complete':
        return 'text-green-400'
      case 'failed':
        return 'text-red-400'
      case 'sending':
      case 'generating':
        return 'text-yellow-400'
      default:
        return 'text-ink-400'
    }
  }

  const getStatusBg = (status) => {
    const s = status?.toLowerCase() || ''
    switch (s) {
      case 'complete':
        return 'bg-green-500/10 border-green-500/30'
      case 'failed':
        return 'bg-red-500/10 border-red-500/30'
      case 'sending':
      case 'generating':
        return 'bg-yellow-500/10 border-yellow-500/30'
      default:
        return 'bg-ink-800/50'
    }
  }

  const totalCount = sessions.length

  return (
    <div className="card p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Clock size={14} className="text-fire-500" />
        <span className="label">History ({totalCount})</span>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-2 top-2.5 text-ink-500" />
        <input
          type="text"
          placeholder="Search company or ICP..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-ink-800 border border-ink-700 rounded px-3 py-2 pl-7 text-xs text-ink-200 placeholder-ink-600 focus:outline-none focus:border-fire-600"
        />
      </div>

      {/* Sessions List */}
      <div className="max-h-96 overflow-y-auto space-y-2 pr-1">
        {loading && (
          <div className="text-xs text-ink-500 text-center py-4">Loading...</div>
        )}

        {!loading && sessions.length === 0 && (
          <div className="text-xs text-ink-600 text-center py-4">
            {searchQuery ? 'No results found' : 'No history yet'}
          </div>
        )}

        {sessions.map((session) => (
          <button
            key={session.session_id}
            onClick={() => onSelectSession(session)}
            className={clsx(
              "w-full text-left p-3 rounded border transition-all",
              selectedSessionId === session.session_id
                ? "border-fire-600 bg-fire-600/10"
                : "border-ink-700 bg-ink-800/30 hover:bg-ink-800/50 hover:border-ink-600"
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="font-mono text-xs text-ink-500">
                    {session.session_id.slice(0, 8)}...
                  </span>
                  <span className={clsx(
                    'text-xs font-semibold px-2 py-1 rounded border',
                    getStatusColor(session.status),
                    getStatusBg(session.status)
                  )}>
                    {formatStatus(session.status)}
                  </span>
                </div>
                <div className="text-sm font-semibold text-ink-200 truncate">
                  {session.company}
                </div>
                <div className="text-xs text-ink-500 truncate">
                  {session.email}
                </div>
                <div className="text-xs text-ink-600 mt-1">
                  {new Date(session.created_at).toLocaleDateString()} {new Date(session.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-1 flex-shrink-0">
                {session.status?.toLowerCase() === 'failed' && (
                  <button
                    onClick={(e) => handleRetry(session, e)}
                    disabled={retryingId === session.session_id}
                    className="p-1.5 hover:bg-yellow-500/20 disabled:opacity-50 rounded text-ink-500 hover:text-yellow-400 transition-colors"
                    title="Retry outreach"
                  >
                    <RotateCcw size={14} />
                  </button>
                )}
                {session.status?.toLowerCase() === 'complete' && session.email_body && (
                  <button
                    onClick={(e) => handleResendEmail(session, e)}
                    disabled={resendingId === session.session_id}
                    className="p-1.5 hover:bg-blue-500/20 disabled:opacity-50 rounded text-ink-500 hover:text-blue-400 transition-colors"
                    title="Resend email"
                  >
                    <Mail size={14} />
                  </button>
                )}
                <button
                  onClick={(e) => handleDelete(session.session_id, e)}
                  className="p-1.5 hover:bg-red-500/20 rounded text-ink-500 hover:text-red-400 transition-colors"
                  title="Delete"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Refresh button */}
      <button
        onClick={loadHistory}
        disabled={loading}
        className="w-full py-2 text-xs bg-fire-600/20 hover:bg-fire-600/30 disabled:opacity-50 text-fire-400 rounded font-mono transition-colors"
      >
        {loading ? 'Loading...' : 'Refresh'}
      </button>
    </div>
  )
}
