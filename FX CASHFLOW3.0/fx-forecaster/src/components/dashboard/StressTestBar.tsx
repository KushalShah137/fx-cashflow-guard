import { useState } from "react"
import { Flame, RotateCcw, AlertTriangle, Zap } from "lucide-react"

interface StressTestBarProps {
  currentStressCurrency: string
  currentStressPct: number
  onApplyStress: (currency: string, pct: number) => void
  onResetStress: () => void
}

export function StressTestBar({
  currentStressCurrency,
  currentStressPct,
  onApplyStress,
  onResetStress,
}: StressTestBarProps) {
  const [activeCurrency, setActiveCurrency] = useState<string>(
    currentStressCurrency || "USD"
  )
  const [sliderVal, setSliderVal] = useState<number>(currentStressPct || 0)

  const handlePreset = (currency: string, pct: number) => {
    setActiveCurrency(currency)
    setSliderVal(pct)
    onApplyStress(currency, pct)
  }

  const handleSliderChange = (val: number) => {
    setSliderVal(val)
    onApplyStress(activeCurrency, val)
  }

  const isStressed = sliderVal !== 0 || currentStressCurrency !== ""

  return (
    <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-4 font-mono">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#E4E2D9] pb-3 mb-3">
        <div className="flex items-center gap-2">
          <Flame className={`w-4 h-4 ${isStressed ? "text-[#B91C1C]" : "text-[#B45309]"}`} />
          <span className="text-xs font-bold uppercase tracking-wider text-[#18181B]">
            LIVE MACRO STRESS-TEST SIMULATOR
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isStressed && (
            <span className="text-[11px] px-2 py-0.5 bg-[#FEE2E2] text-[#B91C1C] border border-[#B91C1C] font-bold">
              ACTIVE STRESS: {activeCurrency} {sliderVal > 0 ? `+${sliderVal}%` : `${sliderVal}%`}
            </span>
          )}
          <button
            onClick={() => {
              setSliderVal(0)
              onResetStress()
            }}
            disabled={!isStressed}
            className="px-2 py-1 text-xs border border-[#E4E2D9] bg-[#F4F3EE] hover:bg-[#E4E2D9] text-[#18181B] flex items-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <RotateCcw className="w-3 h-3" /> RESET
          </button>
        </div>
      </div>

      {/* Preset Action Chips */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-4">
        <button
          onClick={() => handlePreset("USD", 5.0)}
          className={`p-2 border text-left text-xs transition-colors flex items-center justify-between ${
            activeCurrency === "USD" && sliderVal === 5.0
              ? "border-[#B91C1C] bg-[#FEF2F2] text-[#B91C1C] font-bold"
              : "border-[#E4E2D9] bg-[#FFFFFF] hover:border-[#18181B] text-[#18181B]"
          }`}
        >
          <span className="flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-[#B45309]" />
            Simulate USD Spike (+5%)
          </span>
          <span className="text-[11px] text-[#71717A]">+₹87.41 → ₹91.78</span>
        </button>

        <button
          onClick={() => handlePreset("INR_CRASH", -4.0)}
          className={`p-2 border text-left text-xs transition-colors flex items-center justify-between ${
            activeCurrency === "INR_CRASH" && sliderVal === -4.0
              ? "border-[#B91C1C] bg-[#FEF2F2] text-[#B91C1C] font-bold"
              : "border-[#E4E2D9] bg-[#FFFFFF] hover:border-[#18181B] text-[#18181B]"
          }`}
        >
          <span className="flex items-center gap-1.5">
            <Flame className="w-3.5 h-3.5 text-[#B91C1C]" />
            Simulate Rupee Crash (-4%)
          </span>
          <span className="text-[11px] text-[#71717A]">Broad FX Surge</span>
        </button>

        <button
          onClick={() => handlePreset("EUR", 8.0)}
          className={`p-2 border text-left text-xs transition-colors flex items-center justify-between ${
            activeCurrency === "EUR" && sliderVal === 8.0
              ? "border-[#B91C1C] bg-[#FEF2F2] text-[#B91C1C] font-bold"
              : "border-[#E4E2D9] bg-[#FFFFFF] hover:border-[#18181B] text-[#18181B]"
          }`}
        >
          <span className="flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-[#1D4ED8]" />
            EUR Volatility (+8%)
          </span>
          <span className="text-[11px] text-[#71717A]">ECB Rate Shock</span>
        </button>
      </div>

      {/* Interactive Custom Stress Slider */}
      <div className="bg-[#F4F3EE] border border-[#E4E2D9] p-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="text-[#71717A] uppercase text-[11px]">TARGET CURRENCY:</span>
            {["USD", "EUR", "GBP", "INR_CRASH"].map((c) => (
              <button
                key={c}
                onClick={() => {
                  setActiveCurrency(c)
                  onApplyStress(c, sliderVal)
                }}
                className={`px-2 py-0.5 text-xs border ${
                  activeCurrency === c
                    ? "bg-[#18181B] text-[#FAF9F5] border-[#18181B] font-bold"
                    : "bg-[#FFFFFF] text-[#71717A] border-[#E4E2D9] hover:text-[#18181B]"
                }`}
              >
                {c === "INR_CRASH" ? "INR DEP." : c}
              </button>
            ))}
          </div>
          <div className="text-right">
            <span className="text-[#71717A] text-[11px]">MAGNITUDE: </span>
            <span
              className={`font-bold ${
                sliderVal > 0
                  ? "text-[#B91C1C]"
                  : sliderVal < 0
                  ? "text-[#B45309]"
                  : "text-[#18181B]"
              }`}
            >
              {sliderVal > 0 ? `+${sliderVal}%` : `${sliderVal}%`}
            </span>
          </div>
        </div>

        <input
          type="range"
          min="-15"
          max="15"
          step="0.5"
          value={sliderVal}
          onChange={(e) => handleSliderChange(parseFloat(e.target.value))}
          className="w-full h-1.5 bg-[#E4E2D9] rounded-none appearance-none cursor-pointer accent-[#18181B]"
        />

        <div className="flex justify-between text-[10px] text-[#71717A]">
          <span>-15% (Appreciation)</span>
          <span>0% (Market Drift Baseline)</span>
          <span>+15% (Severe Depreciation Shock)</span>
        </div>
      </div>
    </div>
  )
}
