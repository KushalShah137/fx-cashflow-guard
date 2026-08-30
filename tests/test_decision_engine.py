"""
Unit tests for FX Decision Engine (Layer 3).
Can be run via: python -m unittest tests/test_decision_engine.py
"""

import json
import unittest
from datetime import date

from backend.engines.cash_flow import CashFlowEngine, FlowDirection, TransactionStatus
from backend.engines.risk_classifier import RiskClassifier
from backend.engines.decision_engine import DecisionEngine, DecisionPolicy, ActionType, ActionPriority

class TestDecisionEngine(unittest.TestCase):

    def setUp(self):
        # Default policy and engines
        self.policy = DecisionPolicy(
            minimum_exposure_base=1000.0,
            high_priority_days=30,
            margin_threshold_pct=0.03,
            liquidity_buffer_warning=5000.0
        )
        self.engine = DecisionEngine(self.policy)

        # Baseline FX Config
        self.fx_config = {
            "base_currency": "USD",
            "rates": {"USD": 1.0, "EUR": 1.08, "GBP": 1.28},
            "daily_volatility": {"USD": 0.0, "EUR": 0.008, "GBP": 0.009}
        }

        # Mock Risk Classifier output
        self.classifier_output = {
            "overall_risk_level": "HIGH",
            "overall_risk_score": 85,
            "risk_trajectory": "WORSENING",
            "decision_context": {
                "currencies_at_risk": ["EUR", "GBP"],
                "exposure_direction": {"EUR": "PAYABLE", "GBP": "RECEIVABLE"}
            },
            "horizons": {
                "30": {
                    "classification": {"overall_risk_level": "HIGH", "risk_score": 85, "liquidity_status": "WATCH"},
                    "through_horizon": {"minimum_liquidity_buffer": 2000.0, "breach_count": 0}
                },
                "60": {
                    "classification": {"overall_risk_level": "HIGH", "risk_score": 85, "liquidity_status": "BREACH"},
                    "through_horizon": {"minimum_liquidity_buffer": -1000.0, "breach_count": 5}
                },
                "90": {
                    "classification": {"overall_risk_level": "HIGH", "risk_score": 85, "liquidity_status": "BREACH"},
                    "through_horizon": {"minimum_liquidity_buffer": -5000.0, "breach_count": 12}
                }
            }
        }

    def test_unfunded_payable(self):
        # Transaction is payable, EUR, unfunded (demo_action is not settle_now)
        cf_engine = CashFlowEngine(
            transactions=[{
                "id": "tx1", "date": "2026-09-10", "currency": "EUR", "amount": -10000.0,
                "description": "EUR Software License", "type": "payable", "status": "pending"
            }],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config=self.fx_config
        )
        res = self.engine.generate_decisions(cf_engine, self.classifier_output, anchor_date=date(2026, 9, 1))
        
        recs = res["recommendations"]
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["action"], ActionType.CONVERT_AND_HOLD)
        self.assertEqual(recs[0]["recommended_amount"], 10000.0)
        self.assertEqual(recs[0]["priority"], ActionPriority.HIGH)  # Due in 9 days (< 30)

    def test_funded_payable(self):
        # Transaction is payable, EUR, funded (demo_action = settle_now)
        cf_engine = CashFlowEngine(
            transactions=[{
                "id": "tx1", "date": "2026-09-15", "currency": "EUR", "amount": -10000.0,
                "description": "EUR Hardware", "type": "payable", "status": "pending",
                "demo_action": "settle_now"
            }],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config=self.fx_config
        )
        res = self.engine.generate_decisions(cf_engine, self.classifier_output, anchor_date=date(2026, 9, 1))
        
        recs = res["recommendations"]
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["action"], ActionType.SETTLE_NOW)
        self.assertEqual(recs[0]["recommended_amount"], 10000.0)

    def test_receivable_with_margin_risk(self):
        # GBP receivable due in 50 days (volatility 0.009 -> threatens > 3% margin)
        cf_engine = CashFlowEngine(
            transactions=[{
                "id": "tx1", "date": "2026-10-20", "currency": "GBP", "amount": 25000.0,
                "description": "UK Retainer", "type": "receivable", "status": "pending"
            }],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config=self.fx_config
        )
        res = self.engine.generate_decisions(cf_engine, self.classifier_output, anchor_date=date(2026, 9, 1))
        
        recs = res["recommendations"]
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["action"], ActionType.RE_QUOTE)
        self.assertIsNone(recs[0]["recommended_amount"])

    def test_receivable_without_margin_risk(self):
        # GBP receivable due in 1 day (volatility 0.009 -> downside is very small, < 3% margin threshold)
        cf_engine = CashFlowEngine(
            transactions=[{
                "id": "tx1", "date": "2026-09-02", "currency": "GBP", "amount": 10000.0,
                "description": "UK Retainer immediate", "type": "receivable", "status": "pending"
            }],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config=self.fx_config
        )
        res = self.engine.generate_decisions(cf_engine, self.classifier_output, anchor_date=date(2026, 9, 1))
        
        recs = res["recommendations"]
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["action"], ActionType.MONITOR)

    def test_base_currency_transaction(self):
        # USD transaction should not receive any recommendation
        cf_engine = CashFlowEngine(
            transactions=[{
                "id": "tx1", "date": "2026-09-10", "currency": "USD", "amount": -10000.0,
                "description": "USD Expense", "type": "payable", "status": "pending"
            }],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config=self.fx_config
        )
        res = self.engine.generate_decisions(cf_engine, self.classifier_output, anchor_date=date(2026, 9, 1))
        self.assertEqual(len(res["recommendations"]), 0)

    def test_settled_transaction(self):
        # Settled transaction should not receive any recommendation
        cf_engine = CashFlowEngine(
            transactions=[{
                "id": "tx1", "date": "2026-09-10", "currency": "EUR", "amount": -10000.0,
                "description": "EUR Software", "type": "payable", "status": "settled"
            }],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config=self.fx_config
        )
        res = self.engine.generate_decisions(cf_engine, self.classifier_output, anchor_date=date(2026, 9, 1))
        self.assertEqual(len(res["recommendations"]), 0)

    def test_cancelled_transaction(self):
        # Cancelled transaction should not receive any recommendation
        cf_engine = CashFlowEngine(
            transactions=[{
                "id": "tx1", "date": "2026-09-10", "currency": "EUR", "amount": -10000.0,
                "description": "EUR Software", "type": "payable", "status": "cancelled"
            }],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config=self.fx_config
        )
        res = self.engine.generate_decisions(cf_engine, self.classifier_output, anchor_date=date(2026, 9, 1))
        self.assertEqual(len(res["recommendations"]), 0)

    def test_multiple_exposures_sorting(self):
        # Add:
        # 1. EUR payable due in 10 days, amount 10000 (HIGH priority)
        # 2. EUR payable due in 45 days, amount 10000 (MEDIUM priority)
        # 3. GBP receivable due in 5 days, low risk (MONITOR -> LOW priority)
        cf_engine = CashFlowEngine(
            transactions=[
                {
                    "id": "tx1", "date": "2026-09-11", "currency": "EUR", "amount": -10000.0,
                    "description": "Payable A", "type": "payable", "status": "pending"
                },
                {
                    "id": "tx2", "date": "2026-10-16", "currency": "EUR", "amount": -10000.0,
                    "description": "Payable B", "type": "payable", "status": "pending"
                },
                {
                    "id": "tx3", "date": "2026-09-06", "currency": "GBP", "amount": 1000.0,
                    "description": "Receivable C", "type": "receivable", "status": "pending"
                }
            ],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config=self.fx_config
        )
        res = self.engine.generate_decisions(cf_engine, self.classifier_output, anchor_date=date(2026, 9, 1))
        
        recs = res["recommendations"]
        self.assertEqual(len(recs), 3)
        self.assertEqual(recs[0]["transaction_id"], "tx1") # HIGH priority
        self.assertEqual(recs[0]["priority"], ActionPriority.HIGH)
        self.assertEqual(recs[1]["transaction_id"], "tx2") # MEDIUM priority
        self.assertEqual(recs[1]["priority"], ActionPriority.MEDIUM)
        self.assertEqual(recs[2]["transaction_id"], "tx3") # LOW priority (MONITOR)
        self.assertEqual(recs[2]["priority"], ActionPriority.LOW)

    def test_no_action(self):
        # All transactions are below the materiality threshold of 1000 USD
        cf_engine = CashFlowEngine(
            transactions=[{
                "id": "tx1", "date": "2026-09-10", "currency": "EUR", "amount": -50.0,
                "description": "EUR tiny expense", "type": "payable", "status": "pending"
            }],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config=self.fx_config
        )
        res = self.engine.generate_decisions(cf_engine, self.classifier_output, anchor_date=date(2026, 9, 1))
        
        self.assertEqual(res["overall"]["requires_intervention"], False)
        self.assertEqual(res["decision_kpis"]["actions_required"], 0)
        self.assertEqual(res["recommendations"][0]["action"], ActionType.MONITOR)

    def test_decision_context(self):
        cf_engine = CashFlowEngine(
            transactions=[{
                "id": "tx1", "date": "2026-09-10", "currency": "EUR", "amount": -10000.0,
                "description": "EUR Software License", "type": "payable", "status": "pending"
            }],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config=self.fx_config
        )
        res = self.engine.generate_decisions(cf_engine, self.classifier_output, anchor_date=date(2026, 9, 1))
        
        self.assertIn("currencies_at_risk", res["decision_context"])
        self.assertEqual(res["decision_context"]["currencies_at_risk"], ["EUR", "GBP"])

    def test_json_serialization(self):
        cf_engine = CashFlowEngine(
            transactions=[{
                "id": "tx1", "date": "2026-09-10", "currency": "EUR", "amount": -10000.0,
                "description": "EUR Software License", "type": "payable", "status": "pending"
            }],
            starting_balance=50000,
            danger_threshold=20000,
            fx_config=self.fx_config
        )
        res = self.engine.generate_decisions(cf_engine, self.classifier_output, anchor_date=date(2026, 9, 1))
        
        raw_json = json.dumps(res)
        self.assertIsInstance(raw_json, str)


if __name__ == "__main__":
    unittest.main()
