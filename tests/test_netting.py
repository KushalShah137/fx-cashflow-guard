import unittest
from datetime import date
from backend.netting_engine import NettingEngine


class MockTransaction:
    def __init__(self, id_val, date_val, currency, amount, direction, status="pending"):
        self.id = id_val
        self.date = date_val
        self.currency = currency
        self.amount = amount
        self.direction = direction
        self.status = status


class TestNettingEngine(unittest.TestCase):

    def setUp(self):
        self.engine = NettingEngine(default_fee_rate=0.005)
        self.fx_rates = {
            "EUR": 0.85,
            "GBP": 0.75,
            "USD": 1.0
        }

    def test_perfect_same_day_netting(self):
        # EUR Inflow +10,000 and EUR Outflow -10,000 on the same day
        txs = [
            MockTransaction("1", date(2026, 9, 10), "EUR", 10000.0, "receivable"),
            MockTransaction("2", date(2026, 9, 10), "EUR", 10000.0, "payable")
        ]
        res = self.engine.calculate_netting(txs, self.fx_rates, anchor_date=date(2026, 9, 1))
        
        eur = res["portfolio"]["EUR"]
        self.assertEqual(eur["gross_receivables"], 10000.0)
        self.assertEqual(eur["gross_payables"], 10000.0)
        self.assertEqual(eur["net_exposure"], 0.0)
        self.assertEqual(eur["unnecessary_conversion_amount"], 10000.0)
        self.assertEqual(eur["perfect_same_day_netting"], 10000.0)
        self.assertEqual(eur["estimated_fees_avoided"], 50.0)  # 10000 * 0.005
        self.assertEqual(eur["estimated_risk_reduction"], 20000.0)  # Gross 20000 - Net 0

    def test_partial_netting(self):
        # EUR Inflow +15,000 and EUR Outflow -10,000
        txs = [
            MockTransaction("1", date(2026, 9, 10), "EUR", 15000.0, "receivable"),
            MockTransaction("2", date(2026, 9, 10), "EUR", 10000.0, "payable")
        ]
        res = self.engine.calculate_netting(txs, self.fx_rates, anchor_date=date(2026, 9, 1))
        
        eur = res["portfolio"]["EUR"]
        self.assertEqual(eur["net_exposure"], 5000.0)
        self.assertEqual(eur["unnecessary_conversion_amount"], 10000.0)
        self.assertEqual(eur["perfect_same_day_netting"], 10000.0)
        self.assertEqual(eur["estimated_fees_avoided"], 50.0)
        self.assertEqual(eur["estimated_risk_reduction"], 20000.0)  # Gross 25000 - Net 5000

    def test_different_settlement_dates(self):
        # EUR Inflow on Sept 10 and EUR Outflow on Sept 15
        txs = [
            MockTransaction("1", date(2026, 9, 10), "EUR", 10000.0, "receivable"),
            MockTransaction("2", date(2026, 9, 15), "EUR", 10000.0, "payable")
        ]
        res = self.engine.calculate_netting(txs, self.fx_rates, anchor_date=date(2026, 9, 1))
        
        eur = res["portfolio"]["EUR"]
        # Portfolio aggregate netting still identifies the overlap
        self.assertEqual(eur["unnecessary_conversion_amount"], 10000.0)
        # But perfect same-day netting is 0
        self.assertEqual(eur["perfect_same_day_netting"], 0.0)

    def test_different_currencies_no_netting(self):
        # EUR Inflow +10,000 and GBP Outflow -10,000
        txs = [
            MockTransaction("1", date(2026, 9, 10), "EUR", 10000.0, "receivable"),
            MockTransaction("2", date(2026, 9, 10), "GBP", 10000.0, "payable")
        ]
        res = self.engine.calculate_netting(txs, self.fx_rates, anchor_date=date(2026, 9, 1))
        
        eur = res["portfolio"]["EUR"]
        gbp = res["portfolio"]["GBP"]
        self.assertEqual(eur["unnecessary_conversion_amount"], 0.0)
        self.assertEqual(gbp["unnecessary_conversion_amount"], 0.0)

    def test_no_netting_opportunity(self):
        # Only EUR Inflows
        txs = [
            MockTransaction("1", date(2026, 9, 10), "EUR", 10000.0, "receivable"),
            MockTransaction("2", date(2026, 9, 15), "EUR", 5000.0, "receivable")
        ]
        res = self.engine.calculate_netting(txs, self.fx_rates, anchor_date=date(2026, 9, 1))
        
        eur = res["portfolio"]["EUR"]
        self.assertEqual(eur["unnecessary_conversion_amount"], 0.0)


if __name__ == "__main__":
    unittest.main()
