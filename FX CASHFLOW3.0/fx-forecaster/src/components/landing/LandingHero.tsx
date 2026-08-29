import { useState } from "react"
import { CoinCanvas } from "@/components/3d/CoinCanvas"
import { CURRENCIES } from "@/components/3d/InteractiveCoin"
import { LiquidButton, MetalButton } from "@/components/ui/liquid-glass-button"
import { ArrowRight, Activity, TrendingUp, ShieldCheck } from "lucide-react"

interface LandingHeroProps {
  onOpenLogin: () => void
  onNavigateDashboard: () => void
}

export function LandingHero({ onOpenLogin, onNavigateDashboard }: LandingHeroProps) {
  const [selectedCurrency, setSelectedCurrency] = useState(CURRENCIES[0])

  return (
    <section className="relative w-full border-b border-[#E4E2D9] bg-[#FAF9F5] terminal-grid">
      {/* Editorial Top Ticker Ribbon */}
      <div className="w-full border-b border-[#E4E2D9] bg-[#F4F3EE] px-4 py-2 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-[#047857] font-semibold">
            <span className="w-2 h-2 rounded-full bg-[#047857] animate-pulse" />
            MARKET TELEMETRY ACTIVE
          </span>
          <span className="text-[#71717A] hidden sm:inline">|</span>
          <span className="text-[#18181B]">
            USD/INR <strong className="text-[#047857]">87.41</strong> (+0.14%)
          </span>
          <span className="text-[#18181B]">
            EUR/INR <strong className="text-[#B45309]">93.00</strong> (-0.08%)
          </span>
          <span className="text-[#18181B]">
            GBP/INR <strong className="text-[#047857]">110.20</strong> (+0.22%)
          </span>
        </div>
        <div className="text-[#71717A] flex items-center gap-2">
          <span>BASE CURRENCY: INR (₹)</span>
          <span>•</span>
          <span className="text-[#18181B] font-bold">LATENCY: 14MS</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 lg:py-16">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left Column: Editorial Copy */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 bg-[#F4F3EE] border border-[#E4E2D9] text-xs font-mono font-medium text-[#18181B]">
              <Activity className="w-3.5 h-3.5 text-[#B45309]" />
              <span>4-STEP TREASURY INTELLIGENCE PROTOCOL</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-[#18181B] leading-[1.08]">
              FX-Aware Cash Flow <br />
              <span className="italic font-serif font-normal">Forecasting</span> & SME <br />
              Treasury Decision Layer.
            </h1>

            <p className="text-base sm:text-lg text-[#71717A] leading-relaxed max-w-xl">
              Deterministic schedules alone create blind spots. FX/Forecaster simulates{" "}
              <strong className="text-[#18181B] font-mono">10,000 correlated Monte Carlo paths</strong>,
              gates carry-costs, and delivers 1-click rate execution via the Wise Sandbox.
            </p>

            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-3 gap-3 pt-2 max-w-lg border-y border-[#E4E2D9] py-3">
              <div>
                <div className="font-mono text-[11px] uppercase tracking-wider text-[#71717A]">
                  SIMULATION RUNS
                </div>
                <div className="font-mono text-lg sm:text-xl font-bold text-[#18181B]">
                  10,000 PATHS
                </div>
              </div>
              <div>
                <div className="font-mono text-[11px] uppercase tracking-wider text-[#71717A]">
                  RISK HORIZON
                </div>
                <div className="font-mono text-lg sm:text-xl font-bold text-[#18181B]">
                  30 - 90 DAYS
                </div>
              </div>
              <div>
                <div className="font-mono text-[11px] uppercase tracking-wider text-[#71717A]">
                  WISE SANDBOX
                </div>
                <div className="font-mono text-lg sm:text-xl font-bold text-[#047857] flex items-center gap-1">
                  <ShieldCheck className="w-4 h-4 inline" /> LIVE
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <MetalButton
                variant="default"
                onClick={onNavigateDashboard}
                className="h-12 px-7 text-xs uppercase tracking-wider font-mono font-bold flex items-center gap-2"
              >
                <span>LAUNCH TREASURY TERMINAL</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </MetalButton>

              <LiquidButton
                onClick={onOpenLogin}
                className="h-12 px-6 text-xs uppercase tracking-wider font-mono"
              >
                OPERATOR LOGIN (NODE_01)
              </LiquidButton>
            </div>
          </div>

          {/* Right Column: 3D Interactive Coin Showcase */}
          <div className="lg:col-span-5 flex flex-col items-center">
            <div className="w-full bg-[#F4F3EE] border border-[#E4E2D9] p-4 shadow-sm relative overflow-hidden">
              {/* Box Header */}
              <div className="flex items-center justify-between border-b border-[#E4E2D9] pb-2 mb-2 font-mono text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-[#D97706] rounded-full" />
                  <span className="font-bold uppercase tracking-wider text-[#18181B]">
                    ASSET TELEMETRY: 3D CURRENCY CORE
                  </span>
                </div>
                <span className="text-[#71717A]">{selectedCurrency.code} ACTIVE</span>
              </div>

              {/* 3D Canvas */}
              <CoinCanvas onCurrencyChange={(c) => setSelectedCurrency(c)} />

              {/* Currency Selector Pills */}
              <div className="mt-3 pt-3 border-t border-[#E4E2D9] flex items-center justify-between font-mono text-xs">
                <span className="text-[#71717A] uppercase text-[11px]">ACTIVE UNIT:</span>
                <div className="flex gap-1.5">
                  {CURRENCIES.map((c) => (
                    <span
                      key={c.code}
                      className={`px-2 py-0.5 border text-xs cursor-pointer transition-colors ${
                        selectedCurrency.code === c.code
                          ? "bg-[#18181B] text-[#FAF9F5] border-[#18181B] font-bold"
                          : "bg-[#FFFFFF] text-[#71717A] border-[#E4E2D9] hover:text-[#18181B]"
                      }`}
                    >
                      {c.symbol} {c.code}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
