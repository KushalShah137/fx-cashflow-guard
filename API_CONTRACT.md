# FX-Cashflow Guard // Official Frozen API Contract

> **Version:** 1.0.0-PROD-FREEZE  
> **Base URL:** `http://localhost:8000`  
> **Status:** FROZEN FOR HACKATHON DEMO & FRONTEND INTEGRATION

---

## Overview

FX-Cashflow Guard exposes a four-layer quantitative treasury architecture:
1. **Layer 1:** Deterministic day-by-day multi-currency cash flow balance projection.
2. **Layer 2:** Cholesky-correlated Monte Carlo Value-at-Risk (VaR) simulation (510 real historical observations from Frankfurter.dev across USD, EUR, GBP, INR, CNY, JPY, AUD).
3. **Layer 2.5:** Multi-Horizon (30D, 60D, 90D) liquidity risk classification and trajectory scoring (0–100 scale).
4. **Layer 3:** Decision & Netting Engine producing prioritized actionable hedging recommendations.
5. **Layer 4:** Resilient Wise Sandbox API execution and lifecycle governance state machine.

---

## Endpoints Summary

| Method | Path | Summary | Response Type |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Bloomberg-terminal root landing page | `text/html` |
| `GET` | `/health` | Core server liveness check | `application/json` |
| `GET` | `/demo-script-check` | Pre-demo system readiness checklist | `application/json` |
| `GET` | `/forecast` | Layer 1 daily deterministic cash balance baseline | `application/json` (Array) |
| `POST` | `/apply-action` | Direct fast action execution & simulation update | `application/json` (Array) |
| `POST` | `/reset` | Clean reset of in-memory engine & SQLite database | `application/json` |
| `GET` | `/exposures` | Net exposure per currency (native & USD base) | `application/json` (Array) |
| `GET` | `/demo-actions` | List of actionable demo trigger transactions | `application/json` (Array) |
| `GET` | `/risk-band` | Layer 2 Correlated Monte Carlo simulation bands (P5, P50, P95) | `application/json` |
| `GET` | `/risk-diagnostics` | Historical covariance, correlation & Cholesky matrices | `application/json` |
| `GET` | `/risk-classification` | Multi-horizon risk classification & score | `application/json` |
| `GET` | `/decisions` | Prioritized hedging and settlement recommendations | `application/json` |
| `GET` | `/risk-overview` | Single unified dashboard payload (All-in-One) | `application/json` |
| `GET` | `/netting-opportunities`| Detected same-currency matching opportunities | `application/json` |
| `GET` | `/economic-impact` | Quantified cost vs. value preservation metrics | `application/json` |
| `GET` | `/actions` | Action recommendations lifecycle records in SQLite | `application/json` (Array) |
| `GET` | `/actions/{id}` | Single action detail with lifecycle state | `application/json` |
| `POST` | `/actions/{id}/approve`| Transition recommendation to APPROVED | `application/json` |
| `POST` | `/actions/{id}/reject` | Transition recommendation to REJECTED | `application/json` |
| `POST` | `/actions/{id}/execute`| Execute approved recommendation on ledger & Wise | `application/json` |
| `GET` | `/viz/dashboard` | Standalone interactive Bloomberg terminal dashboard | `text/html` |
| `GET` | `/viz/dashboard.png` | Static high-res PNG export of dashboard | `image/png` |
| `GET` | `/viz/health` | Visualization module health check | `application/json` |

---

## Detailed Endpoint Schemas

### 1. `GET /forecast`
Returns the deterministic day-by-day cash balance projection.

- **Query Parameters:**
  - `currency` *(string, optional, default: "USD")*: Target base currency.
  - `days` *(integer, optional, default: 90, min: 1, max: 180)*: Forecast horizon.
- **Response `200 OK`:**
```json
[
  {
    "date": "2026-09-01",
    "balance": 41500.0,
    "is_breach": false,
    "transactions_today": ["txn_001"]
  },
  {
    "date": "2026-09-02",
    "balance": 41500.0,
    "is_breach": false,
    "transactions_today": []
  }
]
```

---

### 2. `POST /apply-action`
Executes an immediate hedging or early settlement action on a pending transaction, invokes Wise Sandbox API quote generation, synchronizes SQLite state, and returns the updated forecast.

