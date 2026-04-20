import { Flame, Zap, Github } from 'lucide-react'
import { useFireReach } from './hooks/useFireReach'
import { useHistory } from './hooks/useHistory'
import InputForm       from './components/InputForm'
import StatusTimeline  from './components/StatusTimeline'
import SignalsPanel    from './components/SignalsPanel'
import ChatHistory     from './components/ChatHistory'
import LoadingSkeleton from './components/LoadingSkeleton'
import HistoryPanel    from './components/HistoryPanel'
import { AccountBrief, EmailPanel } from './components/OutputPanels'
import './styles/globals.css'

function Header() {
  return (
    <header className="border-b border-ink-800 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-fire-600 flex items-center justify-center fire-glow">
          <Flame size={18} className="text-white" />
        </div>
        <div>
          <h1 className="font-display font-bold text-lg text-gradient-fire leading-none">
            FireReach
          </h1>
          <p className="text-xs text-ink-500 font-mono">autonomous outreach AI</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs text-ink-500 font-mono">
          <Zap size={11} className="text-fire-500" />
          Signal → Research → Email → Send
        </div>
      </div>
    </header>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-center py-16">
      <div className="w-16 h-16 rounded-2xl bg-fire-600/10 border border-fire-600/20 flex items-center justify-center">
        <Flame size={28} className="text-fire-600/50" />
      </div>
      <div>
        <p className="text-ink-400 text-sm">Fill in your ICP, company, and email</p>
        <p className="text-ink-600 text-xs mt-1">
          FireReach will harvest signals, research the account, and send a personalized email.
        </p>
      </div>
    </div>
  )
}

export default function App() {
  const { form, handleChange, result, loading, errors, handleRun, handleReset } = useFireReach()
  const { selectedSession, historyLoading, loadSessionFromHistory, clearSelection } = useHistory()

  const hasResults = result.status !== 'idle'
  const displayResult = selectedSession || result

  async function handleSelectFromHistory(session) {
    await loadSessionFromHistory(session.session_id)
  }

  function handleNewOutreach() {
    clearSelection()
    handleReset()
  }

  return (
    <div className="min-h-screen bg-ink-900 text-ink-100 flex flex-col">
      <Header />

      <main className="flex-1 flex overflow-hidden">
        {/* Left panel — Input & History */}
        <aside className="w-96 flex-shrink-0 border-r border-ink-800 overflow-y-auto p-5 space-y-4">
          {/* Subtitle */}
          <div className="space-y-1">
            <h2 className="font-display text-xl font-bold text-ink-100">
              Launch an outreach
            </h2>
            <p className="text-sm text-ink-500">
              Provide your ICP and target. The agent does the rest.
            </p>
          </div>

          <InputForm
            form={form}
            onChange={handleChange}
            errors={errors}
            onRun={handleRun}
            onReset={handleNewOutreach}
            loading={loading}
          />

          {/* History Panel */}
          <HistoryPanel
            onSelectSession={handleSelectFromHistory}
            selectedSessionId={selectedSession?.session_id}
            onRetry={(result) => {
              // Show the new result when retry completes
              window.location.reload()
            }}
          />

          {/* How it works */}
          <div className="card p-4 space-y-2.5">
            <div className="label">How It Works</div>
            {[
              { step: "01", label: "Signal Harvesting",  desc: "Apify + Tavily gather live company signals" },
              { step: "02", label: "Research Analysis",  desc: "Groq LLM writes a grounded account brief" },
              { step: "03", label: "Email Generation",   desc: "Hyper-personalized email from real signals" },
              { step: "04", label: "Automated Send",     desc: "Delivered via SendGrid" },
            ].map(({ step, label, desc }) => (
              <div key={step} className="flex gap-3 items-start">
                <span className="font-mono text-xs text-fire-600 flex-shrink-0 mt-0.5">{step}</span>
                <div>
                  <p className="text-xs font-medium text-ink-300">{label}</p>
                  <p className="text-xs text-ink-600">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Right panel — Results */}
        <section className="flex-1 overflow-y-auto p-5 space-y-4">
          {selectedSession && (
            <div className="card p-3 bg-fire-600/10 border border-fire-600/30 flex items-center justify-between">
              <span className="text-sm text-fire-300">Viewing history: {selectedSession.company}</span>
              <button
                onClick={handleNewOutreach}
                className="text-xs px-3 py-1 bg-fire-600/30 hover:bg-fire-600/50 text-fire-300 rounded transition-colors"
              >
                New Outreach
              </button>
            </div>
          )}

          {!displayResult && !loading && !selectedSession && <EmptyState />}

          {(loading || historyLoading) && <LoadingSkeleton />}

          {!loading && !historyLoading && displayResult && (
            <>
              <StatusTimeline status={displayResult.status} error={displayResult.error} />
              <SignalsPanel   signals={displayResult.signals} />
              <ChatHistory    messages={displayResult.chat_history} />
              <AccountBrief   brief={displayResult.research_brief} />
              <EmailPanel     subject={displayResult.email_subject} body={displayResult.email_body} />
            </>
          )}
        </section>
      </main>
    </div>
  )
}
