"""
================================================================================
SQLITE PERSISTENCE LAYER & DATABASE INITIALIZER
--------------------------------------------------------------------------------
Provides database connection management, schema initialization, and data seeding
from mock JSON files on first boot.
================================================================================
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("db")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "treasury.db"
MOCK_TX_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_transactions.json"
FX_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "fx_historical_cache.json"


def get_db_connection() -> sqlite3.Connection:
    """Returns a connection to the SQLite database with Row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(force: bool = False) -> None:
    """
    Initializes the database schema. If the database file is missing or force=True,
    creates the schema and seeds default data.
    """
    if DB_PATH.exists() and not force:
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Initializing SQLite database at %s", DB_PATH)

    conn = get_db_connection()
    try:
        with conn:
            # 1. Transactions Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    amount REAL NOT NULL,
                    direction TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    category TEXT DEFAULT 'uncategorized',
                    status TEXT NOT NULL,
                    demo_action TEXT,
                    demo_action_label TEXT
                );
            """)

            # 2. FX Rates Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fx_rates (
                    date TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    rate REAL NOT NULL,
                    PRIMARY KEY (date, currency)
                );
            """)

            # 3. Risk Snapshots Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS risk_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    horizon_days INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    point_in_time_json TEXT NOT NULL,
                    through_horizon_json TEXT NOT NULL,
                    classification_json TEXT NOT NULL,
                    explanation TEXT NOT NULL
                );
            """)

            # 4. Recommendations Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    action_id TEXT PRIMARY KEY,
                    transaction_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    confidence INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    reason_codes_json TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,
                    amount_base REAL NOT NULL,
                    recommended_amount REAL,
                    risk_before TEXT DEFAULT 'LOW',
                    risk_after_estimate TEXT DEFAULT 'LOW',
                    estimated_action_cost REAL DEFAULT 0.0,
                    estimated_inaction_cost REAL DEFAULT 0.0,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE CASCADE
                );
            """)

            # 5. Approvals Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    action_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (action_id) REFERENCES recommendations (action_id) ON DELETE CASCADE
                );
            """)

            # 6. Executions Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    action_id TEXT NOT NULL,
                    quote_id TEXT,
                    rate REAL,
                    fee REAL,
                    source_amount REAL,
                    target_amount REAL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (action_id) REFERENCES recommendations (action_id) ON DELETE CASCADE
                );
            """)

            # 7. Audit Logs Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    action_id TEXT,
                    transaction_id TEXT,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    old_state TEXT,
                    new_state TEXT,
                    metadata_json TEXT
                );
            """)

            # 8. V2 Quotes Table (Additive)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quotes_v2 (
                    quote_id TEXT PRIMARY KEY,
                    action_id TEXT NOT NULL,
                    transaction_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    source_currency TEXT NOT NULL,
                    target_currency TEXT NOT NULL,
                    source_amount REAL NOT NULL,
                    target_amount REAL NOT NULL,
                    rate REAL NOT NULL,
                    fee REAL NOT NULL,
                    delivery_estimate TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    raw_json TEXT
                );
            """)

            # 9. V2 Executions Table (Additive)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions_v2 (
                    execution_id TEXT PRIMARY KEY,
                    action_id TEXT NOT NULL,
                    transaction_id TEXT NOT NULL,
                    quote_id TEXT,
                    idempotency_key TEXT UNIQUE,
                    provider TEXT NOT NULL,
                    provider_reference TEXT,
                    status TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    approved_at TEXT,
                    quoted_at TEXT,
                    confirmed_at TEXT,
                    executing_at TEXT,
                    executed_at TEXT,
                    verified_at TEXT,
                    failure_reason TEXT,
                    verification_json TEXT,
                    metadata_json TEXT
                );
            """)

            # 10. V2 Reforecast Snapshots Table (Additive)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reforecast_snapshots_v2 (
                    reforecast_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    before_json TEXT NOT NULL,
                    after_json TEXT NOT NULL,
                    impact_json TEXT NOT NULL
                );
            """)

        # Seed data
        seed_db(conn)

    finally:
        conn.close()


def seed_db(conn: sqlite3.Connection) -> None:
    """Seeds default mock transactions and FX rates from JSON caches."""
    logger.info("Seeding database tables...")

    with conn:
        # Seed Transactions
        if MOCK_TX_PATH.exists():
            with open(MOCK_TX_PATH, "r", encoding="utf-8") as f:
                tx_data = json.load(f)
                transactions = tx_data.get("transactions", [])
                for tx in transactions:
                    # Resolve amount sign
                    amt = float(tx.get("amount", 0.0))
                    direction = tx.get("type", "payable")
                    if direction in ("payable", "operating_expense", "payroll") or amt < 0:
                        dir_val = "payable"
                    else:
                        dir_val = "receivable"

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO transactions 
                        (id, date, currency, amount, direction, description, category, status, demo_action, demo_action_label)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            tx["id"],
                            tx["date"],
                            tx["currency"],
                            abs(amt),
                            dir_val,
                            tx.get("description", ""),
                            tx.get("type", "uncategorized"),
                            tx.get("status", "pending"),
                            tx.get("demo_action"),
                            tx.get("demo_action_label")
                        )
                    )

        # Seed FX Rates Cache
        if FX_CACHE_PATH.exists():
            with open(FX_CACHE_PATH, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                rates_list = cache_data.get("historical_rates", [])
                currencies = cache_data.get("currencies", ["EUR", "GBP", "INR", "CNY", "JPY", "AUD"])
                for row in rates_list:
                    dt = row["date"]
                    for ccy in currencies:
                        if ccy in row:
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO fx_rates (date, currency, rate)
                                VALUES (?, ?, ?)
                                """,
                                (dt, ccy, float(row[ccy]))
                            )

        # Write initial audit log
        conn.execute(
            """
            INSERT INTO audit_logs (event_type, timestamp, actor, metadata_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                "DATABASE_INITIALIZED",
                datetime.utcnow().isoformat() + "Z",
                "system",
                json.dumps({"description": "Database tables created and seeded successfully."})
            )
        )
        logger.info("Database seeding complete.")


def update_transaction_in_db(tx) -> None:
    """Updates a transaction's fields in the transactions table."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE transactions 
                SET date = ?, currency = ?, amount = ?, direction = ?, description = ?, 
                    category = ?, status = ?, demo_action = ?, demo_action_label = ?
                WHERE id = ?
                """,
                (
                    tx.date.isoformat() if hasattr(tx.date, "isoformat") else str(tx.date),
                    tx.currency,
                    tx.amount,
                    tx.direction.value if hasattr(tx.direction, "value") else str(tx.direction),
                    tx.description,
                    tx.category,
                    tx.status.value if hasattr(tx.status, "value") else str(tx.status),
                    tx.demo_action,
                    tx.demo_action_label,
                    tx.id
                )
            )
    finally:
        conn.close()

