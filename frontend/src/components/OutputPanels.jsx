import { FileText, Mail, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

// ---------------------------------------------------------------------------
// Copy button
// ---------------------------------------------------------------------------
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }
  return (
    <button
      onClick={handleCopy}
      className={clsx(
        "p-1.5 rounded-lg border transition-all text-xs",
        copied
          ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10"
          : "border-ink-600 text-ink-400 hover:text-ink-200 hover:border-ink-500",
      )}
    >
      {copied ? <Check size={13} /> : <Copy size={13} />}
    </button>
  )
}

// ---------------------------------------------------------------------------
// Account Brief
// ---------------------------------------------------------------------------
export function AccountBrief({ brief }) {
  if (!brief) return null
  return (
    <div className="card p-5 space-y-3 animate-slide-up">
      <div className="flex items-center gap-2">
        <FileText size={14} className="text-fire-500" />
        <span className="label">Account Brief</span>
      </div>
      <div className="prose prose-sm max-w-none">
        {brief.split('\n').filter(Boolean).map((para, i) => (
          <p key={i} className="text-sm text-ink-200 leading-relaxed mb-2">{para}</p>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Generated Email
// ---------------------------------------------------------------------------
export function EmailPanel({ subject, body }) {
  if (!subject && !body) return null
  const fullText = `Subject: ${subject}\n\n${body}`

  return (
    <div className="card p-5 space-y-4 animate-slide-up border-fire-500/20">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Mail size={14} className="text-fire-500" />
          <span className="label">Generated Email</span>
        </div>
        <CopyButton text={fullText} />
      </div>

      {subject && (
        <div className="p-3 bg-ink-900 rounded-xl border border-ink-700">
          <div className="label text-xs mb-1">Subject</div>
          <p className="text-sm text-ink-100 font-medium">{subject}</p>
        </div>
      )}

      {body && (
        <div className="p-4 bg-ink-900 rounded-xl border border-ink-700 space-y-3">
          <div className="label text-xs mb-1">Body</div>
          {body.split('\n').filter(Boolean).map((line, i) => (
            <p key={i} className="text-sm text-ink-200 leading-relaxed">{line}</p>
          ))}
        </div>
      )}
    </div>
  )
}
