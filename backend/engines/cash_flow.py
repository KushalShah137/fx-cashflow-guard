"""
================================================================================
CASH FLOW ENGINE
--------------------------------------------------------------------------------
Layer 1 of the FX-Aware Cash Flow Forecaster.

Responsibilities of this module (and ONLY this module):
    1. Load + validate a transaction ledger (from dict or JSON file).
    2. Normalize heterogeneous transaction schemas into a single internal
       Transaction model.
    3. Convert every transaction into the business's base currency using a
       supplied FX rate table (static rates — Monte Carlo/volatility is
       Layer 2's job, not this engine's).
    4. Project a day-by-day cumulative cash balance forward N days.
    5. Detect danger-threshold breaches (a business-defined liquidity floor).
    6. Report net FX exposure per currency (what Layer 2's risk band and
       Layer 3's Convert & Hold / Settle Now actions operate on).
    7. Serialize all of the above to plain dict/JSON so a FastAPI layer
       can return it with zero extra glue code.

Explicitly OUT of scope for this module (belongs to later layers):
    - Monte Carlo simulation / Value-at-Risk (Layer 2)
    - Wise sandbox calls / Convert & Hold / Settle Now execution (Layer 3)
    - HTTP concerns (FastAPI routing, request/response models)

Zero external dependencies beyond the Python standard library.
Python 3.10+ required (uses match-free but modern type hints).
================================================================================
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Optional, Union, Any
from pathlib import Path

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logger = logging.getLogger("cash_flow_engine")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


# --------------------------------------------------------------------------- #
# Exceptions — specific, catchable error types instead of bare ValueError
# --------------------------------------------------------------------------- #
class CashFlowEngineError(Exception):
    """Base exception for all engine errors."""


class InvalidTransactionError(CashFlowEngineError):
    """Raised when a transaction record is malformed or fails validation."""


class DuplicateTransactionIdError(CashFlowEngineError):
    """Raised when two transactions share the same id."""


class MissingFXRateError(CashFlowEngineError):
    """Raised when a transaction's currency has no rate in fx_config and
    strict_fx mode is enabled."""


class InvalidDateFormatError(CashFlowEngineError):
    """Raised when a date string cannot be parsed as YYYY-MM-DD."""


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class FlowDirection(str, Enum):
    PAYABLE = "payable"        # cash out
    RECEIVABLE = "receivable"  # cash in


class TransactionStatus(str, Enum):
    PENDING = "pending"
    SETTLED = "settled"
    CANCELLED = "cancelled"


# --------------------------------------------------------------------------- #
# Data models
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Transaction:
    """
    Canonical internal transaction representation.

    Every transaction that enters the engine — regardless of its original
    source schema (payroll, operating_expense, payable, receivable, ...) —
    is normalized into this shape. `direction` is derived from the sign of
    the original amount (negative = payable/cash-out, positive =
    receivable/cash-in) unless explicitly overridden by the source `type`
    field being "payable" or "receivable".
    """
    id: str
    date: date
    currency: str
    amount: float                    # always stored as a POSITIVE magnitude
    direction: FlowDirection
    description: str = ""
    category: str = "uncategorized"  # original source type: payroll, operating_expense, etc.
    status: TransactionStatus = TransactionStatus.PENDING
    demo_action: Optional[str] = None
    demo_action_label: Optional[str] = None

    @property
    def signed_amount(self) -> float:
        """Positive for receivables, negative for payables."""
        return self.amount if self.direction == FlowDirection.RECEIVABLE else -self.amount

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        d["direction"] = self.direction.value
        d["status"] = self.status.value
        return d


@dataclass
class DailyBalancePoint:
    """One point on the forecast timeline, in base-currency terms."""
    date: date
    balance: float
    is_breach: bool = False          # True if balance < danger_threshold
    transactions_today: list[str] = field(default_factory=list)  # transaction ids settling today

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "balance": round(self.balance, 2),
            "is_breach": self.is_breach,
            "transactions_today": self.transactions_today,
        }


@dataclass
class CurrencyExposure:
    """Net FX exposure for a single currency (excludes base currency)."""
    currency: str
    gross_payable: float
    gross_receivable: float
    net_exposure: float              # receivable - payable, in that currency
    net_exposure_base_ccy: float     # same, converted to base currency
    direction: FlowDirection         # PAYABLE if net_exposure < 0 else RECEIVABLE

    def to_dict(self) -> dict:
        d = asdict(self)
        d["direction"] = self.direction.value
        return d


# --------------------------------------------------------------------------- #
# The Engine
# --------------------------------------------------------------------------- #
class CashFlowEngine:
    """
    Loads a transaction ledger + FX config, and produces:
      - a day-by-day base-currency balance forecast
      - danger-threshold breach detection
      - per-currency net exposure (feeds the FX Risk Band / Monte Carlo layer)
      - demo-action lookups (feeds the Wise Convert&Hold / Settle Now layer)

    Usage:
        engine = CashFlowEngine.from_file("mock_transactions.json")
        forecast = engine.get_forecast(days=90)
        exposures = engine.get_currency_exposures()
        summary = engine.get_summary(days=90)
    """

    DATE_FMT = "%Y-%m-%d"

    def __init__(
        self,
        transactions: list[dict],
        starting_balance: float = 0.0,
        danger_threshold: Optional[float] = None,
        fx_config: Optional[dict] = None,
        strict_fx: bool = False,
    ):
        """
        Args:
            transactions: raw transaction dicts (any of the supported schemas,
                see _normalize_transaction for accepted shapes).
            starting_balance: cash balance in base currency as of "today".
            danger_threshold: liquidity floor in base currency; balances
                below this are flagged as breaches. None disables detection.
            fx_config: {
                "base_currency": "USD",
                "rates": {"USD": 1.0, "EUR": 1.08, "GBP": 1.28, ...},
                "daily_volatility": {...}   # ignored here, Layer 2 owns this
            }
            strict_fx: if True, a transaction in a currency missing from
                fx_config["rates"] raises MissingFXRateError. If False
                (default), it falls back to a 1:1 rate and logs a warning —
                safer default for a hackathon demo where you don't want a
                single bad row to crash the whole forecast.
        """
        self.fx_config = fx_config or {}
        self.base_currency: str = self.fx_config.get("base_currency", "USD")
        self.fx_rates: dict[str, float] = dict(self.fx_config.get("rates", {}))
        self.fx_rates.setdefault(self.base_currency, 1.0)
        self.strict_fx = strict_fx

        self.starting_balance = float(starting_balance)
        self.danger_threshold = float(danger_threshold) if danger_threshold is not None else None

        self.transactions: list[Transaction] = self._normalize_and_validate(transactions)
        logger.info(
            "CashFlowEngine initialized: %d transactions, base_currency=%s, "
            "starting_balance=%.2f, danger_threshold=%s",
            len(self.transactions), self.base_currency, self.starting_balance,
            self.danger_threshold,
        )

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def from_file(cls, path: Union[str, Path], strict_fx: bool = False) -> "CashFlowEngine":
        """
        Load an engine directly from a JSON file matching the project's
        mock_transactions.json schema:
            {
              "starting_balance": 50000.0,
              "danger_threshold": 20000.0,
              "fx_config": {...},
              "transactions": [...]
            }
        Also accepts a bare list of transactions (no wrapper object) for
        backwards compatibility with simpler mock files.
        """
        path = Path(path)
        raw_text = path.read_text(encoding="utf-8-sig")
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise CashFlowEngineError(f"Could not parse {path}: {e}") from e

        if isinstance(data, list):
            return cls(transactions=data, strict_fx=strict_fx)

        if not isinstance(data, dict):
            raise CashFlowEngineError(
                f"{path} must contain a JSON object or array, got {type(data).__name__}"
            )

        transactions_list = []
        try:
            from backend.database.legacy_sqlite import init_db, get_db_connection
            init_db()  # Ensures tables exist and are seeded
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transactions")
            db_rows = cursor.fetchall()
            conn.close()
            
            for r in db_rows:
                transactions_list.append({
                    "id": r["id"],
                    "date": r["date"],
                    "currency": r["currency"],
                    "amount": -r["amount"] if r["direction"] == "payable" else r["amount"],
                    "description": r["description"],
                    "type": r["category"],
                    "status": r["status"],
                    "demo_action": r["demo_action"],
                    "demo_action_label": r["demo_action_label"]
                })
        except Exception as e:
            logger.warning("Failed to load transactions from SQLite database (%s). Falling back to JSON.", e)
            transactions_list = data.get("transactions", [])

        return cls(
            transactions=transactions_list,
            starting_balance=data.get("starting_balance", 0.0),
            danger_threshold=data.get("danger_threshold"),
            fx_config=data.get("fx_config", {}),
            strict_fx=strict_fx,
        )

    # ------------------------------------------------------------------ #
    # Normalization & validation
    # ------------------------------------------------------------------ #
    def _parse_date(self, raw: str, context: str) -> date:
        if not isinstance(raw, str):
            raise InvalidDateFormatError(f"{context}: date must be a string, got {type(raw).__name__}")
        try:
            return datetime.strptime(raw, self.DATE_FMT).date()
        except ValueError as e:
            raise InvalidDateFormatError(
                f"{context}: '{raw}' is not a valid date in {self.DATE_FMT} format"
            ) from e

    def _resolve_direction(self, tx: dict) -> FlowDirection:
        """
        Direction resolution order:
          1. Explicit type == "payable" / "receivable" wins outright.
          2. Otherwise, derive from the sign of `amount`
             (negative -> payable, positive -> receivable, zero -> receivable
              by convention, logged as a warning).
        """
        raw_type = str(tx.get("type", "")).lower()
        if raw_type == FlowDirection.PAYABLE.value:
            return FlowDirection.PAYABLE
        if raw_type == FlowDirection.RECEIVABLE.value:
            return FlowDirection.RECEIVABLE

        amount = tx.get("amount", 0)
        if amount < 0:
            return FlowDirection.PAYABLE
        if amount == 0:
            logger.warning("Transaction %s has amount == 0; defaulting direction to RECEIVABLE", tx.get("id"))
        return FlowDirection.RECEIVABLE

    def _normalize_and_validate(self, raw_transactions: list[dict]) -> list[Transaction]:
        normalized: list[Transaction] = []
        seen_ids: set[str] = set()

        for idx, raw in enumerate(raw_transactions):
            context = f"transaction[{idx}] (id={raw.get('id', '<missing>')})"

            if "date" not in raw:
                raise InvalidTransactionError(f"{context}: missing required field 'date'")
            if "currency" not in raw:
                raise InvalidTransactionError(f"{context}: missing required field 'currency'")
            if "amount" not in raw:
                raise InvalidTransactionError(f"{context}: missing required field 'amount'")

            try:
                amount_value = float(raw["amount"])
            except (TypeError, ValueError) as e:
                raise InvalidTransactionError(f"{context}: 'amount' must be numeric, got {raw['amount']!r}") from e

            tx_id = str(raw.get("id") or f"auto_{idx:04d}")
            if tx_id in seen_ids:
                raise DuplicateTransactionIdError(f"Duplicate transaction id encountered: '{tx_id}'")
            seen_ids.add(tx_id)

            tx_date = self._parse_date(raw["date"], context)
            currency = str(raw["currency"]).upper().strip()
            if not currency:
                raise InvalidTransactionError(f"{context}: 'currency' cannot be empty")

            direction = self._resolve_direction(raw)

            status_raw = str(raw.get("status", "pending")).lower()
            try:
                status = TransactionStatus(status_raw)
            except ValueError:
                logger.warning("%s: unknown status '%s', defaulting to 'pending'", context, status_raw)
                status = TransactionStatus.PENDING

            self._ensure_fx_rate(currency, context)

            normalized.append(
                Transaction(
                    id=tx_id,
                    date=tx_date,
                    currency=currency,
                    amount=abs(amount_value),
                    direction=direction,
                    description=str(raw.get("description", "")),
                    category=str(raw.get("type", "uncategorized")),
                    status=status,
                    demo_action=raw.get("demo_action"),
                    demo_action_label=raw.get("demo_action_label"),
                )
            )

        return normalized

    def _ensure_fx_rate(self, currency: str, context: str) -> None:
        if currency in self.fx_rates:
            return
        if self.strict_fx:
            raise MissingFXRateError(
                f"{context}: no FX rate configured for currency '{currency}' "
                f"(strict_fx=True). Add it to fx_config['rates']."
            )
        logger.warning(
            "%s: no FX rate for currency '%s' — falling back to 1.0 "
            "(pass strict_fx=True to raise instead)",
            context, currency,
        )
        self.fx_rates[currency] = 1.0

    # ------------------------------------------------------------------ #
    # FX conversion
    # ------------------------------------------------------------------ #
    def convert_to_base(self, amount: float, currency: str) -> float:
        """
        Convert `amount` in `currency` into the base currency.

        Rate convention: fx_config["rates"][X] is the value of 1 unit of
        base currency expressed in X (e.g. base=USD, rates={"EUR": 1.08}
        means 1 USD = 1.08 EUR). To go from currency X back to base we
        DIVIDE by the rate.
        """
        currency = currency.upper().strip()
        rate = self.fx_rates.get(currency, 1.0)
        if rate == 0:
            logger.error("FX rate for %s is 0 — treating as 1.0 to avoid division by zero", currency)
            rate = 1.0
        return amount / rate

    # ------------------------------------------------------------------ #
    # Core forecasting
    # ------------------------------------------------------------------ #
    def get_forecast(
        self,
        days: int = 90,
        base_date: Optional[Union[str, date]] = None,
        only_settled: bool = False,
    ) -> list[DailyBalancePoint]:
        """
        Project the day-by-day cumulative balance, in base currency,
        starting from `starting_balance` on `base_date`.

        Args:
            days: forecast horizon length, must be >= 1.
            base_date: forecast start date (defaults to today).
            only_settled: if True, only include settled transactions.

        Returns:
            List of DailyBalancePoint in chronological order.
        """
        if days < 1:
            raise ValueError(f"days must be >= 1, got {days}")

        start = self._resolve_base_date(base_date)

        relevant = [
            tx for tx in self.transactions
            if tx.status != TransactionStatus.CANCELLED
            and (not only_settled or tx.status == TransactionStatus.SETTLED)
        ]
        relevant.sort(key=lambda t: t.date)

        points: list[DailyBalancePoint] = []
        running_balance = self.starting_balance
        tx_cursor = 0
        n = len(relevant)

        for i in range(days):
            current_day = start + timedelta(days=i)

            todays_ids: list[str] = []
            while tx_cursor < n and relevant[tx_cursor].date <= current_day:
                tx = relevant[tx_cursor]
                base_amount = self.convert_to_base(tx.signed_amount, tx.currency)
                running_balance += base_amount
                if tx.date == current_day:
                    todays_ids.append(tx.id)
                tx_cursor += 1

            is_breach = (
                self.danger_threshold is not None
                and running_balance < self.danger_threshold
            )

            points.append(
                DailyBalancePoint(
                    date=current_day,
                    balance=running_balance,
                    is_breach=is_breach,
                    transactions_today=todays_ids,
                )
            )

        return points

    def _resolve_base_date(self, base_date: Optional[Union[str, date]]) -> date:
        if base_date is None:
            if self.transactions:
                return min(tx.date for tx in self.transactions)
            return date.today()
        if isinstance(base_date, date):
            return base_date
        return self._parse_date(base_date, "base_date")

    # ------------------------------------------------------------------ #
    # Exposure analysis (feeds Layer 2 — FX Risk Band)
    # ------------------------------------------------------------------ #
    def get_currency_exposures(self, exclude_base: bool = True) -> list[CurrencyExposure]:
        """
        Net exposure per currency, both in native currency and converted to
        base currency. Excludes settled and cancelled transactions.
        """
        gross_payable: dict[str, float] = {}
        gross_receivable: dict[str, float] = {}

        for tx in self.transactions:
            if tx.status in (TransactionStatus.CANCELLED, TransactionStatus.SETTLED):
                continue
            if tx.direction == FlowDirection.PAYABLE:
                gross_payable[tx.currency] = gross_payable.get(tx.currency, 0.0) + tx.amount
            else:
                gross_receivable[tx.currency] = gross_receivable.get(tx.currency, 0.0) + tx.amount

        currencies = set(gross_payable) | set(gross_receivable)
        if exclude_base:
            currencies.discard(self.base_currency)

        exposures = []
        for currency in sorted(currencies):
            payable = gross_payable.get(currency, 0.0)
            receivable = gross_receivable.get(currency, 0.0)
            net = receivable - payable
            net_base = self.convert_to_base(net, currency)
            exposures.append(
                CurrencyExposure(
                    currency=currency,
                    gross_payable=payable,
                    gross_receivable=receivable,
                    net_exposure=net,
                    net_exposure_base_ccy=net_base,
                    direction=FlowDirection.RECEIVABLE if net >= 0 else FlowDirection.PAYABLE,
                )
            )
        return exposures

    # ------------------------------------------------------------------ #
    # Demo action lookups (feeds Layer 3 — Wise sandbox actions)
    # ------------------------------------------------------------------ #
    def get_demo_actions(self) -> list[dict]:
        """
        Returns pending transactions flagged with demo_action.
        """
        return [
            {
                "transaction_id": tx.id,
                "action": tx.demo_action,
                "label": tx.demo_action_label or tx.demo_action,
                "currency": tx.currency,
                "amount": tx.amount,
                "direction": tx.direction.value,
                "date": tx.date.isoformat(),
                "description": tx.description,
                "status": tx.status.value,
            }
            for tx in self.transactions
            if tx.demo_action and tx.status == TransactionStatus.PENDING
        ]

    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Lookup a single transaction by id."""
        return next((tx for tx in self.transactions if tx.id == transaction_id), None)

    def mark_settled(self, transaction_id: str) -> Transaction:
        """
        Mark a transaction as settled and return the updated record.
        """
        for i, tx in enumerate(self.transactions):
            if tx.id == transaction_id:
                updated = Transaction(
                    id=tx.id, date=tx.date, currency=tx.currency, amount=tx.amount,
                    direction=tx.direction, description=tx.description, category=tx.category,
                    status=TransactionStatus.SETTLED, demo_action=tx.demo_action,
                    demo_action_label=tx.demo_action_label,
                )
                self.transactions[i] = updated
                logger.info("Transaction %s marked as SETTLED", transaction_id)
                try:
                    from backend.database.legacy_sqlite import update_transaction_in_db
                    update_transaction_in_db(updated)
                except Exception as e:
                    logger.warning("Failed to persist transaction settlement to SQLite: %s", e)
                return updated
        raise InvalidTransactionError(f"No transaction found with id '{transaction_id}'")

    def apply_action(
        self,
        transaction_id: str,
        action: str,
        settle_date: Optional[Union[str, date]] = None,
    ) -> Transaction:
        """
        Apply a hedging/settlement action (e.g. 'convert_and_hold' or 'settle_now')
        to a pending transaction in memory, triggering Wise Sandbox quote first.
        """
        action_norm = action.lower().strip()
        tx = self.get_transaction_by_id(transaction_id)
        if not tx:
            raise InvalidTransactionError(f"No transaction found with id '{transaction_id}'")

        # Step: Call Wise Sandbox API (graceful fallback on any error/timeout/missing keys)
        try:
            from backend.integrations.wise import execute_wise_action
            wise_result = execute_wise_action(
                action=action_norm,
                currency=tx.currency,
                amount=tx.amount,
                base_currency=self.base_currency,
            )
            logger.info("Wise Sandbox result for %s (%s): %s", transaction_id, action_norm, wise_result.get("status"))
        except Exception as e:
            logger.warning("Wise Sandbox API call encountered an error: %s. Proceeding with local ledger update.", e)

        idx = next(i for i, t in enumerate(self.transactions) if t.id == transaction_id)
        target_date = self._resolve_base_date(settle_date) if settle_date else tx.date

        if action_norm == "convert_and_hold":
            base_amount = self.convert_to_base(tx.amount, tx.currency)
            updated = Transaction(
                id=tx.id,
                date=tx.date,
                currency=self.base_currency,
                amount=round(base_amount, 2),
                direction=tx.direction,
                description=f"{tx.description} (Hedged)",
                category=tx.category,
                status=TransactionStatus.PENDING,
                demo_action=None,
                demo_action_label=None,
            )
            self.transactions[idx] = updated
            logger.info("Transaction %s: applied 'convert_and_hold'", transaction_id)
            try:
                from backend.database.legacy_sqlite import update_transaction_in_db
                update_transaction_in_db(updated)
            except Exception as e:
                logger.warning("Failed to persist action update to SQLite: %s", e)
            return updated

        elif action_norm == "settle_now":
            base_amount = self.convert_to_base(tx.amount, tx.currency)
            updated = Transaction(
                id=tx.id,
                date=target_date,
                currency=self.base_currency,
                amount=round(base_amount, 2),
                direction=tx.direction,
                description=f"{tx.description} (Settled Early)",
                category=tx.category,
                status=TransactionStatus.SETTLED,
                demo_action=None,
                demo_action_label=None,
            )
            self.transactions[idx] = updated
            logger.info("Transaction %s: applied 'settle_now'", transaction_id)
            try:
                from backend.database.legacy_sqlite import update_transaction_in_db
                update_transaction_in_db(updated)
            except Exception as e:
                logger.warning("Failed to persist action update to SQLite: %s", e)
            return updated

        else:
            raise ValueError(f"Unknown action '{action}'. Supported: 'convert_and_hold', 'settle_now'")

    # ------------------------------------------------------------------ #
    # Threshold / breach reporting
    # ------------------------------------------------------------------ #
    def get_breach_dates(self, days: int = 90, base_date: Optional[Union[str, date]] = None) -> list[date]:
        """All dates within the forecast window where balance < danger_threshold."""
        if self.danger_threshold is None:
            return []
        forecast = self.get_forecast(days=days, base_date=base_date)
        return [p.date for p in forecast if p.is_breach]

    def get_first_breach(self, days: int = 90, base_date: Optional[Union[str, date]] = None) -> Optional[DailyBalancePoint]:
        """The earliest point at which the forecast dips below danger_threshold, or None."""
        if self.danger_threshold is None:
            return None
        forecast = self.get_forecast(days=days, base_date=base_date)
        for point in forecast:
            if point.is_breach:
                return point
        return None

    # ------------------------------------------------------------------ #
    # Summary / serialization
    # ------------------------------------------------------------------ #
    def get_summary(self, days: int = 90, base_date: Optional[Union[str, date]] = None) -> dict:
        """
        One-call summary combining forecast + exposures + breach info + demo actions.
        """
        forecast = self.get_forecast(days=days, base_date=base_date)
        exposures = self.get_currency_exposures()
        first_breach = self.get_first_breach(days=days, base_date=base_date)

        return {
            "base_currency": self.base_currency,
            "starting_balance": round(self.starting_balance, 2),
            "danger_threshold": self.danger_threshold,
            "forecast_days": days,
            "final_balance": round(forecast[-1].balance, 2) if forecast else self.starting_balance,
            "min_balance": round(min(p.balance for p in forecast), 2) if forecast else self.starting_balance,
            "max_balance": round(max(p.balance for p in forecast), 2) if forecast else self.starting_balance,
            "breach_count": sum(1 for p in forecast if p.is_breach),
            "first_breach_date": first_breach.date.isoformat() if first_breach else None,
            "daily_balances": [p.to_dict() for p in forecast],
            "currency_exposures": [e.to_dict() for e in exposures],
            "demo_actions": self.get_demo_actions(),
            "transaction_count": len(self.transactions),
        }

    def to_json(self, days: int = 90, base_date: Optional[Union[str, date]] = None, indent: int = 2) -> str:
        """Serialize get_summary() straight to a JSON string."""
        return json.dumps(self.get_summary(days=days, base_date=base_date), indent=indent)


