"""
================================================================================
EXECUTION ENGINE V2 — COMPLETE FINANCIAL LIFECYCLE ORCHESTRATOR
================================================================================
Authoritative orchestration layer for the complete closed-loop treasury cycle:
Decision -> Approval -> Quote -> Confirmation -> Execution -> Verification ->
Financial State Update -> Reforecast -> Risk Reclassification -> Audit Trail.
================================================================================
"""

import json
import uuid
import logging
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional, Tuple

from backend.db import get_db_connection, update_transaction_in_db
from backend.cash_flow_engine import CashFlowEngine, TransactionStatus, FlowDirection, Transaction
from backend.risk_model_v2 import get_risk_band as get_risk_band_v2, DEFAULT_START_DATE
from backend.risk_classifier import RiskClassifier
from backend.integrations.provider_interface import (
    ProviderExecutionProtocol,
    ProviderQuote,
    ProviderExecutionResult,
    ProviderStatusResult,
    ProviderTimeoutError,
    ProviderError,
)
from backend.integrations.provider_factory import get_execution_provider
from backend.execution_models import (
    ExecutionStateV2,
    QuoteResponse,
    QuoteConfirmationResponse,
    ExecutionDetailResponse,
    ExecutionTimelineEvent,
    VerificationResult,
    RiskSnapshotMetrics,
    ReforecastImpact,
    ExecutionImpactResponse,
    AllowedNextActionsResponse,
)

logger = logging.getLogger("execution_engine_v2")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

EXECUTABLE_ACTIONS = {"CONVERT_AND_HOLD", "SETTLE_NOW"}


