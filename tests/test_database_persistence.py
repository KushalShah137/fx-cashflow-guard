"""
================================================================================
UNIT TESTS: DATABASE PERSISTENCE & DUAL-MODE EXECUTION
================================================================================
"""
import os
from pathlib import Path

TEST_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "test_treasury.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

import unittest
import numpy as np
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.connection import SessionLocal, engine, Base
from backend.database.models import FxRate, TransactionModel, SimulationRun, AiExplanation
from backend.database.seeder import seed_fx_rates, seed_transactions
from backend.engines.risk_model import _load_from_json_legacy, load_aligned_returns_from_db

class TestDatabasePersistence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        session = SessionLocal()
        try:
            seed_fx_rates(session)
            seed_transactions(session)
        finally:
            session.close()
        cls.client = TestClient(app)

    def test_01_seeding_and_row_counts(self):
        session = SessionLocal()
        try:
            fx_count = session.query(FxRate).count()
            tx_count = session.query(TransactionModel).count()
            self.assertGreaterEqual(fx_count, 3000)
            self.assertGreaterEqual(tx_count, 20)
        finally:
            session.close()

    def test_02_seeding_idempotency(self):
        session = SessionLocal()
        try:
            fx_res = seed_fx_rates(session)
            tx_res = seed_transactions(session)
            self.assertEqual(fx_res["inserted"], 0)
            self.assertEqual(tx_res["inserted"], 0)
        finally:
            session.close()

    def test_03_db_and_json_numerical_equivalence(self):
        m_json, c_json = _load_from_json_legacy()
        m_db, c_db = load_aligned_returns_from_db()
        self.assertEqual(c_json, c_db)
        self.assertEqual(m_json.shape, m_db.shape)
        max_abs_diff = float(np.max(np.abs(m_json - m_db)))
        self.assertAlmostEqual(max_abs_diff, 0.0, places=10)

    def test_04_forecast_endpoint_persists_simulation_and_ai_explanation(self):
        response = self.client.get("/api/forecast?horizon=60")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("summary", data)
        self.assertIn("timeline", data)

        session = SessionLocal()
        try:
            latest_run = session.query(SimulationRun).order_by(SimulationRun.id.desc()).first()
            self.assertIsNotNone(latest_run)
            self.assertEqual(latest_run.horizon_days, 60)

            latest_exp = session.query(AiExplanation).filter(AiExplanation.simulation_run_id == latest_run.id).first()
            self.assertIsNotNone(latest_exp)
            self.assertIn("qwen", latest_exp.model_used.lower())
        finally:
            session.close()

    def test_05_simulation_history_endpoint(self):
        response = self.client.get("/api/simulations/history?limit=5")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("history", payload)
        self.assertIn("count", payload)
        self.assertGreater(payload["count"], 0)

    def test_06_non_blocking_db_failure_resilience(self):
        from unittest.mock import patch
        with patch("backend.main._persist_simulation_run_safe", side_effect=Exception("Simulated DB lock error")):
            resp = self.client.get("/api/forecast?horizon=30")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["horizon_days"], 30)

if __name__ == "__main__":
    unittest.main()
