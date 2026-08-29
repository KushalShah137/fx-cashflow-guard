"""
================================================================================
ACTION RECOMMENDATION LIFECYCLE & STATE MACHINE
--------------------------------------------------------------------------------
Manages the state transitions of treasury recommendations (RECOMMENDED, APPROVED, 
REJECTED, EXECUTING, EXECUTED, FAILED, EXPIRED).
================================================================================
"""

import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from backend.db import get_db_connection

logger = logging.getLogger("state_machine")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


class RecommendationState(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class LifecycleError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


# Map of valid status transitions
VALID_TRANSITIONS = {
    RecommendationState.RECOMMENDED: [
        RecommendationState.APPROVED,
        RecommendationState.REJECTED,
        RecommendationState.EXPIRED
    ],
    RecommendationState.APPROVED: [
        RecommendationState.EXECUTING,
        RecommendationState.REJECTED
    ],
    RecommendationState.EXECUTING: [
        RecommendationState.EXECUTED,
        RecommendationState.FAILED
    ],
    # Terminal states: REJECTED, EXECUTED, FAILED, EXPIRED (no transitions out)
}


def validate_transition(current: str, target: str) -> None:
    """Asserts that transition from current to target is permitted."""
    curr_state = RecommendationState(current)
    targ_state = RecommendationState(target)
    
    if curr_state == targ_state:
        return
        
    allowed = VALID_TRANSITIONS.get(curr_state, [])
    if targ_state not in allowed:
        raise LifecycleError(
            f"Invalid transition from {curr_state.value} to {targ_state.value}. "
            f"Allowed next states: {[s.value for s in allowed]}"
        )


def get_all_recommendations() -> List[Dict[str, Any]]:
    """Loads all recommendations from the database as dictionaries."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recommendations ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        result = []
        for r in rows:
            result.append({
                "action_id": r["action_id"],
                "transaction_id": r["transaction_id"],
                "action_type": r["action_type"],
                "priority": r["priority"],
                "risk_score": r["risk_score"],
                "confidence": r["confidence"],
                "reason": r["reason"],
                "reason_codes": json.loads(r["reason_codes_json"]),
                "warnings": json.loads(r["warnings_json"]),
                "amount_base": r["amount_base"],
                "recommended_amount": r["recommended_amount"],
                "risk_before": r["risk_before"],
                "risk_after_estimate": r["risk_after_estimate"],
                "estimated_action_cost": r["estimated_action_cost"],
                "estimated_inaction_cost": r["estimated_inaction_cost"],
                "status": r["status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"]
            })
        return result
    finally:
        conn.close()


def get_recommendation_by_id(action_id: str) -> Optional[Dict[str, Any]]:
    """Loads a single recommendation by ID from the database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recommendations WHERE action_id = ?", (action_id,))
        r = cursor.fetchone()
        if not r:
            return None
            
        return {
            "action_id": r["action_id"],
            "transaction_id": r["transaction_id"],
            "action_type": r["action_type"],
            "priority": r["priority"],
            "risk_score": r["risk_score"],
            "confidence": r["confidence"],
            "reason": r["reason"],
            "reason_codes": json.loads(r["reason_codes_json"]),
            "warnings": json.loads(r["warnings_json"]),
            "amount_base": r["amount_base"],
            "recommended_amount": r["recommended_amount"],
            "risk_before": r["risk_before"],
            "risk_after_estimate": r["risk_after_estimate"],
            "estimated_action_cost": r["estimated_action_cost"],
            "estimated_inaction_cost": r["estimated_inaction_cost"],
            "status": r["status"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"]
        }
    finally:
        conn.close()


def create_or_update_recommendation(rec: Dict[str, Any]) -> str:
    """Inserts a new recommendation or updates it if it exists in RECOMMENDED state."""
    conn = get_db_connection()
    now_str = datetime.utcnow().isoformat() + "Z"
    action_id = rec.get("action_id") or f"act_{uuid.uuid4().hex[:8]}"
    
    try:
        with conn:
            # Check if recommendation already exists for this transaction and is active
            cursor = conn.cursor()
            cursor.execute(
                "SELECT action_id, status FROM recommendations WHERE transaction_id = ? AND status = 'RECOMMENDED'",
                (rec["transaction_id"],)
            )
            existing = cursor.fetchone()
            
            if existing:
                action_id = existing["action_id"]
                conn.execute(
                    """
                    UPDATE recommendations
                    SET action_type = ?, priority = ?, risk_score = ?, confidence = ?, reason = ?, 
                        reason_codes_json = ?, warnings_json = ?, amount_base = ?, recommended_amount = ?, 
                        risk_before = ?, risk_after_estimate = ?, estimated_action_cost = ?, 
                        estimated_inaction_cost = ?, updated_at = ?
                    WHERE action_id = ?
                    """,
                    (
                        rec["action_type"],
                        rec["priority"],
                        rec["risk_score"],
                        rec["confidence"],
                        rec["reason"],
                        json.dumps(rec.get("reason_codes", [])),
                        json.dumps(rec.get("warnings", [])),
                        rec["amount_base"],
                        rec.get("recommended_amount"),
                        rec.get("risk_before", "LOW"),
                        rec.get("risk_after_estimate", "LOW"),
                        rec.get("estimated_action_cost", 0.0),
                        rec.get("estimated_inaction_cost", 0.0),
                        now_str,
                        action_id
                    )
                )
            else:
                conn.execute(
                    """
                    INSERT INTO recommendations 
                    (action_id, transaction_id, action_type, priority, risk_score, confidence, reason, 
                     reason_codes_json, warnings_json, amount_base, recommended_amount, 
                     risk_before, risk_after_estimate, estimated_action_cost, estimated_inaction_cost, 
                     status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_id,
                        rec["transaction_id"],
                        rec["action_type"],
                        rec["priority"],
                        rec["risk_score"],
                        rec["confidence"],
                        rec["reason"],
                        json.dumps(rec.get("reason_codes", [])),
                        json.dumps(rec.get("warnings", [])),
                        rec["amount_base"],
                        rec.get("recommended_amount"),
                        rec.get("risk_before", "LOW"),
                        rec.get("risk_after_estimate", "LOW"),
                        rec.get("estimated_action_cost", 0.0),
                        rec.get("estimated_inaction_cost", 0.0),
                        RecommendationState.RECOMMENDED.value,
                        now_str,
                        now_str
                    )
                )
                
                # Write audit log
                conn.execute(
                    """
                    INSERT INTO audit_logs (event_type, action_id, transaction_id, timestamp, actor, new_state)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "RECOMMENDATION_CREATED",
                        action_id,
                        rec["transaction_id"],
                        now_str,
                        "system",
                        RecommendationState.RECOMMENDED.value
                    )
                )
        return action_id
    finally:
        conn.close()


def transition_recommendation_status(action_id: str, target_status: str, actor: str = "user") -> Dict[str, Any]:
    """Transitions status of a recommendation with full lifecycle validation and audit logging."""
    conn = get_db_connection()
    now_str = datetime.utcnow().isoformat() + "Z"
    
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recommendations WHERE action_id = ?", (action_id,))
            r = cursor.fetchone()
            if not r:
                raise ValueError(f"No recommendation found with ID '{action_id}'")
                
            current_status = r["status"]
            validate_transition(current_status, target_status)
            
            # Update status
            conn.execute(
                "UPDATE recommendations SET status = ?, updated_at = ? WHERE action_id = ?",
                (target_status, now_str, action_id)
            )
            
            # Map state to audit event type
            event_type = f"ACTION_{target_status}"
            if target_status == RecommendationState.EXPIRED.value:
                event_type = "ACTION_EXPIRED"
            elif target_status == RecommendationState.FAILED.value:
                event_type = "ACTION_FAILED"
            elif target_status == RecommendationState.EXECUTED.value:
                event_type = "EXECUTION_COMPLETED"
            elif target_status == RecommendationState.EXECUTING.value:
                event_type = "EXECUTION_STARTED"
                
            # Log audit
            conn.execute(
                """
                INSERT INTO audit_logs (event_type, action_id, transaction_id, timestamp, actor, old_state, new_state)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    action_id,
                    r["transaction_id"],
                    now_str,
                    actor,
                    current_status,
                    target_status
                )
            )
            
            # Log specific approvals/executions
            if target_status == RecommendationState.APPROVED.value:
                approval_id = f"appr_{uuid.uuid4().hex[:8]}"
                conn.execute(
                    "INSERT INTO approvals (approval_id, action_id, status, actor, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (approval_id, action_id, "APPROVED", actor, now_str)
                )
            elif target_status == RecommendationState.REJECTED.value:
                approval_id = f"appr_{uuid.uuid4().hex[:8]}"
                conn.execute(
                    "INSERT INTO approvals (approval_id, action_id, status, actor, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (approval_id, action_id, "REJECTED", actor, now_str)
                )
            
        return get_recommendation_by_id(action_id)
    finally:
        conn.close()
