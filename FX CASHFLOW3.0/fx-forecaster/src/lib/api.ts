import {
  ForecastResponse,
  Transaction,
  MarketSentiment,
  WiseQuoteRequest,
  WiseQuoteResponse,
  WiseExecutionRequest,
  WiseExecutionResponse,
  WalletBalances,
  AuditLogEntry,
  TimelinePoint,
  EconomicImpactResponse,
  RecommendationLifecycle,
} from "@/types"

const API_BASE = (import.meta as any).env?.VITE_API_URL || ""

// In-memory fallback state to guarantee 100% offline & demo reliability
let fallbackBalances: WalletBalances = {
  INR: 8251800.0,
  USD: 20000.0,
  EUR: 15000.0,
  GBP: 0.0,
}

let fallbackTransactions: Transaction[] = [
  {
    id: "TX-101",
    counterparty: "Apex Cloud Systems (US)",
    type: "PAYABLE",
    currency: "USD",
    foreign_amount: 20000.0,
    inr_book_value: 1720000.0,
    current_inr_value: 1748200.0,
    due_date: "2026-09-28",
    days_until_due: 30,
    status: "UNFUNDED",
    classification: "CONVERT_AND_HOLD",
    netting_group: "USD-30D",
    is_netted: false,
    adverse_var_inr: 86000.0,
    carry_cost_inr: 14200.0,
    carry_cost_gate_passed: true,
    recommended_action: "Convert & Hold",
    rationale:
      "Adverse 95% VaR (₹86,000) significantly exceeds 30-day carry cost (₹14,200). Lock USD now.",
  },
  {
    id: "TX-102",
    counterparty: "Berlin Dev Studio GmbH",
    type: "PAYABLE",
    currency: "EUR",
    foreign_amount: 15000.0,
    inr_book_value: 1395000.0,
    current_inr_value: 1395000.0,
    due_date: "2026-09-12",
    days_until_due: 14,
    status: "FUNDED",
    classification: "SETTLE_NOW",
    netting_group: "EUR-14D",
    is_netted: false,
    adverse_var_inr: 0.0,
    carry_cost_inr: 0.0,
    carry_cost_gate_passed: false,
    recommended_action: "Settle Now",
    rationale:
      "EUR balance already funded and sitting idle. Settle invoice immediately to eliminate settlement friction.",
  },
  {
    id: "TX-103",
    counterparty: "Nordic Retailers AB",
    type: "RECEIVABLE",
    currency: "USD",
    foreign_amount: 18000.0,
    inr_book_value: 1548000.0,
    current_inr_value: 1512000.0,
    due_date: "2026-10-15",
    days_until_due: 47,
    status: "EXPOSED_RECEIVABLE",
    classification: "RE_QUOTE_OR_HEDGE",
    netting_group: "USD-45D",
    is_netted: false,
    adverse_var_inr: 62000.0,
    carry_cost_inr: 0.0,
    carry_cost_gate_passed: false,
    recommended_action: "Re-Quote / Dynamic Buffer",
    rationale:
      "USD receivable at risk of rupee appreciation. Consider adding a 1.5% FX buffer on next contract renewal.",
  },
  {
    id: "TX-104",
    counterparty: "London Design Syndicate",
    type: "PAYABLE",
    currency: "GBP",
    foreign_amount: 8500.0,
    inr_book_value: 935000.0,
    current_inr_value: 936700.0,
    due_date: "2026-10-02",
    days_until_due: 34,
    status: "UNFUNDED",
    classification: "CONVERT_AND_HOLD",
    netting_group: "GBP-30D",
    is_netted: false,
    adverse_var_inr: 42500.0,
    carry_cost_inr: 7800.0,
    carry_cost_gate_passed: true,
    recommended_action: "Convert & Hold",
    rationale:
      "GBP volatility elevated post Bank of England rates meeting. VaR exceeds hurdle rate.",
  },
  {
    id: "TX-105",
    counterparty: "Kyoto Electronics",
    type: "PAYABLE",
    currency: "USD",
    foreign_amount: 12000.0,
    inr_book_value: 1044000.0,
    current_inr_value: 1048800.0,
    due_date: "2026-10-15",
    days_until_due: 47,
    status: "UNFUNDED",
    classification: "NATURALLY_NETTED",
    netting_group: "USD-45D",
    is_netted: true,
    adverse_var_inr: 18000.0,
    carry_cost_inr: 4100.0,
    carry_cost_gate_passed: false,
    recommended_action: "Hold (Natural Net)",
    rationale:
      "Matched against TX-103 ($18,000 receivable). Net exposure is only $6,000 credit. No forward lock required.",
  },
  {
    id: "TX-106",
    counterparty: "Munich SaaS Logistics",
    type: "PAYABLE",
    currency: "EUR",
    foreign_amount: 9000.0,
    inr_book_value: 837000.0,
    current_inr_value: 842000.0,
    due_date: "2026-11-20",
    days_until_due: 83,
    status: "UNFUNDED",
    classification: "CONVERT_AND_HOLD",
    netting_group: "EUR-90D",
    is_netted: false,
    adverse_var_inr: 54000.0,
    carry_cost_inr: 11200.0,
    carry_cost_gate_passed: true,
    recommended_action: "Convert & Hold",
    rationale:
      "Quarterly server infrastructure invoice. Unhedged tail risk pushes horizon balance near danger floor.",
  },
]

