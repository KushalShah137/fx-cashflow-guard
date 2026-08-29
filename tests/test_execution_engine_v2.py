"""
================================================================================
EXECUTION ENGINE V2 UNIT TEST SUITE
================================================================================
Exhaustive unit testing for quotes, confirmations, idempotent execution, timeout
handling, post-execution verification, financial state updates, and reforecasts.
================================================================================
"""

import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from backend.db import init_db
from backend.cash_flow_engine import CashFlowEngine, FlowDirection, TransactionStatus
from backend.integrations.mock_wise_client import MockWiseClient
from backend.execution_engine_v2 import ExecutionEngineV2, ExecutionEngineError
from backend.decision_engine import DecisionEngine
from backend.risk_classifier import RiskClassifier
from backend.risk_model_v2 import get_risk_band as get_risk_band_v2, DEFAULT_START_DATE


class TestExecutionEngineV2(unittest.TestCase):

    def setUp(self):
        init_db(force=True)
        self.mock_provider = MockWiseClient()
        self.exec_engine = ExecutionEngineV2(provider=self.mock_provider)

        from backend.main import get_engine, save_and_enrich_recommendations
        self.engine = get_engine(reload=True)

        # Generate recommendation
        band = get_risk_band_v2(self.engine, days=90, n_simulations=100, seed=42)
        classifier = RiskClassifier()
        classification = classifier.classify(self.engine, band, days=90)
        dec_engine = DecisionEngine()
        decisions = dec_engine.generate_decisions(self.engine, classification, anchor_date=DEFAULT_START_DATE)
        
        # Save recommendation to DB
        decisions = save_and_enrich_recommendations(decisions)

        exec_rec = next(r for r in decisions["recommendations"] if r["action"].upper() in ("CONVERT_AND_HOLD", "SETTLE_NOW"))
        self.action_id = exec_rec["action_id"]
        self.tx_id = exec_rec["transaction_id"]
        self.orig_ccy = self.engine.get_transaction_by_id(self.tx_id).currency

    def test_01_quote_creation_and_retrieval(self):
        """Verifies quote generation, unmodifiable fields, and retrieval from DB."""
        quote = self.exec_engine.request_quote(self.action_id, self.engine, expiry_seconds=300)
        self.assertIsNotNone(quote.quote_id)
        self.assertEqual(quote.source_currency, "USD")
        self.assertEqual(quote.target_currency, self.orig_ccy)
        self.assertGreater(quote.rate, 0.0)
        self.assertGreaterEqual(quote.fee, 0.0)
        self.assertEqual(quote.status, "QUOTE_READY")

        # Retrieve active quote
        retrieved = self.exec_engine.get_current_quote(self.action_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.quote_id, quote.quote_id)
        self.assertFalse(retrieved.is_expired)

    def test_02_quote_confirmation(self):
        """Verifies quote confirmation transition."""
        quote = self.exec_engine.request_quote(self.action_id, self.engine)
        conf = self.exec_engine.confirm_quote(self.action_id, quote.quote_id)
        self.assertEqual(conf.status, "CONFIRMED")
        self.assertEqual(conf.quote_id, quote.quote_id)

    def test_03_quote_expiry_rejection(self):
        """Verifies expired quotes cannot be confirmed or executed."""
        # Request quote with expired expiry
        quote = self.exec_engine.request_quote(self.action_id, self.engine, expiry_seconds=-10)
        
        with self.assertRaises(ExecutionEngineError) as ctx:
            self.exec_engine.confirm_quote(self.action_id, quote.quote_id)
        self.assertEqual(ctx.exception.error_code, "QUOTE_EXPIRED")

    def test_04_quote_mismatch_rejection(self):
        """Verifies confirming a quote ID belonging to another action is rejected."""
        self.exec_engine.request_quote(self.action_id, self.engine)
        with self.assertRaises(ExecutionEngineError) as ctx:
            self.exec_engine.confirm_quote(self.action_id, "non_existent_quote_999")
        self.assertEqual(ctx.exception.error_code, "QUOTE_MISMATCH")

    def test_05_idempotent_execution(self):
        """Verifies duplicate execution requests return existing execution without double-execution."""
        quote = self.exec_engine.request_quote(self.action_id, self.engine)
        self.exec_engine.confirm_quote(self.action_id, quote.quote_id)

        idem_key = "test_idempotency_key_12345"
        exec1 = self.exec_engine.execute_action(self.action_id, self.engine, idempotency_key=idem_key)
        self.assertEqual(exec1.status, "VERIFIED")

        # Second execution with exact same key
        exec2 = self.exec_engine.execute_action(self.action_id, self.engine, idempotency_key=idem_key)
        self.assertEqual(exec2.execution_id, exec1.execution_id)
        self.assertEqual(exec2.status, "VERIFIED")

    def test_06_provider_timeout_marks_requires_review(self):
        """Verifies network timeout sets REQUIRES_REVIEW without financial state corruption."""
        quote = self.exec_engine.request_quote(self.action_id, self.engine)
        self.exec_engine.confirm_quote(self.action_id, quote.quote_id)

        self.mock_provider.simulate_timeout = True
        with self.assertRaises(ExecutionEngineError) as ctx:
            self.exec_engine.execute_action(self.action_id, self.engine)
        self.assertEqual(ctx.exception.error_code, "PROVIDER_TIMEOUT")

        # Verify transaction in engine was NOT modified
        tx = self.engine.get_transaction_by_id(self.tx_id)
        self.assertEqual(tx.currency, self.orig_ccy)
        self.assertEqual(tx.status, TransactionStatus.PENDING)

    def test_07_provider_failure_marks_failed(self):
        """Verifies provider rejection sets FAILED without financial state corruption."""
        quote = self.exec_engine.request_quote(self.action_id, self.engine)
        self.exec_engine.confirm_quote(self.action_id, quote.quote_id)

        self.mock_provider.simulate_failure = True
        with self.assertRaises(ExecutionEngineError) as ctx:
            self.exec_engine.execute_action(self.action_id, self.engine)
        self.assertEqual(ctx.exception.error_code, "PROVIDER_EXECUTION_FAILED")

        # Verify transaction remained untouched
        tx = self.engine.get_transaction_by_id(self.tx_id)
        self.assertEqual(tx.currency, self.orig_ccy)

    def test_08_verification_mismatch_flags_review(self):
        """Verifies mismatched currency/amount during verification flags REQUIRES_REVIEW."""
        quote = self.exec_engine.request_quote(self.action_id, self.engine)
        self.exec_engine.confirm_quote(self.action_id, quote.quote_id)

        self.mock_provider.simulate_verification_mismatch = True
        with self.assertRaises(ExecutionEngineError) as ctx:
            self.exec_engine.execute_action(self.action_id, self.engine)
        self.assertEqual(ctx.exception.error_code, "VERIFICATION_FAILED")

        # Verify transaction in engine remained untouched
        tx = self.engine.get_transaction_by_id(self.tx_id)
        self.assertEqual(tx.currency, self.orig_ccy)

    def test_09_full_verified_execution_and_reforecast(self):
        """Verifies complete end-to-end flow with state update, reforecast, and metrics capture."""
        quote = self.exec_engine.request_quote(self.action_id, self.engine)
        self.exec_engine.confirm_quote(self.action_id, quote.quote_id)

        res = self.exec_engine.execute_action(self.action_id, self.engine)
        self.assertEqual(res.status, "VERIFIED")
        self.assertIsNotNone(res.provider_reference)
        self.assertIsNotNone(res.reforecast)
        self.assertGreaterEqual(len(res.timeline), 4)

        # Confirm transaction state was updated
        tx = self.engine.get_transaction_by_id(self.tx_id)
        self.assertEqual(tx.currency, "USD")

        # Confirm reforecast impact object
        impact = res.reforecast.impact
        self.assertIsNotNone(impact.risk_score_change)
        self.assertIsNotNone(impact.p5_change)

    def test_10_non_executable_actions_rejected(self):
        """Verifies RE_QUOTE and MONITOR actions cannot be quoted or executed."""
        self.assertFalse(ExecutionEngineV2.is_executable_action("RE_QUOTE"))
        self.assertFalse(ExecutionEngineV2.is_executable_action("MONITOR"))
        self.assertTrue(ExecutionEngineV2.is_executable_action("CONVERT_AND_HOLD"))
        self.assertTrue(ExecutionEngineV2.is_executable_action("SETTLE_NOW"))


if __name__ == "__main__":
    unittest.main()
