"""
================================================================================
IDEMPOTENT DATABASE SEEDER (FX RATES & TRANSACTIONS)
================================================================================
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.database.connection import engine, SessionLocal, Base
from backend.database.models import FxRate, TransactionModel

logger = logging.getLogger("seed_fx_rates")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

FX_CACHE_PATH = Path(_project_root) / "data" / "fx_historical_cache.json"
MOCK_TX_PATH = Path(_project_root) / "data" / "mock_transactions.json"

def seed_fx_rates(db_session) -> Dict[str, int]:
    if not FX_CACHE_PATH.exists():
        logger.warning("FX cache file not found at %s. Skipping FX rate seeding.", FX_CACHE_PATH)
        return {"inserted": 0, "skipped": 0, "total": 0}

    with open(FX_CACHE_PATH, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    historical_rates = data.get("historical_rates", [])
    currencies = data.get("currencies", ["EUR", "GBP", "INR", "CNY", "JPY", "AUD"])

    existing_records = set(
        db_session.query(FxRate.currency_pair, FxRate.date).all()
    )

    inserted = 0
    skipped = 0
    to_insert: List[FxRate] = []

    for entry in historical_rates:
        raw_date_str = entry.get("date")
        if not raw_date_str:
            continue
        date_val = str(raw_date_str).strip()
        for ccy in currencies:
            if ccy in entry and isinstance(entry[ccy], (int, float)) and entry[ccy] > 0:
                pair = f"{ccy}/USD"
                key = (pair, date_val)
                if key in existing_records:
                    skipped += 1
                else:
                    to_insert.append(
                        FxRate(
                            currency_pair=pair,
                            currency=ccy.upper(),
                            date=date_val,
                            rate=float(entry[ccy]),
                            source="Frankfurter/ECB",
                        )
                    )
                    existing_records.add(key)
                    inserted += 1

    if to_insert:
        db_session.bulk_save_objects(to_insert)
        db_session.commit()

    logger.info("FX Rates Seeding: Inserted %d, Skipped %d existing (Total: %d)",
                inserted, skipped, inserted + skipped)
    return {"inserted": inserted, "skipped": skipped, "total": inserted + skipped}

def seed_transactions(db_session) -> Dict[str, int]:
    if not MOCK_TX_PATH.exists():
        logger.warning("Mock transactions file not found at %s. Skipping transaction seeding.", MOCK_TX_PATH)
        return {"inserted": 0, "skipped": 0, "total": 0}

    with open(MOCK_TX_PATH, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    tx_list = data.get("transactions", [])
    existing_ids = set(r[0] for r in db_session.query(TransactionModel.id).all())

    inserted = 0
    skipped = 0
    to_insert: List[TransactionModel] = []

    for tx in tx_list:
        tx_id = tx.get("id")
        if not tx_id:
            continue
        if tx_id in existing_ids:
            skipped += 1
            continue
        amt = float(tx.get("amount", 0.0))
        direction = tx.get("direction")
        if not direction:
            direction = "inflow" if amt >= 0 else "outflow"
        to_insert.append(
            TransactionModel(
                id=tx_id,
                date=tx.get("date", "2026-09-01"),
                currency=tx.get("currency", "USD").upper(),
                amount=amt,
                direction=direction,
                description=tx.get("description", ""),
                category=tx.get("category", tx.get("type", "uncategorized")),
                status=tx.get("status", "pending"),
                demo_action=tx.get("demo_action"),
                demo_action_label=tx.get("demo_action_label"),
            )
        )
        existing_ids.add(tx_id)
        inserted += 1

    if to_insert:
        db_session.bulk_save_objects(to_insert)
        db_session.commit()

    logger.info("Transactions Seeding: Inserted %d, Skipped %d existing (Total: %d)",
                inserted, skipped, inserted + skipped)
    return {"inserted": inserted, "skipped": skipped, "total": inserted + skipped}

def run_all_seeds():
    logger.info("Creating database tables via SQLAlchemy metadata...")
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if "fx_rates" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("fx_rates")]
        if "currency_pair" not in columns:
            logger.info("Upgrading legacy fx_rates table schema to include currency_pair...")
            Base.metadata.tables["fx_rates"].drop(engine, checkfirst=True)
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        fx_res = seed_fx_rates(session)
        tx_res = seed_transactions(session)
        print("\n" + "=" * 60)
        print("DATABASE SEEDING SUMMARY")
        print("=" * 60)
        print(f"FX Rates:     {fx_res['inserted']} inserted, {fx_res['skipped']} skipped (Total: {fx_res['total']})")
        print(f"Transactions: {tx_res['inserted']} inserted, {tx_res['skipped']} skipped (Total: {tx_res['total']})")
        print("=" * 60 + "\n")
    finally:
        session.close()

if __name__ == "__main__":
    run_all_seeds()
