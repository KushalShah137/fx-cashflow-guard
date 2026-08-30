import { useState } from "react"
import { MarketSentiment } from "@/types"
import { Newspaper, CheckCircle2, X, ExternalLink } from "lucide-react"

interface LiveNewsFeedProps {
  sentiment: MarketSentiment | null
}

export function LiveNewsFeed({ sentiment }: LiveNewsFeedProps) {
  const headlines = sentiment?.headlines || []
  const [dismissedIndices, setDismissedIndices] = useState<number[]>([])

  const activeHeadlines = headlines.filter((_, idx) => !dismissedIndices.includes(idx))

  const handleDismiss = (originalIdx: number) => {
    setDismissedIndices((prev) => [...prev, originalIdx])
  }

  const handleReset = () => {
    setDismissedIndices([])
  }

  return (
    <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-4 font-mono space-y-4">
      {/* Pinned Quantitative Regime Synthesis Summary Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#E4E2D9] pb-3">
        <div className="flex items-center gap-2">
          <Newspaper className="w-4 h-4 text-[#18181B]" />
          <span className="text-xs font-bold uppercase tracking-wider text-[#18181B]">
            QUANTITATIVE REGIME SYNTHESIS // LIVE TELEMETRY
          </span>
        </div>
        <div className="text-[11px] text-[#71717A] bg-[#F4F3EE] border border-[#E4E2D9] px-2 py-0.5">
          UPDATED: {sentiment?.last_updated ? new Date(sentiment.last_updated).toLocaleTimeString() : "LIVE"}
        </div>
      </div>

      {/* Pinned Synthesis Banner */}
      <div className="bg-[#F4F3EE] border-l-4 border-l-[#18181B] border border-[#E4E2D9] p-3 text-xs">
        <div className="text-[10px] text-[#71717A] font-bold uppercase tracking-wider mb-0.5">
          MACRO REGIME SUMMARY:
        </div>
        <div className="font-bold text-[#18181B]">
          {sentiment?.sentiment_summary || "Cautious on INR due to oil imports; USD resilient"}
        </div>
        <div className="flex items-center gap-4 mt-2 text-[11px] text-[#71717A]">
          <span>DRIFT BIAS: <strong className="text-[#18181B]">+{((sentiment?.drift_adjustment || 0.03) * 100).toFixed(1)} bps</strong></span>
          <span>VOLATILITY MULTIPLIER: <strong className="text-[#18181B]">{(1 + (sentiment?.volatility_adjustment || 0.08)).toFixed(2)}x</strong></span>
        </div>
      </div>

      {/* Headline Cards Stack */}
      {activeHeadlines.length > 0 ? (
        <div className="space-y-2">
          {activeHeadlines.map((headlineText, i) => {
            const originalIdx = headlines.indexOf(headlineText)
            // Color logic: green accent for positive/hike, red for pressure/crash/inflation
            const isNegative = /pressure|crash|inflation|risk|down|lower/i.test(headlineText)
            const accentColor = isNegative ? "border-l-[#B91C1C]" : "border-l-[#047857]"
            const dotColor = isNegative ? "bg-[#B91C1C]" : "bg-[#047857]"

            return (
              <div
                key={originalIdx}
                className={`bg-[#FFFFFF] border border-[#E4E2D9] border-l-4 ${accentColor} p-3 flex items-start justify-between gap-3 transition-all hover:border-[#18181B] group`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-[10px] text-[#71717A]">
                    <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
                    <span className="font-bold text-[#18181B] uppercase">LIVE NEWS FEED</span>
                    <span>•</span>
                    <span>FINNHUB / OLLAMA PIPELINE</span>
                  </div>
                  <p className="text-xs font-semibold text-[#18181B] leading-snug">
                    {headlineText}
                  </p>
                </div>

                <div className="flex items-center gap-1 flex-shrink-0">
                  <button
                    onClick={() => handleDismiss(originalIdx)}
                    className="text-[#71717A] hover:text-[#B91C1C] p-1 transition-colors"
                    title="Dismiss headline"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        /* Empty State: You're all caught up! */
        <div className="bg-[#FFFFFF] border border-[#E4E2D9] p-6 text-center space-y-2">
          <CheckCircle2 className="w-6 h-6 text-[#047857] mx-auto" />
          <div className="text-xs font-bold text-[#18181B]">You're all caught up!</div>
          <p className="text-[11px] text-[#71717A]">
            All macroeconomic news telemetry cards have been reviewed.
          </p>
          <button
            onClick={handleReset}
            className="text-[11px] font-bold text-[#18181B] underline hover:text-[#047857] mt-1"
          >
            Reload headlines feed
          </button>
        </div>
      )}
    </div>
  )
}
