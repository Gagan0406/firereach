import clsx from 'clsx'
import { CheckCircle, Circle, XCircle, Loader } from 'lucide-react'

const STEPS = [
  { key: 'validating',  label: 'Input Validation' },
  { key: 'harvesting',  label: 'Signal Harvesting' },
  { key: 'researching', label: 'Research Analysis' },
  { key: 'generating',  label: 'Email Generation' },
  { key: 'sending',     label: 'Sending Email' },
  { key: 'complete',    label: 'Complete' },
]

const STATUS_ORDER = ['initialized', 'validating', 'harvesting', 'researching', 'generating', 'sending', 'complete']

function getStepState(stepKey, currentStatus, isFailed) {
  if (isFailed) {
    const failedIdx  = STATUS_ORDER.indexOf(currentStatus)
    const stepIdx    = STATUS_ORDER.indexOf(stepKey)
    if (stepIdx < failedIdx)  return 'done'
    if (stepIdx === failedIdx) return 'error'
    return 'idle'
  }

  if (currentStatus === 'complete') return 'done'

  const currentIdx = STATUS_ORDER.indexOf(currentStatus)
  const stepIdx    = STATUS_ORDER.indexOf(stepKey)

  if (stepIdx < currentIdx) return 'done'
  if (stepIdx === currentIdx) return 'active'
  return 'idle'
}

const StepIcon = ({ state }) => {
  const baseClass = "w-5 h-5 flex-shrink-0"

  switch(state) {
    case 'done':
      return <CheckCircle className={`${baseClass} text-green-400 stroke-2`} />
    case 'active':
      return <Loader className={`${baseClass} text-fire-500 animate-spin stroke-2`} />
    case 'error':
      return <XCircle className={`${baseClass} text-red-500 stroke-2`} />
    default:
      return <Circle className={`${baseClass} text-ink-500 stroke-1`} />
  }
}

export default function StatusTimeline({ status, error }) {
  if (!status || status === 'idle') return null

  const isFailed = status === 'failed'
  const isRunning = status === 'running'

  return (
    <div className="card p-5 space-y-1 animate-slide-up">
      <div className="label mb-3">Execution Status</div>

      <div className="space-y-2">
        {STEPS.map((step, i) => {
          const state = isRunning ? 'idle' : getStepState(step.key, status, isFailed)
          return (
            <div key={step.key} className="flex items-center gap-3">
              <StepIcon state={state} />
              <span className={clsx(
                "text-sm font-body transition-colors",
                state === 'done'   && "text-ink-300",
                state === 'active' && "text-fire-400 font-medium",
                state === 'error'  && "text-red-400",
                state === 'idle'   && "text-ink-600",
              )}>
                {step.label}
              </span>
            </div>
          )
        })}
      </div>

      {isFailed && error && (
        <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
          <p className="text-xs text-red-400 font-mono">{error}</p>
        </div>
      )}

      {status === 'complete' && (
        <div className="mt-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
          <p className="text-xs text-emerald-400 font-mono">✓ Outreach complete</p>
        </div>
      )}
    </div>
  )
}
