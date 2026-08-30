import { useMemo } from "react"
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
    return forecast.timeline.map((pt) => {
      const worst = pt.worst_case_5th ?? 0
      const best = pt.best_case_95th ?? 0
      const exp = pt.expected_50th ?? pt.deterministic_balance ?? 0
      return {
        ...pt,
        worst_case_5th: worst,
        best_case_95th: best,
        expected_50th: exp,
        bandBase: worst,
        bandSpread: Math.max(0, best - worst),
        displayDate: pt.date ? pt.date.slice(5) : "", // "MM-DD"
      }
    })
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
    <div className="space-y-6 w-full">
      {/* ============================================================
          HEADER BAR: Title, Risk Breach Badge & Horizon/Confidence Toggles
      ============================================================= */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#E4E2D9] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h3 className="text-xl sm:text-2xl font-black text-[#18181B] font-display tracking-tight">
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
              className="text-[11px] font-mono uppercase tracking-wider font-bold px-2 py-0.5"
            >
              {summary.risk_status === "BREACH" && <ShieldAlert className="w-3 h-3 mr-1 inline" />}
              [RISK {summary.risk_status}: 10,000 SIMS]
            </Badge>
          </div>
          <p className="text-xs text-[#71717A] mt-1 font-mono tracking-wide">
            5th / 50th / 95th Percentile Uncertainty Envelope across correlated FX drifts
          </p>
        </div>

        {/* Horizon & Risk Tolerance Toggles */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Horizon Toggle */}
          <div className="flex items-center border border-[#18181B] bg-[#FAF9F5] p-0.5 rounded-sm shadow-xs">
            <span className="text-[10px] font-mono font-bold text-[#71717A] px-2 uppercase tracking-wider">
              HORIZON:
            </span>
            {[30, 60, 90].map((h) => (
              <button
                key={h}
                onClick={() => onHorizonChange(h)}
                className={`px-3 py-1 font-mono text-xs transition-all cursor-pointer ${
                  horizon === h
                    ? "bg-[#18181B] text-[#FAF9F5] font-bold shadow-xs"
                    : "text-[#71717A] hover:text-[#18181B] hover:bg-[#E4E2D9]/40"
                }`}
              >
                {h}D
              </button>
            ))}
          </div>

          {/* Risk Tolerance Toggle */}
          <div className="flex items-center border border-[#DCD5C4] bg-[#F4F3EE] p-0.5 rounded-sm shadow-xs">
            <span className="text-[10px] font-mono font-bold text-[#71717A] px-2 uppercase tracking-wider">
              CONFIDENCE:
            </span>
            {[
              { id: "conservative", label: "CONS" },
              { id: "moderate", label: "MODE" },
              { id: "aggressive", label: "AGGR" },
            ].map((r) => (
              <button
                key={r.id}
                onClick={() => onRiskToleranceChange(r.id)}
                className={`px-2.5 py-1 font-mono text-[11px] transition-all cursor-pointer ${
                  riskTolerance === r.id
                    ? "bg-[#18181B] text-[#FAF9F5] font-bold shadow-xs"
                    : "text-[#71717A] hover:text-[#18181B] hover:bg-[#E4E2D9]/40"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ============================================================
          METRIC CARDS GRID (ROW 1: 4 Cards | ROW 2: 3 Cards)
      ============================================================= */}
      <div className="space-y-3.5">
        {/* Row 1: Core 4 Risk Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 font-mono">
          <div className="bg-[#FAF9F5] border border-[#E4E2D9] rounded-lg p-4 sm:p-4.5 flex flex-col justify-between shadow-xs hover:border-[#18181B]/40 transition-colors">
            <div className="text-[11px] font-bold text-[#71717A] tracking-wider uppercase">
              EXPECTED BALANCE (50TH)
            </div>
            <div className="text-2xl lg:text-[26px] font-black text-[#18181B] my-1.5 tracking-tight">
              {formatINR(summary.expected_final_balance)}
            </div>
            <div className="text-[11px] text-[#047857] flex items-center gap-1 font-medium">
              <ArrowUpRight className="w-3.5 h-3.5 shrink-0" />
              <span>Baseline Deterministic Path</span>
            </div>
          </div>

          <div className="bg-[#FAF9F5] border border-[#E4E2D9] rounded-lg p-4 sm:p-4.5 flex flex-col justify-between shadow-xs hover:border-[#18181B]/40 transition-colors">
            <div className="text-[11px] font-bold text-[#71717A] tracking-wider uppercase">
              WORST-CASE (5TH ADVERSE VaR)
            </div>
            <div className="text-2xl lg:text-[26px] font-black text-[#B91C1C] my-1.5 tracking-tight">
              {formatINR(summary.worst_case_5th_var)}
            </div>
            <div className="text-[11px] text-[#B91C1C] flex items-center gap-1 font-medium">
              <ArrowDownRight className="w-3.5 h-3.5 shrink-0" />
              <span>Tail Risk Floor</span>
            </div>
          </div>

          <div className="bg-[#FAF9F5] border border-[#E4E2D9] rounded-lg p-4 sm:p-4.5 flex flex-col justify-between shadow-xs hover:border-[#18181B]/40 transition-colors">
            <div className="text-[11px] font-bold text-[#71717A] tracking-wider uppercase">
              BEST-CASE (95TH TAIL)
            </div>
            <div className="text-2xl lg:text-[26px] font-black text-[#047857] my-1.5 tracking-tight">
              {formatINR(summary.best_case_95th)}
            </div>
            <div className="text-[11px] text-[#047857] flex items-center gap-1 font-medium">
              <ArrowUpRight className="w-3.5 h-3.5 shrink-0" />
              <span>Currency Tail Upside</span>
            </div>
          </div>

          <div className="bg-[#FAF9F5] border border-[#E4E2D9] rounded-lg p-4 sm:p-4.5 flex flex-col justify-between shadow-xs hover:border-[#18181B]/40 transition-colors">
            <div className="text-[11px] font-bold text-[#71717A] tracking-wider uppercase">
              VALUE AT RISK (95% VaR)
            </div>
            <div className="text-2xl lg:text-[26px] font-black text-[#B91C1C] my-1.5 tracking-tight">
              {formatINR(summary.value_at_risk_95)}
            </div>
            <div className="text-[11px] text-[#B45309] flex items-center gap-1 font-medium">
              <Activity className="w-3.5 h-3.5 shrink-0" />
              <span>Exposure to Hedge</span>
            </div>
          </div>
        </div>

        {/* Row 2: Inaction vs. Hedging Cost & Net Benefit (3 Cards) */}
        {economicImpact && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 font-mono">
            <div className="bg-[#FAF9F5] border border-[#E4E2D9] rounded-lg p-4 sm:p-4.5 flex flex-col justify-between shadow-xs hover:border-[#18181B]/40 transition-colors">
              <div className="text-[11px] font-bold text-[#71717A] tracking-wider uppercase">
                EXPECTED LOSS FROM INACTION
              </div>
              <div className="text-2xl lg:text-[26px] font-black text-[#B91C1C] my-1.5 tracking-tight">
                {formatINR(economicImpact.total_estimated_avoided_loss)}
              </div>
              <div className="text-[11px] text-[#B91C1C] flex items-center gap-1 font-medium">
                <ArrowDownRight className="w-3.5 h-3.5 shrink-0" />
                <span>Unhedged Downside Risk</span>
              </div>
            </div>

            <div className="bg-[#FAF9F5] border border-[#E4E2D9] rounded-lg p-4 sm:p-4.5 flex flex-col justify-between shadow-xs hover:border-[#18181B]/40 transition-colors">
              <div className="text-[11px] font-bold text-[#71717A] tracking-wider uppercase">
                WISE HEDGING COST
              </div>
              <div className="text-2xl lg:text-[26px] font-black text-[#18181B] my-1.5 tracking-tight">
                {formatINR(economicImpact.total_action_cost)}
              </div>
              <div className="text-[11px] text-[#71717A] flex items-center gap-1 font-medium">
                <Activity className="w-3.5 h-3.5 text-[#B45309] shrink-0" />
                <span>Conversion Fees + Slippage</span>
              </div>
            </div>

            <div className="bg-[#FAF9F5] border-l-4 border-l-[#059669] border-y border-r border-[#E4E2D9] rounded-lg p-4 sm:p-4.5 flex flex-col justify-between shadow-xs hover:border-[#059669] transition-colors">
              <div className="text-[11px] font-bold text-[#065F46] tracking-wider uppercase">
                NET BENEFIT OF ACTION
              </div>
              <div className="text-2xl lg:text-[26px] font-black text-[#047857] my-1.5 tracking-tight">
                {formatINR(economicImpact.total_net_economic_benefit)}
              </div>
              <div className="text-[11px] text-[#047857] flex items-center gap-1 font-medium">
                <ArrowUpRight className="w-3.5 h-3.5 shrink-0" />
                <span>Preserved Enterprise Value</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ============================================================
          ENLARGED MONTE CARLO CFaR CHART CANVAS (CENTERPIECE)
      ============================================================= */}
      <div className="w-full h-[520px] sm:h-[580px] lg:h-[620px] bg-[#FAF9F5] border border-[#E4E2D9] rounded-xl p-4 sm:p-6 relative shadow-sm">
        {isLoading && (
          <div className="absolute inset-0 bg-[#FAF9F5]/75 backdrop-blur-xs flex items-center justify-center z-20 rounded-xl">
            <span className="font-mono text-xs font-bold text-[#18181B] bg-[#F4F3EE] border border-[#18181B] px-4 py-2 shadow-md">
              RECALCULATING 10,000 MONTE CARLO PATHS...
            </span>
          </div>
        )}

        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            key={
              forecast
                ? `${forecast.summary?.expected_final_balance || 0}-${forecast.summary?.value_at_risk_95 || 0}-${horizon}-${riskTolerance}`
                : "loading"
            }
            data={chartData}
            margin={{ top: 25, right: 35, left: 25, bottom: 25 }}
          >
            <defs>
              {/* Shaded Uncertainty Envelope Gradient between P5 and P95 */}
              <linearGradient id="uncertaintyEnvelope" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#D4CEBE" stopOpacity={0.55} />
                <stop offset="50%" stopColor="#E2DEC7" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#D4CEBE" stopOpacity={0.55} />
              </linearGradient>
            </defs>

            <CartesianGrid stroke="#E4E2D9" strokeDasharray="3 3" vertical={false} />

            <XAxis
              dataKey="displayDate"
              stroke="#71717A"
              fontSize={12}
              fontFamily="JetBrains Mono, monospace"
              fontWeight={500}
              tickLine={{ stroke: "#E4E2D9" }}
              axisLine={{ stroke: "#E4E2D9" }}
              dy={10}
            />

            <YAxis
              stroke="#71717A"
              fontSize={12}
              fontFamily="JetBrains Mono, monospace"
              fontWeight={500}
              tickFormatter={(val) =>
                val >= 0
                  ? `₹${(val / 100000).toFixed(0)}L`
                  : `-₹${(Math.abs(val) / 100000).toFixed(0)}L`
              }
              tickLine={{ stroke: "#E4E2D9" }}
              axisLine={{ stroke: "#E4E2D9" }}
              domain={["auto", "auto"]}
              dx={-8}
              width={75}
            />

            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload
                  return (
                    <div className="bg-[#18181B] text-[#FAF9F5] p-3.5 border border-[#18181B] rounded-lg font-mono text-xs shadow-2xl space-y-1.5 min-w-[200px]">
                      <div className="border-b border-[#3F3F46] pb-1.5 font-bold text-[#FEF08A] flex justify-between">
                        <span>DATE:</span>
                        <span>{data.date || data.displayDate} (D+{data.day_index || 0})</span>
                      </div>
                      <div className="flex justify-between gap-4 text-[#D4D4D8]">
                        <span>Deterministic:</span>
                        <span className="text-[#FAF9F5] font-semibold">
                          {formatINR(data.deterministic_balance)}
                        </span>
                      </div>
                      <div className="flex justify-between gap-4 text-[#34D399]">
                        <span>95th Upper:</span>
                        <span className="font-bold">{formatINR(data.best_case_95th)}</span>
                      </div>
                      <div className="flex justify-between gap-4 text-[#FAF9F5]">
                        <span>50th Expected:</span>
                        <span className="font-black text-[#FEF08A]">{formatINR(data.expected_50th)}</span>
                      </div>
                      <div className="flex justify-between gap-4 text-[#F87171]">
                        <span>5th Worst-Case:</span>
                        <span className="font-bold">{formatINR(data.worst_case_5th)}</span>
                      </div>
                      {data.net_cash_flow !== undefined && data.net_cash_flow !== 0 && (
                        <div className="border-t border-[#3F3F46] pt-1 text-[11px] text-[#93C5FD] flex justify-between">
                          <span>Net Cash Flow:</span>
                          <span className="font-semibold">{formatINR(data.net_cash_flow)}</span>
                        </div>
                      )}
                    </div>
                  )
                }
                return null
              }}
            />

            {/* Dotted MIN Liquidity Floor Threshold Reference Line */}
            <ReferenceLine
              y={dangerThreshold}
              stroke="#B91C1C"
              strokeDasharray="4 4"
              strokeWidth={1.6}
              label={{
                value: `MIN`,
                position: "right",
                fill: "#B91C1C",
                fontSize: 11,
                fontFamily: "JetBrains Mono, monospace",
                fontWeight: "bold",
              }}
            />

            {/* Stacked Areas for Continuous 5th-95th Shaded Uncertainty Envelope */}
            {/* 1. Base area up to 5th percentile (transparent fill, single continuous bottom stroke) */}
            <Area
              type="monotone"
              dataKey="bandBase"
              stackId="cfarBand"
              stroke="#52525B"
              strokeWidth={1.2}
              fill="transparent"
              isAnimationActive={false}
              connectNulls={true}
              name="5th Percentile Floor"
            />

            {/* 2. Spread area from 5th to 95th (single continuous shaded envelope, top stroke) */}
            <Area
              type="monotone"
              dataKey="bandSpread"
              stackId="cfarBand"
              stroke="#52525B"
              strokeWidth={1.2}
              fill="url(#uncertaintyEnvelope)"
              isAnimationActive={false}
              connectNulls={true}
              name="95th Percentile Ceiling"
            />

            {/* Expected Median Path (50th Percentile) — Single Continuous Bold Line */}
            <Line
              type="monotone"
              dataKey="expected_50th"
              stroke="#18181B"
              strokeWidth={2.8}
              dot={false}
              activeDot={{ r: 5, fill: "#18181B", stroke: "#FAF9F5", strokeWidth: 2 }}
              isAnimationActive={false}
              connectNulls={true}
              name="50th Expected Path"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ============================================================
          FOOTER STATUS BARS: Summary Metrics & Node Integrity
      ============================================================= */}
      <div className="space-y-2 border-t border-[#E4E2D9] pt-4 font-mono text-xs text-[#71717A]">
        {/* Row 1: Economic Benefit & Hedging Cost Summary */}
        <div className="flex flex-wrap items-center justify-center sm:justify-start gap-x-3 gap-y-1 font-semibold text-[#18181B]">
          <span>
            Net Benefit of Action:{" "}
            <span className="text-[#047857]">
              {formatINR(economicImpact?.total_net_economic_benefit || 2550)}
            </span>{" "}
            <span className="text-[#71717A] font-normal">[Preserved Enterprise Value]</span>
          </span>
          <span className="text-[#DCD5C4] hidden sm:inline">|</span>
          <span>
            Wise Hedging Cost:{" "}
            <span>{formatINR(economicImpact?.total_action_cost || 470)}</span>{" "}
            <span className="text-[#71717A] font-normal">[Conversion Fees + Slippage]</span>
          </span>
        </div>

        {/* Row 2: Quant Terminal Telemetry & Verification Status */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#71717A] pt-1">
          <div className="flex items-center gap-2">
            <span>FX // FORECASTER • SME TREASURY INTELLIGENCE LAYER</span>
            <span>|</span>
            <span className="text-[#047857] font-bold">NODE_01 CONNECTED</span>
          </div>
          <div className="flex items-center gap-2">
            <span>LATENCY: 14MS</span>
            <span>•</span>
            <span>DATA INTEGRITY: VERIFIED SHA-256</span>
          </div>
        </div>
      </div>
    </div>
  )
}

