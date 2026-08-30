import { WalletBalances } from "@/types"
import { formatINR, formatForeign } from "@/lib/utils"
import { Wallet, ShieldCheck, ArrowRightLeft } from "lucide-react"

interface MultiWalletProps {
  balances: WalletBalances
  onOpenQuickConvert?: (curr: string) => void
}

export function MultiWallet({ balances, onOpenQuickConvert }: MultiWalletProps) {
  const currencies: Array<{
    code: keyof WalletBalances
    name: string
    symbol: string
    rateVsINR: number
    color: string
    status: string
  }> = [
    {
      code: "INR",
      name: "Indian Rupee (Base Operating)",
      symbol: "₹",
      rateVsINR: 1.0,
      color: "text-[#18181B]",
      status: "PRIMARY OPERATING",
    },
    {
      code: "USD",
      name: "US Dollar (Hedging Holding)",
      symbol: "$",
      rateVsINR: 87.41,
      color: "text-[#B45309]",
      status: "WISE MULTI-CURRENCY",
    },
    {
      code: "EUR",
      name: "Euro (Settlement Ready)",
      symbol: "€",
      rateVsINR: 93.0,
      color: "text-[#1D4ED8]",
      status: "WISE MULTI-CURRENCY",
    },
    {
      code: "GBP",
      name: "British Pound",
      symbol: "£",
      rateVsINR: 110.2,
      color: "text-[#047857]",
      status: "WISE MULTI-CURRENCY",
    },
  ]

  // Calculate total portfolio value in INR
  const totalValueINR =
    balances.INR +
    balances.USD * 87.41 +
    balances.EUR * 93.0 +
    balances.GBP * 110.2

  return (
    <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-5 font-mono space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E4E2D9] pb-3">
        <div className="flex items-center gap-2">
          <Wallet className="w-4 h-4 text-[#18181B]" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-[#18181B] font-display">
            Multi-Currency Treasury Holding Wallet
          </h3>
        </div>
        <div className="text-right">
          <span className="text-[11px] text-[#71717A] uppercase">TOTAL CONSOLIDATED: </span>
          <span className="text-sm font-bold text-[#18181B]">{formatINR(totalValueINR)}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {currencies.map((curr) => {
          const balance = balances[curr.code] || 0
          const inrEquivalent = balance * curr.rateVsINR

          return (
            <div
              key={curr.code}
              className="bg-[#F4F3EE] border border-[#E4E2D9] p-3 flex flex-col justify-between hover:border-[#18181B] transition-colors"
            >
              <div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-bold text-[#18181B] flex items-center gap-1">
                    <span className="w-2 h-2 rounded-none bg-[#18181B]" />
                    {curr.code}
                  </span>
                  <span className="text-[10px] text-[#71717A] bg-[#FFFFFF] px-1 border border-[#E4E2D9]">
                    {curr.code === "INR" ? "BASE" : `${curr.rateVsINR.toFixed(2)} / INR`}
                  </span>
                </div>
                <div className="text-lg font-bold text-[#18181B] mt-2">
                  {curr.code === "INR"
                    ? formatINR(balance)
                    : formatForeign(balance, curr.code)}
                </div>
                {curr.code !== "INR" && (
                  <div className="text-[11px] text-[#71717A] mt-0.5">
                    ≈ {formatINR(inrEquivalent)}
                  </div>
                )}
              </div>

              <div className="mt-3 pt-2 border-t border-[#E4E2D9] flex items-center justify-between text-[10px]">
                <span className="text-[#047857] font-semibold flex items-center gap-0.5">
                  <ShieldCheck className="w-3 h-3" /> {curr.status}
                </span>
                {curr.code !== "INR" && onOpenQuickConvert && (
                  <button
                    onClick={() => onOpenQuickConvert(curr.code)}
                    className="text-[#18181B] hover:underline font-bold flex items-center gap-0.5"
                  >
                    <ArrowRightLeft className="w-2.5 h-2.5" /> Convert
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
