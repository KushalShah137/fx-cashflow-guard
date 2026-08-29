"""
================================================================================
CORRELATED FX RISK ENGINE (V2)
--------------------------------------------------------------------------------
Layer 2 of the FX-Aware Cash Flow Forecaster.

Provides a correlated Monte Carlo simulation for FX rates using historical returns,
covariance estimation, and Cholesky decomposition to capture currency correlation.
Integrates with CashFlowEngine to produce 90-day cash flow forecasts with P5 (worst),
P50 (median), and P95 (best) Value-at-Risk (VaR) bands.

All simulations utilize the indirect quote convention of CashFlowEngine:
base_amount = foreign_amount / rate (where rate represents units of foreign
currency per 1 unit of base currency).
================================================================================
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import numpy as np

from backend.cash_flow_engine import CashFlowEngine, TransactionStatus, FlowDirection

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logger = logging.getLogger("risk_model_v2")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "fx_historical_cache.json"
NEWS_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "news_sentiment_cache.json"
DEFAULT_START_DATE = date(2026, 9, 1)  # Align with mock transactions date range
DEFAULT_CURRENCIES: Tuple[str, ...] = ("EUR", "GBP", "INR", "CNY", "JPY", "AUD")


def load_news_sentiment_cache(cache_path: Path = NEWS_CACHE_PATH) -> Optional[Dict[str, Any]]:
    """Loads news sentiment cache if present and valid; returns None on any failure."""
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not read news sentiment cache (%s). Falling back to baseline.", e)
        return None


def compute_news_parameters(
    sentiment_data: Optional[Dict[str, Any]],
    currencies_modeled: List[str],
    days: int,
    default_decay_days: int = 5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Translates news sentiment data into time-varying drift (mu) and volatility multiplier (alpha)
    matrices of shape (days, len(currencies_modeled)).

    When sentiment_data is None or empty:
      - mu_matrix is all zeros (zero drift)
      - alpha_matrix is all ones (1.0x baseline volatility)
    """
    n_ccy = len(currencies_modeled)
    mu_matrix = np.zeros((days, n_ccy), dtype=np.float64)
    alpha_matrix = np.ones((days, n_ccy), dtype=np.float64)

    if not sentiment_data:
        return mu_matrix, alpha_matrix

    ccy_dict = sentiment_data.get("currencies", sentiment_data)

    for idx, ccy in enumerate(currencies_modeled):
        if ccy not in ccy_dict:
            continue

        info = ccy_dict[ccy]
        effective = info.get("effective", {})
        raw = info.get("raw", {})

        # Drift in basis points (1 bp = 0.0001) -> converted to daily return drift
        drift_bps = effective.get(
            "drift_bias_bps",
            raw.get("drift_bias_bps", info.get("drift_bias_bps", 0.0)),
        )
        daily_drift = float(drift_bps) / 10000.0

        # Volatility multiplier (1.0 = baseline historical vol)
        vol_mult = effective.get(
            "volatility_multiplier",
            raw.get("volatility_multiplier", info.get("volatility_multiplier", 1.0)),
        )
        vol_mult = float(vol_mult)

        decay_days = max(1, int(info.get("decay_days", default_decay_days)))

        for t in range(days):
            if t < decay_days:
                decay_factor = 1.0 - (t / decay_days)
                mu_matrix[t, idx] = daily_drift * decay_factor
                alpha_matrix[t, idx] = 1.0 + (vol_mult - 1.0) * decay_factor
            else:
                mu_matrix[t, idx] = 0.0
                alpha_matrix[t, idx] = 1.0

    return mu_matrix, alpha_matrix