# ============================================================================ #
# SMOKE TESTS
# ============================================================================ #
_SAMPLE_TRANSACTIONS = [
    {"id": "tx1", "date": "2024-09-05", "type": "payable", "amount": 3000, "currency": "EUR", "description": "Supplier A"},
    {"id": "tx2", "date": "2024-09-07", "type": "receivable", "amount": 5000, "currency": "USD", "description": "Client X"},
    {"id": "tx3", "date": "2024-09-10", "type": "payable", "amount": 2000, "currency": "GBP", "description": "Supplier B"},
]


def _run_smoke_tests() -> None:
    """Runs sanity checks when executed as a script."""
    print("=" * 70)
    print("CASH FLOW ENGINE — SMOKE TESTS")
    print("=" * 70)

    # Test 1: Basic construction + forecast
    engine = CashFlowEngine(
        transactions=_SAMPLE_TRANSACTIONS,
        starting_balance=10_000,
        danger_threshold=5_000,
        fx_config={"base_currency": "USD", "rates": {"USD": 1.0, "EUR": 1.08, "GBP": 1.28}},
    )
    forecast = engine.get_forecast(days=30, base_date="2024-09-01")
    assert forecast[0].date == date(2024, 9, 1)
    assert len(forecast) == 30
    print(f"[PASS] Basic forecast: {len(forecast)} days generated")

    # Test 2: Exposures
    exposures = engine.get_currency_exposures()
    ccy_set = {e.currency for e in exposures}
    assert ccy_set == {"EUR", "GBP"}, f"unexpected currencies: {ccy_set}"
    print(f"[PASS] Exposures computed for: {sorted(ccy_set)}")

    # Test 3: Duplicate id detection
    try:
        CashFlowEngine(transactions=[
            {"id": "dup", "date": "2024-01-01", "amount": 100, "currency": "USD"},
            {"id": "dup", "date": "2024-01-02", "amount": -50, "currency": "USD"},
        ])
        raise AssertionError("Expected DuplicateTransactionIdError")
    except DuplicateTransactionIdError:
        print("[PASS] Duplicate transaction id correctly rejected")

    # Test 4: Missing field
    try:
        CashFlowEngine(transactions=[{"id": "bad", "amount": 100, "currency": "USD"}])
        raise AssertionError("Expected InvalidTransactionError")
    except InvalidTransactionError:
        print("[PASS] Missing required field correctly rejected")

    # Test 5: Bad date format
    try:
        CashFlowEngine(transactions=[{"id": "bad2", "date": "05-09-2024", "amount": 100, "currency": "USD"}])
        raise AssertionError("Expected InvalidDateFormatError")
    except InvalidDateFormatError:
        print("[PASS] Malformed date string correctly rejected")

    # Test 6: Strict FX
    try:
        CashFlowEngine(
            transactions=[{"id": "fx1", "date": "2024-01-01", "amount": 100, "currency": "JPY"}],
            fx_config={"base_currency": "USD", "rates": {"USD": 1.0}},
            strict_fx=True,
        )
        raise AssertionError("Expected MissingFXRateError")
    except MissingFXRateError:
        print("[PASS] strict_fx correctly rejects unconfigured currency")

    # Test 7: Non-strict FX fallback
    lenient = CashFlowEngine(
        transactions=[{"id": "fx2", "date": "2024-01-01", "amount": 100, "currency": "JPY"}],
        fx_config={"base_currency": "USD", "rates": {"USD": 1.0}},
        strict_fx=False,
    )
    assert lenient.fx_rates["JPY"] == 1.0
    print("[PASS] non-strict FX falls back to 1.0 gracefully")

    # Test 8: Zero-days guard
    try:
        engine.get_forecast(days=0)
        raise AssertionError("Expected ValueError for days=0")
    except ValueError:
        print("[PASS] days=0 correctly rejected")

    # Test 9: Mark settled
    tx_before = engine.get_transaction_by_id("tx1")
    assert tx_before.status == TransactionStatus.PENDING
    engine.mark_settled("tx1")
    tx_after = engine.get_transaction_by_id("tx1")
    assert tx_after.status == TransactionStatus.SETTLED
    print("[PASS] mark_settled updates status correctly")

    # Test 10: Summary / JSON
    summary = engine.get_summary(days=10, base_date="2024-09-01")
    json.dumps(summary)
    assert "daily_balances" in summary and "currency_exposures" in summary
    print("[PASS] get_summary() produces JSON-serializable output")

    print("=" * 70)
    print("ALL CASH FLOW ENGINE SMOKE TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    _run_smoke_tests()
    mock_file = Path(__file__).resolve().parent.parent / "data" / "mock_transactions.json"
    if mock_file.exists():
        print(f"\n" + "=" * 70)
        print(f"RUNNING AGAINST REAL DATA FILE: {mock_file}")
        print("=" * 70)
        real_engine = CashFlowEngine.from_file(mock_file)
        res = real_engine.get_summary(days=90, base_date="2026-09-01")
        print(f"Base currency: {res['base_currency']}")
        print(f"Starting balance: ${res['starting_balance']:,.2f}")
        print(f"Danger threshold: ${res['danger_threshold']:,.2f}")
        print(f"Final balance (day 90): ${res['final_balance']:,.2f}")
        print(f"Min balance: ${res['min_balance']:,.2f}  |  Max balance: ${res['max_balance']:,.2f}")
        print(f"Breach count: {res['breach_count']}, first breach: {res['first_breach_date']}")

        print("\nAll Currency Exposures:")
        for exp in res["currency_exposures"]:
            print(f"  - {exp['currency']} exposure: net {exp['net_exposure']:,.2f} ({exp['direction'].upper()}), "
                  f"{exp['net_exposure_base_ccy']:,.2f} in base currency")

        print("\nAll Demo Actions:")
        for action in res["demo_actions"]:
            print(f"  - [{action['transaction_id']}] {action['label']} ({action['amount']:,.2f} {action['currency']}) "
                  f"action={action['action']}")

        print("\nFirst 10 Days of Forecast:")
        for point in res["daily_balances"][:10]:
            flag = "  <-- BREACH" if point["is_breach"] else ""
            tx_info = f" (txns: {', '.join(point['transactions_today'])})" if point["transactions_today"] else ""
            print(f"  {point['date']}: ${point['balance']:,.2f}{flag}{tx_info}")
        print("=" * 70)

