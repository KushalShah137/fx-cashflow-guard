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
        self.assertEqual(diag["method"], "correlated_monte_carlo")
        self.assertIn("currencies_modeled", diag)
        self.assertIn("correlation_matrix", diag)

    def test_news_parameter_computation(self):
        from backend.risk_model_v2 import compute_news_parameters
        mock_news = {
            "currencies": {
                "EUR": {
                    "effective": {"drift_bias_bps": -20.0, "volatility_multiplier": 1.5},
                    "decay_days": 4,
                }
            }
        }
        mu, alpha = compute_news_parameters(mock_news, ["EUR", "GBP"], days=10)
        # Day 0: full effect
        self.assertAlmostEqual(mu[0, 0], -0.0020, places=4)
        self.assertAlmostEqual(alpha[0, 0], 1.5, places=2)
        # GBP unaffected
        self.assertAlmostEqual(mu[0, 1], 0.0)
        self.assertAlmostEqual(alpha[0, 1], 1.0)
        # Day 4+: decayed back to baseline
        self.assertAlmostEqual(mu[4, 0], 0.0)
        self.assertAlmostEqual(alpha[4, 0], 1.0)

    def test_news_sentiment_injection_expands_band(self):
        engine = CashFlowEngine(
            transactions=[
                {"id": "t_start", "date": "2026-09-01", "type": "payable", "amount": 0, "currency": "USD"},
                {"id": "t_eur", "date": "2026-09-06", "type": "payable", "amount": 25000, "currency": "EUR"},
            ],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config={"base_currency": "USD", "rates": {"USD": 1.0, "EUR": 1.08, "GBP": 1.28}},
        )
        # Run baseline simulation
        base_band = get_risk_band(
            engine, days=30, n_simulations=2000, seed=42, news_sentiment=None, news_cache_path=None
        )
        # Run shocked simulation with EUR elevated volatility
        mock_news = {
            "currencies": {
                "EUR": {
                    "effective": {"drift_bias_bps": -30.0, "volatility_multiplier": 1.8},
                    "decay_days": 10,
                }
            }
        }
        shocked_band = get_risk_band(
            engine, days=30, n_simulations=2000, seed=42, news_sentiment=mock_news, news_cache_path=None
        )

        # Day 6 (settlement date offset 5) shock width should be strictly wider
        base_width_d5 = base_band[5]["p95"] - base_band[5]["p5"]
        shock_width_d5 = shocked_band[5]["p95"] - shocked_band[5]["p5"]
        self.assertGreater(shock_width_d5, base_width_d5)

    def test_news_sentiment_none_matches_baseline(self):
        band_1 = get_risk_band(
            self.engine, days=15, n_simulations=500, seed=42, news_sentiment=None, news_cache_path=None
        )
        band_2 = get_risk_band(
            self.engine, days=15, n_simulations=500, seed=42, news_sentiment={}, news_cache_path=None
        )
        for p1, p2 in zip(band_1, band_2):
            self.assertEqual(p1["p5"], p2["p5"])
            self.assertEqual(p1["p50"], p2["p50"])
            self.assertEqual(p1["p95"], p2["p95"])


if __name__ == "__main__":
    unittest.main()
