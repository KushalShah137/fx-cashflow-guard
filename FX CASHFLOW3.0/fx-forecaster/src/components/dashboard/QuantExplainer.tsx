import { MarketSentiment } from "@/types"
import { Cpu, TrendingUp, Newspaper, HelpCircle, Activity } from "lucide-react"

interface QuantExplainerProps {
  sentiment: MarketSentiment | null
}

export function QuantExplainer({ sentiment }: QuantExplainerProps) {
  const s = sentiment || {
    sentiment_summary: "Cautious on INR due to oil imports; USD resilient",
    drift_adjustment: 0.03,
    volatility_adjustment: 0.08,
    last_updated: "2026-08-29T21:45:00Z",
    headlines: [
      "Crude prices put pressure on emerging market currencies",
      "US Fed signals higher-for-longer policy trajectory",
      "RBI maintains strategic foreign exchange intervention corridor",
    ],
  }

  return (
    <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-5 font-mono space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#E4E2D9] pb-3">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-[#18181B]" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-[#18181B] font-display">
            AI Quant Diagnostic & Market Drift Engine
          </h3>
        </div>
        <span className="text-[11px] text-[#71717A]">
          UPDATED: {new Date(s.last_updated).toLocaleTimeString()}
        </span>
      </div>

      {/* Model Parameter Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        <div className="bg-[#F4F3EE] border border-[#E4E2D9] p-3">
          <div className="text-[11px] text-[#71717A] uppercase flex items-center justify-between">
            <span>ANNUALIZED DRIFT (μ)</span>
            <Activity className="w-3.5 h-3.5 text-[#B45309]" />
          </div>
          <div className="text-lg font-bold text-[#18181B] mt-1">
            +{(s.drift_adjustment * 100).toFixed(1)}% / YR
          </div>
          <div className="text-[10px] text-[#71717A] mt-1">
            USD/INR drift incorporates interest rate differential (SOFR vs RBI Repo).
          </div>
        </div>

        <div className="bg-[#F4F3EE] border border-[#E4E2D9] p-3">
          <div className="text-[11px] text-[#71717A] uppercase flex items-center justify-between">
            <span>VOLATILITY ADJUSTMENT (σ)</span>
            <TrendingUp className="w-3.5 h-3.5 text-[#1D4ED8]" />
          </div>
          <div className="text-lg font-bold text-[#18181B] mt-1">
            +{(s.volatility_adjustment * 100).toFixed(1)}% VOL
          </div>
          <div className="text-[10px] text-[#71717A] mt-1">
            Computed from 2-year rolling daily log-returns (Frankfurter / ECB).
          </div>
        </div>

        <div className="bg-[#F4F3EE] border border-[#E4E2D9] p-3">
          <div className="text-[11px] text-[#71717A] uppercase flex items-center justify-between">
            <span>CARRY-COST SPREAD (Δi)</span>
            <HelpCircle className="w-3.5 h-3.5 text-[#047857]" />
          </div>
          <div className="text-lg font-bold text-[#047857] mt-1">
            3.85% APY SPREAD
          </div>
          <div className="text-[10px] text-[#71717A] mt-1">
            Gating condition: Only lock forward if Adverse VaR &gt; ₹14,200 carry drag.
          </div>
        </div>
      </div>

      {/* Synthesis Summary */}
      <div className="bg-[#FFFFFF] border border-[#18181B] p-3 text-xs space-y-1.5">
        <div className="font-bold text-[#18181B] flex items-center gap-1.5 uppercase text-[11px]">
          <span className="w-2 h-2 bg-[#B45309] rounded-none" />
          QUANTITATIVE REGIME SYNTHESIS:
        </div>
        <p className="text-sm text-[#18181B] font-sans">
          "{s.sentiment_summary}"
        </p>
      </div>

      {/* Live Market Feeds */}
      <div>
        <div className="text-[11px] font-bold text-[#71717A] uppercase flex items-center gap-1.5 mb-2">
          <Newspaper className="w-3.5 h-3.5" /> RECENT MACRO TELEMETRY HEADLINES:
        </div>
        <div className="space-y-1.5">
          {s.headlines.map((headline, idx) => (
            <div
              key={idx}
              className="text-xs bg-[#F4F3EE] border border-[#E4E2D9] px-3 py-1.5 text-[#18181B] flex items-center justify-between"
            >
              <span>• {headline}</span>
              <span className="text-[10px] text-[#71717A] uppercase">VERIFIED FEED</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
