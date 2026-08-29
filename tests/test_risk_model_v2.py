"""
Unit tests for Correlated FX Risk Engine (V2).
Can be run via: python -m unittest tests/test_risk_model_v2.py
"""

import unittest
from datetime import date
import numpy as np

from backend.cash_flow_engine import CashFlowEngine
from backend.risk_model_v2 import (
    load_aligned_returns,
    calculate_historical_covariance_and_correlation,
    stabilized_cholesky,
    get_risk_band,
    get_model_diagnostics,
    run_monte_carlo_forecast_v2
)

class TestRiskModelV2(unittest.TestCase):

    def setUp(self):
        # Create standard test CashFlowEngine
        self.mock_txs = [
            {"id": "t1", "date": "2026-09-01", "type": "payable", "amount": 10000, "currency": "EUR"},
            {"id": "t2", "date": "2026-09-10", "type": "receivable", "amount": 15000, "currency": "GBP"},
            {"id": "t3", "date": "2026-11-20", "type": "payable", "amount": 20000, "currency": "EUR"},
        ]
        self.engine = CashFlowEngine(
            transactions=self.mock_txs,
            starting_balance=50000,
            danger_threshold=20000,
            fx_config={"base_currency": "USD", "rates": {"USD": 1.0, "EUR": 1.08, "GBP": 1.28}}
        )

    def test_correlation_matrix_symmetry_and_validity(self):
        returns, currencies = load_aligned_returns()
        cov, corr = calculate_historical_covariance_and_correlation(returns, currencies)
        
        # Symmetry
        self.assertTrue(np.allclose(corr, corr.T, atol=1e-8))
        # Diagonal elements ≈ 1
        self.assertTrue(np.allclose(np.diag(corr), 1.0, atol=1e-5))
        # Bounds checking
        self.assertTrue((corr >= -1.0).all() and (corr <= 1.0).all())

    def test_covariance_symmetry(self):
        returns, currencies = load_aligned_returns()
        cov, corr = calculate_historical_covariance_and_correlation(returns, currencies)
        
        self.assertTrue(np.allclose(cov, cov.T, atol=1e-8))
        self.assertTrue((np.diag(cov) > 0).all())

    def test_cholesky_success(self):
        returns, currencies = load_aligned_returns()
        cov, corr = calculate_historical_covariance_and_correlation(returns, currencies)
        L = stabilized_cholesky(cov)
        
        self.assertTrue(np.allclose(L @ L.T, cov, atol=1e-5))
        self.assertFalse(np.isnan(L).any())

    def test_correlated_shock_generation(self):
        returns, currencies = load_aligned_returns()
        cov, corr = calculate_historical_covariance_and_correlation(returns, currencies)
        L = stabilized_cholesky(cov)
        
        rng = np.random.default_rng(100)
        Z = rng.normal(size=(50000, len(currencies)))
        shocks = Z @ L.T
        
        empirical_cov = np.cov(shocks, rowvar=False)
        empirical_corr = np.corrcoef(shocks, rowvar=False)
        
        self.assertTrue(np.allclose(empirical_cov, cov, atol=2e-2))
        self.assertTrue(np.allclose(empirical_corr, corr, atol=2e-2))

    def test_simulation_default_config(self):
        import inspect
        sig = inspect.signature(run_monte_carlo_forecast_v2)
        self.assertEqual(sig.parameters["n_simulations"].default, 2000)

    def test_horizon_uncertainty_expansion(self):
        band = get_risk_band(self.engine, days=90, n_simulations=2000, seed=42)
        self.assertEqual(len(band), 90)
        
        widths = [p["p95"] - p["p5"] for p in band]
        self.assertGreater(widths[-1], widths[10])

    def test_zero_exposure_collapses_band(self):
        zero_engine = CashFlowEngine(
            transactions=[{"id": "usd_only", "date": "2026-09-05", "type": "payable", "amount": 5000, "currency": "USD"}],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config={"base_currency": "USD", "rates": {"USD": 1.0, "EUR": 1.08, "GBP": 1.28}}
        )
        zero_band = get_risk_band(zero_engine, days=90, n_simulations=2000, seed=42)
        for p in zero_band:
            self.assertAlmostEqual(p["p5"], p["baseline"], places=2)
            self.assertAlmostEqual(p["p50"], p["baseline"], places=2)
            self.assertAlmostEqual(p["p95"], p["baseline"], places=2)

    def test_baseline_consistency(self):
        band = get_risk_band(self.engine, days=90, n_simulations=2000, seed=42)
        det_forecast = self.engine.get_forecast(days=90, base_date=date(2026, 9, 1))
        for i, p in enumerate(band):
            self.assertAlmostEqual(p["baseline"], det_forecast[i].balance, places=2)

    def test_model_diagnostics(self):
        diag = get_model_diagnostics()
        self.assertEqual(diag["model_version"], "v2")
        self.assertIn("correlated_monte_carlo", diag["method"])
        self.assertIn("currencies_modeled", diag)
        self.assertIn("correlation_matrix", diag)
        self.assertIn("volatility_comparison", diag)
        self.assertIn("ewma_daily_volatility", diag)
        self.assertIn("flat_historical_daily_volatility", diag)

    def test_data_alignment_diagnostics(self):
        from backend.risk_model_v2 import get_data_alignment_diagnostics
        data_diag = get_data_alignment_diagnostics()
        self.assertEqual(data_diag["status"], "HEALTHY")
        self.assertGreater(data_diag["raw_row_count"], 0)
        self.assertEqual(data_diag["rows_dropped"], 0)
        self.assertEqual(data_diag["alignment_retention_rate_pct"], 100.0)

    def test_ewma_volatility_calculation(self):
        from backend.risk_model_v2 import compute_ewma_volatility, load_aligned_returns, CACHE_PATH
        returns, currencies = load_aligned_returns(CACHE_PATH, ("EUR", "GBP"))
        ewma_eur = compute_ewma_volatility(returns[:, 0], lambda_decay=0.94)
        flat_eur = float(np.std(returns[:, 0], ddof=1))
        self.assertGreater(ewma_eur, 0.0)
        self.assertNotEqual(ewma_eur, flat_eur)


if __name__ == "__main__":
    unittest.main()
