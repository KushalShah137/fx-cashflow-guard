import unittest
from fastapi.testclient import TestClient
from backend.main import app, get_engine


class TestBackendHealthAndEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        # Ensure fresh state
        self.client.post("/reset")

    def tearDown(self):
        # Reset after tests
        self.client.post("/reset")

    def test_01_health(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    def test_02_transactions(self):
        res = self.client.get("/transactions")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("transactions", data)
        self.assertGreaterEqual(len(data["transactions"]), 18)
        self.assertIn("starting_balance", data)
        self.assertIn("danger_threshold", data)

    def test_03_forecast_deterministic(self):
        res = self.client.get("/forecast?currency=USD&days=90")
        self.assertEqual(res.status_code, 200)
        pts = res.json()
        self.assertIsInstance(pts, list)
        self.assertEqual(len(pts), 90)
        first_pt = pts[0]
        self.assertIn("date", first_pt)
        self.assertIn("balance", first_pt)
        self.assertIn("is_breach", first_pt)
        self.assertIn("transactions_today", first_pt)

    def test_04_currency_exposures(self):
        res = self.client.get("/exposures")
        self.assertEqual(res.status_code, 200)
        exposures = res.json()
        self.assertIsInstance(exposures, list)
        currencies = [e["currency"] for e in exposures]
        self.assertIn("EUR", currencies)
        self.assertIn("GBP", currencies)

    def test_05_demo_actions_list(self):
        res = self.client.get("/demo-actions")
        self.assertEqual(res.status_code, 200)
        actions = res.json()
        self.assertIsInstance(actions, list)
        action_ids = [a["transaction_id"] for a in actions]
        self.assertIn("txn_010", action_ids)
        self.assertIn("txn_013", action_ids)

    def test_06_apply_action_convert_and_hold(self):
        res = self.client.post(
            "/apply-action",
            json={"transaction_id": "txn_010", "action": "convert_and_hold"}
        )
        self.assertEqual(res.status_code, 200)
        forecast_pts = res.json()
        self.assertIsInstance(forecast_pts, list)
        self.assertEqual(len(forecast_pts), 90)

    def test_07_apply_action_settle_now(self):
        res = self.client.post(
            "/apply-action",
            json={"transaction_id": "txn_013", "action": "settle_now"}
        )
        self.assertEqual(res.status_code, 200)
        forecast_pts = res.json()
        self.assertIsInstance(forecast_pts, list)
        self.assertEqual(len(forecast_pts), 90)

    def test_08_apply_action_invalid_transaction(self):
        res = self.client.post(
            "/apply-action",
            json={"transaction_id": "invalid_tx_id", "action": "convert_and_hold"}
        )
        self.assertEqual(res.status_code, 400)

    def test_09_state_reset(self):
        # Apply an action
        self.client.post(
            "/apply-action",
            json={"transaction_id": "txn_010", "action": "convert_and_hold"}
        )
        # Check that demo action was consumed
        demo_actions_before = self.client.get("/demo-actions").json()
        self.assertNotIn("txn_010", [a["transaction_id"] for a in demo_actions_before])

        # Reset state
        reset_res = self.client.post("/reset")
        self.assertEqual(reset_res.status_code, 200)
        self.assertEqual(reset_res.json(), {"status": "reset_successful"})

        # Check that txn_010 is restored
        demo_actions_after = self.client.get("/demo-actions").json()
        self.assertIn("txn_010", [a["transaction_id"] for a in demo_actions_after])

    def test_10_risk_band_monte_carlo(self):
        res = self.client.get("/risk-band?days=90&simulations=100")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("risk_band", data)
        self.assertEqual(len(data["risk_band"]), 90)
        p = data["risk_band"][0]
        self.assertIn("baseline", p)
        self.assertIn("p5", p)
        self.assertIn("p50", p)
        self.assertIn("p95", p)

    def test_11_risk_diagnostics(self):
        res = self.client.get("/risk-diagnostics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("currencies_modeled", data)
        self.assertIn("correlation_matrix", data)

    def test_12_risk_classification(self):
        res = self.client.get("/risk-classification?days=90&simulations=100")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("overall_risk_level", data)
        self.assertIn("overall_risk_score", data)
        self.assertIn("horizons", data)

    def test_13_decisions(self):
        res = self.client.get("/decisions?days=90&simulations=100")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("overall", data)
        self.assertIn("decision_kpis", data)
        self.assertIn("recommendations", data)

    def test_14_risk_overview(self):
        res = self.client.get("/risk-overview?days=90&simulations=100")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("baseline_forecast", data)
        self.assertIn("risk_band", data)
        self.assertIn("risk_classification", data)
        self.assertIn("exposures", data)
        self.assertIn("decisions", data)


if __name__ == "__main__":
    unittest.main()