- **Request Body:**
```json
{
  "transaction_id": "txn_010",
  "action": "convert_and_hold"
}
```
*Supported actions:* `"convert_and_hold"`, `"settle_now"`.
- **Response `200 OK`:** Returns array of `DailyBalancePoint` (same shape as `/forecast`).
- **Error Responses:**
  - `404 Not Found`: If `transaction_id` does not exist (`{"detail": "Transaction '...' not found"}`).
  - `400 Bad Request`: If action execution fails.

---

### 3. `POST /reset`
Resets both the in-memory engine and the SQLite database (`data/treasury.db`) to the initial mock transaction state.

- **Response `200 OK`:**
```json
{
  "status": "reset_successful"
}
```

---

### 4. `GET /exposures`
Returns gross payables, gross receivables, and net exposure converted to base currency.

- **Response `200 OK`:**
```json
[
  {
    "currency": "EUR",
    "gross_payable": 37500.0,
    "gross_receivable": 26500.0,
    "net_exposure": -11000.0,
    "net_exposure_base_ccy": -12807.23,
    "direction": "payable"
  }
]
```

---

### 5. `GET /risk-band`
Returns 1,000+ run Cholesky-correlated Monte Carlo Value-at-Risk percentiles per day.

- **Query Parameters:**
  - `days` *(int, default: 90)*
  - `simulations` *(int, default: 2000)*
- **Response `200 OK`:**
```json
{
  "days": 90,
  "simulations": 2000,
  "currency": "USD",
  "risk_band": [
    {
      "day": 1,
      "date": "2026-09-01",
      "baseline": 41500.0,
      "p5": 40850.23,
      "p50": 41495.10,
      "p95": 42120.45,
      "p5_net_change": -649.77,
      "p95_net_change": 620.45,
      "active_currencies": ["EUR", "GBP", "INR", "CNY", "JPY", "AUD"]
    }
  ]
}
```

---

### 6. `GET /risk-classification`
Returns multi-horizon risk scoring (30D, 60D, 90D), overall score (0–100), risk level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and trajectory (`STABLE`, `IMPROVING`, `WORSENING`).

- **Response `200 OK`:**
```json
{
  "overall_risk_level": "CRITICAL",
  "overall_risk_score": 85,
  "primary_driver": "Liquidity floor breach projected on day 40",
  "trajectory": "WORSENING",
  "horizons": {
    "30_day": { "risk_level": "LOW", "risk_score": 15 },
    "60_day": { "risk_level": "CRITICAL", "risk_score": 85 },
    "90_day": { "risk_level": "HIGH", "risk_score": 75 }
  }
}
```

---

### 7. `GET /decisions`
Returns prioritized actionable recommendations generated by Layer 3 Decision Engine.

- **Response `200 OK`:**
```json
{
  "overall": {
    "risk_level": "CRITICAL",
    "risk_score": 85,
    "primary_driver": "EUR payable batch creates VaR floor breach"
  },
  "decision_kpis": {
    "total_recommendations": 3,
    "high_priority_count": 2,
    "hedged_capital_base": 48500.0
  },
  "recommendations": [
    {
      "action_id": "act_a1b2c3d4",
      "transaction_id": "txn_010",
      "action_type": "convert_and_hold",
      "priority": "CRITICAL",
      "risk_score": 85,
      "confidence": 92,
      "reason": "Eliminates EUR currency risk before large datacenter outflow.",
      "estimated_action_cost": 125.0,
      "estimated_inaction_cost": 3450.0,
      "status": "RECOMMENDED"
    }
  ]
}
```

---

### 8. `GET /risk-overview`
**Recommended for Frontend:** Unified all-in-one payload containing `baseline_forecast`, `risk_band`, `risk_classification`, `exposures`, and `decisions`.

---

### 9. `GET /netting-opportunities` & `GET /economic-impact`
- `/netting-opportunities`: Lists matched same-currency payables/receivables and total gross savings.
- `/economic-impact`: Quantifies total preserved cash value, FX conversion spread savings, and hedge cost.

---

### 10. `GET /demo-script-check`
Health validation check to run 5 minutes before live presentation.

- **Response `200 OK`:**
```json
{
  "all_systems_go": true,
  "status": "GREEN",
  "timestamp": "2026-08-29T21:55:00Z",
  "checks": {
    "sqlite_database": { "status": "PASS", "transaction_rows": 26 },
    "fx_historical_cache": { "status": "PASS", "rows": 510, "currencies": ["EUR", "GBP", "INR", "CNY", "JPY", "AUD"] },
    "wise_sandbox_resilience": { "status": "PASS", "indicative_rate": 1.1582 },
    "demo_transactions_initial_state": { "status": "PASS" }
  }
}
```
