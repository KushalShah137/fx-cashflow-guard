"""
================================================================================
EXECUTION ENGINE V2 INTEGRATION TEST SUITE
================================================================================
Full API route integration testing for the V2 financial execution lifecycle:
/actions/{id}/quote -> /actions/{id}/confirm-quote -> /actions/{id}/execute
-> /executions/{id} -> /executions/{id}/impact -> /actions/{id}/lifecycle.
================================================================================
"""

import unittest
from fastapi.testclient import TestClient
from backend.main import app


class TestExecutionIntegration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.client.post("/reset")

    def tearDown(self):
        self.client.post("/reset")

    def test_01_full_api_execution_lifecycle_mock_dataset(self):
        """
        Executes full closed-loop cycle on real mock transaction dataset:
        1. Generate decisions
        2. Request quote for critical action (e.g. txn_010 EUR payable)
        3. Retrieve quote via GET
        4. Confirm quote
        5. Check allowed next actions
        6. Execute action with idempotency
        7. Retrieve execution details & timeline
        8. Retrieve before/after reforecast impact
        """
        # Step 1: Generate decisions
        dec_res = self.client.get("/decisions?days=90&simulations=200")
        self.assertEqual(dec_res.status_code, 200)
        decisions = dec_res.json()["recommendations"]
        self.assertGreater(len(decisions), 0)

        target_action = next(a for a in decisions if a["action"].upper() in ("CONVERT_AND_HOLD", "SETTLE_NOW"))
        action_id = target_action["action_id"]

        # Step 2: Request Quote
        quote_res = self.client.post(f"/actions/{action_id}/quote")
        self.assertEqual(quote_res.status_code, 200)
        qdata = quote_res.json()
        self.assertEqual(qdata["status"], "QUOTE_READY")
        self.assertGreater(qdata["rate"], 0.0)
        self.assertGreaterEqual(qdata["fee"], 0.0)
        quote_id = qdata["quote_id"]

        # Step 3: Retrieve Quote via GET
        get_quote_res = self.client.get(f"/actions/{action_id}/quote")
        self.assertEqual(get_quote_res.status_code, 200)
        self.assertEqual(get_quote_res.json()["quote_id"], quote_id)

        # Step 4: Check Lifecycle / Allowed Actions
        lc_res = self.client.get(f"/actions/{action_id}/lifecycle")
        self.assertEqual(lc_res.status_code, 200)
        self.assertIn("CONFIRM_QUOTE", lc_res.json()["allowed_next_actions"])

        # Step 5: Confirm Quote
        conf_res = self.client.post(
            f"/actions/{action_id}/confirm-quote",
            json={"quote_id": quote_id}
        )
        self.assertEqual(conf_res.status_code, 200)
        self.assertEqual(conf_res.json()["status"], "CONFIRMED")

        # Step 6: Execute Action
        exec_res = self.client.post(
            f"/actions/{action_id}/execute",
            json={"idempotency_key": f"test_e2e_{action_id}"}
        )
        self.assertEqual(exec_res.status_code, 200)
        exec_data = exec_res.json()
        self.assertEqual(exec_data["status"], "VERIFIED")
        execution_id = exec_data["execution_id"]

        # Step 7: Retrieve Execution Details
        detail_res = self.client.get(f"/executions/{execution_id}")
        self.assertEqual(detail_res.status_code, 200)
        details = detail_res.json()
        self.assertEqual(details["status"], "VERIFIED")
        self.assertIsNotNone(details["verification"])
        self.assertTrue(details["verification"]["verified"])
        self.assertGreaterEqual(len(details["timeline"]), 3)

        # Step 8: Retrieve Before/After Reforecast Impact
        impact_res = self.client.get(f"/executions/{execution_id}/impact")
        self.assertEqual(impact_res.status_code, 200)
        impact = impact_res.json()
        self.assertIn("before", impact)
        self.assertIn("after", impact)
        self.assertIn("impact", impact)
        self.assertIsNotNone(impact["impact"]["risk_score_change"])

    def test_02_quote_and_execute_single_call_fallback(self):
        """
        Verifies POST /actions/{id}/execute with no pre-existing quote seamlessly
        quotes, confirms, executes, and verifies in one call for backward-compatible triggers.
        """
        dec_res = self.client.get("/decisions?days=90&simulations=100")
        decisions = dec_res.json()["recommendations"]
        target_action = next(a for a in decisions if a["action"].upper() in ("CONVERT_AND_HOLD", "SETTLE_NOW"))
        action_id = target_action["action_id"]

        exec_res = self.client.post(f"/actions/{action_id}/execute")
        self.assertEqual(exec_res.status_code, 200)
        data = exec_res.json()
        self.assertEqual(data["status"], "VERIFIED")
        self.assertIsNotNone(data["quote"])
        self.assertIsNotNone(data["reforecast"])


if __name__ == "__main__":
    unittest.main()
