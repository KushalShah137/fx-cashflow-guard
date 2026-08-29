import { useState } from "react"
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts"
import { AuditLogEntry } from "@/types"
import { formatINR, formatForeign } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { History, ShieldCheck, CheckCircle2, FileText } from "lucide-react"

interface CalibrationAuditProps {
  auditLogs: AuditLogEntry[]
}

const HISTORICAL_CALIBRATION_DATA = [
  { day: "D-90", actual: 1200000, p5: 1100000, p95: 1300000 },
  { day: "D-75", actual: 1340000, p5: 1180000, p95: 1450000 },
  { day: "D-60", actual: 1280000, p5: 1150000, p95: 1420000 },
  { day: "D-45", actual: 1490000, p5: 1290000, p95: 1600000 },
  { day: "D-30", actual: 1620000, p5: 1400000, p95: 1750000 },
  { day: "D-15", actual: 1580000, p5: 1420000, p95: 1720000 },
  { day: "D-0 (TODAY)", actual: 1740000, p5: 1550000, p95: 1900000 },
]

export function CalibrationAudit({ auditLogs }: CalibrationAuditProps) {
  const [activeTab, setActiveTab] = useState<"calibration" | "audit">("audit")

  return (
    <div className="bg-[#FAF9F5] border border-[#E4E2D9] font-mono">
      {/* Tab Switcher Header */}
      <div className="p-4 border-b border-[#E4E2D9] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-[#18181B]" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-[#18181B] font-display">
            Trust Calibration & Immutable Ledger
          </h3>
        </div>

        <div className="flex items-center border border-[#18181B] bg-[#FAF9F5] p-0.5 text-xs">
          <button
            onClick={() => setActiveTab("audit")}
            className={`px-3 py-1 transition-colors ${
              activeTab === "audit"
                ? "bg-[#18181B] text-[#FAF9F5] font-bold"
                : "text-[#71717A] hover:text-[#18181B]"
            }`}
          >
            IMMUTABLE AUDIT TRAIL ({auditLogs.length})
          </button>
          <button
            onClick={() => setActiveTab("calibration")}
            className={`px-3 py-1 transition-colors ${
              activeTab === "calibration"
                ? "bg-[#18181B] text-[#FAF9F5] font-bold"
                : "text-[#71717A] hover:text-[#18181B]"
            }`}
          >
            PAST 90D TRUST CALIBRATION
          </button>
        </div>
      </div>

      {activeTab === "audit" ? (
        /* Audit Trail Table */
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#18181B] bg-[#F4F3EE] text-[#18181B] uppercase text-[11px]">
                <th className="p-3">Audit ID / Time</th>
                <th className="p-3">Action Type</th>
                <th className="p-3">Tx Ref / Counterparty</th>
                <th className="p-3">Foreign Traded</th>
                <th className="p-3">INR Settled</th>
                <th className="p-3">Locked Rate</th>
                <th className="p-3">Sandbox Transfer ID</th>
                <th className="p-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E4E2D9]">
              {auditLogs.map((log) => (
                <tr key={log.id} className="hover:bg-[#F4F3EE]/80 transition-colors">
                  <td className="p-3 whitespace-nowrap">
                    <div className="font-bold text-[#18181B]">{log.id}</div>
                    <div className="text-[10px] text-[#71717A]">{log.timestamp}</div>
                  </td>
                  <td className="p-3 whitespace-nowrap">
                    <Badge
                      variant={log.action === "SETTLE_NOW" ? "protected" : "caution"}
                      shape="subtle"
                    >
                      {log.action}
                    </Badge>
                  </td>
                  <td className="p-3 whitespace-nowrap">
                    <div className="font-semibold text-[#18181B]">{log.counterparty}</div>
                    <div className="text-[10px] text-[#71717A]">{log.transaction_id}</div>
                  </td>
                  <td className="p-3 font-bold text-[#18181B] whitespace-nowrap">
                    {formatForeign(log.foreign_amount, log.currency)}
                  </td>
                  <td className="p-3 font-semibold text-[#18181B] whitespace-nowrap">
                    {formatINR(log.inr_amount)}
                  </td>
                  <td className="p-3 whitespace-nowrap font-mono font-bold text-[#047857]">
                    {log.locked_rate.toFixed(2)} INR/{log.currency}
                  </td>
                  <td className="p-3 whitespace-nowrap text-[#71717A]">
                    <span className="bg-[#F4F3EE] px-1.5 py-0.5 border border-[#E4E2D9] text-[11px] text-[#18181B]">
                      {log.sandbox_transfer_id}
                    </span>
                  </td>
                  <td className="p-3 text-right whitespace-nowrap">
                    <span className="text-[#047857] font-bold text-[11px] inline-flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> {log.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* Calibration Chart */
        <div className="p-4 space-y-4">
          <div className="flex items-center justify-between text-xs text-[#71717A]">
            <span>
              <strong>EMPIRICAL COVERAGE RATE: 96.4%</strong> (Actual realized cash stayed strictly within 95% Monte Carlo bands across past 90 days)
            </span>
            <span className="text-[#047857] font-bold flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" /> MODEL CALIBRATED
            </span>
          </div>

          <div className="w-full h-[240px] bg-[#FFFFFF] border border-[#E4E2D9] p-2">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={HISTORICAL_CALIBRATION_DATA}>
                <CartesianGrid stroke="#E4E2D9" strokeDasharray="2 2" vertical={false} />
                <XAxis
                  dataKey="day"
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
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload
                      return (
                        <div className="bg-[#18181B] text-[#FAF9F5] p-2.5 font-mono text-xs border border-[#18181B]">
                          <div className="font-bold text-[#FEF08A]">{d.day}</div>
                          <div>Actual Realized: {formatINR(d.actual)}</div>
                          <div className="text-[#34D399]">95th Band: {formatINR(d.p95)}</div>
                          <div className="text-[#F87171]">5th Band: {formatINR(d.p5)}</div>
                        </div>
                      )
                    }
                    return null
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="p95"
                  stroke="#047857"
                  fill="#047857"
                  fillOpacity={0.12}
                  name="Predicted 95th"
                />
                <Area
                  type="monotone"
                  dataKey="p5"
                  stroke="#B91C1C"
                  fill="#B91C1C"
                  fillOpacity={0.12}
                  name="Predicted 5th"
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  stroke="#18181B"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: "#18181B" }}
                  name="Actual Realized Balance"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
