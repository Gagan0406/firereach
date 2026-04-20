import { Radio, TrendingUp, Users, Cpu, DollarSign, MessageSquare, Zap } from 'lucide-react'
import clsx from 'clsx'

const SIGNAL_ICONS = {
  funding:    DollarSign,
  hiring:     Users,
  leadership: Users,
  tech_stack: Cpu,
  social:     MessageSquare,
  growth:     TrendingUp,
}

const SIGNAL_COLORS = {
  funding:    "text-amber-400 bg-amber-400/10 border-amber-400/20",
  hiring:     "text-blue-400 bg-blue-400/10 border-blue-400/20",
  leadership: "text-purple-400 bg-purple-400/10 border-purple-400/20",
  tech_stack: "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
  social:     "text-pink-400 bg-pink-400/10 border-pink-400/20",
  growth:     "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
}

function SignalBadge({ type }) {
  const Icon = SIGNAL_ICONS[type] || Zap
  const colors = SIGNAL_COLORS[type] || "text-ink-300 bg-ink-700 border-ink-600"
  return (
    <span className={clsx("inline-flex items-center gap-1 text-xs font-mono uppercase px-2 py-0.5 rounded-full border", colors)}>
      <Icon size={10} />
      {type}
    </span>
  )
}

export default function SignalsPanel({ signals }) {
  const signalList = signals?.signals || []
  const snippets   = signals?.raw_snippets || []

  if (!signalList.length && !snippets.length) return null

  return (
    <div className="card p-5 space-y-4 animate-slide-up">
      <div className="flex items-center gap-2">
        <Radio size={14} className="text-fire-500" />
        <span className="label">Live Signals ({signalList.length})</span>
      </div>

      {signalList.length > 0 ? (
        <div className="space-y-3">
          {signalList.map((signal, i) => (
            <div
              key={i}
              className="p-3 bg-ink-900 rounded-xl border border-ink-700 space-y-2 animate-fade-in"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div className="flex items-start justify-between gap-2">
                <SignalBadge type={signal.signal_type} />
                {signal.grounded && (
                  <span className="text-xs text-emerald-500/70 font-mono">● grounded</span>
                )}
              </div>
              <p className="text-sm text-ink-200 leading-relaxed">{signal.description}</p>
              {signal.source && signal.source !== 'Tavily search' && (
                <a
                  href={signal.source.startsWith('http') ? signal.source : '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-ink-500 hover:text-fire-400 transition-colors font-mono truncate block"
                >
                  {signal.source.length > 60 ? signal.source.slice(0, 60) + '...' : signal.source}
                </a>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-ink-500 italic">No structured signals extracted yet.</p>
      )}
    </div>
  )
}
