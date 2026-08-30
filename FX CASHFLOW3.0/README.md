# fx-cashflow-guard

Real-time cash flow forecasting with FX risk modeling. Monte Carlo simulations project best/expected/worst-case scenarios across currencies, flagging danger thresholds before they hit — with one-click Wise integration to convert & hold or settle exposures instantly.

---

## The Problem

Businesses holding receivables and payables in multiple currencies are exposed to FX volatility they usually can't see coming. A €45,000 invoice due in 60 days doesn't look risky today — but by the time it settles, exchange rate swings can quietly erode tens of thousands of dollars in value. Most cash flow tools show you a flat forecast line and stop there: no visibility into currency risk, and no way to act on it even if you did see it.

## The Solution

**fx-cashflow-guard** projects your cash position forward 90 days, then layers in FX risk using Monte Carlo simulation — showing not just an expected balance, but a realistic best-case / worst-case band for every foreign-currency transaction. When worst-case crosses a danger threshold, it's flagged visually and immediately actionable: a single click can convert & hold funds or settle the exposure early via Wise, closing the loop between *seeing* risk and *doing something about it*.

---

## Architecture

```
┌─────────────────────┐       ┌──────────────────────┐
│   React Frontend     │◄─────►│   FastAPI Backend     │
│  (Dashboard + Chart) │       │  (Cash Flow Engine)   │
└─────────┬────────────┘       └──────────┬────────────┘
          │                                │
          │  Convert & Hold /              │  Expands recurring txns,
          │  Settle Now                    │  walks 90-day balance
          ▼                                ▼
┌─────────────────────┐       ┌──────────────────────┐
│   Wise Platform API   │       │  FX & Risk Engine     │
│  (sandbox actions)    │       │  (Monte Carlo, NumPy) │
└─────────────────────┘       └──────────┬────────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │  Frankfurter.dev API   │
                               │ (historical FX rates) │
                               └──────────────────────┘
```

**Flow:**
1. Backend loads transaction data (payables/receivables, recurring + one-off) and expands them across a 90-day window.
2. For each foreign-currency transaction, the FX/Risk engine pulls historical rate data from Frankfurter.dev, computes volatility, and runs a Monte Carlo simulation to generate best/expected/worst-case outcomes.
3. The backend merges the base cash flow projection with the FX risk bands into a single forecast response.
4. The frontend renders this as a forecast line with a shaded risk band, flagging any point where worst-case crosses the danger threshold.
5. From a flagged transaction, the user can trigger **Convert & Hold** or **Settle Now** — calling the Wise sandbox API — which closes the loop by re-running the forecast so the chart updates live.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| FX Risk / Simulation | NumPy (Monte Carlo simulation) |
| Historical FX Data | [Frankfurter.dev](https://frankfurter.dev) |
| Frontend | React |
| Charting | Recharts |
| Payments / Actions | Wise Platform API (sandbox) |
| Data Format | JSON (mock transaction dataset for development) |

---

## Project Structure

```
fx-cashflow-guard/
├── backend/              # FastAPI app, cash flow engine, API endpoints
├── fx-engine/            # Frankfurter integration, volatility calc, Monte Carlo sim
├── frontend/             # React dashboard, Recharts band chart, action buttons
├── wise-integration/     # Convert & Hold / Settle Now endpoints, Wise sandbox client
├── data/                 # Mock transaction JSON (dev/demo dataset)
└── README.md
```

---

## Core Features

- **90-day cash flow forecast** — projects balance forward from a starting position, expanding recurring transactions (rent, payroll, subscriptions) and one-off invoices.
- **FX risk bands** — Monte Carlo simulation turns each foreign-currency transaction into a best/expected/worst-case range, visualized as a shaded band around the forecast line.
- **Danger threshold alerts** — when worst-case balance crosses a configurable threshold, it's flagged visually so risk is impossible to miss.
- **One-click hedging actions** — Convert & Hold or Settle Now, wired directly to flagged transactions and executed via the Wise Platform sandbox.
- **Live re-forecasting** — triggering an action re-runs the forecast so the impact is reflected immediately.

---

## Data Model

Development and demos run against a mock transaction dataset (`data/`) sized specifically to avoid common failure modes:

- 15–25 transactions spread across the full 90-day window
- Multiple currencies (USD base, EUR, GBP) with sufficient depth per currency to produce meaningful FX bands
- At least one large transaction sized to push worst-case below the danger threshold
- Two transactions pre-tagged (`demo_action`) for `convert_and_hold` and `settle_now`, so the demo flow doesn't require guessing which transaction maps to which button

See `data/field_guide` (top of the JSON file) for the full schema.

---

## Team / Ownership

| Role | Responsibility |
|---|---|
| Backend / Cash Flow Lead | FastAPI skeleton, cash flow engine, API response shape, merges FX data in |
| FX & Risk Engineer | Frankfurter integration, volatility calc, Monte Carlo simulation, danger threshold tuning |
| Frontend / Dashboard Engineer | React app, Recharts band chart, danger threshold line, action buttons |
| Wise Integration Engineer | Wise sandbox setup, Convert & Hold / Settle Now endpoints, end-to-end demo testing |

---

## Getting Started

> Setup instructions to be filled in once the backend and frontend skeletons are in place (`pip install -r requirements.txt`, `npm install`, environment variables for Wise sandbox credentials, etc.).

---

## Status

🚧 In development — built for a live 3-minute demo flow: forecast → risk band → danger threshold triggers → one-click Wise action → forecast updates.
