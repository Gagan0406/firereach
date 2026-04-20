import { Target, Mail, Users, Flame, RotateCcw } from 'lucide-react'
import clsx from 'clsx'

const Field = ({ label, icon: Icon, error, children }) => (
  <div className="space-y-1.5">
    <label className="label flex items-center gap-1.5">
      <Icon size={11} className="text-fire-500" />
      {label}
    </label>
    {children}
    {error && (
      <p className="text-xs text-red-400 font-mono animate-fade-in">{error}</p>
    )}
  </div>
)

export default function InputForm({ form, onChange, errors, onRun, onReset, loading }) {
  return (
    <div className="card p-6 space-y-5 animate-slide-up">
      {/* Header */}
      <div className="flex items-center gap-3 pb-1 border-b border-ink-700">
        <div className="w-8 h-8 rounded-lg bg-fire-600/20 border border-fire-600/30 flex items-center justify-center">
          <Flame size={16} className="text-fire-500" />
        </div>
        <div>
          <h2 className="font-display font-semibold text-sm text-ink-100">Launch Outreach</h2>
          <p className="text-xs text-ink-400">Fill in your target details below</p>
        </div>
      </div>

      {/* ICP */}
      <Field label="Ideal Customer Profile" icon={Users} error={errors.icp}>
        <textarea
          rows={3}
          value={form.icp}
          onChange={e => onChange('icp', e.target.value)}
          placeholder="We sell high-end cybersecurity training to Series B startups..."
          disabled={loading}
          className={clsx(
            "w-full bg-ink-900 border rounded-xl px-4 py-3 text-sm text-ink-100",
            "placeholder:text-ink-600 resize-none font-body",
            "focus:outline-none focus:ring-1 transition-all",
            errors.icp
              ? "border-red-500/60 focus:ring-red-500/30"
              : "border-ink-700 focus:ring-fire-500/40 focus:border-fire-500/50",
            loading && "opacity-50 cursor-not-allowed",
          )}
        />
      </Field>

      {/* Company */}
      <Field label="Target Company" icon={Target} error={errors.company}>
        <input
          type="text"
          value={form.company}
          onChange={e => onChange('company', e.target.value)}
          placeholder="Acme Corp, OpenAI, Stripe..."
          disabled={loading}
          className={clsx(
            "w-full bg-ink-900 border rounded-xl px-4 py-3 text-sm text-ink-100",
            "placeholder:text-ink-600 font-body",
            "focus:outline-none focus:ring-1 transition-all",
            errors.company
              ? "border-red-500/60 focus:ring-red-500/30"
              : "border-ink-700 focus:ring-fire-500/40 focus:border-fire-500/50",
            loading && "opacity-50 cursor-not-allowed",
          )}
        />
      </Field>

      {/* Email */}
      <Field label="Target Email" icon={Mail} error={errors.email}>
        <input
          type="email"
          value={form.email}
          onChange={e => onChange('email', e.target.value)}
          placeholder="cto@target.com"
          disabled={loading}
          className={clsx(
            "w-full bg-ink-900 border rounded-xl px-4 py-3 text-sm text-ink-100",
            "placeholder:text-ink-600 font-mono",
            "focus:outline-none focus:ring-1 transition-all",
            errors.email
              ? "border-red-500/60 focus:ring-red-500/30"
              : "border-ink-700 focus:ring-fire-500/40 focus:border-fire-500/50",
            loading && "opacity-50 cursor-not-allowed",
          )}
        />
      </Field>

      {/* Actions */}
      <div className="flex gap-3 pt-1">
        <button
          onClick={onRun}
          disabled={loading}
          className={clsx(
            "flex-1 flex items-center justify-center gap-2",
            "bg-fire-600 hover:bg-fire-500 active:bg-fire-700",
            "text-white font-display font-semibold text-sm",
            "rounded-xl py-3 px-5 transition-all duration-200",
            "fire-glow",
            loading && "opacity-60 cursor-not-allowed",
            !loading && "hover:scale-[1.01] active:scale-[0.99]",
          )}
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Running Agent...
            </>
          ) : (
            <>
              <Flame size={16} />
              Fire Outreach
            </>
          )}
        </button>
        <button
          onClick={onReset}
          disabled={loading}
          title="Reset"
          className={clsx(
            "p-3 rounded-xl border border-ink-700 text-ink-400",
            "hover:border-ink-600 hover:text-ink-200 transition-all",
            loading && "opacity-40 cursor-not-allowed",
          )}
        >
          <RotateCcw size={16} />
        </button>
      </div>
    </div>
  )
}
