"""
Unit tests for Risk Classification Layer (Layer 2.5).
Can be run via: python -m unittest tests/test_risk_classifier.py
"""

import json
import unittest
import numpy as np

from backend.cash_flow_engine import CashFlowEngine
from backend.risk_classifier import RiskClassifier, RiskClassificationConfig

class TestRiskClassifier(unittest.TestCase):

    def setUp(self):
        # Default mock config
        self.config = RiskClassificationConfig()
        self.classifier = RiskClassifier(self.config)

        # Baseline CashFlowEngine
        self.engine = CashFlowEngine(
            transactions=[
                {"id": "tx1", "date": "2026-09-01", "type": "payable", "amount": 10000, "currency": "EUR"},
                {"id": "tx2", "date": "2026-09-10", "type": "receivable", "amount": 15000, "currency": "GBP"},
            ],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config={"base_currency": "USD", "rates": {"USD": 1.0, "EUR": 1.08, "GBP": 1.28}}
        )

    def _generate_mock_band(self, days=90, downside_growth=0.0):
        # Helper to construct a deterministic mock risk band list
        band = []
        base_val = 50000.0
        for i in range(days):
            date_str = f"2026-09-{i+1:02d}" if i < 30 else f"2026-10-{i-29:02d}"
            # Volatility width grows with day if downside_growth is positive
            spread = downside_growth * (i + 1)
            band.append({
                "date": date_str,
                "baseline": base_val,
                "p5": base_val - spread,
                "p50": base_val,
                "p95": base_val + spread
            })
        return band

    def test_horizons_exist_exactly_30_60_90(self):
        band = self._generate_mock_band(90, downside_growth=100.0)
        res = self.classifier.classify(self.engine, band, days=90)
        
        self.assertIn("30", res["horizons"])
        self.assertIn("60", res["horizons"])
        self.assertIn("90", res["horizons"])
        self.assertEqual(len(res["horizons"]), 3)

    def test_correct_day_mapping(self):
        band = self._generate_mock_band(90, downside_growth=10.0)
        res = self.classifier.classify(self.engine, band, days=90)
        
        # Day 30 is at index 29: baseline should match, date should match
        self.assertEqual(res["horizons"]["30"]["date"], "2026-09-30")
        self.assertEqual(res["horizons"]["60"]["date"], "2026-10-30")  # i=59: index offset mapping
        self.assertEqual(res["horizons"]["30"]["baseline"], 50000.0)

    def test_non_arbitrary_horizon_risk_levels(self):
        # Case A: Low risk everywhere
        low_band = self._generate_mock_band(90, downside_growth=0.0)
        res_low = self.classifier.classify(self.engine, low_band, days=90)
        self.assertEqual(res_low["horizons"]["30"]["overall_risk_level"], "LOW")
        self.assertEqual(res_low["horizons"]["60"]["overall_risk_level"], "LOW")
        self.assertEqual(res_low["horizons"]["90"]["overall_risk_level"], "LOW")

        # Case B: High risk everywhere
        high_band = self._generate_mock_band(90, downside_growth=1000.0)
        res_high = self.classifier.classify(self.engine, high_band, days=90)
        self.assertEqual(res_high["horizons"]["30"]["overall_risk_level"], "HIGH")
        self.assertEqual(res_high["horizons"]["60"]["overall_risk_level"], "HIGH")
        self.assertEqual(res_high["horizons"]["90"]["overall_risk_level"], "HIGH")

    def test_liquidity_breach(self):
        # Set a massive downside to force P5 below danger_threshold (20,000)
        # Baseline = 50,000. On day 90, spread is 40,000. P5 = 10,000 (< 20,000)
        breach_band = self._generate_mock_band(90, downside_growth=450.0)
        res = self.classifier.classify(self.engine, breach_band, days=90)
        
        snapshot_90 = res["horizons"]["90"]
        self.assertEqual(snapshot_90["liquidity_status"], "BREACH")
        self.assertEqual(snapshot_90["overall_risk_level"], "HIGH")
        self.assertGreaterEqual(snapshot_90["risk_score"], 67)

    def test_no_fx_exposure(self):
        usd_only_engine = CashFlowEngine(
            transactions=[{"id": "tx1", "date": "2026-09-01", "type": "payable", "amount": 10000, "currency": "USD"}],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config={"base_currency": "USD", "rates": {"USD": 1.0}}
        )
        flat_band = self._generate_mock_band(90, downside_growth=0.0)
        res = self.classifier.classify(usd_only_engine, flat_band, days=90)
        
        for h in ["30", "60", "90"]:
            self.assertEqual(res["horizons"][h]["fx_risk_level"], "LOW")
            self.assertEqual(res["horizons"][h]["risk_score"], 0)

    def test_worsening_trajectory(self):
        # Downside spreads grow rapidly over time: 30D spread is 300, 90D spread is 9000
        # This will escalate scores across horizons
        escalating_band = []
        base_val = 50000.0
        for i in range(90):
            # Non-linear spread growth to force LOW -> MEDIUM -> HIGH
            if i < 30:
                spread = 10.0
            elif i < 60:
                spread = 3000.0
            else:
                spread = 12000.0
            escalating_band.append({
                "date": f"2026-09-{i+1:02d}" if i < 30 else f"2026-10-{i-29:02d}",
                "baseline": base_val,
                "p5": base_val - spread,
                "p50": base_val,
                "p95": base_val + spread
            })
        res = self.classifier.classify(self.engine, escalating_band, days=90)
        self.assertEqual(res["trajectory"], "WORSENING")

    def test_improving_trajectory(self):
        # Construct an artificial reverse scenario where risk falls (e.g. maturing hedge)
        decreasing_band = []
        base_val = 50000.0
        for i in range(90):
            if i < 30:
                spread = 12000.0
            elif i < 60:
                spread = 3000.0
            else:
                spread = 10.0
            decreasing_band.append({
                "date": f"2026-09-{i+1:02d}" if i < 30 else f"2026-10-{i-29:02d}",
                "baseline": base_val,
                "p5": base_val - spread,
                "p50": base_val,
                "p95": base_val + spread
            })
        res = self.classifier.classify(self.engine, decreasing_band, days=90)
        self.assertEqual(res["trajectory"], "IMPROVING")

    def test_stable_trajectory(self):
        stable_band = self._generate_mock_band(90, downside_growth=0.0)
        res = self.classifier.classify(self.engine, stable_band, days=90)
        self.assertEqual(res["trajectory"], "STABLE")

    def test_mathematical_consistency(self):
        band = self._generate_mock_band(90, downside_growth=50.0)
        res = self.classifier.classify(self.engine, band, days=90)
        
        for h in ["30", "60", "90"]:
            snapshot = res["horizons"][h]
            self.assertGreaterEqual(snapshot["downside_amount"], 0.0)
            self.assertGreaterEqual(snapshot["band_width"], 0.0)
            expected_width = round(snapshot["p95"] - snapshot["p5"], 2)
            self.assertAlmostEqual(snapshot["band_width"], expected_width, places=2)

    def test_risk_score_bounds(self):
        # Test extreme boundaries to ensure clamp at 0 and 100
        low_band = self._generate_mock_band(90, downside_growth=0.0)
        res_low = self.classifier.classify(self.engine, low_band, days=90)
        for h in ["30", "60", "90"]:
            self.assertTrue(0 <= res_low["horizons"][h]["risk_score"] <= 100)

        extreme_high_band = self._generate_mock_band(90, downside_growth=80000.0)
        res_high = self.classifier.classify(self.engine, extreme_high_band, days=90)
        for h in ["30", "60", "90"]:
            self.assertTrue(0 <= res_high["horizons"][h]["risk_score"] <= 100)

    def test_no_nan_inf(self):
        # Validate that baseline = 0 or negative baseline doesn't crash calculations
        zero_baseline_band = [
            {"date": f"2026-09-{i+1:02d}", "baseline": 0.0, "p5": -100.0, "p50": 0.0, "p95": 100.0}
            for i in range(90)
        ]
        res = self.classifier.classify(self.engine, zero_baseline_band, days=90)
        for h in ["30", "60", "90"]:
            snapshot = res["horizons"][h]
            self.assertTrue(np.isfinite(snapshot["downside_pct"]))
            self.assertTrue(np.isfinite(snapshot["risk_score"]))

    def test_json_serializability(self):
        band = self._generate_mock_band(90, downside_growth=50.0)
        res = self.classifier.classify(self.engine, band, days=90)
        # Should not raise any TypeError
        raw_json = json.dumps(res)
        self.assertIsInstance(raw_json, str)


if __name__ == "__main__":
    unittest.main()