let fallbackAuditLogs: AuditLogEntry[] = [
  {
    id: "AUD-9912",
    timestamp: "2026-08-28 16:45:10",
    action: "CONVERT_AND_HOLD",
    transaction_id: "TX-098",
    counterparty: "Stripe US Infrastructure",
    currency: "USD",
    foreign_amount: 14500.0,
    inr_amount: 1267445.0,
    locked_rate: 87.41,
    sandbox_transfer_id: "TRX-WISE-SBX-8839102",
    status: "COMPLETED",
  },
  {
    id: "AUD-9911",
    timestamp: "2026-08-25 11:20:00",
    action: "SETTLE_NOW",
    transaction_id: "TX-094",
    counterparty: "AWS Frankfurt Node",
    currency: "EUR",
    foreign_amount: 8200.0,
    inr_amount: 762600.0,
    locked_rate: 93.0,
    sandbox_transfer_id: "TRX-WISE-SBX-8711094",
    status: "COMPLETED",
  },
]

// Recalculation state factor
let activeHedgingVaRReduction = 0

export function generateSyntheticForecast(
  horizon = 60,
  stress_currency = "NONE",
  stress_pct = 0,
  risk_tolerance = "moderate"
): ForecastResponse {
  const starting_balance = 1000000.0
  const danger_threshold = 450000.0

  const multiplier =
    risk_tolerance === "conservative" ? 1.35 : risk_tolerance === "aggressive" ? 0.75 : 1.0

  let stressShift = 0
  if (stress_currency === "USD") {
    stressShift = (stress_pct / 100) * 850000
  } else if (stress_currency === "EUR") {
    stressShift = (stress_pct / 100) * 450000
  } else if (stress_currency === "INR_CRASH") {
    stressShift = -Math.abs(stress_pct / 100) * 1200000
  }

  const timeline: TimelinePoint[] = []
  let runningDeterministic = starting_balance
  const baseDate = new Date("2026-09-01")

  for (let i = 1; i <= horizon; i++) {
    const d = new Date(baseDate)
    d.setDate(baseDate.getDate() + i - 1)
    const dateStr = d.toISOString().split("T")[0]

    // Scheduled flows on specific days
    let dayFlow = 0
    if (i === 14) dayFlow -= 1395000 // EUR settlement
    if (i === 30) dayFlow -= 1748200 // USD payable
    if (i === 34) dayFlow -= 936700 // GBP payable
    if (i === 47) {
      dayFlow += 1512000 // USD receivable
      dayFlow -= 1048800 // USD netted payable
    }
    if (i === 83) dayFlow -= 842000

    // Regular operational inflows/outflows
    if (i % 7 === 0) dayFlow += 380000 // Weekly client inflows
    if (i % 15 === 0) dayFlow -= 220000 // Payroll & utilities

    runningDeterministic += dayFlow

    // Monte Carlo dispersion (widens with sqrt(time))
    const dispersion =
      Math.sqrt(i) * 18500 * multiplier * (1 + Math.abs(stress_pct) / 20)

    const hedgedDampening = Math.max(0, 1 - (activeHedgingVaRReduction / 300000) * (i / horizon))

    const deterministic = runningDeterministic
    const expected = runningDeterministic + (stressShift * (i / horizon))
    const worst =
      expected - dispersion * 1.645 * hedgedDampening - Math.max(0, -stressShift * (i / horizon))
    const best =
      expected + dispersion * 1.645 + Math.max(0, stressShift * (i / horizon))

    timeline.push({
      date: dateStr,
      day_index: i,
      deterministic_balance: Math.round(deterministic),
      worst_case_5th: Math.round(worst),
      expected_50th: Math.round(expected),
      best_case_95th: Math.round(best),
      net_cash_flow: Math.round(dayFlow),
    })
  }

  const finalWorst = timeline[timeline.length - 1].worst_case_5th
  const finalExpected = timeline[timeline.length - 1].expected_50th
  const finalBest = timeline[timeline.length - 1].best_case_95th

  const minWorstInHorizon = Math.min(...timeline.map((t) => t.worst_case_5th))
  let riskStatus: "SAFE" | "CAUTION" | "CRITICAL" | "BREACH" = "SAFE"
  if (minWorstInHorizon < danger_threshold) {
    riskStatus = "BREACH"
  } else if (minWorstInHorizon < danger_threshold * 1.25) {
    riskStatus = "CAUTION"
  }

  return {
    horizon_days: horizon,
    base_currency: "INR",
    starting_balance,
    danger_threshold,
    summary: {
      expected_final_balance: finalExpected,
      worst_case_5th_var: finalWorst,
      best_case_95th: finalBest,
      value_at_risk_95: Math.round(Math.max(0, finalExpected - finalWorst)),
      risk_status: riskStatus,
    },
    timeline,
  }
}

