"""
================================================================================
LAYER 3 — FX DECISION ENGINE
--------------------------------------------------------------------------------
Responsibilities:
    1. Filter pending transactions in foreign currencies.
    2. Determine funded vs unfunded status for payables.
    3. Determine margin risk for receivables using volatility parameters.
    4. Apply configurable decision policies to recommend actions:
       - CONVERT_AND_HOLD
       - SETTLE_NOW
       - RE_QUOTE
       - MONITOR
    5. Prioritize actions by urgency, magnitude, and risk.
    6. Formulate clear business explanations and reason codes.
    7. Generate future execution-compatible decision context.
================================================================================
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import date
from enum import Enum
from typing import List, Dict, Any, Optional

from backend.cash_flow_engine import CashFlowEngine, FlowDirection, TransactionStatus, Transaction
from backend.risk_classifier import RiskClassifier

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logger = logging.getLogger("decision_engine")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


# --------------------------------------------------------------------------- #
# Action and Priority Enums
# --------------------------------------------------------------------------- #
class ActionType(str, Enum):
    CONVERT_AND_HOLD = "CONVERT_AND_HOLD"
    SETTLE_NOW = "SETTLE_NOW"
    RE_QUOTE = "RE_QUOTE"
    MONITOR = "MONITOR"


class ActionPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# --------------------------------------------------------------------------- #
# Configurable Decision Policy
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DecisionPolicy:
    """
    Configurable parameters governing the selection and prioritization of FX actions.
    """
    minimum_exposure_base: float = 1000.0     # Minimum USD-equivalent value to recommend intervention
    high_priority_days: int = 30              # Due within 30 days raises priority
    margin_threshold_pct: float = 0.03        # 3% margin risk threshold triggers re-quote recommendation
    liquidity_buffer_warning: float = 5000.0  # Buffer below which liquidity warnings are generated


# --------------------------------------------------------------------------- #
# Action Recommendation Dataclass
# --------------------------------------------------------------------------- #
@dataclass
class ActionRecommendation:
    transaction_id: str
    action: ActionType
    currency: str
    amount: float
    direction: str
    priority: ActionPriority
    risk_level: str
    risk_score: int
    days_to_due: Optional[int]
    requires_approval: bool
    reason: str
    reason_codes: List[str]
    warnings: List[str] = field(default_factory=list)
    amount_base: float = 0.0
    recommended_amount: Optional[float] = None
    expected_impact: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["action"] = self.action.value
        d["priority"] = self.priority.value
        return d


# --------------------------------------------------------------------------- #
# Decision Engine
# --------------------------------------------------------------------------- #
class DecisionEngine:
    """
    Translates cash flow exposures and risk classifications into actionable recommendations.
    """

    def __init__(self, policy: Optional[DecisionPolicy] = None):
        self.policy = policy or DecisionPolicy()

    def generate_decisions(
        self,
        engine: CashFlowEngine,
        classification_result: Dict[str, Any],
        anchor_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Consumes CashFlowEngine state and RiskClassifier outputs to recommend actions.
        """
        # Resolve forecast starting base date
        base_date = anchor_date or date(2026, 9, 1)
        
        # Pull configurations from engine
        base_ccy = engine.base_currency
        danger_threshold = float(engine.danger_threshold) if engine.danger_threshold is not None else 20000.0
        
        # Volatility maps
        vol_config = engine.fx_config.get("daily_volatility", {})
        
        recommendations: List[ActionRecommendation] = []
        total_foreign_exposures = 0

        # Loop through all transactions
        for tx in engine.transactions:
            # 1. Filter: Status must be pending, and currency != base currency (USD)
            if tx.status != TransactionStatus.PENDING:
                continue
            if tx.currency == base_ccy:
                continue

            total_foreign_exposures += 1

            # Convert magnitude to base equivalent for materiality checks
            amount_base = engine.convert_to_base(tx.amount, tx.currency)
            days_to_due = (tx.date - base_date).days

            # Determine planning horizon snapshot corresponding to the transaction's due date
            if days_to_due <= 30:
                horizon_key = "30"
            elif days_to_due <= 60:
                horizon_key = "60"
            else:
                horizon_key = "90"

            snapshot = classification_result.get("horizons", {}).get(horizon_key, {})
            snapshot_level = snapshot.get("classification", {}).get("overall_risk_level", "LOW")
            snapshot_score = snapshot.get("classification", {}).get("risk_score", 0)
            liquidity_status = snapshot.get("classification", {}).get("liquidity_status", "SAFE")
            minimum_liquidity_buffer = snapshot.get("through_horizon", {}).get("minimum_liquidity_buffer", 999999.0)

            # Establish eligibility and select actions
            action = ActionType.MONITOR
            priority = ActionPriority.LOW
            reason_codes = []
            warnings = []
            reason = ""
            recommended_amount = None

            # Calculate downside margin risk analytically for receivables
            vol = vol_config.get(tx.currency, 0.0)
            t_days = max(1, days_to_due)
            # worst-case rate deviation factor at 95% confidence (1.645 std devs)
            downside_pct = 1.0 - math.exp(-1.645 * vol * math.sqrt(t_days))

            # Funding state classification for payables
            # A payable is funded if its demo action is already settle_now or description suggests funded
            is_funded = (tx.demo_action == "settle_now" or "funded" in tx.description.lower())

            # Policy logic
            is_material = (amount_base >= self.policy.minimum_exposure_base)

            if tx.direction == FlowDirection.PAYABLE:
                # Payables
                if is_funded:
                    action = ActionType.SETTLE_NOW
                    recommended_amount = float(tx.amount)
                    reason_codes.append("FUNDED_PAYABLE")
                    reason = (
                        f"Funded {tx.currency} payable of {tx.amount:,.2f} is pending. "
                        f"Settling early closes the exposure window immediately."
                    )
                else:
                    # Unfunded
                    if is_material and snapshot_level in ("HIGH", "MEDIUM"):
                        action = ActionType.CONVERT_AND_HOLD
                        recommended_amount = float(tx.amount)
                        reason_codes.append("UNFUNDED_PAYABLE")
                        reason = (
                            f"Unfunded {tx.currency} payable of {tx.amount:,.2f} has material exposure. "
                            f"Converting and holding protects against adverse currency moves before settlement."
                        )
                    else:
                        action = ActionType.MONITOR
                        reason_codes.append("LOW_MATERIALITY")
                        reason = f"Unfunded {tx.currency} payable is within acceptable risk tolerance thresholds."

            else:
                # Receivables
                margin_threatened = (downside_pct >= self.policy.margin_threshold_pct)
                if is_material and margin_threatened and snapshot_level in ("HIGH", "MEDIUM"):
                    action = ActionType.RE_QUOTE
                    recommended_amount = None  # Re-quote engine must calculate this later
                    reason_codes.append("RECEIVABLE_MARGIN_RISK")
                    reason = (
                        f"Unpaid {tx.currency} receivable of {tx.amount:,.2f} has a cumulative FX downside "
                        f"of {downside_pct * 100:.1f}%, threatening profit margins. Re-quoting is recommended."
                    )
                else:
                    action = ActionType.MONITOR
                    reason_codes.append("LOW_MATERIALITY")
                    reason = f"Unpaid {tx.currency} receivable remains within acceptable volatility bands."

            # Determine Priority based on severity and proximity
            if action != ActionType.MONITOR:
                # If it requires action
                if snapshot_level == "HIGH" and (days_to_due <= self.policy.high_priority_days or amount_base >= 10000.0):
                    priority = ActionPriority.HIGH
                    reason_codes.append("DUE_SOON" if days_to_due <= self.policy.high_priority_days else "HIGH_EXPOSURE")
                else:
                    priority = ActionPriority.MEDIUM
            else:
                priority = ActionPriority.LOW

            # Add Liquidity Warnings for cash-draining actions (CONVERT_AND_HOLD, SETTLE_NOW)
            if action in (ActionType.CONVERT_AND_HOLD, ActionType.SETTLE_NOW):
                if minimum_liquidity_buffer < self.policy.liquidity_buffer_warning:
                    warnings.append(
                        "Execution of this transaction's conversion/settlement consumes a material portion of the "
                        "available base-currency liquidity buffer."
                    )
                    reason_codes.append("LIQUIDITY_BUFFER_WARNING")

            # Calculate economic impact
            from backend.economic_impact_engine import EconomicImpactEngine
            impact_eng = EconomicImpactEngine()
            impact = impact_eng.calculate_impact(
                amount_base=amount_base,
                daily_volatility=vol,
                days_to_due=days_to_due,
                action=action.value,
                priority=priority.value
            )

            recommendations.append(
                ActionRecommendation(
                    transaction_id=tx.id,
                    action=action,
                    currency=tx.currency,
                    amount=float(tx.amount),
                    direction=tx.direction.value,
                    priority=priority,
                    risk_level=snapshot_level,
                    risk_score=snapshot_score,
                    days_to_due=days_to_due,
                    requires_approval=True,  # Default to maker-checker approval workflow
                    reason=reason,
                    reason_codes=reason_codes,
                    warnings=warnings,
                    amount_base=round(amount_base, 2),
                    recommended_amount=recommended_amount,
                    expected_impact=impact
                )
            )

        # Sort recommendations: HIGH first, then MEDIUM, then LOW
        # Secondary sort: days_to_due ascending, amount_base descending, risk_score descending
        priority_order = {ActionPriority.HIGH: 0, ActionPriority.MEDIUM: 1, ActionPriority.LOW: 2}
        recommendations.sort(
            key=lambda r: (
                priority_order.get(r.priority, 9),
                r.days_to_due if r.days_to_due is not None else 999,
                -r.amount_base,
                -r.risk_score
            )
        )

        # Key performance indicators
        actions_required = sum(1 for r in recommendations if r.action != ActionType.MONITOR)
        high_priority = sum(1 for r in recommendations if r.priority == ActionPriority.HIGH)
        medium_priority = sum(1 for r in recommendations if r.priority == ActionPriority.MEDIUM)
        monitor_only = sum(1 for r in recommendations if r.action == ActionType.MONITOR)

        decision_kpis = {
            "total_foreign_exposures": total_foreign_exposures,
            "actions_required": actions_required,
            "high_priority_actions": high_priority,
            "medium_priority_actions": medium_priority,
            "monitor_only": monitor_only
        }

        # Determine overall decision status
        requires_intervention = (actions_required > 0)
        overall_risk_level = classification_result.get("overall_risk_level", "LOW")
        overall_risk_score = classification_result.get("overall_risk_score", 0)
        days = classification_result.get("forecast_days", 90)
        overall_liquidity_status = classification_result.get("horizons", {}).get(str(days), {}).get("classification", {}).get("liquidity_status", "SAFE")
        overall_trajectory = classification_result.get("risk_trajectory", "STABLE")

        overall = {
            "risk_level": overall_risk_level,
            "risk_score": overall_risk_score,
            "liquidity_status": overall_liquidity_status,
            "trajectory": overall_trajectory,
            "requires_intervention": requires_intervention
        }

        # Future-proof decision context
        currencies_at_risk = classification_result.get("decision_context", {}).get("currencies_at_risk", [])
        exposure_direction = classification_result.get("decision_context", {}).get("exposure_direction", {})

        decision_context = {
            "currencies_at_risk": currencies_at_risk,
            "exposure_direction": exposure_direction
        }

        return {
            "model_version": "decision_engine_v1",
            "decision_policy_version": "v1",
            "overall": overall,
            "decision_kpis": decision_kpis,
            "recommendations": [r.to_dict() for r in recommendations],
            "decision_context": decision_context
        }
