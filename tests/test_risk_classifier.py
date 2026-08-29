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
        self.assertEqual(res["horizons"]["30"]["point_in_time"]["date"], "2026-09-30")
        self.assertEqual(res["horizons"]["60"]["point_in_time"]["date"], "2026-10-30")  # index 59
        self.assertEqual(res["horizons"]["30"]["point_in_time"]["baseline"], 50000.0)

    def test_non_arbitrary_horizon_risk_levels(self):
        # Case A: Low risk everywhere
        low_band = self._generate_mock_band(90, downside_growth=0.0)
        res_low = self.classifier.classify(self.engine, low_band, days=90)
        self.assertEqual(res_low["horizons"]["30"]["classification"]["overall_risk_level"], "LOW")
        self.assertEqual(res_low["horizons"]["60"]["classification"]["overall_risk_level"], "LOW")
        self.assertEqual(res_low["horizons"]["90"]["classification"]["overall_risk_level"], "LOW")

        # Case B: High risk everywhere
        high_band = self._generate_mock_band(90, downside_growth=1000.0)
        res_high = self.classifier.classify(self.engine, high_band, days=90)
        self.assertEqual(res_high["horizons"]["30"]["classification"]["overall_risk_level"], "HIGH")
        self.assertEqual(res_high["horizons"]["60"]["classification"]["overall_risk_level"], "HIGH")
        self.assertEqual(res_high["horizons"]["90"]["classification"]["overall_risk_level"], "HIGH")

    def test_liquidity_breach(self):
        # Set a downside that forces P5 below danger_threshold (20,000)
        # Baseline = 50,000. spread grows at 450 per day, so day 90 spread is 450 * 90 = 40500. p5 = 9500 (< 20000)
        breach_band = self._generate_mock_band(90, downside_growth=450.0)
        res = self.classifier.classify(self.engine, breach_band, days=90)
        
        snapshot_90 = res["horizons"]["90"]
        self.assertEqual(snapshot_90["classification"]["liquidity_status"], "BREACH")
        self.assertEqual(snapshot_90["classification"]["overall_risk_level"], "HIGH")
        self.assertGreaterEqual(snapshot_90["classification"]["risk_score"], 67)

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
            self.assertEqual(res["horizons"][h]["classification"]["fx_risk_level"], "LOW")
            self.assertEqual(res["horizons"][h]["classification"]["risk_score"], 0)

    def test_worsening_trajectory(self):
        # Non-linear spread growth to force WORSENING trajectory
        escalating_band = []
        base_val = 50000.0
        for i in range(90):
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
        self.assertEqual(res["risk_trajectory"], "WORSENING")

    def test_improving_trajectory(self):
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
        self.assertEqual(res["risk_trajectory"], "IMPROVING")

    def test_stable_trajectory(self):
        stable_band = self._generate_mock_band(90, downside_growth=0.0)
        res = self.classifier.classify(self.engine, stable_band, days=90)
        self.assertEqual(res["risk_trajectory"], "STABLE")

    def test_mathematical_consistency(self):
        band = self._generate_mock_band(90, downside_growth=50.0)
        res = self.classifier.classify(self.engine, band, days=90)
        
        for h in ["30", "60", "90"]:
            snapshot = res["horizons"][h]
            # PIT checks
            pit = snapshot["point_in_time"]
            self.assertGreaterEqual(pit["downside_amount"], 0.0)
            self.assertGreaterEqual(pit["band_width"], 0.0)
            expected_width = round(pit["p95"] - pit["p5"], 2)
            self.assertAlmostEqual(pit["band_width"], expected_width, places=2)

    def test_risk_score_bounds(self):
        low_band = self._generate_mock_band(90, downside_growth=0.0)
        res_low = self.classifier.classify(self.engine, low_band, days=90)
        for h in ["30", "60", "90"]:
            self.assertTrue(0 <= res_low["horizons"][h]["classification"]["risk_score"] <= 100)

        extreme_high_band = self._generate_mock_band(90, downside_growth=80000.0)
        res_high = self.classifier.classify(self.engine, extreme_high_band, days=90)
        for h in ["30", "60", "90"]:
            self.assertTrue(0 <= res_high["horizons"][h]["classification"]["risk_score"] <= 100)

    def test_no_nan_inf(self):
        zero_baseline_band = [
            {"date": f"2026-09-{i+1:02d}", "baseline": 0.0, "p5": -100.0, "p50": 0.0, "p95": 100.0}
            for i in range(90)
        ]
        res = self.classifier.classify(self.engine, zero_baseline_band, days=90)
        for h in ["30", "60", "90"]:
            snapshot = res["horizons"][h]
            self.assertTrue(np.isfinite(snapshot["point_in_time"]["downside_pct"]))
            self.assertTrue(np.isfinite(snapshot["classification"]["risk_score"]))

    def test_json_serializability(self):
        band = self._generate_mock_band(90, downside_growth=50.0)
        res = self.classifier.classify(self.engine, band, days=90)
        raw_json = json.dumps(res)
        self.assertIsInstance(raw_json, str)

    def test_through_horizon_minimums(self):
        # A band where balance starts at 50k, drops to 25k on day 15, then recovers to 50k on day 30, and drops to 15k on day 50.
        band = []
        base_val = 50000.0
        for i in range(90):
            day_num = i + 1
            if day_num == 15:
                p5 = 25000.0
            elif day_num == 50:
                p5 = 15000.0
            else:
                p5 = 48000.0
            band.append({
                "date": f"2026-09-{day_num:02d}" if day_num <= 30 else f"2026-10-{day_num-30:02d}",
                "baseline": base_val,
                "p5": p5,
                "p50": base_val,
                "p95": base_val + 2000.0
            })
        
        res = self.classifier.classify(self.engine, band, days=90)
        # Test B: 30D minimum P5 is 25000.0
        self.assertEqual(res["horizons"]["30"]["through_horizon"]["minimum_p5"], 25000.0)
        # Test C: 60D minimum P5 is 15000.0
        self.assertEqual(res["horizons"]["60"]["through_horizon"]["minimum_p5"], 15000.0)
        # Test D: 90D minimum P5 is 15000.0
        self.assertEqual(res["horizons"]["90"]["through_horizon"]["minimum_p5"], 15000.0)

    def test_mid_horizon_breach_recovery(self):
        # Test E / Mid-horizon breach followed by recovery
        # Day 1-30: Safe (danger threshold is 20000.0). p5 is 30000.
        # Day 40: Breach (p5 is 10000).
        # Day 60: Recovered (p5 is 35000).
        # Day 90: Recovered (p5 is 40000).
        band = []
        base_val = 50000.0
        for i in range(90):
            day_num = i + 1
            if day_num <= 30:
                p5 = 30000.0
            elif 35 <= day_num <= 50:
                p5 = 10000.0  # Breach!
            else:
                p5 = 35000.0  # Recovered!
            band.append({
                "date": f"2026-09-{day_num:02d}" if day_num <= 30 else f"2026-10-{day_num-30:02d}",
                "baseline": base_val,
                "p5": p5,
                "p50": base_val,
                "p95": base_val + 2000.0
            })
        
        res = self.classifier.classify(self.engine, band, days=90)
        # 30D should be SAFE
        self.assertEqual(res["horizons"]["30"]["classification"]["liquidity_status"], "SAFE")
        # 60D should be BREACH because the breach happened in day 35-50
        self.assertEqual(res["horizons"]["60"]["classification"]["liquidity_status"], "BREACH")
        # 90D should also be BREACH because the breach happened in day 35-50, even though day 90 itself is recovered (p5 = 35000)
        self.assertEqual(res["horizons"]["90"]["classification"]["liquidity_status"], "BREACH")
        
        # Verify first breach date is populated
        self.assertIsNotNone(res["horizons"]["90"]["through_horizon"]["first_breach_date"])
        self.assertEqual(res["horizons"]["90"]["through_horizon"]["days_to_first_breach"], 35)


if __name__ == "__main__":
    unittest.main()