export async function fetchForecast(params: {
  horizon?: number
  stress_currency?: string
  stress_pct?: number
  risk_tolerance?: string
}): Promise<ForecastResponse> {
  const horizon = params.horizon || 60
  const stress_currency = params.stress_currency || ""
  const stress_pct = params.stress_pct || 0
  const risk_tolerance = params.risk_tolerance || "moderate"

  const url = `${API_BASE}/api/forecast?horizon=${horizon}&stress_currency=${encodeURIComponent(
    stress_currency
  )}&stress_pct=${stress_pct}&risk_tolerance=${risk_tolerance}`

  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(3000) })
    if (res.ok) {
      const data = await res.json()
      if (data && data.timeline) return data
    }
  } catch (_e) {
    // Graceful fallback to client-side Monte Carlo generator
  }

  return generateSyntheticForecast(
    horizon,
    stress_currency,
    stress_pct,
    risk_tolerance
  )
}

export async function fetchTransactions(): Promise<Transaction[]> {
  try {
    const res = await fetch(`${API_BASE}/api/transactions`, {
      signal: AbortSignal.timeout(3000),
    })
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) {
        fallbackTransactions = data
        return data
      }
    }
  } catch (_e) {
    // Graceful fallback to local rich state
  }
  return [...fallbackTransactions]
}

export async function fetchMarketSentiment(): Promise<MarketSentiment> {
  try {
    const res = await fetch(`${API_BASE}/api/market-sentiment`, {
      cache: "no-store",
      headers: { "Cache-Control": "no-cache, no-store, must-revalidate" },
      signal: AbortSignal.timeout(5000),
    })
    if (res.ok) {
      const data: MarketSentiment = await res.json()
      if (!data.currencies || Object.keys(data.currencies).length === 0) {
        try {
          const rawRes = await fetch(`${API_BASE}/news-sentiment`, {
            cache: "no-store",
            signal: AbortSignal.timeout(3000),
          })
          if (rawRes.ok) {
            const rawData = await rawRes.json()
            if (rawData.currencies) {
              data.currencies = rawData.currencies
            }
            if (rawData.generated_at) {
              data.last_updated = rawData.generated_at
            }
          }
        } catch (_err) {}
      }
      return data
    }
  } catch (_e) {
    // Graceful fallback
  }

  return {
    sentiment_summary: "Cautious on INR due to oil imports; USD resilient",
    drift_adjustment: 0.03,
    volatility_adjustment: 0.08,
    last_updated: new Date().toISOString(),
    headlines: [
      "Crude prices put pressure on emerging market currencies",
      "US Fed signals higher-for-longer policy trajectory",
      "RBI maintains strategic foreign exchange intervention corridor",
    ],
  }
}

export async function refreshMarketSentiment(): Promise<MarketSentiment> {
  try {
    const res = await fetch(`${API_BASE}/refresh-news`, {
      method: "POST",
      cache: "no-store",
      headers: { "Cache-Control": "no-cache, no-store, must-revalidate" },
      signal: AbortSignal.timeout(45000),
    })
    if (res.ok) {
      return await fetchMarketSentiment()
    }
  } catch (_e) {
    // Fallback to fetch current
  }
  return fetchMarketSentiment()
}

