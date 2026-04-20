import { MessageSquare } from 'lucide-react'
import clsx from 'clsx'

const ROLE_STYLES = {
  system:    "text-ink-400",
  assistant: "text-fire-300",
  user:      "text-ink-200",
}

const ROLE_LABELS = {
  system:    "System",
  assistant: "FireReach",
  user:      "User",
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function parseMarkdown(text) {
  // Escape HTML first to prevent XSS, then apply inline bold/italic
  const escaped = escapeHtml(text)
  return escaped
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
}

export default function ChatHistory({ messages }) {
  if (!messages || messages.length === 0) return null

  return (
    <div className="card p-5 space-y-3 animate-slide-up">
      <div className="flex items-center gap-2">
        <MessageSquare size={14} className="text-fire-500" />
        <span className="label">Agent Log ({messages.length})</span>
      </div>
      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {messages.map((msg, i) => (
          <div
            key={i}
            className="flex gap-2 text-sm animate-fade-in"
            style={{ animationDelay: `${i * 30}ms` }}
          >
            <span className={clsx("font-mono text-xs w-20 flex-shrink-0 pt-0.5", ROLE_STYLES[msg.role] || "text-ink-400")}>
              [{ROLE_LABELS[msg.role] || msg.role}]
            </span>
            <span
              className="text-ink-300 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: parseMarkdown(msg.content) }}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