class ExecutionEngineError(Exception):
    def __init__(self, message: str, error_code: str = "EXECUTION_ERROR", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class ExecutionEngineV2:
    """Authoritative financial transaction execution orchestrator."""

    def __init__(self, provider: Optional[ProviderExecutionProtocol] = None):
        self.provider = provider or get_execution_provider()

    @staticmethod
    def is_executable_action(action: str) -> bool:
        return action.upper().strip() in EXECUTABLE_ACTIONS

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _log_audit_event(
        action_id: Optional[str],
        transaction_id: Optional[str],
        event_type: str,
        actor: str,
        old_state: Optional[str] = None,
        new_state: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        conn = get_db_connection()
        now_str = datetime.now(timezone.utc).isoformat()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO audit_logs (event_type, action_id, transaction_id, timestamp, actor, old_state, new_state, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_type,
                        action_id,
                        transaction_id,
                        now_str,
                        actor,
                        old_state,
                        new_state,
                        json.dumps(metadata or {}),
                    )
                )
        except Exception as e:
            logger.warning("Failed to write audit log: %s", e)
        finally:
            conn.close()

    # --------------------------------------------------------------------------- #
    # 1. Quote Request & Retrieval Lifecycle
    # --------------------------------------------------------------------------- #
    def request_quote(
        self,
        action_id: str,
        engine: CashFlowEngine,
        expiry_seconds: int = 600,
        actor: str = "user",
    ) -> QuoteResponse:
        """
        Generates and persists an unmodifiable currency quote for an approved action.
        """
        conn = get_db_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM recommendations WHERE action_id = ?", (action_id,))
                rec = cur.fetchone()
                if not rec:
                    raise ExecutionEngineError(f"Recommendation '{action_id}' not found.", error_code="ACTION_NOT_FOUND", status_code=404)

                action_type = rec["action_type"].upper().strip()
                if not self.is_executable_action(action_type):
                    raise ExecutionEngineError(
                        f"Action '{action_type}' is an advisory action and cannot be quoted for money movement.",
                        error_code="NON_EXECUTABLE_ACTION",
                        status_code=400,
                    )

                tx_id = rec["transaction_id"]
                tx = engine.get_transaction_by_id(tx_id)
                if not tx or tx.status != TransactionStatus.PENDING:
                    raise ExecutionEngineError(
                        f"Transaction '{tx_id}' is not in a pending state for execution.",
                        error_code="TRANSACTION_NOT_PENDING",
                        status_code=409,
                    )

                # Determine source and target currencies
                # For a foreign payable (e.g. EUR 28k), business acquires EUR using base USD
                if action_type == "CONVERT_AND_HOLD":
                    source_ccy = engine.base_currency
                    target_ccy = tx.currency
                    source_amount = engine.convert_to_base(tx.amount, tx.currency)
                else:  # SETTLE_NOW
                    source_ccy = tx.currency
                    target_ccy = engine.base_currency
                    source_amount = tx.amount

                # Call Provider
                try:
                    pquote = self.provider.create_quote(
                        source_currency=source_ccy,
                        target_currency=target_ccy,
                        source_amount=source_amount,
                        expiry_seconds=expiry_seconds,
                    )
                except Exception as e:
                    self._log_audit_event(action_id, tx_id, "QUOTE_REQUEST_FAILED", actor=actor, metadata={"error": str(e)})
                    raise ExecutionEngineError(f"Provider failed to generate quote: {e}", error_code="PROVIDER_QUOTE_FAILED", status_code=502)

                # Persist quote into quotes_v2
                now_str = self._now_iso()
                conn.execute(
                    """
                    INSERT INTO quotes_v2
                    (quote_id, action_id, transaction_id, provider, source_currency, target_currency, 
                     source_amount, target_amount, rate, fee, delivery_estimate, status, created_at, expires_at, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'QUOTE_READY', ?, ?, ?)
                    """,
                    (
                        pquote.quote_id,
                        action_id,
                        tx_id,
                        pquote.provider,
                        pquote.source_currency,
                        pquote.target_currency,
                        pquote.source_amount,
                        pquote.target_amount,
                        pquote.rate,
                        pquote.fee,
                        pquote.delivery_estimate,
                        pquote.created_at,
                        pquote.expires_at,
                        json.dumps(pquote.raw_payload),
                    )
                )

                # Update recommendation state to QUOTE_READY
                old_status = rec["status"]
                conn.execute(
                    "UPDATE recommendations SET status = 'QUOTE_READY', updated_at = ? WHERE action_id = ?",
                    (now_str, action_id)
                )

                self._log_audit_event(
                    action_id=action_id,
                    transaction_id=tx_id,
                    event_type="QUOTE_RECEIVED",
                    actor=self.provider.provider_name,
                    old_state=old_status,
                    new_state="QUOTE_READY",
                    metadata={
                        "quote_id": pquote.quote_id,
                        "rate": pquote.rate,
                        "fee": pquote.fee,
                        "expires_at": pquote.expires_at,
                    }
                )

                return QuoteResponse(
                    quote_id=pquote.quote_id,
                    action_id=action_id,
                    transaction_id=tx_id,
                    source_currency=pquote.source_currency,
                    target_currency=pquote.target_currency,
                    source_amount=pquote.source_amount,
                    target_amount=pquote.target_amount,
                    rate=pquote.rate,
                    fee=pquote.fee,
                    delivery_estimate=pquote.delivery_estimate,
                    provider=pquote.provider,
                    status="QUOTE_READY",
                    created_at=pquote.created_at,
                    expires_at=pquote.expires_at,
                    is_expired=False,
                    raw_payload=pquote.raw_payload,
                )
        finally:
            conn.close()

    def get_current_quote(self, action_id: str) -> Optional[QuoteResponse]:
        """Retrieves the active quote for an action, validating expiration timestamp."""
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM quotes_v2 WHERE action_id = ? ORDER BY created_at DESC LIMIT 1",
                (action_id,)
            )
            row = cur.fetchone()
            if not row:
                return None

            now = datetime.now(timezone.utc)
            expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
            is_expired = now > expires_at

            status = "QUOTE_EXPIRED" if is_expired else row["status"]

            return QuoteResponse(
                quote_id=row["quote_id"],
                action_id=row["action_id"],
                transaction_id=row["transaction_id"],
                source_currency=row["source_currency"],
                target_currency=row["target_currency"],
                source_amount=row["source_amount"],
                target_amount=row["target_amount"],
                rate=row["rate"],
                fee=row["fee"],
                delivery_estimate=row["delivery_estimate"] or "Standard settlement",
                provider=row["provider"],
                status=status,
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                is_expired=is_expired,
                raw_payload=json.loads(row["raw_json"] or "{}"),
            )
        finally:
            conn.close()

    # --------------------------------------------------------------------------- #
    # 2. Quote Confirmation Step
    # --------------------------------------------------------------------------- #
    def confirm_quote(
        self,
        action_id: str,
        quote_id: str,
        actor: str = "user",
    ) -> QuoteConfirmationResponse:
        """
        User confirms exact unmodifiable quote before financial execution.
        """
        conn = get_db_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM quotes_v2 WHERE quote_id = ? AND action_id = ?", (quote_id, action_id))
                q_row = cur.fetchone()
                if not q_row:
                    raise ExecutionEngineError("Specified quote does not match action.", error_code="QUOTE_MISMATCH", status_code=404)

                now = datetime.now(timezone.utc)
                expires_at = datetime.fromisoformat(q_row["expires_at"].replace("Z", "+00:00"))
                if now > expires_at:
                    raise ExecutionEngineError("Quote has expired. A fresh quote must be requested.", error_code="QUOTE_EXPIRED", status_code=409)

                cur.execute("SELECT status FROM recommendations WHERE action_id = ?", (action_id,))
                rec = cur.fetchone()
                old_status = rec["status"] if rec else "UNKNOWN"

                now_str = now.isoformat()
                conn.execute(
                    "UPDATE recommendations SET status = 'CONFIRMED', updated_at = ? WHERE action_id = ?",
                    (now_str, action_id)
                )
                conn.execute(
                    "UPDATE quotes_v2 SET status = 'CONFIRMED' WHERE quote_id = ?",
                    (quote_id,)
                )

                self._log_audit_event(
                    action_id=action_id,
                    transaction_id=q_row["transaction_id"],
                    event_type="QUOTE_CONFIRMED",
                    actor=actor,
                    old_state=old_status,
                    new_state="CONFIRMED",
                    metadata={"quote_id": quote_id, "confirmed_at": now_str}
                )

                return QuoteConfirmationResponse(
                    action_id=action_id,
                    transaction_id=q_row["transaction_id"],
                    quote_id=quote_id,
                    status="CONFIRMED",
                    confirmed_at=now_str,
                    message="Quote successfully confirmed. Ready for financial execution.",
                )
        finally:
            conn.close()

    # --------------------------------------------------------------------------- #
    # 3. Execution, Post-Verification & Reforecast Orchestration
    # --------------------------------------------------------------------------- #
    def execute_action(
        self,
        action_id: str,
        engine: CashFlowEngine,
        idempotency_key: Optional[str] = None,
        actor: str = "user",
    ) -> ExecutionDetailResponse:
        """
        Authoritative money-movement execution flow with post-verification and reforecast.
        """
        conn = get_db_connection()
        now_dt = datetime.now(timezone.utc)
        now_str = now_dt.isoformat()

        # Step A: Validate Action and Active Quote
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM recommendations WHERE action_id = ?", (action_id,))
            rec = cur.fetchone()
            if not rec:
                raise ExecutionEngineError(f"Action '{action_id}' not found.", error_code="ACTION_NOT_FOUND", status_code=404)

            action_type = rec["action_type"].upper().strip()
            if not self.is_executable_action(action_type):
                raise ExecutionEngineError(f"Action '{action_type}' is non-executable.", error_code="NON_EXECUTABLE_ACTION", status_code=400)

            tx_id = rec["transaction_id"]
            tx = engine.get_transaction_by_id(tx_id)
            if not tx or tx.status != TransactionStatus.PENDING:
                raise ExecutionEngineError(f"Transaction '{tx_id}' is not pending.", error_code="TRANSACTION_NOT_PENDING", status_code=409)

            # Retrieve active confirmed quote
            cur.execute(
                "SELECT * FROM quotes_v2 WHERE action_id = ? ORDER BY created_at DESC LIMIT 1",
                (action_id,)
            )
            q_row = cur.fetchone()
            if not q_row:
                raise ExecutionEngineError("No quote found. Request a quote first.", error_code="QUOTE_REQUIRED", status_code=400)

            expires_at = datetime.fromisoformat(q_row["expires_at"].replace("Z", "+00:00"))
            if now_dt > expires_at:
                raise ExecutionEngineError("Quote has expired. Request a fresh quote.", error_code="QUOTE_EXPIRED", status_code=409)

            quote_id = q_row["quote_id"]
            idem_key = idempotency_key or f"idem_{action_id}_{quote_id}"

            # Step B: Idempotency Check in Database
            cur.execute("SELECT * FROM executions_v2 WHERE idempotency_key = ?", (idem_key,))
            existing_exec = cur.fetchone()
            if existing_exec:
                logger.info("Duplicate execution detected for idempotency key %s. Returning existing execution state.", idem_key)
                return self.get_execution_details(existing_exec["execution_id"], engine)

            # Generate new execution record
            execution_id = f"exec_{uuid.uuid4().hex[:12]}"

            # Capture Before-Execution Snapshot
            before_metrics = self._capture_risk_snapshot(engine)

            # Persist execution start in DB
            with conn:
                conn.execute(
                    """
                    INSERT INTO executions_v2
                    (execution_id, action_id, transaction_id, quote_id, idempotency_key, provider, 
                     status, requested_at, approved_at, quoted_at, confirmed_at, executing_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'EXECUTING', ?, ?, ?, ?, ?)
                    """,
                    (
                        execution_id,
                        action_id,
                        tx_id,
                        quote_id,
                        idem_key,
                        self.provider.provider_name,
                        now_str,
                        rec["created_at"],
                        q_row["created_at"],
                        now_str,
                        now_str,
                    )
                )
                conn.execute(
                    "UPDATE recommendations SET status = 'EXECUTING', updated_at = ? WHERE action_id = ?",
                    (now_str, action_id)
                )

            self._log_audit_event(action_id, tx_id, "EXECUTION_STARTED", actor=actor, old_state="CONFIRMED", new_state="EXECUTING", metadata={"execution_id": execution_id, "quote_id": quote_id})

            # Step C: Execute with Provider
            pquote = ProviderQuote(
                quote_id=q_row["quote_id"],
                source_currency=q_row["source_currency"],
                target_currency=q_row["target_currency"],
                source_amount=q_row["source_amount"],
                target_amount=q_row["target_amount"],
                rate=q_row["rate"],
                fee=q_row["fee"],
                delivery_estimate=q_row["delivery_estimate"] or "",
                provider=q_row["provider"],
                created_at=q_row["created_at"],
                expires_at=q_row["expires_at"],
                raw_payload=json.loads(q_row["raw_json"] or "{}"),
            )

            try:
                exec_result = self.provider.execute_quote(
                    quote=pquote,
                    idempotency_key=idem_key,
                    action_type=action_type,
                    metadata={"execution_id": execution_id, "action_id": action_id, "tx_id": tx_id},
                )
            except ProviderTimeoutError as timeout_err:
                logger.warning("Provider timeout during execution: %s", timeout_err)
                with conn:
                    conn.execute(
                        "UPDATE executions_v2 SET status = 'REQUIRES_REVIEW', failure_reason = ? WHERE execution_id = ?",
                        (str(timeout_err), execution_id)
                    )
                    conn.execute("UPDATE recommendations SET status = 'REQUIRES_REVIEW' WHERE action_id = ?", (action_id,))
                self._log_audit_event(action_id, tx_id, "EXECUTION_TIMEOUT_REVIEW_REQUIRED", actor=self.provider.provider_name, new_state="REQUIRES_REVIEW", metadata={"error": str(timeout_err)})
                raise ExecutionEngineError("Provider execution timed out. Flagged as REQUIRES_REVIEW.", error_code="PROVIDER_TIMEOUT", status_code=504)
            except Exception as exec_err:
                logger.error("Provider execution failed: %s", exec_err)
                with conn:
                    conn.execute(
                        "UPDATE executions_v2 SET status = 'FAILED', failure_reason = ? WHERE execution_id = ?",
                        (str(exec_err), execution_id)
                    )
                    conn.execute("UPDATE recommendations SET status = 'FAILED' WHERE action_id = ?", (action_id,))
                self._log_audit_event(action_id, tx_id, "EXECUTION_FAILED", actor=self.provider.provider_name, new_state="FAILED", metadata={"error": str(exec_err)})
                raise ExecutionEngineError(f"Provider execution failed: {exec_err}", error_code="PROVIDER_EXECUTION_FAILED", status_code=502)

            # Step D: Verification Step
            verification = self._verify_execution_result(exec_result, pquote, tx_id)
            if not verification.verified:
                with conn:
                    conn.execute(
                        """
                        UPDATE executions_v2
                        SET status = 'REQUIRES_REVIEW', provider_reference = ?, executed_at = ?, failure_reason = ?, verification_json = ?
                        WHERE execution_id = ?
                        """,
                        (exec_result.provider_reference, exec_result.executed_at, "; ".join(verification.discrepancies), json.dumps(verification.model_dump()), execution_id)
                    )
                    conn.execute("UPDATE recommendations SET status = 'REQUIRES_REVIEW' WHERE action_id = ?", (action_id,))
                self._log_audit_event(action_id, tx_id, "VERIFICATION_FAILED_REVIEW_REQUIRED", actor="SYSTEM", new_state="REQUIRES_REVIEW", metadata={"discrepancies": verification.discrepancies})
                raise ExecutionEngineError("Post-execution verification failed. Status is REQUIRES_REVIEW.", error_code="VERIFICATION_FAILED", status_code=422)

            # Step E: Update Financial State (ONLY AFTER VERIFIED)
            verified_at_str = self._now_iso()
            with conn:
                conn.execute(
                    """
                    UPDATE executions_v2
                    SET status = 'VERIFIED', provider_reference = ?, executed_at = ?, verified_at = ?, verification_json = ?
                    WHERE execution_id = ?
                    """,
                    (exec_result.provider_reference, exec_result.executed_at, verified_at_str, json.dumps(verification.model_dump()), execution_id)
                )
                conn.execute(
                    "UPDATE recommendations SET status = 'EXECUTED', updated_at = ? WHERE action_id = ?",
                    (verified_at_str, action_id)
                )

            # Apply mutation in memory and persist in SQLite transactions table
            engine.apply_action(transaction_id=tx_id, action=action_type.lower(), settle_date=DEFAULT_START_DATE)

            self._log_audit_event(
                action_id=action_id,
                transaction_id=tx_id,
                event_type="FINANCIAL_STATE_UPDATED",
                actor="SYSTEM",
                old_state="EXECUTING",
                new_state="VERIFIED",
                metadata={"provider_reference": exec_result.provider_reference, "action_type": action_type}
            )

            # Step F: Post-Action Reforecast & Reclassification
            impact_res = None
            try:
                after_metrics = self._capture_risk_snapshot(engine)
                impact_res = self._compute_reforecast_impact(
                    execution_id=execution_id,
                    action_id=action_id,
                    before=before_metrics,
                    after=after_metrics,
                )
                with conn:
                    conn.execute(
                        """
                        INSERT INTO reforecast_snapshots_v2
                        (reforecast_id, execution_id, action_id, created_at, before_json, after_json, impact_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            impact_res.reforecast_id,
                            execution_id,
                            action_id,
                            verified_at_str,
                            json.dumps(impact_res.before.model_dump()),
                            json.dumps(impact_res.after.model_dump()),
                            json.dumps(impact_res.impact.model_dump()),
                        )
                    )
                self._log_audit_event(action_id, tx_id, "REFORECAST_COMPLETED", actor="SYSTEM", metadata={"impact": impact_res.impact.model_dump()})
            except Exception as ref_err:
                logger.error("Reforecast failed after verified execution: %s", ref_err)
                self._log_audit_event(action_id, tx_id, "REFORECAST_FAILED", actor="SYSTEM", metadata={"error": str(ref_err)})

            return self.get_execution_details(execution_id, engine)

        finally:
            conn.close()

    # --------------------------------------------------------------------------- #
    # 4. Helpers: Verification, Snapshot & Details
    # --------------------------------------------------------------------------- #
    def _verify_execution_result(
        self,
        exec_res: ProviderExecutionResult,
        quote: ProviderQuote,
        tx_id: str,
    ) -> VerificationResult:
        discrepancies = []
        checks = {
            "has_provider_reference": bool(exec_res.provider_reference),
            "status_success": exec_res.status == "SUCCESS",
            "matching_quote_id": exec_res.quote_id == quote.quote_id,
            "matching_source_currency": exec_res.source_currency == quote.source_currency,
            "matching_target_currency": exec_res.target_currency == quote.target_currency,
            "matching_source_amount": abs(exec_res.source_amount - quote.source_amount) < 0.01,
        }

        for check_name, passed in checks.items():
            if not passed:
                discrepancies.append(f"Verification check '{check_name}' failed.")

        verified = len(discrepancies) == 0
        return VerificationResult(
            verified=verified,
            status="VERIFIED" if verified else "REQUIRES_REVIEW",
            provider_reference=exec_res.provider_reference,
            verified_at=self._now_iso(),
            checks_passed=checks,
            discrepancies=discrepancies,
        )

    def _capture_risk_snapshot(self, engine: CashFlowEngine) -> RiskSnapshotMetrics:
        """Captures mathematical risk metrics using RiskModelV2 and RiskClassifier."""
        band = get_risk_band_v2(engine=engine, days=90, n_simulations=500, seed=42)
        classifier = RiskClassifier()
        classification = classifier.classify(engine, band, days=90)

        min_p5 = min(p["p5"] for p in band) if band else engine.starting_balance
        threshold = engine.danger_threshold or 20000.0
        status = "BREACH" if min_p5 < threshold else "SAFE"

        return RiskSnapshotMetrics(
            risk_level=classification.get("overall_risk_level", "MEDIUM"),
            risk_score=classification.get("overall_risk_score", 50),
            p5=round(min_p5, 2),
            liquidity_status=status,
            trajectory=classification.get("trajectory", "STABLE"),
        )

    def _compute_reforecast_impact(
        self,
        execution_id: str,
        action_id: str,
        before: RiskSnapshotMetrics,
        after: RiskSnapshotMetrics,
    ) -> ExecutionImpactResponse:
        score_change = before.risk_score - after.risk_score
        p5_change = round(after.p5 - before.p5, 2)
        mitigated = (before.liquidity_status == "BREACH" and after.liquidity_status == "SAFE")

        desc = f"Risk score improved by {score_change} pts (P5 floor increased by ${p5_change:+,.2f})."
        if mitigated:
            desc += " Projected cash floor breach successfully mitigated."

        return ExecutionImpactResponse(
            reforecast_id=f"rf_{uuid.uuid4().hex[:12]}",
            execution_id=execution_id,
            action_id=action_id,
            completed_at=self._now_iso(),
            before=before,
            after=after,
            impact=ReforecastImpact(
                risk_score_change=score_change,
                p5_change=p5_change,
                liquidity_status_before=before.liquidity_status,
                liquidity_status_after=after.liquidity_status,
                is_breach_mitigated=mitigated,
                risk_reduction_description=desc,
            ),
        )

    def get_execution_details(self, execution_id: str, engine: Optional[CashFlowEngine] = None) -> ExecutionDetailResponse:
        """Retrieves full execution details with timeline, quote, verification, and reforecast impact."""
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM executions_v2 WHERE execution_id = ?", (execution_id,))
            ex = cur.fetchone()
            if not ex:
                raise ExecutionEngineError(f"Execution '{execution_id}' not found.", error_code="EXECUTION_NOT_FOUND", status_code=404)

            action_id = ex["action_id"]

            # Quote
            quote_resp = self.get_current_quote(action_id)

            # Verification
            ver_obj = None
            if ex["verification_json"]:
                vdata = json.loads(ex["verification_json"])
                ver_obj = VerificationResult(**vdata)

            # Reforecast Impact
            cur.execute("SELECT * FROM reforecast_snapshots_v2 WHERE execution_id = ?", (execution_id,))
            rf_row = cur.fetchone()
            impact_resp = None
            if rf_row:
                impact_resp = ExecutionImpactResponse(
                    reforecast_id=rf_row["reforecast_id"],
                    execution_id=execution_id,
                    action_id=action_id,
                    completed_at=rf_row["created_at"],
                    before=RiskSnapshotMetrics(**json.loads(rf_row["before_json"])),
                    after=RiskSnapshotMetrics(**json.loads(rf_row["after_json"])),
                    impact=ReforecastImpact(**json.loads(rf_row["impact_json"])),
                )

            # Timeline from audit logs
            cur.execute(
                "SELECT * FROM audit_logs WHERE action_id = ? ORDER BY timestamp ASC",
                (action_id,)
            )
            audit_rows = cur.fetchall()
            timeline = [
                ExecutionTimelineEvent(
                    event=r["event_type"],
                    timestamp=r["timestamp"],
                    actor=r["actor"],
                    from_state=r["old_state"],
                    to_state=r["new_state"],
                    metadata=json.loads(r["metadata_json"] or "{}"),
                )
                for r in audit_rows
            ]

            # Allowed Next Actions
            status = ex["status"]
            allowed = self.get_allowed_next_actions(status)

            return ExecutionDetailResponse(
                execution_id=ex["execution_id"],
                action_id=action_id,
                transaction_id=ex["transaction_id"],
                provider=ex["provider"],
                provider_reference=ex["provider_reference"],
                quote_id=ex["quote_id"],
                idempotency_key=ex["idempotency_key"],
                status=status,
                requested_at=ex["requested_at"],
                approved_at=ex["approved_at"],
                quoted_at=ex["quoted_at"],
                confirmed_at=ex["confirmed_at"],
                executing_at=ex["executing_at"],
                executed_at=ex["executed_at"],
                verified_at=ex["verified_at"],
                failure_reason=ex["failure_reason"],
                quote=quote_resp,
                verification=ver_obj,
                reforecast=impact_resp,
                timeline=timeline,
                allowed_next_actions=allowed,
            )
        finally:
            conn.close()

    @staticmethod
    def get_allowed_next_actions(status: str) -> List[str]:
        s = status.upper().strip()
        if s == "RECOMMENDED":
            return ["APPROVE", "REJECT"]
        if s == "APPROVED":
            return ["REQUEST_QUOTE", "REJECT"]
        if s == "QUOTE_READY":
            return ["CONFIRM_QUOTE", "REQUEST_QUOTE", "REJECT"]
        if s == "QUOTE_EXPIRED":
            return ["REQUEST_QUOTE", "REJECT"]
        if s == "CONFIRMED":
            return ["EXECUTE", "REQUEST_QUOTE"]
        if s in ("VERIFIED", "EXECUTED"):
            return ["VIEW_REFORECAST", "VIEW_AUDIT_TRAIL"]
        if s == "REQUIRES_REVIEW":
            return ["MANUAL_REVIEW", "VERIFY", "CANCEL"]
        if s == "FAILED":
            return ["RETRY", "REQUEST_QUOTE"]
        return []
