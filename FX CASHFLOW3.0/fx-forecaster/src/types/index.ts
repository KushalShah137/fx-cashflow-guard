export interface TimelinePoint {
  date: string
  day_index: number
  deterministic_balance: number
  worst_case_5th: number
  expected_50th: number
  best_case_95th: number
  net_cash_flow: number
}

export interface ForecastSummary {
  expected_final_balance: number
  worst_case_5th_var: number
  best_case_95th: number
  value_at_risk_95: number
  risk_status: "SAFE" | "CAUTION" | "CRITICAL" | "BREACH"
}

export interface ForecastResponse {
  horizon_days: number
  base_currency: string
  starting_balance: number
  danger_threshold: number
  summary: ForecastSummary
  timeline: TimelinePoint[]
}

export type ExposureClassification =
  | "CONVERT_AND_HOLD"
  | "SETTLE_NOW"
  | "RE_QUOTE_OR_HEDGE"
  | "NATURALLY_NETTED"
  | "UNEXPOSED"

export interface Transaction {
  id: string
  counterparty: string
  type: "PAYABLE" | "RECEIVABLE"
  currency: "USD" | "EUR" | "GBP" | "INR"
  foreign_amount: number
  inr_book_value: number
  current_inr_value: number
  due_date: string
  days_until_due: number
  status: "UNFUNDED" | "FUNDED" | "EXPOSED_RECEIVABLE" | "SETTLED" | "HEDGED"
  classification: ExposureClassification
  netting_group: string
  is_netted: boolean
  adverse_var_inr: number
  carry_cost_inr: number
  carry_cost_gate_passed: boolean
  recommended_action: string
  rationale: string
}

export interface MarketSentiment {
  sentiment_summary: string
  drift_adjustment: number
  volatility_adjustment: number
  last_updated: string
  headlines: string[]
}

export interface WiseQuoteRequest {
  source_currency: string
  target_currency: string
  target_amount: number
}

export interface WiseQuoteResponse {
  quote_id: string
  source_currency: string
  target_currency: string
  target_amount: number
  source_amount: number
  mid_market_rate: number
  fee_inr: number
  traditional_bank_fee_estimate_inr: number
  rate_guaranteed_minutes: number
  delivery_estimate: string
}

export interface WiseExecutionRequest {
  quote_id: string
  action_type: "CONVERT_AND_HOLD" | "SETTLE_NOW"
  transaction_id: string
  target_currency: string
  target_amount: number
  source_amount: number
}

export interface WalletBalances {
  INR: number
  USD: number
  EUR: number
  GBP: number
}

export interface WiseExecutionResponse {
  success: boolean
  sandbox_transfer_id: string
  status: string
  action_executed: "CONVERT_AND_HOLD" | "SETTLE_NOW"
  executed_at: string
  locked_rate: number
  amount_debited_inr: number
  amount_credited_foreign: number
  updated_wallet_balances: WalletBalances
  recalculated_var_reduction_inr: number
}

export interface AuditLogEntry {
  id: string
  timestamp: string
  action: string
  transaction_id: string
  counterparty: string
  currency: string
  foreign_amount: number
  inr_amount: number
  locked_rate: number
  sandbox_transfer_id: string
  status: "COMPLETED" | "VERIFIED"
}
