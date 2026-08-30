"""
Integration tests for the FX-Aware Cash Flow Forecaster pipeline:
Layer 1 (CashFlowEngine) -> Layer 2 (RiskModelV2) -> Layer 2.5 (RiskClassifier) -> Layer 3 (DecisionEngine).
Can be run via: python -m unittest tests/test_integration_flow.py
"""

import json
import unittest
import numpy as np
from pathlib import Path

from backend.engines.cash_flow import CashFlowEngine
from backend.engines.risk_model import get_risk_band, DEFAULT_START_DATE
from backend.engines.risk_classifier import RiskClassifier
from backend.engines.decision_engine import DecisionEngine, ActionType, ActionPriority

class TestIntegrationFlow(unittest.TestCase):

    def setUp(self):
        # Resolve real file paths
        self.data_dir = Path(__file__).resolve().parent.parent / "data"
        self.mock_tx_path = self.data_dir / "mock_transactions.json"
        self.fx_cache_path = self.data_dir / "fx_historical_cache.json"
        
        # Initialize real engines with real data
        self.cf_engine = CashFlowEngine.from_file(self.mock_tx_path)
        self.classifier = RiskClassifier()
        self.decision_engine = DecisionEngine()

    def test_full_pipeline_real_dataset(self):
        # 1. Run Layer 2 Monte Carlo simulations (2000 runs) over 90 days
        risk_band = get_risk_band(
            engine=self.cf_engine,
            days=90,
            n_simulations=2000,
            seed=42,
            cache_path=self.fx_cache_path
        )
        
        # Verify simulated band output
        self.assertEqual(len(risk_band), 90)
        self.assertEqual(risk_band[0]["baseline"], 41500.0) # Matches first day of mock dataset
        
        # 2. Run Layer 2.5 Risk Classifier to evaluate severity
        classification = self.classifier.classify(self.cf_engine, risk_band, days=90)
        
        # Verify classification features
        self.assertEqual(classification["model_version"], "risk_classifier_v2")
        self.assertEqual(classification["overall_risk_level"], "HIGH")
        self.assertEqual(classification["overall_risk_score"], 100)
        self.assertEqual(classification["risk_trajectory"], "WORSENING")
        
        # 3. Run Layer 3 Decision Engine to generate recommendations
        decisions = self.decision_engine.generate_decisions(
            engine=self.cf_engine,
            classification_result=classification,
            anchor_date=DEFAULT_START_DATE
        )
        
        # Verify decision KPIs and recommendations list
        kpis = decisions["decision_kpis"]
        recs = decisions["recommendations"]
        
        self.assertEqual(decisions["model_version"], "decision_engine_v1")
        self.assertTrue(decisions["overall"]["requires_intervention"])
        
        # Look for expected recommendations matching default mock dataset:
        # txn_010: Frankfurt Data Center Hardware, EUR -28,000, unfunded. Expect Action: CONVERT_AND_HOLD.
        # txn_013: London Strategic Advisory, GBP 32,000, unpaid. Expect Action: RE_QUOTE.
        # Check that both recommended actions exist in sorted list:
        
        txn_010_rec = next((r for r in recs if r["transaction_id"] == "txn_010"), None)
        self.assertIsNotNone(txn_010_rec)
        self.assertEqual(txn_010_rec["action"], ActionType.CONVERT_AND_HOLD)
        self.assertEqual(txn_010_rec["priority"], ActionPriority.HIGH)
        self.assertEqual(txn_010_rec["recommended_amount"], 28000.0)
        self.assertTrue(txn_010_rec["requires_approval"])
        
        txn_013_rec = next((r for r in recs if r["transaction_id"] == "txn_013"), None)
        self.assertIsNotNone(txn_013_rec)
        self.assertEqual(txn_013_rec["action"], ActionType.RE_QUOTE)
        self.assertIsNone(txn_013_rec["recommended_amount"])
        self.assertEqual(txn_013_rec["priority"], ActionPriority.HIGH)
        
        # Verify sorted ranking: HIGH priority goes first
        self.assertEqual(recs[0]["priority"], ActionPriority.HIGH)
        
        # Verify JSON serializability of overall output
        raw_json = json.dumps(decisions)
        self.assertIsInstance(raw_json, str)


if __name__ == "__main__":
    unittest.main()