export async function fetchBalances(): Promise<WalletBalances> {
  try {
    const res = await fetch(`${API_BASE}/api/balances`, {
      signal: AbortSignal.timeout(3000),
    })
    if (res.ok) {
      const data = await res.json()
      fallbackBalances = data
      return data
    }
  } catch (_e) {
    // Graceful fallback
  }
  return { ...fallbackBalances }
}

export async function fetchAuditLogs(): Promise<AuditLogEntry[]> {
  try {
    const res = await fetch(`${API_BASE}/api/audit-log`, {
      signal: AbortSignal.timeout(3000),
    })
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data)) return data
    }
  } catch (_e) {
    // Graceful fallback
  }
  return [...fallbackAuditLogs]
}

export async function fetchWiseQuote(
  req: WiseQuoteRequest
): Promise<WiseQuoteResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/wise/quote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
      signal: AbortSignal.timeout(3500),
    })
    if (res.ok) {
      return await res.json()
    }
  } catch (_e) {
    // Fallback simulation
  }

  const rates: Record<string, number> = {
    USD: 87.41,
    EUR: 93.0,
    GBP: 110.2,
  }
  const midRate = rates[req.target_currency.toUpperCase()] || 87.41
  const sourceAmount = Math.round(req.target_amount * midRate)
  const wiseFee = Math.round(sourceAmount * 0.0028)
  const bankFee = Math.round(sourceAmount * 0.02)

  return {
    quote_id: `Q-WISE-${Math.floor(100000 + Math.random() * 900000)}`,
    source_currency: "INR",
    target_currency: req.target_currency.toUpperCase(),
    target_amount: req.target_amount,
    source_amount: sourceAmount + wiseFee,
    mid_market_rate: midRate,
    fee_inr: wiseFee,
    traditional_bank_fee_estimate_inr: bankFee,
    rate_guaranteed_minutes: 30,
    delivery_estimate: "Instant / Within 2 hours",
  }
}

export async function executeWiseTransfer(
  req: WiseExecutionRequest
): Promise<WiseExecutionResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/wise/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
      signal: AbortSignal.timeout(4000),
    })
    if (res.ok) {
      const data = await res.json()
      fallbackBalances = data.updated_wallet_balances
      activeHedgingVaRReduction += data.recalculated_var_reduction_inr || 86000
      return data
    }
  } catch (_e) {
    // Fallback execution
  }

  const targetCurr = req.target_currency as keyof WalletBalances
  const sourceDebit = req.source_amount
  const foreignCredit = req.target_amount

  fallbackBalances.INR = Math.max(0, fallbackBalances.INR - sourceDebit)
  if (targetCurr in fallbackBalances) {
    fallbackBalances[targetCurr] += foreignCredit
  }

  activeHedgingVaRReduction += 86000

  // Update matching transaction in fallback list
  fallbackTransactions = fallbackTransactions.map((tx) => {
    if (tx.id === req.transaction_id) {
      return {
        ...tx,
        status: req.action_type === "SETTLE_NOW" ? "SETTLED" : "HEDGED",
        classification:
          req.action_type === "SETTLE_NOW" ? "UNEXPOSED" : "NATURALLY_NETTED",
        adverse_var_inr: 0,
        rationale: "Successfully locked rate via Wise Sandbox. Position protected.",
      }
    }
    return tx
  })

  const newLog: AuditLogEntry = {
    id: `AUD-${Math.floor(1000 + Math.random() * 9000)}`,
    timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
    action: req.action_type,
    transaction_id: req.transaction_id,
    counterparty:
      fallbackTransactions.find((t) => t.id === req.transaction_id)
        ?.counterparty || "Wise Multi-Currency Balance",
    currency: req.target_currency,
    foreign_amount: req.target_amount,
    inr_amount: req.source_amount,
    locked_rate: req.source_amount / req.target_amount,
    sandbox_transfer_id: `TRX-WISE-SBX-${Math.floor(1000000 + Math.random() * 9000000)}`,
    status: "COMPLETED",
  }
  fallbackAuditLogs.unshift(newLog)

  return {
    success: true,
    sandbox_transfer_id: newLog.sandbox_transfer_id,
    status: "COMPLETED",
    action_executed: req.action_type,
    executed_at: new Date().toISOString(),
    locked_rate: Number((req.source_amount / req.target_amount).toFixed(2)),
    amount_debited_inr: req.source_amount,
    amount_credited_foreign: req.target_amount,
    updated_wallet_balances: { ...fallbackBalances },
    recalculated_var_reduction_inr: 86000.0,
  }
}