# --------------------------------------------------------------------------- #
# Step 1: Parse and Load Aligned Historical FX Data & Log Returns
# --------------------------------------------------------------------------- #
def load_aligned_returns(
    cache_path: Path = CACHE_PATH,
    currencies: Tuple[str, ...] = DEFAULT_CURRENCIES
) -> Tuple[np.ndarray, List[str]]:
    """
    Loads historical exchange rates from cache, filters/aligns by date,
    and returns a matrix of daily log returns of shape (N, len(currencies)).

    r_t = ln(P_t / P_{t-1})
    """
    if not cache_path.exists():
        raise FileNotFoundError(f"FX historical cache file not found at: {cache_path}")

    try:
        with open(cache_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to read/parse JSON from cache: {e}") from e

    rates_list = data.get("historical_rates", [])
    if not rates_list:
        raise ValueError("Historical rates cache is empty.")

    # Sort rates list by date to ensure proper returns calculation
    try:
        rates_list = sorted(rates_list, key=lambda x: x["date"])
    except KeyError:
        raise ValueError("Historical rates entries are missing the 'date' field.")

    # Extract aligned series
    aligned_dates: List[str] = []
    aligned_rates: Dict[str, List[float]] = {ccy: [] for ccy in currencies}

    for entry in rates_list:
        dt = entry.get("date")
        # Ensure all requested currencies have valid positive rates for this date
        if not dt or not all(ccy in entry and isinstance(entry[ccy], (int, float)) and entry[ccy] > 0 for ccy in currencies):
            continue
        aligned_dates.append(dt)
        for ccy in currencies:
            aligned_rates[ccy].append(float(entry[ccy]))

    n_obs = len(aligned_dates)
    if n_obs < 3:
        raise ValueError(f"Insufficient aligned observations ({n_obs}) to calculate historical returns.")

    # Compute daily log returns for each currency
    log_returns_list = []
    for ccy in currencies:
        prices = np.array(aligned_rates[ccy], dtype=np.float64)
        # Compute r_t = ln(P_t / P_{t-1})
        returns = np.diff(np.log(prices))
        log_returns_list.append(returns)

    # Combine into a single matrix of shape (N - 1, K)
    return_matrix = np.column_stack(log_returns_list)
    logger.info(
        "Successfully loaded and aligned %d historical FX return observations for %s",
        return_matrix.shape[0], currencies
    )
    return return_matrix, list(currencies)


# --------------------------------------------------------------------------- #
# Step 2: Correlation & Covariance Matrix Calculations
# --------------------------------------------------------------------------- #
def calculate_historical_covariance_and_correlation(
    return_matrix: np.ndarray,
    currencies: List[str]
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes standard covariance and correlation matrices from aligned returns.
    """
    if return_matrix.ndim != 2 or return_matrix.shape[1] != len(currencies):
        raise ValueError("Log returns matrix dimensions must match currencies list.")

    # Compute covariance and correlation matrices using NumPy
    cov_matrix = np.cov(return_matrix, rowvar=False)
    corr_matrix = np.corrcoef(return_matrix, rowvar=False)

    # If 1D arrays, convert to proper 2D matrices
    if np.isscalar(cov_matrix):
        cov_matrix = np.array([[cov_matrix]], dtype=np.float64)
    if np.isscalar(corr_matrix):
        corr_matrix = np.array([[corr_matrix]], dtype=np.float64)

    # Validations
    if not np.isfinite(cov_matrix).all() or not np.isfinite(corr_matrix).all():
        raise ValueError("Covariance or correlation matrix contains non-finite values.")

    # Symmetry validation
    if not np.allclose(cov_matrix, cov_matrix.T, atol=1e-8):
        raise ValueError("Computed covariance matrix is asymmetric.")
    if not np.allclose(corr_matrix, corr_matrix.T, atol=1e-8):
        raise ValueError("Computed correlation matrix is asymmetric.")

    # Diagonal check
    if not (np.diag(cov_matrix) > 0).all():
        raise ValueError("Covariance matrix diagonal contains zero or negative variance values.")
    if not np.allclose(np.diag(corr_matrix), 1.0, atol=1e-6):
        raise ValueError("Correlation matrix diagonal values must be approximately 1.0.")

    # Bounds check for correlation
    if not (corr_matrix >= -1.0 - 1e-6).all() or not (corr_matrix <= 1.0 + 1e-6).all():
        raise ValueError("Correlation matrix values lie outside the valid [-1, 1] range.")

    return cov_matrix, corr_matrix


# --------------------------------------------------------------------------- #
# Step 3: Stabilized Cholesky Decomposition
# --------------------------------------------------------------------------- #
def stabilized_cholesky(
    cov_matrix: np.ndarray,
    epsilon: float = 1e-9,
    max_retries: int = 3
) -> np.ndarray:
    """
    Performs Cholesky decomposition L of the covariance matrix.
    Includes diagonal stabilization (jitter) to handle near-singular cases.
    """
    cov_working = cov_matrix.copy()
    for attempt in range(max_retries):
        try:
            L = np.linalg.cholesky(cov_working)
            # Validate output
            if np.isnan(L).any() or not np.isfinite(L).all():
                raise ValueError("Cholesky output contains NaNs or non-finite elements.")

            # Validate decomposition L * L^T = cov_working
            if not np.allclose(L @ L.T, cov_working, atol=1e-6):
                raise ValueError("Cholesky decomposition validation failed: L @ L.T != covariance.")

            return L
        except np.linalg.LinAlgError:
            # If decomposition failed, apply small diagonal stabilization
            logger.warning(
                "Covariance matrix is not positive-definite. Applying stabilization jitter (eps=%.2e, attempt=%d/%d)",
                epsilon, attempt + 1, max_retries
            )
            np.fill_diagonal(cov_working, cov_working.diagonal() + epsilon)
            epsilon *= 10  # Increase stabilization magnitude for next attempt

    raise ValueError("Covariance matrix is singular or not positive-definite even after diagonal stabilization.")


# --------------------------------------------------------------------------- #
# Step 4: Correlated Monte Carlo Simulation Engine
# --------------------------------------------------------------------------- #
def run_monte_carlo_forecast_v2(
    engine: CashFlowEngine,
    days: int = 90,
    n_simulations: int = 2000,
    base_date: Optional[date] = None,
    seed: Optional[int] = 42,
    cache_path: Path = CACHE_PATH,
    news_sentiment: Optional[Dict[str, Any]] = None,
    news_cache_path: Optional[Path] = NEWS_CACHE_PATH,
) -> Dict[str, Any]:
    """
    Runs correlated Monte Carlo simulation using Cholesky-decomposed historical return cov.
    Aligns with existing CashFlowEngine interfaces, with optional macro news sentiment injection.
    """
    if days < 1:
        raise ValueError(f"forecast horizon must be >= 1 day, got {days}")
    if n_simulations < 10:
        raise ValueError(f"simulation count must be at least 10, got {n_simulations}")

    start_date = base_date or (min(tx.date for tx in engine.transactions) if engine.transactions else date.today())
    base_rates = dict(engine.fx_rates)
    foreign_currencies = [c for c in base_rates if c != engine.base_currency]

    # Handle zero-exposure or base-only currencies scenario
    if not foreign_currencies:
        # Fall back to baseline forecast with 0 volatility
        logger.info("No foreign currencies exposed. Returning collapsed baseline forecast.")
        baseline_forecast = engine.get_forecast(days=days, base_date=start_date)
        forecast_points = []
        for p in baseline_forecast:
            val = round(p.balance, 2)
            forecast_points.append({
                "date": p.date.isoformat(),
                "best": val,
                "expected": val,
                "worst": val,
                "net_change": 0.0  # Will be calculated dynamically below if needed
            })
        return {
            "currency": engine.base_currency,
            "starting_balance": round(engine.starting_balance, 2),
            "danger_threshold": engine.danger_threshold,
            "has_breach": any(p["worst"] < (engine.danger_threshold or 0) for p in forecast_points),
            "breach_dates": [p["date"] for p in forecast_points if p["worst"] < (engine.danger_threshold or 0)],
            "summary": {
                "min_worst_case": round(min(p["worst"] for p in forecast_points), 2),
                "max_best_case": round(max(p["best"] for p in forecast_points), 2),
                "final_expected": round(forecast_points[-1]["expected"], 2)
            },
            "forecast": forecast_points
        }

    # Load and decompose returns matrix
    return_matrix, currencies_modeled = load_aligned_returns(cache_path, tuple(foreign_currencies))
    cov_matrix, corr_matrix = calculate_historical_covariance_and_correlation(return_matrix, currencies_modeled)
    L = stabilized_cholesky(cov_matrix)

    # Initialize local RNG for reproducibility
    rng = np.random.default_rng(seed)

    # Vectorized Correlated Shock Generation:
    # 1. Draw standard normal shocks Z of shape (n_simulations, days, n_currencies)
    Z = rng.normal(loc=0.0, scale=1.0, size=(n_simulations, days, len(currencies_modeled)))
    # 2. Correlate using Cholesky factor: shocks = Z @ L.T
    # Resulting shocks shape: (n_simulations, days, n_currencies)
    shocks = Z @ L.T

    # 3. Inject news sentiment drift (mu) & volatility scaling (alpha)
    if news_sentiment is None and news_cache_path is not None:
        news_sentiment = load_news_sentiment_cache(news_cache_path)

    mu_mat, alpha_mat = compute_news_parameters(news_sentiment, currencies_modeled, days)
    # Apply broadcasted adjustments: (days, n_currencies) -> (n_simulations, days, n_currencies)
    shocks = mu_mat + (alpha_mat * shocks)

    # 4. Ensure rate on day 0 is spot rate (no shock yet)
    shocks[:, 0, :] = 0.0

    # Cumulate simulated log returns over the horizon to get rate paths
    cum_shocks = np.cumsum(shocks, axis=1) # (n_simulations, days, n_currencies)
    
    # Evolve rate paths for each foreign currency: simulated_rate = base_rate * exp(cum_shocks)
    rate_paths: Dict[str, np.ndarray] = {}
    for idx, ccy in enumerate(currencies_modeled):
        r0 = base_rates[ccy]
        rate_paths[ccy] = r0 * np.exp(cum_shocks[:, :, idx])

    # Filter out cancelled transactions
    relevant = [
        tx for tx in engine.transactions
        if tx.status != TransactionStatus.CANCELLED
    ]

    # Log current portfolio exposures for tracking
    exposures = engine.get_currency_exposures()
    logger.info("Current net portfolio currency exposures: %s", 
                [{e.currency: e.net_exposure} for e in exposures])

    # Initialize daily cashflows matrix: shape (n_simulations, days)
    daily_cashflows = np.zeros((n_simulations, days), dtype=np.float64)
    # Track baseline (static) daily net changes in base currency
    deterministic_daily_net = np.zeros(days, dtype=np.float64)

    for tx in relevant:
        day_offset = (tx.date - start_date).days
        if 0 <= day_offset < days:
            # Deterministic baseline conversion using spot rate
            det_base_amt = engine.convert_to_base(tx.signed_amount, tx.currency)
            deterministic_daily_net[day_offset] += det_base_amt

            # Simulated revaluation
            if tx.status == TransactionStatus.SETTLED or tx.currency == engine.base_currency:
                # If transaction is already settled or in base currency, it has zero volatility.
                # Its value remains locked at static converted amount.
                daily_cashflows[:, day_offset] += det_base_amt
            else:
                # Evolve using simulated paths
                sim_rates = rate_paths[tx.currency][:, day_offset]
                daily_cashflows[:, day_offset] += (tx.signed_amount / sim_rates)

    # Compute cumulative balance paths: shape (n_simulations, days)
    cumulative_cashflows = np.cumsum(daily_cashflows, axis=1)
    balance_paths = engine.starting_balance + cumulative_cashflows

    # Extract daily confidence percentiles (P5, P50, P95)
    p5 = np.percentile(balance_paths, 5, axis=0)
    p50 = np.percentile(balance_paths, 50, axis=0)
    p95 = np.percentile(balance_paths, 95, axis=0)

    # Retrieve Layer 1 baseline forecast series
    baseline_forecast = engine.get_forecast(days=days, base_date=start_date)

    forecast_points = []
    breach_dates = []
    danger_threshold = engine.danger_threshold or 20000.0

    for i in range(days):
        current_day = start_date + timedelta(days=i)
        day_str = current_day.isoformat()
        baseline_val = round(baseline_forecast[i].balance, 2)

        worst_val = round(float(p5[i]), 2)
        expected_val = round(float(p50[i]), 2)
        best_val = round(float(p95[i]), 2)

        if worst_val < danger_threshold:
            breach_dates.append(day_str)

        forecast_points.append({
            "date": day_str,
            "baseline": baseline_val,
            "best": best_val,
            "expected": expected_val,
            "worst": worst_val,
            "net_change": round(deterministic_daily_net[i], 2),
        })


    all_worst = [p["worst"] for p in forecast_points]
    all_best = [p["best"] for p in forecast_points]

    min_worst = min(all_worst) if all_worst else engine.starting_balance
    max_best = max(all_best) if all_best else engine.starting_balance
    final_expected = forecast_points[-1]["expected"] if forecast_points else engine.starting_balance

    return {
        "currency": engine.base_currency,
        "starting_balance": round(engine.starting_balance, 2),
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


# --------------------------------------------------------------------------- #
# Step 5: High-Level Client Functions
# --------------------------------------------------------------------------- #
def get_risk_band(
    engine: CashFlowEngine,
    days: int = 90,
    n_simulations: int = 2000,
    seed: Optional[int] = 42,
    cache_path: Path = CACHE_PATH,
    news_sentiment: Optional[Dict[str, Any]] = None,
    news_cache_path: Optional[Path] = NEWS_CACHE_PATH,
) -> List[Dict[str, Any]]:
    """
    Primary API function returning the risk band in a Recharts-friendly contract:
    list of dict with {date, baseline, p5, p50, p95}
    """
    res = run_monte_carlo_forecast_v2(
        engine=engine,
        days=days,
        n_simulations=n_simulations,
        seed=seed,
        cache_path=cache_path,
        news_sentiment=news_sentiment,
        news_cache_path=news_cache_path,
    )
    risk_band = []
    for p in res["forecast"]:
        risk_band.append({
            "date": p["date"],
            "baseline": p["baseline"],
            "p5": p["worst"],
            "p50": p["expected"],
            "p95": p["best"]
        })
    return risk_band


def get_model_diagnostics(
    cache_path: Path = CACHE_PATH,
    currencies: Optional[Tuple[str, ...]] = None,
) -> Dict[str, Any]:
    """
    Diagnostic dashboard endpoint returning matrix calculations for hackathon judges.
    """
    if currencies is None:
        currencies = DEFAULT_CURRENCIES
    try:
        return_matrix, ccy_list = load_aligned_returns(cache_path, currencies)
        cov_matrix, corr_matrix = calculate_historical_covariance_and_correlation(return_matrix, ccy_list)
        L = stabilized_cholesky(cov_matrix)

        return {
            "model_version": "v2",
            "method": "correlated_monte_carlo",
            "currencies_modeled": ccy_list,
            "observations_count": int(return_matrix.shape[0]),
            "correlation_matrix": corr_matrix.tolist(),
            "covariance_matrix": cov_matrix.tolist(),
            "cholesky_matrix": L.tolist(),
            "numerical_stabilization_epsilon": 1e-9
        }
    except Exception as e:
        logger.error("Failed to compute diagnostics: %s", e)
        return {
            "model_version": "v2",
            "error": str(e),
            "status": "diagnostics_unavailable"
        }


# ============================================================================ #
# V2 SELF-TESTS (Step 14)
# ============================================================================ #
def _run_diagnostics_and_self_tests() -> None:
    """Runs a battery of unit self-tests to verify correlation and matrix logic."""
    print("=" * 70)
    print("CORRELATED FX RISK ENGINE V2 — SELF TESTS")
    print("=" * 70)

    # 1. Load data
    try:
        returns, currencies = load_aligned_returns(CACHE_PATH, ("EUR", "GBP"))
        print(f"[PASS] Aligned returns loaded: {returns.shape[0]} rows, currencies: {currencies}")
    except Exception as e:
        print(f"[FAIL] Returns loader failed: {e}")
        return

    # 2. Covariance and Correlation calculations
    try:
        cov, corr = calculate_historical_covariance_and_correlation(returns, currencies)
        
        # TEST 1 & 2: Correlation matrix validity
        assert np.allclose(corr, corr.T), "Correlation matrix is not symmetric."
        assert np.allclose(np.diag(corr), 1.0, atol=1e-5), "Correlation diagonal is not 1."
        assert (corr >= -1.0).all() and (corr <= 1.0).all(), "Correlation coefficients out of bounds."
        print(f"[PASS] Test 1 & 2: Correlation Matrix Symmetry & Validity passed.")
        print(f"       EUR/GBP correlation coefficient: {corr[0, 1]:.4f}")

        # TEST 3: Covariance matrix symmetry
        assert np.allclose(cov, cov.T), "Covariance matrix is not symmetric."
        assert (np.diag(cov) > 0).all(), "Covariance diagonal contains non-positive variance."
        print("[PASS] Test 3: Covariance Matrix Symmetry passed.")
    except Exception as e:
        print(f"[FAIL] Matrix calculations failed: {e}")
        return

    # 3. TEST 4: Stabilized Cholesky success
    try:
        L = stabilized_cholesky(cov)
        assert np.allclose(L @ L.T, cov, atol=1e-5), "L @ L.T does not reconstruct covariance matrix."
        assert not np.isnan(L).any(), "Cholesky matrix L contains NaNs."
        print("[PASS] Test 4: Cholesky decomposition & reconstruction succeeded.")
    except Exception as e:
        print(f"[FAIL] Cholesky failed: {e}")
        return

    # 4. TEST 5: Correlated Shock Generation Validation
    try:
        rng = np.random.default_rng(42)
        n_test_sims = 100000  # Large sample for statistical validation
        Z_test = rng.normal(size=(n_test_sims, len(currencies)))
        shocks_test = Z_test @ L.T
        empirical_cov = np.cov(shocks_test, rowvar=False)
        empirical_corr = np.corrcoef(shocks_test, rowvar=False)

        assert np.allclose(empirical_cov, cov, atol=1e-2), "Empirical covariance does not match theoretical cov."
        assert np.allclose(empirical_corr, corr, atol=1e-2), "Empirical correlation does not match theoretical corr."
        print(f"[PASS] Test 5: Correlated shocks correctly reproduce covariance structure.")
    except Exception as e:
        print(f"[FAIL] Shock validation failed: {e}")
        return

    # 5. TEST 6: Default Simulation Count config check
    # Check signature defaults
    import inspect
    sig = inspect.signature(run_monte_carlo_forecast_v2)
    assert sig.parameters["n_simulations"].default == 2000, "Default simulations must be 2000."
    print("[PASS] Test 6: Default simulation count config is exactly 2000.")

    # 6. Setup sample CashFlowEngine for Forecast tests
    mock_txs = [
        {"id": "t1", "date": "2026-09-01", "type": "payable", "amount": 10000, "currency": "EUR"},
        {"id": "t2", "date": "2026-09-10", "type": "receivable", "amount": 15000, "currency": "GBP"},
        {"id": "t3", "date": "2026-11-20", "type": "payable", "amount": 20000, "currency": "EUR"},
    ]
    engine = CashFlowEngine(
        transactions=mock_txs,
        starting_balance=50000,
        danger_threshold=20000,
        fx_config={"base_currency": "USD", "rates": {"USD": 1.0, "EUR": 1.08, "GBP": 1.28}}
    )

    # TEST 7: Horizon Uncertainty Expansion
    try:
        band = get_risk_band(engine, days=90, n_simulations=2000, seed=42)
        assert len(band) == 90, "Risk band should contain exactly 90 entries."
        
        # Calculate widths (p95 - p5) over time
        widths = [p["p95"] - p["p5"] for p in band]
        
        # Uncertainty should generally expand over time as shocks cumulate
        # Verify that terminal uncertainty is significantly higher than early uncertainty
        assert widths[-1] > widths[10], "Risk band does not widen as forecast horizon increases."
        print(f"[PASS] Test 7: Horizon uncertainty expansion confirmed. Day 10 width: {widths[10]:.2f}, Day 90 width: {widths[-1]:.2f}")
    except Exception as e:
        print(f"[FAIL] Horizon uncertainty test failed: {e}")
        return

    # 7. TEST 8: Zero-exposure collapses band to baseline
    try:
        zero_engine = CashFlowEngine(
            transactions=[{"id": "usd_only", "date": "2026-09-05", "type": "payable", "amount": 5000, "currency": "USD"}],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config={"base_currency": "USD", "rates": {"USD": 1.0, "EUR": 1.08, "GBP": 1.28}}
        )
        zero_band = get_risk_band(zero_engine, days=90, n_simulations=2000, seed=42)
        for p in zero_band:
            assert np.isclose(p["p5"], p["baseline"], atol=1e-2), f"Band did not collapse: {p}"
            assert np.isclose(p["p50"], p["baseline"], atol=1e-2), f"Band did not collapse: {p}"
            assert np.isclose(p["p95"], p["baseline"], atol=1e-2), f"Band did not collapse: {p}"
        print("[PASS] Test 8: Zero FX exposure successfully collapsed the risk band to baseline.")
    except Exception as e:
        print(f"[FAIL] Zero-exposure collapse test failed: {e}")
        return

    # 8. TEST 9: Baseline consistency check
    try:
        # Verify that when exposure is non-zero, baseline values in risk_band match deterministic forecast
        det_forecast = engine.get_forecast(days=90, base_date=DEFAULT_START_DATE)
        for i, p in enumerate(band):
            assert np.isclose(p["baseline"], det_forecast[i].balance, atol=1e-2), "Baseline mismatch."
        print("[PASS] Test 9: Risk engine baseline is perfectly consistent with Layer 1 deterministic forecast.")
    except Exception as e:
        print(f"[FAIL] Baseline consistency check failed: {e}")
        return

    print("=" * 70)
    print("ALL V2 RISK ENGINE SELF TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    _run_diagnostics_and_self_tests()
