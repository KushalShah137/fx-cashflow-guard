"""
================================================================================
PRE-DEMO HARDENING & RESILIENCE REGRESSION TEST SUITE
================================================================================
"""

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.wise_api import WiseSandboxClient, FALLBACK_INDICATIVE_RATES


class TestDemoHardening(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.client.post("/reset")

    def tearDown(self):
        self.client.post("/reset")

    def test_01_demo_script_check_returns_green(self):
        """Verifies /demo-script-check self-diagnostic passes with GREEN status."""
        res = self.client.get("/demo-script-check")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["all_systems_go"])
        self.assertEqual(data["status"], "GREEN")
        self.assertEqual(data["checks"]["sqlite_database"]["status"], "PASS")
        self.assertEqual(data["checks"]["fx_historical_cache"]["status"], "PASS")
        self.assertEqual(data["checks"]["wise_sandbox_resilience"]["status"], "PASS")
        self.assertEqual(data["checks"]["demo_transactions_initial_state"]["status"], "PASS")

    def test_02_dual_action_trigger_synchronization(self):
        """
        Verifies calling /apply-action on txn_010 updates in-memory engine,
        the forecast risk bands, and GET /actions in SQLite simultaneously.
        """
        # 1. Trigger decisions to ensure recommendations exist
        self.client.get("/decisions?days=90&simulations=100")

        # 2. Call /apply-action on txn_010
        act_res = self.client.post(
            "/apply-action",
            json={"transaction_id": "txn_010", "action": "convert_and_hold"}
        )
        self.assertEqual(act_res.status_code, 200)
        forecast_pts = act_res.json()
        self.assertEqual(len(forecast_pts), 90)

        # 3. Verify in-memory engine updated
        txs = self.client.get("/transactions").json().get("transactions", [])
        # In memory transactions
        demo_actions = self.client.get("/demo-actions").json()
        self.assertNotIn("txn_010", [a["transaction_id"] for a in demo_actions])

        # 4. Verify SQLite recommendations state updated to EXECUTED
        actions_res = self.client.get("/actions")
        self.assertEqual(actions_res.status_code, 200)
        actions_list = actions_res.json()
        t10_actions = [a for a in actions_list if a["transaction_id"] == "txn_010"]
        self.assertGreater(len(t10_actions), 0)
        self.assertEqual(t10_actions[0]["status"], "EXECUTED")

    def test_03_action_execution_via_state_machine_endpoint(self):
        """
        Verifies POST /actions/{id}/execute transitions state machine and updates in-memory engine.
        """
        # 1. Generate recommendations
        dec_res = self.client.get("/decisions?days=90&simulations=100")
        self.assertEqual(dec_res.status_code, 200)
        recs = dec_res.json()["recommendations"]
        self.assertGreater(len(recs), 0)

        target_rec = recs[0]
        action_id = target_rec["action_id"]
        tx_id = target_rec["transaction_id"]

        # 2. Execute via state machine
        exec_res = self.client.post(f"/actions/{action_id}/execute")
        self.assertEqual(exec_res.status_code, 200)
        self.assertEqual(exec_res.json()["status"], "EXECUTED")

        # 3. Confirm demo action consumed in engine
        demo_actions = self.client.get("/demo-actions").json()
        self.assertNotIn(tx_id, [a["transaction_id"] for a in demo_actions])

    def test_04_apply_action_idempotency_and_404(self):
        """Verifies rapid repeated calls and non-existent IDs behave safely."""
        # 1. Non-existent ID returns 404 cleanly
        res_404 = self.client.post(
            "/apply-action",
            json={"transaction_id": "txn_non_existent_999", "action": "convert_and_hold"}
        )
        self.assertEqual(res_404.status_code, 404)
        self.assertIn("not found", res_404.json()["detail"].lower())

        # 2. Repeated execution on txn_010 (idempotency)
        res1 = self.client.post(
            "/apply-action",
            json={"transaction_id": "txn_010", "action": "convert_and_hold"}
        )
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post(
            "/apply-action",
            json={"transaction_id": "txn_010", "action": "convert_and_hold"}
        )
        self.assertEqual(res2.status_code, 200)

    def test_05_frankfurter_offline_fallback(self):
        """Verifies offline network failure falls back to local cache safely."""
        with patch("requests.get", side_effect=ConnectionError("Offline demo mode")):
            # /forecast should succeed using cached data
            res_fc = self.client.get("/forecast?currency=USD&days=90")
            self.assertEqual(res_fc.status_code, 200)
            self.assertEqual(len(res_fc.json()), 90)

            # /risk-diagnostics should succeed from cache
            res_diag = self.client.get("/risk-diagnostics")
            self.assertEqual(res_diag.status_code, 200)
            self.assertEqual(res_diag.json()["model_version"], "v2")

    def test_06_wise_sandbox_resilience_401_and_timeout(self):
        """Verifies Wise client returns identical valid shape on 401 and timeout."""
        bad_client = WiseSandboxClient(api_key="bad_token", profile_id="12345", timeout=0.001)

        # 1. Simulate 401
        with patch("httpx.Client.post") as mock_post:
            mock_post.return_value.status_code = 401
            mock_post.return_value.text = "Unauthorized"
            q_401 = bad_client.create_quote("EUR", "USD", 10000.0)
            self.assertIn("quote_id", q_401)
            self.assertIn("rate", q_401)
            self.assertIn("fee", q_401)
            self.assertEqual(q_401["sourceCurrency"], "EUR")

        # 2. Simulate Timeout
        with patch("httpx.Client.post", side_effect=Exception("Timeout")):
            q_timeout = bad_client.create_quote("GBP", "USD", 5000.0)
            self.assertIn("quote_id", q_timeout)
            self.assertIn("rate", q_timeout)
            self.assertIn("fee", q_timeout)
            self.assertEqual(q_timeout["sourceCurrency"], "GBP")

    def test_07_full_rehearsal_sequence(self):
        """Runs the entire 8-step live demo sequence in order."""
        # Step 1: Clean Reset
        res_reset = self.client.post("/reset")
        self.assertEqual(res_reset.status_code, 200)

        # Step 2: Check Initial Forecast (Breach exists on worst-case)
        res_overview1 = self.client.get("/risk-overview?days=90")
        self.assertEqual(res_overview1.status_code, 200)
        data1 = res_overview1.json()
        self.assertIn(data1["risk_classification"]["overall_risk_level"], ["HIGH", "CRITICAL"])

        # Step 3: Apply Hedge on txn_010 (EUR Payable)
        res_act1 = self.client.post(
            "/apply-action",
            json={"transaction_id": "txn_010", "action": "convert_and_hold"}
        )
        self.assertEqual(res_act1.status_code, 200)

        # Step 4: Settle Early txn_013 (GBP Receivable)
        res_act2 = self.client.post(
            "/apply-action",
            json={"transaction_id": "txn_013", "action": "settle_now"}
        )
        self.assertEqual(res_act2.status_code, 200)

        # Step 5: Check Netting Opportunities
        res_net = self.client.get("/netting-opportunities")
        self.assertEqual(res_net.status_code, 200)

        # Step 6: Check Economic Impact
        res_eco = self.client.get("/economic-impact")
        self.assertEqual(res_eco.status_code, 200)

        # Step 7: Check Risk Diagnostics
        res_diag = self.client.get("/risk-diagnostics")
        self.assertEqual(res_diag.status_code, 200)

        # Step 8: Check Visual Terminal HTML
        res_viz = self.client.get("/viz/dashboard")
        self.assertEqual(res_viz.status_code, 200)


if __name__ == "__main__":
    unittest.main()