let fallbackActions: RecommendationLifecycle[] = []

export async function fetchEconomicImpact(): Promise<EconomicImpactResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/economic-impact`, { signal: AbortSignal.timeout(3000) })
    if (res.ok) {
      return await res.json()
    }
  } catch (_e) {}
  
  return {
    total_estimated_avoided_loss: 182500,
    total_action_cost: 36200,
    total_net_economic_benefit: 146300,
    itemized_impacts: []
  }
}

export async function fetchActions(): Promise<RecommendationLifecycle[]> {
  try {
    const res = await fetch(`${API_BASE}/api/actions`, { signal: AbortSignal.timeout(3000) })
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data)) {
        fallbackActions = data
        return data
      }
    }
  } catch (_e) {}

  if (fallbackActions.length === 0) {
    fallbackActions = fallbackTransactions.map((tx, idx) => ({
      action_id: `act-${tx.id}`,
      transaction_id: tx.id,
      action_type: tx.classification === "CONVERT_AND_HOLD" ? "CONVERT_AND_HOLD" : tx.classification === "SETTLE_NOW" ? "SETTLE_NOW" : "RE_QUOTE",
      priority: idx % 2 === 0 ? "HIGH" : "MEDIUM",
      risk_score: 75,
      confidence: 80,
      reason: tx.rationale,
      risk_before: "HIGH",
      risk_after_estimate: "LOW",
      estimated_action_cost: tx.carry_cost_inr,
      estimated_inaction_cost: tx.adverse_var_inr,
      status: (tx.status === "SETTLED" || tx.status === "HEDGED") ? "EXECUTED" : "RECOMMENDED",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }))
  }
  return [...fallbackActions]
}

export async function approveAction(actionId: string): Promise<RecommendationLifecycle> {
  try {
    const res = await fetch(`${API_BASE}/api/actions/${actionId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    })
    if (res.ok) {
      const updated = await res.json()
      fallbackActions = fallbackActions.map(a => a.action_id === actionId ? updated : a)
      return updated
    }
    const err = await res.json().catch(() => ({ detail: "Approval failed" }))
    throw new Error(err.detail || "Approval failed")
  } catch (e) {
    if (e instanceof Error && e.message !== "Approval failed") {
      let updated: RecommendationLifecycle | null = null
      fallbackActions = fallbackActions.map(a => {
        if (a.action_id === actionId) {
          if (a.status !== "RECOMMENDED") {
            throw new Error(`Invalid state transition: Cannot transition from ${a.status} to APPROVED`)
          }
          updated = { ...a, status: "APPROVED", updated_at: new Date().toISOString() }
          return updated
        }
        return a
      })
      if (!updated) throw new Error("Action not found")
      return updated
    }
    throw e
  }
}

export async function rejectAction(actionId: string): Promise<RecommendationLifecycle> {
  try {
    const res = await fetch(`${API_BASE}/api/actions/${actionId}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    })
    if (res.ok) {
      const updated = await res.json()
      fallbackActions = fallbackActions.map(a => a.action_id === actionId ? updated : a)
      return updated
    }
    const err = await res.json().catch(() => ({ detail: "Rejection failed" }))
    throw new Error(err.detail || "Rejection failed")
  } catch (e) {
    if (e instanceof Error && e.message !== "Rejection failed") {
      let updated: RecommendationLifecycle | null = null
      fallbackActions = fallbackActions.map(a => {
        if (a.action_id === actionId) {
          if (a.status !== "RECOMMENDED" && a.status !== "APPROVED") {
            throw new Error(`Invalid state transition: Cannot transition from ${a.status} to REJECTED`)
          }
          updated = { ...a, status: "REJECTED", updated_at: new Date().toISOString() }
          return updated
        }
        return a
      })
      if (!updated) throw new Error("Action not found")
      const targetAction = fallbackActions.find(a => a.action_id === actionId)
      if (targetAction) {
        fallbackTransactions = fallbackTransactions.map(tx => 
          tx.id === targetAction.transaction_id ? { ...tx, status: "HEDGED" as any } : tx
        )
      }
      return updated
    }
    throw e
  }
}
