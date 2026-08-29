import { useEffect } from "react"
import confetti from "canvas-confetti"
import { WiseExecutionResponse } from "@/types"
import { formatINR, formatForeign } from "@/lib/utils"
import { MetalButton } from "@/components/ui/liquid-glass-button"
import { CheckCircle2, ShieldCheck, ArrowRight, RefreshCw, X } from "lucide-react"

interface SandboxReceiptProps {
  receipt: WiseExecutionResponse | null
  onClose: () => void
  onNavigateDashboard: () => void
}

export function SandboxReceipt({
  receipt,
  onClose,
  onNavigateDashboard,
}: SandboxReceiptProps) {
  useEffect(() => {
    if (receipt) {
      // Editorial subtle particle burst
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.6 },
        colors: ["#D97706", "#047857", "#18181B", "#FEF08A"],
      })
    }
  }, [receipt])

  if (!receipt) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-[#FAF9F5] border border-[#18181B] shadow-2xl p-6 font-mono rounded-none">
        {/* Top Header */}
        <div className="flex items-center justify-between border-b border-[#E4E2D9] pb-3 mb-4">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-[#047857] rounded-none" />
            <span className="text-xs font-bold tracking-wider uppercase text-[#18181B]">
              OFFICIAL SETTLEMENT RECEIPT // WISE SANDBOX
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-[#71717A] hover:text-[#18181B] transition-colors p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Success Banner */}
        <div className="bg-[#D1FAE5]/40 border border-[#047857] p-4 text-center space-y-1 mb-5">
          <div className="inline-flex items-center justify-center w-10 h-10 bg-[#047857] text-[#FAF9F5] rounded-none mb-1">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-[#047857] uppercase">
            {receipt.action_executed === "CONVERT_AND_HOLD"
              ? "FX RATE LOCKED & HELD IN WALLET"
              : "INVOICE SETTLEMENT COMPLETED"}
          </h3>
          <p className="text-xs text-[#18181B]">
            Transfer ID: <strong>{receipt.sandbox_transfer_id}</strong>
          </p>
        </div>

        {/* Receipt Key-Value Rows */}
        <div className="bg-[#FFFFFF] border border-[#E4E2D9] p-4 space-y-2.5 text-xs mb-5">
          <div className="flex justify-between border-b border-[#F4F3EE] pb-1.5">
            <span className="text-[#71717A]">EXECUTION TIMESTAMP:</span>
            <span className="font-bold text-[#18181B]">{receipt.executed_at}</span>
          </div>

          <div className="flex justify-between border-b border-[#F4F3EE] pb-1.5">
            <span className="text-[#71717A]">LOCKED MID-MARKET RATE:</span>
            <span className="font-bold text-[#047857]">
              {receipt.locked_rate.toFixed(2)} INR / FX
            </span>
          </div>

          <div className="flex justify-between border-b border-[#F4F3EE] pb-1.5">
            <span className="text-[#71717A]">INR DEBITED (SOURCE):</span>
            <span className="font-bold text-[#18181B]">
              {formatINR(receipt.amount_debited_inr)}
            </span>
          </div>

          <div className="flex justify-between border-b border-[#F4F3EE] pb-1.5">
            <span className="text-[#71717A]">FOREIGN CREDITED (TARGET):</span>
            <span className="font-bold text-[#18181B]">
              {receipt.amount_credited_foreign.toLocaleString("en-US", {
                minimumFractionDigits: 2,
              })}
            </span>
          </div>

          <div className="flex justify-between pt-1 text-[#047857] font-bold">
            <span className="flex items-center gap-1">
              <RefreshCw className="w-3.5 h-3.5" /> RECHECK VAR REDUCTION:
            </span>
            <span>-{formatINR(receipt.recalculated_var_reduction_inr)}</span>
          </div>
        </div>

        {/* Action Button to Dashboard */}
        <div className="space-y-2">
          <MetalButton
            variant="default"
            onClick={() => {
              onClose()
              onNavigateDashboard()
            }}
            className="w-full h-11 text-xs uppercase tracking-wider font-bold flex items-center justify-center gap-2"
          >
            <span>VIEW TIGHTENED RISK BAND ON DASHBOARD</span>
            <ArrowRight className="w-4 h-4" />
          </MetalButton>

          <p className="font-mono text-[10px] text-[#71717A] text-center">
            IMMUTABLE RECEIPT LOGGED TO TELEMETRY AUDIT TRAIL
          </p>
        </div>
      </div>
    </div>
  )
}
