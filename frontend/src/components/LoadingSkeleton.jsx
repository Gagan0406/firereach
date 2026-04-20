export default function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-fade-in">
      {/* Status skeleton */}
      <div className="card p-5 space-y-3">
        <div className="shimmer-line h-3 w-24" />
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="shimmer-line w-5 h-5 rounded-full" />
            <div className="shimmer-line h-3 flex-1" style={{ maxWidth: `${60 + i * 10}%` }} />
          </div>
        ))}
      </div>

      {/* Signals skeleton */}
      <div className="card p-5 space-y-3">
        <div className="shimmer-line h-3 w-32" />
        {[...Array(3)].map((_, i) => (
          <div key={i} className="p-3 bg-ink-900 rounded-xl border border-ink-700 space-y-2">
            <div className="shimmer-line h-4 w-20 rounded-full" />
            <div className="shimmer-line h-3 w-full" />
            <div className="shimmer-line h-3 w-4/5" />
          </div>
        ))}
      </div>
    </div>
  )
}
