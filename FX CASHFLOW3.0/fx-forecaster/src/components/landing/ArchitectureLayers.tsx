import {
  Layers,
  Activity,
  Cpu,
  ShieldCheck,
  Zap,
  ArrowRight,
  TrendingDown,
  RefreshCw,
} from "lucide-react"
import { MetalButton } from "@/components/ui/liquid-glass-button"

interface ArchitectureLayersProps {
  onNavigateDashboard: () => void
  onNavigateWise: () => void
}

export function ArchitectureLayers({
  onNavigateDashboard,
  onNavigateWise,
}: ArchitectureLayersProps) {
  return (
    <section className="w-full bg-[#F9F8F5] py-16 px-4 sm:px-6 lg:px-8 border-b border-[#E4E2D9]">
      <div className="max-w-7xl mx-auto space-y-12">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between border-b border-[#18181B] pb-4 gap-4">
          <div>
            <div className="font-mono text-xs font-bold uppercase tracking-wider text-[#71717A] mb-1">
              SYSTEM ARCHITECTURE // SPECIFICATION
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#18181B]">
              The 4-Step Treasury Intelligence Loop
            </h2>
          </div>
          <div className="font-mono text-xs text-[#71717A] text-right">
            <span>SPEC: RFC-8841-FX</span>
            <br />
            <span>CORE ENGINE: NUMPY + FASTAPI + WISE SANDBOX</span>
          </div>
        </div>

        {/* 3 Main Architectural Layers Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Layer 1 */}
          <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-6 flex flex-col justify-between hover:border-[#18181B] transition-colors group">
            <div className="space-y-4">
              <div className="flex items-center justify-between font-mono text-xs">
                <span className="px-2 py-0.5 bg-[#F4F3EE] border border-[#E4E2D9] font-bold text-[#18181B]">
                  LAYER 01
                </span>
                <span className="text-[#047857] font-semibold flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" /> DETERMINISTIC
                </span>
              </div>
              <div className="w-10 h-10 bg-[#F4F3EE] border border-[#E4E2D9] flex items-center justify-center text-[#18181B]">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="text-xl font-bold text-[#18181B]">
                Cash Flow Engine & Schedule Walk
              </h3>
              <p className="text-sm text-[#71717A] leading-relaxed">
                Aggregates all AR (receivables) and AP (payables) across rolling 30, 60, and 90-day windows.
                Calculates daily net liquidity deltas with deterministic certainty.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-[#E4E2D9] font-mono text-xs text-[#18181B] flex items-center justify-between">
              <span>LEDGER SYNC: ACTIVE</span>
              <span className="text-[#047857]">BASE: INR (₹)</span>
            </div>
          </div>

          {/* Layer 2 */}
          <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-6 flex flex-col justify-between hover:border-[#18181B] transition-colors group">
            <div className="space-y-4">
              <div className="flex items-center justify-between font-mono text-xs">
                <span className="px-2 py-0.5 bg-[#F4F3EE] border border-[#E4E2D9] font-bold text-[#18181B]">
                  LAYER 02
                </span>
                <span className="text-[#B45309] font-semibold flex items-center gap-1">
                  <Activity className="w-3.5 h-3.5" /> PROBABILISTIC
                </span>
              </div>
              <div className="w-10 h-10 bg-[#F4F3EE] border border-[#E4E2D9] flex items-center justify-center text-[#18181B]">
                <Cpu className="w-5 h-5" />
              </div>
              <h3 className="text-xl font-bold text-[#18181B]">
                Monte Carlo FX Risk Band (10k Paths)
              </h3>
              <p className="text-sm text-[#71717A] leading-relaxed">
                Replaces misleading single-point balances with realistic 5th, 50th, and 95th percentile confidence bands.
                Simulates multi-currency correlation matrices and flags danger floor breaches.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-[#E4E2D9] font-mono text-xs text-[#18181B] flex items-center justify-between">
              <span>95% CFaR DISPERSION</span>
              <span className="text-[#B45309]">FLOOR: ₹450,000</span>
            </div>
          </div>

          {/* Layer 3 */}
          <div className="bg-[#FAF9F5] border border-[#E4E2D9] p-6 flex flex-col justify-between hover:border-[#18181B] transition-colors group">
            <div className="space-y-4">
              <div className="flex items-center justify-between font-mono text-xs">
                <span className="px-2 py-0.5 bg-[#F4F3EE] border border-[#E4E2D9] font-bold text-[#18181B]">
                  LAYER 03
                </span>
                <span className="text-[#1D4ED8] font-semibold flex items-center gap-1">
                  <Zap className="w-3.5 h-3.5" /> WISE SANDBOX
                </span>
              </div>
              <div className="w-10 h-10 bg-[#F4F3EE] border border-[#E4E2D9] flex items-center justify-center text-[#18181B]">
                <Zap className="w-5 h-5" />
              </div>
              <h3 className="text-xl font-bold text-[#18181B]">
                One-Click Treasury Protection
              </h3>
              <p className="text-sm text-[#71717A] leading-relaxed">
                Closes the loop between seeing risk and acting on it. Execute <em>Convert & Hold</em> or <em>Settle Now</em> via
                Wise Sandbox API. Instant recalculation tightens the uncertainty band in real time.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-[#E4E2D9] font-mono text-xs text-[#18181B] flex items-center justify-between">
              <span>EXECUTION TIME: &lt; 200MS</span>
              <span className="text-[#047857]">SAVINGS: ~80% FEES</span>
            </div>
          </div>
        </div>

        {/* Treasury Decision Flow Banner */}
        <div className="bg-[#F4F3EE] border border-[#18181B] p-6 sm:p-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="font-mono text-xs font-bold text-[#B45309] uppercase tracking-wider flex items-center gap-2">
              <RefreshCw className="w-4 h-4" /> CLOSED-LOOP RECHECK LOGIC
            </div>
            <h3 className="text-2xl font-bold text-[#18181B]">
              Natural Netting ($E_{`{net}`} = R_{`{FC}`} - P_{`{FC}`}$) & Carry-Cost Gating
            </h3>
            <p className="text-sm text-[#71717A]">
              We automatically offset matching receivables and payables in the same currency window, ensuring you only pay hedging carry-costs when adverse VaR strictly exceeds the interest rate differential.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
            <MetalButton
              variant="default"
              onClick={onNavigateDashboard}
              className="h-11 px-5 text-xs uppercase tracking-wider font-mono font-bold"
            >
              EXPLORE LIVE DASHBOARD
            </MetalButton>
            <MetalButton
              variant="gold"
              onClick={onNavigateWise}
              className="h-11 px-5 text-xs uppercase tracking-wider font-mono font-bold"
            >
              WISE SANDBOX CONSOLE
            </MetalButton>
          </div>
        </div>

        {/* Mandatory Footer Disclaimer */}
        <div className="border-t border-[#E4E2D9] pt-8 text-center sm:text-left flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="font-mono text-xs text-[#71717A] max-w-2xl">
            <strong className="text-[#18181B]">MANDATORY SYSTEM NOTICE:</strong> Production would need bank-grade transaction feeds and compliance — this demonstrates the mechanism with real infrastructure, not a mock.
          </p>
          <div className="font-mono text-xs text-[#71717A] flex items-center gap-4">
            <span>API: FASTAPI V0.1.0</span>
            <span>•</span>
            <span>ENGINE: MONTE CARLO V2</span>
            <span>•</span>
            <span>WISE SBX: READY</span>
          </div>
        </div>
      </div>
    </section>
  )
}
