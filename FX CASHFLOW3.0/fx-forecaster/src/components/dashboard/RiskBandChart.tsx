import { useState, useMemo } from "react"
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from "recharts"
import { ForecastResponse, EconomicImpactResponse } from "@/types"
import { formatINR } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { ShieldAlert, ArrowUpRight, ArrowDownRight, Activity } from "lucide-react"

interface RiskBandChartProps {
  forecast: ForecastResponse | null
  isLoading: boolean
  horizon: number
  onHorizonChange: (h: number) => void
  riskTolerance: string
  onRiskToleranceChange: (r: string) => void
  economicImpact?: EconomicImpactResponse
}

export function RiskBandChart({
  forecast,
  isLoading,
  horizon,
  onHorizonChange,
  riskTolerance,
  onRiskToleranceChange,
  economicImpact,
}: RiskBandChartProps) {
  const chartData = useMemo(() => {
    if (!forecast || !forecast.timeline) return []
    return forecast.timeline.map((pt) => ({
      ...pt,
      // For stacked/band area calculation:
      // bandBase = pt.worst_case_5th
      // bandSpread = pt.best_case_95th - pt.worst_case_5th
      bandSpread: Math.max(0, pt.best_case_95th - pt.worst_case_5th),
      displayDate: pt.date.slice(5), // "MM-DD"
    }))
  }, [forecast])

  const summary = forecast?.summary || {
    expected_final_balance: 1845000,
    worst_case_5th_var: 1320000,
    best_case_95th: 2210000,
    value_at_risk_95: 525000,
    risk_status: "CAUTION",
  }

  const dangerThreshold = forecast?.danger_threshold || 450000

  return (
    <div className="space-y-6">
      {/* Top Controls & Horizon Selector */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#E4E2D9] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-xl font-bold text-[#18181B] font-display">
              Monte Carlo Cash Flow at Risk (CFaR)
            </h3>
            <Badge
              variant={
                summary.risk_status === "BREACH"
                  ? "danger"
                  : summary.risk_status === "CAUTION"
                  ? "caution"
                  : "protected"
              }
              className="text-[11px] font-mono uppercase"
            >
              {summary.risk_status === "BREACH" && <ShieldAlert className="w-3 h-3 mr-1 inline" />}
              {summary.risk_status} // 10,000 SIMS
            </Badge>
          </div>
          <p className="text-xs text-[#71717A] mt-1 font-mono">
            5th / 50th / 95th Percentile Uncertainty Envelope across correlated FX drifts
          </p>
        </div>

        {/* Horizon & Risk Tolerance Toggles */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Horizon Toggle */}
          <div className="flex items-center border border-[#18181B] bg-[#FAF9F5] p-0.5">
            <span className="text-[10px] font-mono font-bold text-[#71717A] px-2 uppercase">
              HORIZON:
            </span>
            {[30, 60, 90].map((h) => (
              <button
                key={h}
                onClick={() => onHorizonChange(h)}
                className={`px-3 py-1 font-mono text-xs transition-colors ${
                  horizon === h
                    ? "bg-[#18181B] text-[#FAF9F5] font-bold"
                    : "text-[#71717A] hover:text-[#18181B]"
                }`}
              >
                {h}D
              </button>
            ))}
          </div>

          {/* Risk Tolerance Toggle */}
          <div className="flex items-center border border-[#E4E2D9] bg-[#F4F3EE] p-0.5">
            <span className="text-[10px] font-mono font-bold text-[#71717A] px-2 uppercase">
              CONFIDENCE:
            </span>
            {[
              { id: "conservative", label: "99% (CONSERVATIVE)" },
              { id: "moderate", label: "95% (STANDARD)" },
              { id: "aggressive", label: "90% (ACTIVE)" },
            ].map((r) => (
              <button
                key={r.id}
                onClick={() => onRiskToleranceChange(r.id)}
                className={`px-2.5 py-1 font-mono text-[11px] transition-colors ${
                  riskTolerance === r.id
                    ? "bg-[#18181B] text-[#FAF9F5] font-bold"
                    : "text-[#71717A] hover:text-[#18181B]"
                }`}
              >
                {r.id.toUpperCase().slice(0, 4)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* KPI Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
        <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-3">
          <div className="text-[11px] text-[#71717A] uppercase">Expected Balance (50th)</div>
          <div className="text-xl font-bold text-[#18181B] mt-0.5">
            {formatINR(summary.expected_final_balance)}
          </div>
          <div className="text-[10px] text-[#047857] flex items-center gap-1 mt-1">
            <ArrowUpRight className="w-3 h-3" /> Baseline Deterministic Path
          </div>
        </div>

        <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-3">
          <div className="text-[11px] text-[#71717A] uppercase">Worst-Case (5th Adverse VaR)</div>
          <div className="text-xl font-bold text-[#B91C1C] mt-0.5">
            {formatINR(summary.worst_case_5th_var)}
          </div>
          <div className="text-[10px] text-[#B91C1C] flex items-center gap-1 mt-1">
            <ArrowDownRight className="w-3 h-3" /> Tail Risk Floor
          </div>
        </div>

        <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-3">
          <div className="text-[11px] text-[#71717A] uppercase">Best-Case (95th Tail)</div>
          <div className="text-xl font-bold text-[#047857] mt-0.5">
            {formatINR(summary.best_case_95th)}
          </div>
          <div className="text-[10px] text-[#047857] flex items-center gap-1 mt-1">
            <ArrowUpRight className="w-3 h-3" /> Currency Tail Upside
          </div>
        </div>

        <div className="bg-[#FAF9F5] border border-[#18181B] p-3 bg-[#F4F3EE]">
          <div className="text-[11px] text-[#18181B] font-bold uppercase">Value at Risk (95% VaR)</div>
          <div className="text-xl font-bold text-[#B45309] mt-0.5">
            {formatINR(summary.value_at_risk_95)}
          </div>
          <div className="text-[10px] text-[#71717A] flex items-center gap-1 mt-1">
            <Activity className="w-3 h-3 text-[#B45309]" /> Exposure to Hedge
          </div>
        </div>
      </div>

      {/* Cost of Inaction Card */}
      {economicImpact && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono mt-3 mb-3">
          <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-3">
            <div className="text-[11px] text-[#71717A] uppercase">Expected Loss from Inaction</div>
            <div className="text-xl font-bold text-[#B91C1C] mt-0.5">
              {formatINR(economicImpact.total_estimated_avoided_loss)}
            </div>
            <div className="text-[10px] text-[#B91C1C] flex items-center gap-1 mt-1">
              <ArrowDownRight className="w-3 h-3" /> Unhedged Downside Risk
            </div>
          </div>

          <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-3">
            <div className="text-[11px] text-[#71717A] uppercase">Wise Hedging Cost</div>
            <div className="text-xl font-bold text-[#B45309] mt-0.5">
              {formatINR(economicImpact.total_action_cost)}
            </div>
            <div className="text-[10px] text-[#71717A] flex items-center gap-1 mt-1">
              <Activity className="w-3 h-3 text-[#B45309]" /> Conversion Fees + Slippage
            </div>
          </div>

          <div className="bg-[#FAF9F5] border border-[#18181B] p-3 bg-[#ECFDF5] border-l-4 border-l-[#059669]">
            <div className="text-[11px] text-[#065F46] font-bold uppercase">Net Benefit of Action</div>
            <div className="text-xl font-bold text-[#047857] mt-0.5">
              {formatINR(economicImpact.total_net_economic_benefit)}
            </div>
            <div className="text-[10px] text-[#047857] flex items-center gap-1 mt-1">
              <ArrowUpRight className="w-3 h-3" /> Preserved Enterprise Value
            </div>
          </div>
        </div>
      )}

      {/* Chart Canvas */}
      <div className="w-full h-[360px] bg-[#FAF9F5] border border-[#E4E2D9] p-2 relative">
        {isLoading && (
          <div className="absolute inset-0 bg-[#FAF9F5]/70 flex items-center justify-center z-20">
            <span className="font-mono text-xs font-bold text-[#18181B] bg-[#F4F3EE] border border-[#18181B] px-3 py-1.5">
              RECALCULATING 10,000 MONTE CARLO PATHS...
            </span>
          </div>
        )}

        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            key={forecast ? `${forecast.summary?.expected_final_balance || 0}-${forecast.summary?.value_at_risk_95 || 0}-${horizon}-${riskTolerance}` : "loading"}
            data={chartData}
            margin={{ top: 15, right: 25, left: 20, bottom: 20 }}
          >
            <defs>
              {/* Light emerald tint for upside band */}
              <linearGradient id="bestCaseBand" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#047857" stopOpacity={0.18} />
                <stop offset="95%" stopColor="#047857" stopOpacity={0.02} />
              </linearGradient>
              {/* Light crimson/amber tint for downside band */}
              <linearGradient id="worstCaseBand" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#B45309" stopOpacity={0.18} />
                <stop offset="95%" stopColor="#B91C1C" stopOpacity={0.04} />
              </linearGradient>
            </defs>

            <CartesianGrid stroke="#E4E2D9" strokeDasharray="2 2" vertical={false} />

            <XAxis
              dataKey="displayDate"
              stroke="#71717A"
              fontSize={11}
              fontFamily="JetBrains Mono"
              tickLine={{ stroke: "#E4E2D9" }}
              axisLine={{ stroke: "#E4E2D9" }}
            />

            <YAxis
              stroke="#71717A"
              fontSize={11}
              fontFamily="JetBrains Mono"
              tickFormatter={(val) => `₹${(val / 100000).toFixed(1)}L`}
              tickLine={{ stroke: "#E4E2D9" }}
              axisLine={{ stroke: "#E4E2D9" }}
              domain={["auto", "auto"]}
            />

            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload
                  return (
                    <div className="bg-[#18181B] text-[#FAF9F5] p-3 border border-[#18181B] font-mono text-xs shadow-xl space-y-1 rounded-none">
                      <div className="border-b border-[#71717A] pb-1 font-bold text-[#FEF08A]">
                        DATE: {data.date} (Day {data.day_index})
                      </div>
                      <div className="flex justify-between gap-4 text-[#A1A1AA]">
                        <span>Deterministic:</span>
                        <span className="text-[#FAF9F5]">
                          {formatINR(data.deterministic_balance)}
                        </span>
                      </div>
                      <div className="flex justify-between gap-4 text-[#34D399]">
                        <span>95th Percentile:</span>
                        <span className="font-bold">{formatINR(data.best_case_95th)}</span>
                      </div>
                      <div className="flex justify-between gap-4 text-[#FAF9F5]">
                        <span>50th Expected:</span>
                        <span className="font-bold">{formatINR(data.expected_50th)}</span>
                      </div>
                      <div className="flex justify-between gap-4 text-[#F87171]">
                        <span>5th Worst-Case:</span>
                        <span className="font-bold">{formatINR(data.worst_case_5th)}</span>
                      </div>
                      {data.net_cash_flow !== 0 && (
                        <div className="border-t border-[#3F3F46] pt-1 text-[11px] text-[#93C5FD]">
                          Net Scheduled Flow: {formatINR(data.net_cash_flow)}
                        </div>
                      )}
                    </div>
                  )
                }
                return null
              }}
            />

            {/* Danger Threshold Line */}
            <ReferenceLine
              y={dangerThreshold}
              stroke="#B91C1C"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              label={{
                value: `MIN LIQUIDITY FLOOR: ₹450K`,
                position: "right",
                fill: "#B91C1C",
                fontSize: 10,
                fontFamily: "JetBrains Mono",
                fontWeight: "bold",
              }}
            />

            {/* Area band for 95th Percentile (Best Case) */}
            <Area
              type="monotone"
              dataKey="best_case_95th"
              stroke="#047857"
              strokeWidth={1}
              fill="url(#bestCaseBand)"
              name="95th Upper Bound"
            />

            {/* Area band for 5th Percentile (Worst Case) */}
            <Area
              type="monotone"
              dataKey="worst_case_5th"
              stroke="#B91C1C"
              strokeWidth={1}
              fill="url(#worstCaseBand)"
              name="5th Lower Bound"
            />

            {/* Expected Median Curve (50th Percentile) */}
            <Line
              type="monotone"
              dataKey="expected_50th"
              stroke="#18181B"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#18181B" }}
              name="50th Expected Path"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Chart Legend & Explanation */}
      <div className="flex flex-wrap items-center justify-between text-xs font-mono text-[#71717A] border-t border-[#E4E2D9] pt-3">
        <div className="flex flex-wrap items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-[#18181B]" /> 50th Expected Path
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-2 bg-[#047857]/20 border border-[#047857]" /> 95th Upside Band
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-2 bg-[#B91C1C]/20 border border-[#B91C1C]" /> 5th Adverse VaR Band
          </span>
          <span className="flex items-center gap-1.5 text-[#B91C1C]">
            <span className="w-3 h-0.5 border-b border-dashed border-[#B91C1C]" /> Danger Floor (₹450k)
          </span>
        </div>
        <div>
          <span>RECHECK INTERVAL: INSTANT ON WISE SETTLEMENT</span>
        </div>
      </div>
    </div>
  )
}
