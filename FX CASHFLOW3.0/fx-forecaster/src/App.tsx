import { useState, useEffect, useCallback } from "react"
import {
  ForecastResponse,
  Transaction,
  MarketSentiment,
  WalletBalances,
  AuditLogEntry,
  WiseExecutionResponse,
  EconomicImpactResponse,
  RecommendationLifecycle,
} from "@/types"
import {
  fetchForecast,
  fetchTransactions,
  fetchMarketSentiment,
  fetchBalances,
  fetchAuditLogs,
  fetchEconomicImpact,
  fetchActions,
  approveAction,
  rejectAction,
} from "@/lib/api"
import { LandingHero } from "@/components/landing/LandingHero"
import { TerminalLoginModal } from "@/components/landing/TerminalLoginModal"
import { ContainerScroll } from "@/components/ui/container-scroll-animation"
import { RiskBandChart } from "@/components/dashboard/RiskBandChart"
import { StressTestBar } from "@/components/dashboard/StressTestBar"
import { ExposureMatrix } from "@/components/dashboard/ExposureMatrix"
import { LiveNewsFeed } from "@/components/dashboard/LiveNewsFeed"
import { CalibrationAudit } from "@/components/dashboard/CalibrationAudit"
import { MultiWallet } from "@/components/wise/MultiWallet"
import { WiseQuoteModal } from "@/components/wise/WiseQuoteModal"
import { SandboxReceipt } from "@/components/wise/SandboxReceipt"
import { Terminal, Zap } from "lucide-react"

