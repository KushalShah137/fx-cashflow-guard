import { useState, useEffect } from "react"
import {
  Transaction,
  WiseQuoteResponse,
  WiseExecutionResponse,
  WalletBalances,
} from "@/types"
import { fetchWiseQuote, executeWiseTransfer } from "@/lib/api"
import { formatINR } from "@/lib/utils"
import { MetalButton } from "@/components/ui/liquid-glass-button"
import {
  X,
  Clock,
  Percent,
  AlertCircle,
} from "lucide-react"

interface WiseQuoteModalProps {
  isOpen: boolean
  onClose: () => void
  selectedTransaction?: Transaction | null
  walletBalances?: WalletBalances
  onExecutionSuccess: (res: WiseExecutionResponse) => void
}

export function WiseQuoteModal({
  isOpen,
  onClose,
  selectedTransaction,
  walletBalances: _walletBalances,
  onExecutionSuccess,
}: WiseQuoteModalProps) {
  const [targetCurrency, setTargetCurrency] = useState<string>("USD")
  const [targetAmount, setTargetAmount] = useState<number>(20000)
  const [quote, setQuote] = useState<WiseQuoteResponse | null>(null)
  const [isLoadingQuote, setIsLoadingQuote] = useState<boolean>(false)
  const [isExecuting, setIsExecuting] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Initialize from transaction if passed
  useEffect(() => {
    if (selectedTransaction) {
      setTargetCurrency(selectedTransaction.currency)
      setTargetAmount(selectedTransaction.foreign_amount)
    }
  }, [selectedTransaction])

  // Fetch live quote whenever currency or amount changes
  useEffect(() => {
    if (!isOpen) return

    let cancelled = false
    setIsLoadingQuote(true)
    setErrorMsg(null)

    const timer = setTimeout(async () => {
      try {
        const res = await fetchWiseQuote({
          source_currency: "INR",
          target_currency: targetCurrency,
          target_amount: targetAmount,
        })
        if (!cancelled) {
          setQuote(res)
        }
      } catch (_err: any) {
        if (!cancelled) setErrorMsg("Failed to generate Wise quote.")
      } finally {
        if (!cancelled) setIsLoadingQuote(false)
      }
    }, 250)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [isOpen, targetCurrency, targetAmount])

  if (!isOpen) return null

  const handleExecute = async (actionType: "CONVERT_AND_HOLD" | "SETTLE_NOW") => {
    if (!quote) return
    setIsExecuting(actionType)
    setErrorMsg(null)

    try {
      const res = await executeWiseTransfer({
        quote_id: quote.quote_id,
        action_type: actionType,
        transaction_id: selectedTransaction?.id || `TX-CUSTOM-${Date.now().toString().slice(-4)}`,
        target_currency: targetCurrency,
        target_amount: targetAmount,
        source_amount: quote.source_amount,
      })

      setIsExecuting(null)
      onExecutionSuccess(res)
      onClose()
    } catch (_err: any) {
      setIsExecuting(null)
      setErrorMsg("Execution error in Wise Sandbox.")
    }
  }

  const bankSavings = quote
    ? Math.max(0, quote.traditional_bank_fee_estimate_inr - quote.fee_inr)
    : 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-[#FAF9F5] border border-[#18181B] shadow-2xl p-6 font-mono rounded-none max-h-[90vh] overflow-y-auto">
        {/* Modal Top Bar */}
        <div className="flex items-center justify-between border-b border-[#E4E2D9] pb-3 mb-4">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 bg-[#047857] rounded-none" />
            <span className="text-xs font-bold tracking-wider uppercase text-[#18181B]">
              WISE SANDBOX // GUARANTEED QUOTE & EXECUTION
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-[#71717A] hover:text-[#18181B] transition-colors p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Selected Transaction Context Banner */}
        {selectedTransaction && (
          <div className="bg-[#F4F3EE] border border-[#E4E2D9] p-3 mb-4 text-xs space-y-1">
            <div className="flex justify-between items-center">
              <span className="font-bold text-[#18181B]">
                TRANSACTION TARGET: {selectedTransaction.id} — {selectedTransaction.counterparty}
              </span>
              <span className="text-[#B45309] font-bold">
                RECOMMENDED: {selectedTransaction.recommended_action}
              </span>
            </div>
            <p className="text-[11px] text-[#71717A]">{selectedTransaction.rationale}</p>
          </div>
        )}

        {/* Currency & Amount Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-[11px] uppercase tracking-wider text-[#71717A] mb-1">
              Target Currency
            </label>
            <div className="flex gap-2">
              {["USD", "EUR", "GBP"].map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setTargetCurrency(c)}
                  className={`flex-1 py-2 text-xs font-bold border transition-colors ${
                    targetCurrency === c
                      ? "bg-[#18181B] text-[#FAF9F5] border-[#18181B]"
                      : "bg-[#FFFFFF] text-[#71717A] border-[#E4E2D9] hover:text-[#18181B]"
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-[11px] uppercase tracking-wider text-[#71717A] mb-1">
              Target Amount ({targetCurrency})
            </label>
            <input
              type="number"
              value={targetAmount}
              onChange={(e) => setTargetAmount(Math.max(1, parseFloat(e.target.value) || 0))}
              className="w-full bg-[#FFFFFF] border border-[#18181B] font-mono text-sm px-3 py-2 text-[#18181B] focus:outline-none focus:ring-1 focus:ring-[#18181B]"
              min="100"
            />
          </div>
        </div>

        {/* Live Quote Breakdown Card */}
        {isLoadingQuote ? (
          <div className="bg-[#FFFFFF] border border-[#E4E2D9] p-8 text-center text-xs text-[#71717A] my-4">
            FETCHING LIVE MID-MARKET RATES FROM WISE SANDBOX ENGINE...
          </div>
        ) : quote ? (
          <div className="bg-[#FFFFFF] border border-[#18181B] p-4 space-y-4 mb-5">
            <div className="flex items-center justify-between border-b border-[#E4E2D9] pb-2 text-xs">
              <span className="text-[#71717A]">QUOTE ID: {quote.quote_id}</span>
              <span className="text-[#047857] font-semibold flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" /> Rate Guaranteed {quote.rate_guaranteed_minutes}m
              </span>
            </div>

            {/* Main Pricing Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div>
                <div className="text-[10px] text-[#71717A] uppercase">Guaranteed Mid-Market Rate</div>
                <div className="text-base font-bold text-[#18181B] mt-0.5">
                  1 {quote.target_currency} = {quote.mid_market_rate.toFixed(2)} INR
                </div>
              </div>

              <div>
                <div className="text-[10px] text-[#71717A] uppercase">Required INR Debited</div>
                <div className="text-base font-bold text-[#18181B] mt-0.5">
                  {formatINR(quote.source_amount)}
                </div>
              </div>

              <div>
                <div className="text-[10px] text-[#71717A] uppercase">Estimated Delivery</div>
                <div className="text-xs font-bold text-[#047857] mt-1">
                  {quote.delivery_estimate}
                </div>
              </div>
            </div>

            {/* Fee Comparison vs Traditional Wire */}
            <div className="bg-[#F4F3EE] border border-[#E4E2D9] p-3 text-xs space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-[#71717A]">Transparent Wise Platform Fee:</span>
                <span className="font-bold text-[#18181B]">{formatINR(quote.fee_inr)} (0.28%)</span>
              </div>
              <div className="flex justify-between items-center text-[#71717A]">
                <span>Est. Traditional Bank Markup (2.0%):</span>
                <span className="line-through">{formatINR(quote.traditional_bank_fee_estimate_inr)}</span>
              </div>
              <div className="border-t border-[#DCD9CE] pt-1.5 flex justify-between items-center text-[#047857] font-bold">
                <span className="flex items-center gap-1">
                  <Percent className="w-3.5 h-3.5" /> Direct SME Treasury Savings:
                </span>
                <span>+{formatINR(bankSavings)}</span>
              </div>
            </div>
          </div>
        ) : null}

        {errorMsg && (
          <div className="bg-[#FEE2E2] border border-[#B91C1C] text-[#B91C1C] p-3 text-xs mb-4 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {errorMsg}
          </div>
        )}

        {/* Dual Execution Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <div>
            <MetalButton
              type="button"
              variant="gold"
              onClick={() => handleExecute("CONVERT_AND_HOLD")}
              disabled={isExecuting !== null || isLoadingQuote || !quote}
              className="w-full h-12 text-xs uppercase tracking-wider font-bold"
            >
              {isExecuting === "CONVERT_AND_HOLD"
                ? "LOCKING RATE & CONVERTING..."
                : "CONVERT & HOLD IN WALLET"}
            </MetalButton>
            <p className="text-[10px] text-[#71717A] mt-1 text-center">
              Freezes adverse VaR. Holds {targetCurrency} in sandbox wallet.
            </p>
          </div>

          <div>
            <MetalButton
              type="button"
              variant="success"
              onClick={() => handleExecute("SETTLE_NOW")}
              disabled={isExecuting !== null || isLoadingQuote || !quote}
              className="w-full h-12 text-xs uppercase tracking-wider font-bold"
            >
              {isExecuting === "SETTLE_NOW"
                ? "DISPATCHING SETTLEMENT..."
                : "SETTLE NOW TO SUPPLIER"}
            </MetalButton>
            <p className="text-[10px] text-[#71717A] mt-1 text-center">
              Direct transfer to supplier bank account via Wise rails.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
