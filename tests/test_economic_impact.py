import unittest
import math
from backend.economic_impact_engine import EconomicImpactEngine


class TestEconomicImpactEngine(unittest.TestCase):

    def setUp(self):
        self.engine = EconomicImpactEngine(conversion_fee=0.005, slippage_rate=0.002)

    def test_inaction_cost_calculation(self):
        amount_base = 10000.0
        daily_vol = 0.008  # 0.8% daily volatility
        days_to_due = 25   # 25 days

        res = self.engine.calculate_impact(
            amount_base=amount_base,
            daily_volatility=daily_vol,
            days_to_due=days_to_due,
            action="CONVERT_AND_HOLD",
            priority="HIGH"
        )

        # Expected calculation:
        # z = 1.645
        # downside_pct = 1 - exp(-1.645 * 0.008 * sqrt(25))
        # = 1 - exp(-1.645 * 0.008 * 5) = 1 - exp(-0.0658) = 1 - 0.936318 = 0.06368 (6.37%)
        # expected_inaction_cost = 10000 * 0.06368 = 636.81 (rounded)
        expected_downside_pct = 1.0 - math.exp(-1.645 * daily_vol * math.sqrt(days_to_due))
        expected_cost = amount_base * expected_downside_pct

        self.assertAlmostEqual(res["expected_inaction_cost"], expected_cost, places=1)
        self.assertEqual(res["action_cost"], 70.0)  # 10000 * 0.007 = 70.0
        self.assertEqual(res["estimated_avoided_loss"], res["expected_inaction_cost"])
        self.assertEqual(res["estimated_net_benefit"], round(expected_cost - 70.0, 2))
        self.assertEqual(res["risk_reduction_percent"], 100.0)

    def test_requote_impact(self):
        # Receivables re-quoted do not have conversion action cost on our side
        res = self.engine.calculate_impact(
            amount_base=5000.0,
            daily_volatility=0.01,
            days_to_due=10,
            action="RE_QUOTE",
            priority="MEDIUM"
        )
        self.assertEqual(res["action_cost"], 0.0)
        self.assertEqual(res["estimated_avoided_loss"], res["expected_inaction_cost"])
        self.assertEqual(res["estimated_net_benefit"], res["expected_inaction_cost"])

    def test_monitor_impact(self):
        res = self.engine.calculate_impact(
            amount_base=8000.0,
            daily_volatility=0.005,
            days_to_due=90,
            action="MONITOR",
            priority="LOW"
        )
        self.assertEqual(res["action_cost"], 0.0)
        self.assertEqual(res["estimated_avoided_loss"], 0.0)
        self.assertEqual(res["estimated_net_benefit"], 0.0)


if __name__ == "__main__":
    unittest.main()