export function App() {
  // Navigation & Page State
  const [currentPage, setCurrentPage] = useState<"landing" | "dashboard" | "wise">("landing")
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false)
  const [isQuoteModalOpen, setIsQuoteModalOpen] = useState(false)
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null)
  const [executionReceipt, setExecutionReceipt] = useState<WiseExecutionResponse | null>(null)

  // Forecast & Quant Simulation State
  const [horizon, setHorizon] = useState<number>(60)
  const [stressCurrency, setStressCurrency] = useState<string>("")
  const [stressPct, setStressPct] = useState<number>(0)
  const [riskTolerance, setRiskTolerance] = useState<string>("moderate")

  // Data State
  const [forecast, setForecast] = useState<ForecastResponse | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [sentiment, setSentiment] = useState<MarketSentiment | null>(null)
  const [walletBalances, setWalletBalances] = useState<WalletBalances>({
    INR: 8251800.0,
    USD: 20000.0,
    EUR: 15000.0,
    GBP: 0.0,
  })
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([])
  const [isLoadingForecast, setIsLoadingForecast] = useState(false)
  const [economicImpact, setEconomicImpact] = useState<EconomicImpactResponse | null>(null)
  const [actions, setActions] = useState<RecommendationLifecycle[]>([])

  // Load Data
  const loadForecastData = useCallback(async () => {
    setIsLoadingForecast(true)
    try {
      const data = await fetchForecast({
        horizon,
        stress_currency: stressCurrency,
        stress_pct: stressPct,
        risk_tolerance: riskTolerance,
      })
      setForecast(data)
    } finally {
      // Fetch economic impact alongside forecast
      try {
        const impact = await fetchEconomicImpact()
        setEconomicImpact(impact)
      } catch (_e) {}
      setIsLoadingForecast(false)
    }
  }, [horizon, stressCurrency, stressPct, riskTolerance])

  const loadInitialData = useCallback(async () => {
    const [txs, sent, balances, logs, actionList, impact] = await Promise.all([
      fetchTransactions(),
      fetchMarketSentiment(),
      fetchBalances(),
      fetchAuditLogs(),
      fetchActions(),
      fetchEconomicImpact(),
    ])
    setTransactions(txs)
    setSentiment(sent)
    setWalletBalances(balances)
    setAuditLogs(logs)
    setActions(actionList)
    setEconomicImpact(impact)
  }, [])

  useEffect(() => {
    loadInitialData()
  }, [loadInitialData])

  useEffect(() => {
    loadForecastData()
  }, [loadForecastData])

  // Handlers
  const handleApprove = async (actionId: string) => {
    try {
      const updated = await approveAction(actionId)
      setActions(prev => prev.map(a => a.action_id === actionId ? updated : a))
      await loadForecastData()
    } catch (e: any) {
      alert(e.message || "Failed to approve action")
    }
  }

  const handleReject = async (actionId: string) => {
    try {
      const updated = await rejectAction(actionId)
      setActions(prev => prev.map(a => a.action_id === actionId ? updated : a))
      const [txs, logs] = await Promise.all([fetchTransactions(), fetchAuditLogs()])
      setTransactions(txs)
      setAuditLogs(logs)
      await loadForecastData()
    } catch (e: any) {
      alert(e.message || "Failed to reject action")
    }
  }

  const handleStressChange = (curr: string, pct: number) => {
    setStressCurrency(curr)
    setStressPct(pct)
  }

  const handleResetStress = () => {
    setStressCurrency("")
    setStressPct(0)
  }

  const handleOpenWiseAction = (tx: Transaction) => {
    setSelectedTransaction(tx)
    setIsQuoteModalOpen(true)
  }

  const handleExecutionSuccess = async (res: WiseExecutionResponse) => {
    setExecutionReceipt(res)
    setWalletBalances(res.updated_wallet_balances)
    // Refresh transactions, logs, forecast, actions and economic impact
    const [txs, logs, actionList, impact] = await Promise.all([
      fetchTransactions(),
      fetchAuditLogs(),
      fetchActions(),
      fetchEconomicImpact(),
    ])
    setTransactions(txs)
    setAuditLogs(logs)
    setActions(actionList)
    setEconomicImpact(impact)
    await loadForecastData()
  }

  return (
    <div className="min-h-screen bg-[#F6F4EE] text-[#18181B] flex flex-col font-mono selection:bg-[#18181B] selection:text-[#F6F4EE]">
      {/* Top Editorial Financial Terminal Navigation Bar */}
      <header className="nav">
        <div className="nav-left">
          <span className="nav-badge">FX</span>
          <span className="font-bold tracking-wider">FX // FORECASTER</span>
        </div>
        {currentPage !== "landing" && (
          <div className="nav-center">
            <button
              onClick={() => setCurrentPage("landing")}
              className="nav-tab"
            >
              Login (/)
            </button>
            <button
              onClick={() => setCurrentPage("dashboard")}
              className={`nav-tab ${currentPage === "dashboard" ? "active" : ""}`}
            >
              DASHBOARD (/dashboard)
            </button>
            <button
              onClick={() => setCurrentPage("wise")}
              className={`nav-tab ${currentPage === "wise" ? "active" : ""}`}
            >
              WISE SANDBOX (/wise)
            </button>
          </div>
        )}
        <div className="avatar" onClick={() => setIsLoginModalOpen(true)}>KL</div>
      </header>

      {currentPage !== "landing" && (
        <div className="ticker">
          <div className="ticker-left">
            <span><span className="dot"></span>MARKET TELEMETRY ACTIVE</span>
            <span className="divider">|</span>
            <span>USD/INR <span className="up">87.41 (+0.14%)</span></span>
            <span>EUR/INR <span className="down">93.00 (−0.08%)</span></span>
            <span>GBP/INR <span className="up">110.20 (+0.22%)</span></span>
          </div>
          <div className="ticker-right">
            <span>BASE CURRENCY: INR (₹)</span>
            <span>LATENCY: 14MS</span>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1">
        {/* PAGE 1: LANDING PAGE */}
        {currentPage === "landing" && (
          <LandingHero
            onOpenLogin={() => setIsLoginModalOpen(true)}
            onNavigateDashboard={() => setCurrentPage("dashboard")}
            onLoginSuccess={() => {
              setIsLoginModalOpen(false)
              setCurrentPage("dashboard")
            }}
          />
        )}

        {/* PAGE 2: DASHBOARD */}
        {currentPage === "dashboard" && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
            {/* Dashboard Sub-Header */}
            <div className="flex flex-wrap items-end justify-between border-b border-[#18181B] pb-4 gap-4">
              <div>
                <div className="text-xs text-[#71717A] uppercase tracking-wider font-bold mb-1">
                  SME TREASURY DECISION LAYER // ACTIVE TELEMETRY
                </div>
                <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#18181B] font-display">
                  Cash Flow Horizon & Value at Risk (VaR) Engine
                </h1>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    setSelectedTransaction(null)
                    setIsQuoteModalOpen(true)
                  }}
                  className="px-3 py-1.5 text-xs font-bold bg-[#18181B] text-[#FAF9F5] hover:bg-[#27272A] flex items-center gap-1.5"
                >
                  <Zap className="w-3.5 h-3.5 text-[#FEF08A]" />
                  INSTANT WISE CONVERT
                </button>
              </div>
            </div>

            {/* Perspective 3D Container Scroll Forecast Wrapper */}
            <ContainerScroll
              titleComponent={
                <div className="space-y-1">
                  <div className="font-mono text-xs font-bold text-[#B45309] uppercase tracking-wider">
                    SIMULATION ENGINE // PROBABILISTIC MONTE CARLO
                  </div>
                  <h2 className="text-2xl sm:text-3xl font-bold text-[#18181B] font-display">
                    FX Risk Band & Liquidity Buffer Floor
                  </h2>
                </div>
              }
            >
              <RiskBandChart
                forecast={forecast}
                isLoading={isLoadingForecast}
                horizon={horizon}
                onHorizonChange={setHorizon}
                riskTolerance={riskTolerance}
                onRiskToleranceChange={setRiskTolerance}
                economicImpact={economicImpact || undefined}
              />
            </ContainerScroll>

            {/* Live Macro Stress Test Simulator Bar */}
            <StressTestBar
              currentStressCurrency={stressCurrency}
              currentStressPct={stressPct}
              onApplyStress={handleStressChange}
              onResetStress={handleResetStress}
            />

            {/* Live Macro News Telemetry & Quantitative Regime Synthesis */}
            <LiveNewsFeed sentiment={sentiment} />
          </div>
        )}

        {/* PAGE 3: WISE SANDBOX EXECUTION PAGE */}
        {currentPage === "wise" && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
            <div className="flex flex-wrap items-end justify-between border-b border-[#18181B] pb-4 gap-4">
              <div>
                <div className="text-xs text-[#71717A] uppercase tracking-wider font-bold mb-1">
                  SETTLEMENT LAYER // WISE SANDBOX PLATFORM
                </div>
                <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#18181B] font-display">
                  Multi-Currency Treasury Wallet & Execution Terminal
                </h1>
              </div>

              <button
                onClick={() => {
                  setSelectedTransaction(null)
                  setIsQuoteModalOpen(true)
                }}
                className="px-4 py-2 text-xs font-bold bg-[#047857] text-[#FAF9F5] hover:bg-[#065F46] flex items-center gap-1.5"
              >
                <Zap className="w-4 h-4 text-[#FEF08A]" />
                GENERATE GUARANTEED QUOTE
              </button>
            </div>

            {/* Multi-Currency Balances */}
            <MultiWallet
              balances={walletBalances}
              onOpenQuickConvert={(c) => {
                setSelectedTransaction({
                  id: `TX-QUICK-${c}`,
                  counterparty: `Wise Multi-Currency (${c})`,
                  type: "PAYABLE",
                  currency: c as any,
                  foreign_amount: 10000,
                  inr_book_value: 874100,
                  current_inr_value: 874100,
                  due_date: "2026-09-30",
                  days_until_due: 30,
                  status: "UNFUNDED",
                  classification: "CONVERT_AND_HOLD",
                  netting_group: `${c}-30D`,
                  is_netted: false,
                  adverse_var_inr: 45000,
                  carry_cost_inr: 8000,
                  carry_cost_gate_passed: true,
                  recommended_action: "Convert & Hold",
                  rationale: "Lock live mid-market rate to eliminate volatility.",
                })
                setIsQuoteModalOpen(true)
              }}
            />

            {/* Exposure Table with Direct Actions */}
             <ExposureMatrix
              transactions={transactions}
              actions={actions}
              onApproveAction={handleApprove}
              onRejectAction={handleReject}
              onSelectTransactionForAction={handleOpenWiseAction}
            />

            {/* Audit Trail */}
            <CalibrationAudit auditLogs={auditLogs} />
          </div>
        )}
      </main>

      {/* Modals */}
      <TerminalLoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onLoginSuccess={() => {
          setIsLoginModalOpen(false)
          setCurrentPage("dashboard")
        }}
      />

      <WiseQuoteModal
        isOpen={isQuoteModalOpen}
        onClose={() => {
          setIsQuoteModalOpen(false)
          setSelectedTransaction(null)
        }}
        selectedTransaction={selectedTransaction}
        walletBalances={walletBalances}
        onExecutionSuccess={handleExecutionSuccess}
      />

      <SandboxReceipt
        receipt={executionReceipt}
        onClose={() => setExecutionReceipt(null)}
        onNavigateDashboard={() => setCurrentPage("dashboard")}
      />

      {/* Global Terminal Footer */}
      <footer className="w-full border-t border-[#E4E2D9] bg-[#F4F3EE] py-6 px-4 sm:px-6 lg:px-8 font-mono text-xs text-[#71717A]">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div>
            <span>FX // FORECASTER • SME TREASURY INTELLIGENCE LAYER</span>
            <span className="mx-2">|</span>
            <span className="text-[#18181B]">NODE_01 CONNECTED</span>
          </div>
          <div>
            <span>LATENCY: 14MS</span>
            <span className="mx-2">•</span>
            <span>DATA INTEGRITY: VERIFIED SHA-256</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
