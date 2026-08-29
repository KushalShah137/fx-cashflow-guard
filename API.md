# fx-cashflow-guard API Documentation

This API supports the React/Recharts frontend by providing clean separation between deterministic forecasts (Layer 1), raw risk simulation distributions (Layer 2), and through-horizon business risk classifications (Layer 2.5).

---

## 1. GET `/forecast`
*   **Layer Owner**: Layer 1 (Deterministic Cash Flow Engine)
*   **Purpose**: Returns the day-by-day deterministic cash balance forecast based on settled and pending transactions. Excludes FX volatility modeling.
*   **Query Parameters**:
    *   `days` (integer, default=90): The forecast horizon length in days.
*   **Response Schema**: List of points containing:
    *   `date` (string, ISO format): The day of the forecast.
    *   `balance` (float): Projected baseline balance in base currency (USD).
    *   `is_breach` (boolean): Whether the projected balance falls below the danger floor.
    *   `transactions_today` (list of strings): Transaction IDs settling on this day.
*   **Example Response**:
    ```json
    [
      {
        "date": "2026-09-01",
        "balance": 41500.0,
        "is_breach": false,
        "transactions_today": ["txn_001"]
      }
    ]
    ```

---

## 2. GET `/risk-band`
*   **Layer Owner**: Layer 2 V2 (Correlated FX Risk Engine)
*   **Purpose**: Runs a 2,000-path correlated Monte Carlo simulation and returns the risk distribution envelope (P5, P50, P95 percentiles).
*   **Query Parameters**:
    *   `days` (integer, default=90): The forecast horizon length in days.
    *   `simulations` (integer, default=2000): Number of Monte Carlo simulation runs.
*   **Response Schema**: Dictionary containing:
    *   `days` (integer): Forecast days.
    *   `simulations` (integer): Simulation count.
    *   `currency` (string): Base currency of the forecast.
    *   `risk_band` (list of objects): Daily points containing `{date, baseline, p5, p50, p95}`.
*   **Example Response**:
    ```json
    {
      "days": 90,
      "simulations": 2000,
      "currency": "USD",
      "risk_band": [
        {
          "date": "2026-09-01",
          "baseline": 41500.0,
          "p5": 41500.0,
          "p50": 41500.0,
          "p95": 41500.0
        }
      ]
    }
    ```

---

## 3. GET `/risk-classification`
*   **Layer Owner**: Layer 2.5 (Risk Classification & Presentation Layer)
*   **Purpose**: Analyzes the Monte Carlo simulation to classify through-horizon and point-in-time risks at the 30D, 60D, and 90D planning horizons.
*   **Query Parameters**:
    *   `days` (integer, default=90): The forecast horizon length in days.
    *   `simulations` (integer, default=2000): Number of Monte Carlo simulation runs.
*   **Response Schema**:
    *   `model_version` (string): Codebase version of the classifier.
    *   `forecast_days` (integer): Projection length.
    *   `overall_risk_level` (string: LOW/MEDIUM/HIGH): Highest risk level across horizons.
    *   `overall_risk_score` (integer, 0-100): Normalized decision severity score.
    *   `risk_trajectory` (string: STABLE/WORSENING/IMPROVING): Evolution of risk from Day 30 to Day 90.
    *   `risk_pressure` (string: INCREASING/STABLE/DECREASING): Trend in simulated terminal band width.
    *   `horizons` (object): Snapshots for "30", "60", and "90" containing:
        *   `point_in_time`: Metrics evaluated on that specific horizon date.
        *   `through_horizon`: Metrics evaluated across every day from Day 1 to that horizon.
        *   `classification`: `{fx_risk_level, liquidity_status, overall_risk_level, risk_score}`.
        *   `explanation`: Plain English human-readable business explanation.
    *   `horizon_comparison` (list): Compact version of snapshots for cards and tables.
    *   `exposures` (list): Gross/net base currency equivalent currency exposures from Layer 1.
    *   `dashboard_kpis` (object): Fast-binding KPIs for widgets.
    *   `chart_annotations` (object): Visual indicators (first breach date, dates for 30/60/90D markers).
    *   `decision_context` (object): Parameters formatted for the future Decision Engine.
    *   `risk_band` (list): The complete risk band dataset.

---

## 4. GET `/risk-overview`
*   **Layer Owner**: API Aggregator
*   **Purpose**: Combines baseline forecasts, risk bands, classifications, and exposures in a single response to minimize HTTP round-trips for the dashboard.
*   **Response Schema**:
    *   `baseline_forecast`: Same as `GET /forecast`.
    *   `risk_band`: Same as `GET /risk-band`'s `risk_band` array.
    *   `risk_classification`: Same as `GET /risk-classification`.
    *   `exposures`: Same as `/exposures`.
