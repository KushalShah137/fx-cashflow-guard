import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.state_machine import validate_transition, LifecycleError, RecommendationState


class TestActionLifecycle(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        # Force db reload to get fresh clean state
        self.client.post("/reset")

    def tearDown(self):
        self.client.post("/reset")

    def test_01_transition_rules(self):
        # RECOMMENDED to APPROVED/REJECTED/EXPIRED: OK
        validate_transition("RECOMMENDED", "APPROVED")
        validate_transition("RECOMMENDED", "REJECTED")
        validate_transition("RECOMMENDED", "EXPIRED")

        # APPROVED to EXECUTING/REJECTED: OK
        validate_transition("APPROVED", "EXECUTING")
        validate_transition("APPROVED", "REJECTED")

        # EXECUTING to EXECUTED/FAILED: OK
        validate_transition("EXECUTING", "EXECUTED")
        validate_transition("EXECUTING", "FAILED")

        # Invalid transitions
        with self.assertRaises(LifecycleError):
            validate_transition("REJECTED", "APPROVED")
        with self.assertRaises(LifecycleError):
            validate_transition("EXECUTED", "REJECTED")
        with self.assertRaises(LifecycleError):
            validate_transition("FAILED", "EXECUTING")
        with self.assertRaises(LifecycleError):
            validate_transition("RECOMMENDED", "EXECUTED")

    def test_02_lifecycle_endpoints(self):
        # 1. Trigger decisions to populate database with recommendations
        dec_res = self.client.get("/decisions?days=90&simulations=100")
        self.assertEqual(dec_res.status_code, 200)
        dec_data = dec_res.json()
        recommendations = dec_data.get("recommendations", [])
        self.assertGreater(len(recommendations), 0)
        
        # Verify action_id is present
        first_rec = recommendations[0]
        self.assertIn("action_id", first_rec)
        action_id = first_rec["action_id"]

        # 2. Get all actions
        actions_res = self.client.get("/actions")
        self.assertEqual(actions_res.status_code, 200)
        actions_list = actions_res.json()
        self.assertGreater(len(actions_list), 0)
        
        # Ensure our action is in the list with RECOMMENDED status
        db_action = next((a for a in actions_list if a["action_id"] == action_id), None)
        self.assertIsNotNone(db_action)
        self.assertEqual(db_action["status"], "RECOMMENDED")
        self.assertEqual(db_action["transaction_id"], first_rec["transaction_id"])
        self.assertIn("risk_before", db_action)
        self.assertIn("risk_after_estimate", db_action)
        self.assertIn("estimated_action_cost", db_action)
        self.assertIn("estimated_inaction_cost", db_action)

        # 3. Get single action detail
        detail_res = self.client.get(f"/actions/{action_id}")
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json()["status"], "RECOMMENDED")

        # 4. Approve action
        appr_res = self.client.post(f"/actions/{action_id}/approve")
        self.assertEqual(appr_res.status_code, 200)
        self.assertEqual(appr_res.json()["status"], "APPROVED")

        # 5. Reject action (APPROVED -> REJECTED is allowed)
        rej_res = self.client.post(f"/actions/{action_id}/reject")
        self.assertEqual(rej_res.status_code, 200)
        self.assertEqual(rej_res.json()["status"], "REJECTED")

        # 6. Try to approve a rejected action (REJECTED -> APPROVED is NOT allowed)
        invalid_res = self.client.post(f"/actions/{action_id}/approve")
        self.assertEqual(invalid_res.status_code, 409)  # Conflict


if __name__ == "__main__":
    unittest.main()
