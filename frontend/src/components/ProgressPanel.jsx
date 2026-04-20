import { useEffect, useRef } from 'react'
import { CheckCircle, Loader, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

const STAGE_LABELS = {
  started: 'Started',
  validating: 'Validating input',
  harvesting_tavily: 'Searching Tavily',
  harvesting_apify: 'Searching with Apify',
  harvesting_linkedin: 'Extracting LinkedIn data',
  harvesting_twitter: 'Extracting X/Twitter mentions',
  extracting_signals: 'Extracting signals',
  generating_email: 'Generating email',
  quality_check: 'Running quality checks',
  sending_email: 'Sending email',
  completed: 'Completed',
  failed: 'Failed',
}

function StageIcon({ stage, isActive, isCompleted, isFailed }) {
  if (isFailed) {
    return <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
  }
  if (isCompleted) {
    return <CheckCircle className="w-5 h-5 text-emerald-500 flex-shrink-0" />
  }
  if (isActive) {
    return <Loader className="w-5 h-5 text-fire-500 animate-spin flex-shrink-0" />
  }
  return <div className="w-5 h-5 rounded-full border border-ink-600 flex-shrink-0" />
}

export default function ProgressPanel({ events, isStreaming }) {
  const containerRef = useRef(null)
  const lastEventRef = useRef(null)

  // Auto-scroll to latest event
  useEffect(() => {
    if (lastEventRef.current && containerRef.current) {
      lastEventRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [events])

  if (!events || events.length === 0) return null

  // Get unique stages in order
  const stageOrder = [
    'started',
    'validating',
    'harvesting_tavily',
    'harvesting_apify',
    'harvesting_linkedin',
    'harvesting_twitter',
    'extracting_signals',
    'generating_email',
    'quality_check',
    'sending_email',
    'completed',
    'failed',
  ]

  // Track which stages have been seen
  const completedStages = new Set()
  const latestEventPerStage = {}

  events.forEach((event) => {
    if (event.stage) {
      latestEventPerStage[event.stage] = event
      if (event.stage !== 'started' || !isStreaming) {
        completedStages.add(event.stage)
      }
    }
  })

  const currentStage = events[events.length - 1]?.stage
  const hasFailed = events.some((e) => e.stage === 'failed')
  const isComplete = events.some((e) => e.stage === 'completed')

  return (
    <div
      className="card p-5 space-y-3 animate-slide-up max-h-96 overflow-y-auto"
      ref={containerRef}
    >
      <div className="label mb-4">Real-time Progress</div>

      <div className="space-y-2.5">
        {stageOrder.map((stage) => {
          const event = latestEventPerStage[stage]
          if (!event) return null

          const isActive = stage === currentStage && isStreaming
          const isCompleted =
            completedStages.has(stage) && !isActive && !hasFailed
          const isFailed = hasFailed && stage === currentStage

          return (
            <div key={stage} ref={isActive ? lastEventRef : null}>
              <div className="flex items-start gap-3">
                <StageIcon
                  stage={stage}
                  isActive={isActive}
                  isCompleted={isCompleted}
                  isFailed={isFailed}
                />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={clsx(
                        'text-sm font-medium transition-colors',
                        isActive && 'text-fire-400',
                        isCompleted && 'text-emerald-400',
                        isFailed && 'text-red-400',
                        !isActive && !isCompleted && !isFailed && 'text-ink-500'
                      )}
                    >
                      {STAGE_LABELS[stage] || stage}
                    </span>
                    {event.progress !== undefined && (
                      <span className="text-xs text-ink-600">
                        {event.progress}%
                      </span>
                    )}
                  </div>

                  {event.message && (
                    <p className="text-xs text-ink-400 mb-1.5 break-words">
                      {event.message}
                    </p>
                  )}

                  {event.data && Object.keys(event.data).length > 0 && (
                    <div className="text-xs text-ink-500 space-y-0.5 bg-ink-900/50 p-2 rounded">
                      {Object.entries(event.data).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span>{key}:</span>
                          <span className="text-fire-400 font-mono">
                            {typeof value === 'object'
                              ? JSON.stringify(value)
                              : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {event.timestamp && (
                    <p className="text-xs text-ink-700 mt-1.5">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </p>
                  )}
                </div>
              </div>

              {/* Progress bar for active stage */}
              {isActive && event.progress !== undefined && (
                <div className="mt-2 ml-8 h-1 bg-ink-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-fire-500 to-fire-600 transition-all duration-300"
                    style={{ width: `${event.progress}%` }}
                  />
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Completion message */}
      {isComplete && !isStreaming && (
        <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
          <p className="text-xs text-emerald-400 font-mono">
            ✓ All stages completed successfully
          </p>
        </div>
      )}

      {hasFailed && !isStreaming && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-xs text-red-400 font-mono">
            ✗ Process failed. Check error details above.
          </p>
        </div>
      )}
    </div>
  )
}
