import { Transaction, RecommendationLifecycle } from "@/types"
import { formatINR, formatForeign } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { MetalButton } from "@/components/ui/liquid-glass-button"
import {
  ArrowDownLeft,
  ArrowUpRight,
  ShieldAlert,
  Zap,
  Info,
  CheckCircle2,
} from "lucide-react"

interface ExposureMatrixProps {
  transactions: Transaction[]
  actions?: RecommendationLifecycle[]
  onApproveAction?: (actionId: string) => void
  onRejectAction?: (actionId: string) => void
  onSelectTransactionForAction: (tx: Transaction) => void
}

export function ExposureMatrix({
  transactions,
  actions,
  onApproveAction,
  onRejectAction,
  onSelectTransactionForAction,
}: ExposureMatrixProps) {
  return (
    <div className="bg-[#FAF9F5] border border-[#E4E2D9] rounded-xl overflow-hidden shadow-xs">
      {/* 1. Header: Clean Title Only */}
      <div className="p-4 sm:p-5 border-b border-[#E4E2D9] flex flex-wrap items-center justify-between gap-3 bg-[#FAF9F5]">
        <div className="flex items-center gap-3">
          <h3 className="text-lg sm:text-xl font-black text-[#18181B] font-display tracking-tight">
            3-Way Exposure Classification Matrix
          </h3>
          <span className="font-mono text-xs font-bold text-[#71717A] bg-[#F4F3EE] border border-[#DCD5C4] px-2 py-0.5 rounded">
            {transactions.length} SCHEDULED EXPOSURES
          </span>
        </div>

        {/* Status Legend Pills */}
        <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
          <span className="px-2 py-0.5 rounded bg-[#FEF3C7] text-[#92400E] font-semibold">
            CONVERT_AND_HOLD
          </span>
          <span className="px-2 py-0.5 rounded bg-[#DCFCE7] text-[#166534] font-semibold">
            SETTLE_NOW
          </span>
          <span className="px-2 py-0.5 rounded bg-[#DBEAFE] text-[#1E40AF] font-semibold">
            RE_QUOTE_OR_HEDGE
          </span>
          <span className="px-2 py-0.5 rounded bg-[#E2E8F0] text-[#475569] font-semibold">
            NATURALLY NETTED
          </span>
        </div>
      </div>

      {/* 2. Exposure Data Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="border-b border-[#18181B] bg-[#F4F3EE] text-[#71717A] uppercase text-[11px] font-mono tracking-wider font-bold">
              <th className="py-3.5 px-3.5 text-left">TX ID</th>
              <th className="py-3.5 px-3.5 text-left">Counterparty</th>
              <th className="py-3.5 px-3.5 text-left">Type</th>
              <th className="py-3.5 px-3.5 text-right">Foreign Amt</th>
              <th className="py-3.5 px-3.5 text-right">Current INR</th>
              <th className="py-3.5 px-3.5 text-right hidden sm:table-cell">Due / DTD</th>
              <th className="py-3.5 px-3.5 text-right hidden md:table-cell">Adverse VaR</th>
              <th className="py-3.5 px-3.5 text-right hidden lg:table-cell">Carry Cost</th>
              <th className="py-3.5 px-3.5 text-right">Classification</th>
              <th className="py-3.5 px-3.5 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E4E2D9] font-sans">
            {transactions.map((tx) => {
              const isPayable = tx.type === "PAYABLE"
              const rec = actions?.find((a) => a.transaction_id === tx.id)
              const recStatus = rec ? rec.status : null
              const isSettled =
                tx.status === "SETTLED" || tx.status === "HEDGED" || recStatus === "EXECUTED"
              const isRejected = recStatus === "REJECTED"

              return (
                <tr
                  key={tx.id}
                  className={`transition-colors duration-150 hover:bg-[#EDEDF0] ${
                    isSettled ? "bg-[#F4F3EE]/40 opacity-70" : ""
                  } ${isRejected ? "opacity-60 bg-[#F4F3EE]/25" : ""}`}
                >
                  {/* TX ID */}
                  <td className="py-4 px-3.5 font-mono text-xs text-[#71717A] whitespace-nowrap">
                    {tx.id}
                  </td>

                  {/* Counterparty (Sans-Serif for readable prose, Mono for Ticker) */}
                  <td className="py-4 px-3.5 whitespace-nowrap">
                    <div className="font-semibold text-[#18181B] text-sm font-sans">
                      {tx.counterparty}
                    </div>
                    <div className="font-mono text-[11px] text-[#888888] mt-0.5">
                      {tx.netting_group}
                    </div>
                  </td>

                  {/* Type (Softened semantic colors) */}
                  <td className="py-4 px-3.5 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center gap-1 font-semibold text-xs ${
                        isPayable ? "text-[#D32F2F]" : "text-[#2E7D32]"
                      }`}
                    >
                      {isPayable ? (
                        <ArrowDownLeft className="w-3.5 h-3.5" />
                      ) : (
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      )}
                      {tx.type}
                    </span>
                  </td>

                  {/* Foreign Amount (Right-aligned, Mono) */}
                  <td className="py-4 px-3.5 text-right font-mono font-semibold text-[#18181B] whitespace-nowrap">
                    {formatForeign(tx.foreign_amount, tx.currency)}
                  </td>

                  {/* Current INR (Right-aligned, primary strong, book muted) */}
                  <td className="py-4 px-3.5 text-right whitespace-nowrap">
                    <div className="font-mono font-semibold text-[#18181B]">
                      {formatINR(tx.current_inr_value)}
                    </div>
                    <div className="font-mono text-[11px] text-[#888888] mt-0.5">
                      Book: {formatINR(tx.inr_book_value)}
                    </div>
                  </td>

                  {/* Due Date & Remaining Days (Right-aligned, hidden on smallest mobile) */}
                  <td className="py-4 px-3.5 text-right whitespace-nowrap hidden sm:table-cell">
                    <div className="font-mono text-xs text-[#18181B]">{tx.due_date}</div>
                    <div className="font-sans text-[11px] text-[#888888] mt-0.5">
                      {tx.days_until_due} days remaining
                    </div>
                  </td>

                  {/* Adverse VaR (Right-aligned, Mono) */}
                  <td className="py-4 px-3.5 text-right font-mono whitespace-nowrap hidden md:table-cell">
                    {tx.adverse_var_inr > 0 ? (
                      <span className="text-[#D32F2F] font-bold">
                        +{formatINR(tx.adverse_var_inr)}
                      </span>
                    ) : (
                      <span className="text-[#2E7D32] font-semibold">₹0 (NET-ZERO)</span>
                    )}
                  </td>

                  {/* Carry Cost (Right-aligned) */}
                  <td className="py-4 px-3.5 text-right font-mono whitespace-nowrap hidden lg:table-cell">
                    <div className="text-[#18181B]">
                      {tx.carry_cost_inr > 0 ? formatINR(tx.carry_cost_inr) : "—"}
                    </div>
                    {tx.carry_cost_gate_passed ? (
                      <span className="text-[10px] text-[#2E7D32] flex items-center justify-end gap-0.5 mt-0.5 font-sans">
                        <CheckCircle2 className="w-3 h-3" /> Gate Passed
                      </span>
                    ) : tx.carry_cost_inr > 0 ? (
                      <span className="text-[10px] text-[#888888] font-sans">Gate Unmet</span>
                    ) : null}
                  </td>

                  {/* Classification: Unified Single Status Pill */}
                  <td className="py-4 px-3.5 text-right whitespace-nowrap">
                    <div className="flex flex-col items-end gap-1">
                      {tx.classification === "CONVERT_AND_HOLD" && (
                        <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold font-mono bg-[#FEF3C7] text-[#92400E]">
                          <ShieldAlert className="w-3 h-3 mr-1" />
                          CONVERT & HOLD
                        </span>
                      )}
                      {tx.classification === "SETTLE_NOW" && (
                        <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold font-mono bg-[#DCFCE7] text-[#166534]">
                          <Zap className="w-3 h-3 mr-1" />
                          SETTLE NOW
                        </span>
                      )}
                      {tx.classification === "RE_QUOTE_OR_HEDGE" && (
                        <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold font-mono bg-[#DBEAFE] text-[#1E40AF]">
                          RE_QUOTE
                        </span>
                      )}
                      {tx.classification === "NATURALLY_NETTED" && (
                        <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold font-mono bg-[#E2E8F0] text-[#475569]">
                          NETTED POOL
                        </span>
                      )}
                      {tx.is_netted && tx.classification !== "NATURALLY_NETTED" && (
                        <span className="text-[10px] text-[#2E7D32] font-semibold font-mono">
                          [Offset via Netting Pool]
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Action Button: Retains 100% of Execution Logic */}
                  <td className="py-4 px-3.5 text-right whitespace-nowrap">
                    {isSettled ? (
                      <Badge variant="secondary" shape="subtle" className="text-[#2E7D32] bg-[#DCFCE7] font-semibold">
                        <CheckCircle2 className="w-3 h-3 mr-1 inline" />
                        EXECUTED
                      </Badge>
                    ) : isRejected ? (
                      <Badge variant="secondary" shape="subtle" className="text-[#888888]">
                        REJECTED
                      </Badge>
                    ) : recStatus === "RECOMMENDED" ? (
                      <div className="flex justify-end gap-1.5">
                        <MetalButton
                          variant="success"
                          onClick={() => rec && onApproveAction?.(rec.action_id)}
                          className="h-8 px-2.5 text-[10px] uppercase tracking-wider font-bold"
                        >
                          APPROVE
                        </MetalButton>
                        <MetalButton
                          variant="default"
                          onClick={() => rec && onRejectAction?.(rec.action_id)}
                          className="h-8 px-2.5 text-[10px] uppercase tracking-wider font-bold text-[#D32F2F]"
                        >
                          REJECT
                        </MetalButton>
                      </div>
                    ) : (
                      <MetalButton
                        variant={
                          tx.classification === "SETTLE_NOW"
                            ? "success"
                            : tx.classification === "CONVERT_AND_HOLD"
                            ? "gold"
                            : "default"
                        }
                        onClick={() => onSelectTransactionForAction(tx)}
                        className="h-8 px-3 text-[11px] uppercase tracking-wider font-medium"
                      >
                        {tx.classification === "SETTLE_NOW"
                          ? "SETTLE NOW"
                          : tx.classification === "CONVERT_AND_HOLD"
                          ? "CONVERT & HOLD"
                          : "PROTECT"}
                      </MetalButton>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* 3. Footer Rationale */}
      <div className="p-3.5 bg-[#F4F3EE] border-t border-[#E4E2D9] text-xs text-[#71717A] flex items-center gap-2 font-mono">
        <Info className="w-4 h-4 text-[#18181B] shrink-0" />
        <span>
          <strong>DECISION RULE:</strong> Unfunded payables where VaR &gt; Carry Cost are routed to <em>Convert & Hold</em> to lock live Wise mid-market rates. Funded payables sit idle and are flagged for immediate settlement.
        </span>
      </div>
    </div>
  )
}

