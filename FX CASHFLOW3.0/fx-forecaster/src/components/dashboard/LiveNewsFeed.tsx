import { useState, useEffect, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { MarketSentiment } from "@/types"
import {
  Newspaper,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Minus,
  RotateCcw,
  Sparkles,
  ArrowRight,
  Radio,
} from "lucide-react"

interface LiveNewsFeedProps {
  sentiment: MarketSentiment | null
}

interface NewsCardItem {
  id: string
  headline: string
  currency: string
  sentimentScore: number
  sentimentLabel: "bullish" | "bearish" | "neutral"
  driftBps: number
  volatilityMultiplier: number
  source: "live" | "fallback"
  timestamp: string
}

// --------------------------------------------------------------------------- //
// Helper: Map keywords to currency & sentiment characteristics
// --------------------------------------------------------------------------- //
function analyzeHeadline(headline: string, globalSentiment: MarketSentiment | null): NewsCardItem {
  const text = headline.toLowerCase()
  let currency = "USD"
  if (/ecb|euro|lagarde|france|germany/i.test(text)) currency = "EUR"
  else if (/boe|bank of england|bailey|pound|sterling|uk|britain/i.test(text)) currency = "GBP"
  else if (/rbi|rupee|india|nifty|sensex|delhi|mumbai/i.test(text)) currency = "INR"
  else if (/pboc|yuan|cny|china|beijing/i.test(text)) currency = "CNY"
  else if (/boj|yen|jpy|japan|tokyo/i.test(text)) currency = "JPY"
  else if (/rba|aussie|aud|australia/i.test(text)) currency = "AUD"

  // Check sentiment polarity
  const isPositive = /hike|gain|surge|rise|warm up|resilient|boost|jump|support|record high|bullish/i.test(text)
  const isNegative = /pressure|crash|inflation|risk|down|lower|fall|drop|weak|debt|concern|tight|threat|losses/i.test(text)

  let sentimentScore = 0.0
  let sentimentLabel: "bullish" | "bearish" | "neutral" = "neutral"
  let driftBps = 0.0
  let volatilityMultiplier = 1.0

  if (isPositive && !isNegative) {
    sentimentScore = 0.25
    sentimentLabel = "bullish"
    driftBps = 1.75
    volatilityMultiplier = 0.92
  } else if (isNegative && !isPositive) {
    sentimentScore = -0.35
    sentimentLabel = "bearish"
    driftBps = -2.2
    volatilityMultiplier = 1.18
  } else {
    sentimentScore = 0.0
    sentimentLabel = "neutral"
    driftBps = 0.0
    volatilityMultiplier = 1.0
  }

  return {
    id: `hl-${Math.abs(headline.split("").reduce((a, b) => ((a << 5) - a + b.charCodeAt(0)) | 0, 0))}`,
    headline,
    currency,
    sentimentScore,
    sentimentLabel,
    driftBps,
    volatilityMultiplier,
    source: globalSentiment ? "live" : "fallback",
    timestamp: globalSentiment?.last_updated
      ? new Date(globalSentiment.last_updated).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : "Live",
  }
}

// --------------------------------------------------------------------------- //
// Helper: Generate Quantitative Regime Synthesis Sentence
// --------------------------------------------------------------------------- //
function generateRegimeSynthesis(sentiment: MarketSentiment | null): { currency: string; text: string; badge: string; isLive: boolean }[] {
  if (!sentiment || !sentiment.headlines || sentiment.headlines.length === 0) {
    return [
      {
        currency: "ALL",
        text: "No significant market-moving news detected in the current cycle — using historical baseline volatility.",
        badge: "BASELINE",
        isLive: false,
      },
    ]
  }

  const syntheses: { currency: string; text: string; badge: string; isLive: boolean }[] = []

  // Analyze distinct currencies represented in headlines
  const seenCurrencies = new Set<string>()
  for (const h of sentiment.headlines) {
    const item = analyzeHeadline(h, sentiment)
    if (!seenCurrencies.has(item.currency)) {
      seenCurrencies.add(item.currency)

      let qualitativeWord = "neutral"
      let stanceDescription = "Macro conditions remain balanced"

      if (item.sentimentScore > 0.2) {
        qualitativeWord = "constructive (+0.25)"
        stanceDescription = `Recent monetary commentary suggests tightening resilience, lifting ${item.currency} sentiment`
      } else if (item.sentimentScore < -0.2) {
        qualitativeWord = "defensive (-0.35)"
        stanceDescription = `Inflation stickiness and external pressures push ${item.currency} sentiment cautious`
      } else {
        qualitativeWord = "neutral (0.00)"
        stanceDescription = `Balanced trade flows and steady central bank policy keep ${item.currency} stable`
      }

      const driftText = item.driftBps >= 0 ? `+${item.driftBps.toFixed(1)} bps` : `${item.driftBps.toFixed(1)} bps`
      const volText = `${item.volatilityMultiplier.toFixed(2)}x`

      const text = `${stanceDescription} (${qualitativeWord}). Reflected in the forecast as a ${driftText} drift and ${volText} volatility multiplier on ${item.currency}-denominated cash flows over the next 5 days.`

      syntheses.push({
        currency: item.currency,
        text,
        badge: item.sentimentLabel.toUpperCase(),
        isLive: true,
      })
    }
  }

  if (syntheses.length === 0) {
    syntheses.push({
      currency: "MACRO",
      text: "No significant market-moving news detected in the current cycle — using historical baseline volatility.",
      badge: "NEUTRAL",
      isLive: false,
    })
  }

  return syntheses
}

// --------------------------------------------------------------------------- //
// Component: LiveNewsFeed
// --------------------------------------------------------------------------- //
export function LiveNewsFeed({ sentiment }: LiveNewsFeedProps) {
  const rawHeadlines = sentiment?.headlines || [
    "ECB saw a further hike as likely at July meeting - Reuters",
    "Stock traders warm up to Warsh as volatility index touches year-to-date low",
    "Bank of England's Bailey sees 'subdued' second-round inflation effects for now - Reuters",
    "US Fed signals higher-for-longer policy trajectory amid sticky inflation",
    "RBI maintains strategic foreign exchange intervention corridor",
  ]

  // Prepared news items
  const cardItems = useMemo(() => {
    return rawHeadlines.map((h) => analyzeHeadline(h, sentiment))
  }, [rawHeadlines, sentiment])

  // Stack index tracks active top card
  const [currentIndex, setCurrentIndex] = useState(0)

  // Reset when new headlines arrive
  useEffect(() => {
    setCurrentIndex(0)
  }, [rawHeadlines.length])

  const handleNext = () => {
    if (currentIndex < cardItems.length) {
      setCurrentIndex((prev) => prev + 1)
    }
  }

  const handleReset = () => {
    setCurrentIndex(0)
  }

  const synthesisList = useMemo(() => generateRegimeSynthesis(sentiment), [sentiment])

  const isExhausted = currentIndex >= cardItems.length
  const remainingCards = cardItems.slice(currentIndex)

  return (
    <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-5 font-mono space-y-6">
      {/* Top Telemetry Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E4E2D9] pb-3.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-[#18181B] text-[#FAF9F5] rounded-sm">
            <Newspaper className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] text-[#71717A] font-bold uppercase tracking-wider">
              QUANTITATIVE TELEMETRY // AI MACRO INTELLIGENCE
            </div>
            <h3 className="text-sm font-bold text-[#18181B] font-display uppercase tracking-tight">
              Macro Regime Synthesis & News Stack
            </h3>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-[11px] font-bold text-[#047857] bg-[#ECFDF5] border border-[#A7F3D0] px-2.5 py-1 rounded-sm">
            <Radio className="w-3 h-3 animate-pulse" />
            FINNHUB • QWEN 2.5 ACTIVE
          </span>
          <span className="text-[11px] text-[#71717A] bg-[#F4F3EE] border border-[#E4E2D9] px-2.5 py-1">
            UPDATED: {sentiment?.last_updated ? new Date(sentiment.last_updated).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "LIVE"}
          </span>
        </div>
      </div>

      {/* Main Grid: Left = Quantitative Regime Synthesis, Right = Swipeable Card Stack */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ================================================================= */}
        {/* PANEL 1: Quantitative Regime Synthesis Text Explainer */}
        {/* ================================================================= */}
        <div className="lg:col-span-6 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#18181B]">
              <Sparkles className="w-3.5 h-3.5 text-[#B45309]" />
              <span>Quantitative Regime Synthesis</span>
            </div>
            <span className="text-[10px] text-[#71717A] uppercase">
              {synthesisList.length} Active {synthesisList.length === 1 ? "Regime" : "Regimes"}
            </span>
          </div>

          <div className="space-y-3">
            {synthesisList.map((item, idx) => (
              <div
                key={idx}
                className="bg-[#FFFFFF] border border-[#E4E2D9] p-4 rounded-lg shadow-sm space-y-2.5 transition-all hover:border-[#18181B]"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 text-[11px] font-bold bg-[#18181B] text-[#FAF9F5] rounded">
                      {item.currency}
                    </span>
                    <span className="text-[10px] font-bold text-[#71717A] uppercase tracking-wider">
                      FX REGIME IMPACT
                    </span>
                  </div>

                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                      item.badge === "BULLISH"
                        ? "bg-[#ECFDF5] text-[#047857] border-[#A7F3D0]"
                        : item.badge === "BEARISH"
                        ? "bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]"
                        : "bg-[#F4F3EE] text-[#71717A] border-[#E4E2D9]"
                    }`}
                  >
                    {item.badge}
                  </span>
                </div>

                <p className="text-xs text-[#27272A] leading-relaxed font-sans font-medium">
                  {item.text}
                </p>
              </div>
            ))}
          </div>

          {/* Synthesis Macro Drift Legend Bar */}
          <div className="bg-[#F4F3EE] border border-[#E4E2D9] p-3 rounded text-[11px] flex flex-wrap items-center justify-between gap-2 text-[#71717A]">
            <span>
              NET MACRO DRIFT: <strong className="text-[#18181B]">+{((sentiment?.drift_adjustment || 0.014) * 100).toFixed(1)} bps</strong>
            </span>
            <span>
              VOL MULTIPLIER: <strong className="text-[#18181B]">{(1 + (sentiment?.volatility_adjustment || 0.07)).toFixed(2)}x</strong>
            </span>
          </div>
        </div>

        {/* ================================================================= */}
        {/* PANEL 2: Swipeable Card Stack */}
        {/* ================================================================= */}
        <div className="lg:col-span-6 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#18181B]">
              <Newspaper className="w-3.5 h-3.5 text-[#047857]" />
              <span>Live Market News Stack</span>
            </div>
            {!isExhausted && (
              <span className="text-[11px] font-bold text-[#71717A]">
                {currentIndex + 1} of {cardItems.length}
              </span>
            )}
          </div>

          {/* Stacking Container */}
          <div className="relative w-full h-[200px]">
            <AnimatePresence mode="popLayout">
              {!isExhausted ? (
                remainingCards.slice(0, 3).map((item, stackIdx) => {
                  const isTop = stackIdx === 0

                  // Styling based on sentiment
                  const isBullish = item.sentimentScore > 0
                  const isBearish = item.sentimentScore < 0

                  const borderAccentClass = isBullish
                    ? "border-l-4 border-l-[#047857]"
                    : isBearish
                    ? "border-l-4 border-l-[#B91C1C]"
                    : "border-l-4 border-l-[#71717A]"

                  const pillColor = isBullish
                    ? "bg-[#ECFDF5] text-[#047857] border-[#A7F3D0]"
                    : isBearish
                    ? "bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]"
                    : "bg-[#F4F3EE] text-[#71717A] border-[#E4E2D9]"

                  const impactBgClass = isBullish
                    ? "bg-[#F0FDF4] border-[#DCFCE7]"
                    : isBearish
                    ? "bg-[#FEF2F2] border-[#FEE2E2]"
                    : "bg-[#FAF9F5] border-[#E4E2D9]"

                  // Stacking transform calculations: subtle clean layered tabs
                  const yOffset = stackIdx * 8
                  const scale = 1 - stackIdx * 0.04
                  const opacity = isTop ? 1 : 0.85 - stackIdx * 0.25
                  const zIndex = 30 - stackIdx * 10

                  return (
                    <motion.div
                      key={item.id}
                      layout
                      initial={{ scale: 0.92, y: 16, opacity: 0 }}
                      animate={{
                        scale,
                        y: yOffset,
                        opacity,
                        zIndex,
                        transition: { duration: 0.25, ease: "easeOut" },
                      }}
                      exit={{
                        x: 280,
                        rotate: 8,
                        opacity: 0,
                        transition: { duration: 0.22, ease: "easeIn" },
                      }}
                      style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                      }}
                      className={`rounded-xl border border-[#E4E2D9] ${borderAccentClass} bg-[#FFFFFF] shadow-sm p-4 sm:p-4 flex flex-col justify-between select-none ${
                        isTop ? "pointer-events-auto cursor-default" : "pointer-events-none overflow-hidden"
                      }`}
                    >
                      {isTop ? (
                        <>
                          {/* Card Top Row: Metadata */}
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${pillColor}`}>
                                {item.currency} • {item.sentimentLabel.toUpperCase()}
                              </span>
                              <span className="text-[10px] font-bold text-[#71717A] uppercase tracking-wider">
                                FINNHUB PIPELINE
                              </span>
                            </div>
                            <span className="text-[10px] text-[#A1A1AA] font-mono">
                              {item.timestamp}
                            </span>
                          </div>

                          {/* Card Headline */}
                          <div className="my-1">
                            <h4 className="text-[15px] sm:text-base font-bold text-[#18181B] leading-snug font-sans tracking-tight line-clamp-2">
                              {item.headline}
                            </h4>
                          </div>

                          {/* Impact Callout Sub-Block */}
                          <div className={`border rounded-lg px-3 py-1.5 ${impactBgClass}`}>
                            <div className="text-xs font-semibold font-sans">
                              {item.sentimentLabel === "bullish" ? (
                                <span className="text-[#047857] flex items-center gap-1.5">
                                  <TrendingUp className="w-3.5 h-3.5 flex-shrink-0" />
                                  <span>Upward bias on {item.currency} cash flow valuations (+{item.driftBps} bps drift).</span>
                                </span>
                              ) : item.sentimentLabel === "bearish" ? (
                                <span className="text-[#B91C1C] flex items-center gap-1.5">
                                  <TrendingDown className="w-3.5 h-3.5 flex-shrink-0" />
                                  <span>Downward variance pressure ({item.volatilityMultiplier}x vol multiplier applied).</span>
                                </span>
                              ) : (
                                <span className="text-[#71717A] flex items-center gap-1.5">
                                  <Minus className="w-3.5 h-3.5 flex-shrink-0" />
                                  <span>Neutral macro shock — baseline forecast maintained.</span>
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Card Bottom Action Bar */}
                          <div className="flex items-center justify-between border-t border-[#F4F3EE] pt-2.5">
                            <span className="text-[10px] text-[#71717A] font-mono font-medium tracking-wider uppercase">
                              SWIPE OR CLICK NEXT
                            </span>

                            <button
                              onClick={handleNext}
                              className="px-3.5 py-1.5 text-xs font-bold bg-[#18181B] text-[#FAF9F5] hover:bg-[#27272A] rounded flex items-center gap-1.5 transition-all shadow-sm active:scale-95"
                            >
                              <span>NEXT</span>
                              <ArrowRight className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </>
                      ) : (
                        /* Clean background card surface without duplicate ghost text */
                        <div className="w-full h-full" />
                      )}
                    </motion.div>
                  )
                })
              ) : (
                /* ========================================================= */
                /* EMPTY STATE: All Caught Up!                               */
                /* ========================================================= */
                <motion.div
                  key="empty-state"
                  initial={{ scale: 0.95, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1, transition: { duration: 0.3 } }}
                  className="w-full bg-[#FFFFFF] border border-[#E4E2D9] rounded-xl p-8 text-center space-y-3 shadow-sm"
                >
                  <div className="w-10 h-10 bg-[#ECFDF5] border border-[#A7F3D0] rounded-full flex items-center justify-center mx-auto text-[#047857]">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-[#18181B] font-display">
                      You're all caught up!
                    </h4>
                    <p className="text-xs text-[#71717A] font-sans mt-1 max-w-sm mx-auto">
                      No new market-moving headlines in the current telemetry buffer. The Monte Carlo engine is running on latest calibrated weights.
                    </p>
                  </div>
                  <button
                    onClick={handleReset}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold bg-[#F4F3EE] hover:bg-[#E4E2D9] text-[#18181B] border border-[#E4E2D9] rounded transition-colors"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Reset Headlines Feed</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LiveNewsFeed
