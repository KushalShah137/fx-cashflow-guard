import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np

from backend.cash_flow_engine import CashFlowEngine, TransactionStatus, FlowDirection

logger = logging.getLogger("risk_model")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "fx_historical_cache.json"
DEFAULT_START_DATE = date(2026, 8, 29)


def compute_historical_volatilities(cache_path: Path = CACHE_PATH) -> Dict[str, float]:
    """
    Computes standard deviation of daily log returns for foreign currencies
    from the historical FX cache file.
    """
    default_vols = {"EUR": 0.008, "GBP": 0.009}
    if not cache_path.exists():
        logger.warning("FX cache not found at %s; using default volatilities.", cache_path)
        return default_vols

    try:
        with open(cache_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        rates_list = data.get("historical_rates", [])
        if not rates_list:
            return default_vols

        currencies = data.get("currencies", ["EUR", "GBP", "INR", "CNY", "JPY", "AUD"])
        vols = {}
        for ccy in currencies:
            rates = [r[ccy] for r in rates_list if ccy in r and r[ccy] > 0]
            if len(rates) > 2:
                log_returns = np.diff(np.log(rates))
                vols[ccy] = float(np.std(log_returns))
            else:
                vols[ccy] = default_vols.get(ccy, 0.008)
        return vols
    except Exception as e:
        logger.error("Failed to compute volatility from FX cache: %s", e)
        return default_vols


def run_monte_carlo_forecast(
    engine: CashFlowEngine,
    days: int = 90,
    target_currency: str = "USD",
    n_simulations: int = 1000,
    base_date: Optional[date] = None,
    seed: Optional[int] = 42,
) -> Dict[str, Any]:
    """
    Runs Monte Carlo simulation over the cash flow engine transactions
    generating 5th (worst), 50th (expected), and 95th (best) percentiles.
    """
    if seed is not None:
        np.random.seed(seed)

    target_currency = target_currency.upper().strip()
    start_date = base_date or DEFAULT_START_DATE
    volatilities = compute_historical_volatilities()

    # Base initial exchange rates from engine
    base_rates = dict(engine.fx_rates)
    foreign_currencies = [c for c in base_rates if c != engine.base_currency]

    # Generate daily FX rate simulation paths for each foreign currency:
    # Shape: (n_simulations, days)
    # rate_t = rate_0 * exp(cumsum(shocks))
    rate_paths: Dict[str, np.ndarray] = {}
    for ccy in foreign_currencies:
        sigma = volatilities.get(ccy, 0.008)
        r0 = base_rates.get(ccy, 1.0)
        # Daily standard normal shocks
        shocks = np.random.normal(loc=0.0, scale=sigma, size=(n_simulations, days))
        # Initial day t=0 has no shock yet (rate = r0)
        shocks[:, 0] = 0.0
        log_paths = np.cumsum(shocks, axis=1)
        rate_paths[ccy] = r0 * np.exp(log_paths)

    # Filter relevant transactions (pending or settled, not cancelled)
    relevant = [
        tx for tx in engine.transactions
        if tx.status != TransactionStatus.CANCELLED
    ]

    # Matrix of daily cash flows in base currency (USD) across simulations: (n_simulations, days)
    daily_cashflows = np.zeros((n_simulations, days), dtype=np.float64)
    # Also track deterministic net change per day in base currency
    deterministic_daily_net = np.zeros(days, dtype=np.float64)

    for tx in relevant:
        day_offset = (tx.date - start_date).days
        if 0 <= day_offset < days:
            # Deterministic base conversion using static rate
            det_base_amt = engine.convert_to_base(tx.signed_amount, tx.currency)
            deterministic_daily_net[day_offset] += det_base_amt

            # Simulated base conversion across all simulation runs
            if tx.currency == engine.base_currency:
                daily_cashflows[:, day_offset] += tx.signed_amount
            else:
                # Rate convention in engine: base_amount = amount / rate
                simulated_rates_on_day = rate_paths[tx.currency][:, day_offset]
                daily_cashflows[:, day_offset] += (tx.signed_amount / simulated_rates_on_day)

    # Compute cumulative balance paths: (n_simulations, days)
    cumulative_cashflows = np.cumsum(daily_cashflows, axis=1)
    balance_paths = engine.starting_balance + cumulative_cashflows

    # Compute percentiles per day across the 1000 simulations
    p5 = np.percentile(balance_paths, 5, axis=0)
    p50 = np.percentile(balance_paths, 50, axis=0)
    p95 = np.percentile(balance_paths, 95, axis=0)

    # Target currency scaling factor (if user requested forecast in EUR or GBP instead of USD)
    target_rate = engine.fx_rates.get(target_currency, 1.0)
    scale_factor = target_rate if target_currency != engine.base_currency else 1.0

    scaled_starting_balance = round(engine.starting_balance * scale_factor, 2)
    danger_threshold = (
        round(engine.danger_threshold * scale_factor, 2)
        if engine.danger_threshold is not None
        else 20000.0
    )

    forecast_points: List[Dict[str, Any]] = []
    breach_dates: List[str] = []

    for i in range(days):
        current_day = start_date + timedelta(days=i)
        day_str = current_day.isoformat()

        worst_val = round(float(p5[i]) * scale_factor, 2)
        expected_val = round(float(p50[i]) * scale_factor, 2)
        best_val = round(float(p95[i]) * scale_factor, 2)
        net_change_val = round(float(deterministic_daily_net[i]) * scale_factor, 2)

        if worst_val < danger_threshold:
            breach_dates.append(day_str)

        forecast_points.append({
            "date": day_str,
            "best": best_val,
            "expected": expected_val,
            "worst": worst_val,
            "net_change": net_change_val,
        })

    all_worst = [p["worst"] for p in forecast_points]
    all_best = [p["best"] for p in forecast_points]

    min_worst = min(all_worst) if all_worst else scaled_starting_balance
    max_best = max(all_best) if all_best else scaled_starting_balance
    final_expected = forecast_points[-1]["expected"] if forecast_points else scaled_starting_balance

    return {
        "currency": target_currency,
        "starting_balance": scaled_starting_balance,
        "danger_threshold": danger_threshold,
        "has_breach": len(breach_dates) > 0,
        "breach_dates": breach_dates,
        "summary": {
            "min_worst_case": round(min_worst, 2),
            "max_best_case": round(max_best, 2),
            "final_expected": round(final_expected, 2),
        },
        "forecast": forecast_points,
    }