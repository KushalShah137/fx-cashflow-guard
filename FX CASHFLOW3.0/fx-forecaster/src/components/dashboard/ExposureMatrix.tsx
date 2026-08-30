import { Transaction, RecommendationLifecycle } from "@/types"
import { formatINR, formatForeign } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { MetalButton } from "@/components/ui/liquid-glass-button"
import {
  ArrowDownLeft,
  ArrowUpRight,
  ShieldAlert,
  ShieldCheck,
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
    <div className="bg-[#FAF9F5] border border-[#E4E2D9] font-mono">
      {/* Header */}
      <div className="p-4 border-b border-[#E4E2D9] flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-[#18181B] font-display">
              3-Way Exposure Classification Matrix
            </h3>
            <span className="text-xs text-[#71717A]">
              ({transactions.length} SCHEDULED EXPOSURES)
            </span>
          </div>
          <p className="text-xs text-[#71717A] mt-0.5">
            Natural Netting ($E_{`{net}`} = R_{`{FC}`} - P_{`{FC}`}$) & Carry-Cost Gating ($VaR &gt; \Delta i \cdot t$)
          </p>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          <Badge variant="caution" shape="subtle">
            CONVERT_AND_HOLD (UNFUNDED)
          </Badge>
          <Badge variant="protected" shape="subtle">
            SETTLE_NOW (FUNDED IDLE)
          </Badge>
          <Badge variant="accent" shape="subtle">
            RE_QUOTE_OR_HEDGE (AR)
          </Badge>
          <Badge variant="secondary" shape="subtle">
            NATURALLY NETTED
          </Badge>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-[#18181B] bg-[#F4F3EE] text-[#18181B] uppercase text-[11px]">
              <th className="p-3">TX ID</th>
              <th className="p-3">Counterparty</th>
              <th className="p-3">Type</th>
              <th className="p-3">Foreign Amt</th>
              <th className="p-3">Current INR</th>
              <th className="p-3">Due / DTD</th>
              <th className="p-3">Adverse VaR</th>
              <th className="p-3">Carry Cost</th>
              <th className="p-3">Classification & Netting</th>
              <th className="p-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E4E2D9]">
            {transactions.map((tx) => {
              const isPayable = tx.type === "PAYABLE"
              const rec = actions?.find((a) => a.transaction_id === tx.id)
              const recStatus = rec ? rec.status : null
              const isSettled = tx.status === "SETTLED" || tx.status === "HEDGED" || recStatus === "EXECUTED"
              const isRejected = recStatus === "REJECTED"

              return (
                <tr
                  key={tx.id}
                  className={`hover:bg-[#F4F3EE]/80 transition-colors ${
                    isSettled ? "bg-[#F4F3EE]/40 opacity-75" : ""
                  } ${isRejected ? "opacity-60 bg-[#F4F3EE]/25" : ""}`}
                >
                  {/* ID */}
                  <td className="p-3 font-bold text-[#18181B] whitespace-nowrap">
                    {tx.id}
                  </td>

                  {/* Counterparty */}
                  <td className="p-3 whitespace-nowrap">
                    <div className="font-semibold text-[#18181B]">{tx.counterparty}</div>
                    <div className="text-[10px] text-[#71717A]">{tx.netting_group}</div>
                  </td>

                  {/* Type */}
                  <td className="p-3 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center gap-1 font-bold text-[11px] ${
                        isPayable ? "text-[#B45309]" : "text-[#047857]"
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

                  {/* Foreign Amount */}
                  <td className="p-3 font-bold text-[#18181B] whitespace-nowrap">
                    {formatForeign(tx.foreign_amount, tx.currency)}
                  </td>

                  {/* Current INR */}
                  <td className="p-3 whitespace-nowrap">
                    <div className="font-semibold text-[#18181B]">
                      {formatINR(tx.current_inr_value)}
                    </div>
                    <div className="text-[10px] text-[#71717A]">
                      Book: {formatINR(tx.inr_book_value)}
                    </div>
                  </td>

                  {/* Due Date & DTD */}
                  <td className="p-3 whitespace-nowrap">
                    <div className="text-[#18181B]">{tx.due_date}</div>
                    <div className="text-[10px] text-[#71717A]">
                      {tx.days_until_due} DAYS REMAINING
                    </div>
                  </td>

                  {/* Adverse VaR */}
                  <td className="p-3 whitespace-nowrap">
                    {tx.adverse_var_inr > 0 ? (
                      <span className="text-[#B91C1C] font-bold">
                        +{formatINR(tx.adverse_var_inr)}
                      </span>
                    ) : (
                      <span className="text-[#047857] font-semibold">₹0 (NET-ZERO)</span>
                    )}
                  </td>

                  {/* Carry Cost */}
                  <td className="p-3 whitespace-nowrap">
                    <div>
                      {tx.carry_cost_inr > 0 ? formatINR(tx.carry_cost_inr) : "—"}
                    </div>
                    {tx.carry_cost_gate_passed ? (
                      <span className="text-[10px] text-[#047857] flex items-center gap-0.5">
                        <CheckCircle2 className="w-3 h-3" /> Gate Passed
                      </span>
                    ) : tx.carry_cost_inr > 0 ? (
                      <span className="text-[10px] text-[#71717A]">Gate Unmet</span>
                    ) : null}
                  </td>

                  {/* Classification Badge & Netting */}
                  <td className="p-3 whitespace-nowrap">
                    <div className="space-y-1">
                      {tx.classification === "CONVERT_AND_HOLD" && (
                        <Badge variant="caution" shape="subtle">
                          <ShieldAlert className="w-3 h-3 mr-1 inline" />
                          CONVERT_AND_HOLD
                        </Badge>
                      )}
                      {tx.classification === "SETTLE_NOW" && (
                        <Badge variant="protected" shape="subtle">
                          <Zap className="w-3 h-3 mr-1 inline" />
                          SETTLE_NOW
                        </Badge>
                      )}
                      {tx.classification === "RE_QUOTE_OR_HEDGE" && (
                        <Badge variant="accent" shape="subtle">
                          RE_QUOTE_OR_HEDGE
                        </Badge>
                      )}
                      {tx.classification === "NATURALLY_NETTED" && (
                        <Badge variant="secondary" shape="subtle">
                          NATURALLY NETTED
                        </Badge>
                      )}
                      {tx.is_netted && (
                        <div className="text-[10px] text-[#047857] font-semibold">
                          [Offset via Netting Pool]
                        </div>
                      )}
                      {recStatus && (
                        <div className="mt-1">
                          <Badge
                            variant={
                              recStatus === "APPROVED"
                                ? "protected"
                                : recStatus === "RECOMMENDED"
                                ? "caution"
                                : "secondary"
                            }
                            shape="subtle"
                            className="text-[9px] px-1 py-0 uppercase font-bold"
                          >
                            STATE: {recStatus}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </td>

                  {/* Action Button */}
                  <td className="p-3 text-right whitespace-nowrap">
                    {isSettled ? (
                      <Badge variant="secondary" shape="subtle">
                        <CheckCircle2 className="w-3 h-3 mr-1 inline text-[#047857]" />
                        EXECUTED
                      </Badge>
                    ) : isRejected ? (
                      <Badge variant="secondary" shape="subtle" className="text-[#71717A] opacity-70">
                        REJECTED
                      </Badge>
                    ) : recStatus === "RECOMMENDED" ? (
                      <div className="flex justify-end gap-1.5">
                        <MetalButton
                          variant="success"
                          onClick={() => rec && onApproveAction?.(rec.action_id)}
                          className="h-8 px-2 text-[10px] uppercase tracking-wider font-bold"
                        >
                          APPROVE
                        </MetalButton>
                        <MetalButton
                          variant="default"
                          onClick={() => rec && onRejectAction?.(rec.action_id)}
                          className="h-8 px-2 text-[10px] uppercase tracking-wider font-bold text-[#B91C1C]"
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
                        className="h-8 px-3 text-[11px] uppercase tracking-wider"
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

      {/* Rationale Bottom Callout */}
      <div className="p-3 bg-[#F4F3EE] border-t border-[#E4E2D9] text-xs text-[#71717A] flex items-center gap-2">
        <Info className="w-4 h-4 text-[#18181B] shrink-0" />
        <span>
          <strong>DECISION RULE:</strong> Unfunded payables where $VaR_{`{95}`} &gt; CarryCost$ are routed to <em>Convert & Hold</em> to lock live Wise mid-market rate. Funded payables sit idle and are flagged for immediate settlement.
        </span>
      </div>
    </div>
  )
}
