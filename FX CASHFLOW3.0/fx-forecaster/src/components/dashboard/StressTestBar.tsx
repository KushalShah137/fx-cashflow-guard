import { useState } from "react"
import { Flame, RotateCcw } from "lucide-react"

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
    <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-5 font-mono space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#E4E2D9] pb-3">
        <div className="flex items-center gap-2">
          <Flame className={`w-4 h-4 ${isStressed ? "text-[#B91C1C]" : "text-[#B45309]"}`} />
          <span className="text-xs font-bold uppercase tracking-wider text-[#18181B]">
            LIVE MACRO STRESS-TEST SIMULATOR
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isStressed && (
            <span className="text-[11px] px-2 py-0.5 bg-[#FEF2F2] text-[#B91C1C] border border-[#B91C1C] font-bold">
              STRESS ACTIVE: {activeCurrency} {sliderVal > 0 ? `+${sliderVal}%` : `${sliderVal}%`}
            </span>
          )}
          <button
            onClick={() => {
              setSliderVal(0)
              onResetStress()
            }}
            disabled={!isStressed}
            className="px-2.5 py-1 text-xs border border-[#E4E2D9] bg-[#F4F3EE] hover:bg-[#E4E2D9] text-[#18181B] flex items-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-bold"
          >
            <RotateCcw className="w-3 h-3" /> RESET
          </button>
        </div>
      </div>

      {/* PRIMARY FEATURE: Interactive Custom Stress Slider Box */}
      <div className="bg-[#F4F3EE] border border-[#18181B] p-4 space-y-3 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-[#18181B] font-bold uppercase text-[11px]">TARGET CURRENCY:</span>
            {["USD", "EUR", "GBP", "INR_CRASH"].map((c) => (
              <button
                key={c}
                onClick={() => {
                  setActiveCurrency(c)
                  onApplyStress(c, sliderVal)
                }}
                className={`px-2.5 py-1 text-xs border transition-colors ${
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
            <span className="text-[#71717A] text-[11px] uppercase font-bold">SHIFT MAGNITUDE: </span>
            <span
              className={`font-bold text-sm ${
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
          className="w-full accent-[#18181B] cursor-pointer h-2 bg-[#E4E2D9] rounded-none"
        />

        <div className="flex justify-between text-[10px] text-[#71717A] uppercase font-mono">
          <span>-15% Adverse Shift</span>
          <span>0% Baseline</span>
          <span>+15% Severe Shock</span>
        </div>
      </div>

      {/* SECONDARY SHORTCUTS: 3 Quick-Simulate Presets */}
      <div>
        <div className="text-[10px] text-[#71717A] font-bold uppercase tracking-wider mb-2">
          QUICK SIMULATION SHORTCUTS:
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <button
            onClick={() => handlePreset("USD", 5.0)}
            className={`p-2.5 border text-left text-xs transition-colors flex items-center justify-between ${
              activeCurrency === "USD" && sliderVal === 5.0
                ? "border-[#B91C1C] bg-[#FEF2F2] text-[#B91C1C] font-bold"
                : "border-[#E4E2D9] bg-[#FFFFFF] hover:border-[#18181B] text-[#18181B]"
            }`}
          >
            <div>
              <div className="font-bold">USD Spike (+5%)</div>
              <div className="text-[10px] text-[#71717A] mt-0.5">Import Payables Inflation</div>
            </div>
            <span className="text-[11px] font-bold text-[#B91C1C]">+5.0%</span>
          </button>

          <button
            onClick={() => handlePreset("INR_CRASH", -4.0)}
            className={`p-2.5 border text-left text-xs transition-colors flex items-center justify-between ${
              activeCurrency === "INR_CRASH" && sliderVal === -4.0
                ? "border-[#B91C1C] bg-[#FEF2F2] text-[#B91C1C] font-bold"
                : "border-[#E4E2D9] bg-[#FFFFFF] hover:border-[#18181B] text-[#18181B]"
            }`}
          >
            <div>
              <div className="font-bold">Rupee Depreciation (-4%)</div>
              <div className="text-[10px] text-[#71717A] mt-0.5">Broad FX Portfolio Stress</div>
            </div>
            <span className="text-[11px] font-bold text-[#B45309]">-4.0%</span>
          </button>

          <button
            onClick={() => handlePreset("EUR", 8.0)}
            className={`p-2.5 border text-left text-xs transition-colors flex items-center justify-between ${
              activeCurrency === "EUR" && sliderVal === 8.0
                ? "border-[#B91C1C] bg-[#FEF2F2] text-[#B91C1C] font-bold"
                : "border-[#E4E2D9] bg-[#FFFFFF] hover:border-[#18181B] text-[#18181B]"
            }`}
          >
            <div>
              <div className="font-bold">EUR Rate Shock (+8%)</div>
              <div className="text-[10px] text-[#71717A] mt-0.5">ECB Policy Volatility</div>
            </div>
            <span className="text-[11px] font-bold text-[#047857]">+8.0%</span>
          </button>
        </div>
      </div>
    </div>
  )
}
