"""
================================================================================
ECONOMIC IMPACT & COST OF INACTION ENGINE
--------------------------------------------------------------------------------
Calculates expected cost of doing nothing, estimated transaction fees, slippage,
and the net financial benefit of executing risk protection.
================================================================================
"""

import math
import logging
from datetime import date, datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("economic_impact_engine")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


class EconomicImpactEngine:
    """
    Computes deterministic cost of inaction and action economics for treasury hedges.
    """

    def __init__(self, conversion_fee: float = 0.005, slippage_rate: float = 0.002):
        """
        Args:
            conversion_fee: Fee charged by Wise Sandbox (default: 0.5% / 0.005).
            slippage_rate: Market slippage buffer (default: 0.2% / 0.002).
        """
        self.conversion_fee = conversion_fee
        self.slippage_rate = slippage_rate
        self.total_action_rate = conversion_fee + slippage_rate

    def calculate_impact(
        self,
        amount_base: float,
        daily_volatility: float,
        days_to_due: int,
        action: str,
        priority: str
    ) -> Dict[str, Any]:
        """
        Calculates expected inaction cost, protection benefit, and net benefit.
        
        Args:
            amount_base: Transaction value converted to USD base.
            daily_volatility: Daily volatility parameter of the foreign currency.
            days_to_due: Horizon days until transaction settlement.
            action: Action recommendation string (CONVERT_AND_HOLD, SETTLE_NOW, etc.).
            priority: Action priority level (HIGH, MEDIUM, LOW).
        """
        action_norm = action.upper().strip()
        days_to_due = max(1, days_to_due)
        
        # 1. Expected Worst-Case Inaction Downside (at 95% Confidence Level)
        # Downside % = 1 - exp(-1.645 * daily_vol * sqrt(T))
        z_score = 1.645
        downside_pct = 1.0 - math.exp(-z_score * daily_volatility * math.sqrt(days_to_due))
        expected_inaction_cost = amount_base * downside_pct

        # 2. Action Cost (Fee + Slippage on conversion)
        # Only payables being converted or settled early incur conversion costs.
        if action_norm in ("CONVERT_AND_HOLD", "SETTLE_NOW"):
            action_cost = amount_base * self.total_action_rate
            estimated_avoided_loss = expected_inaction_cost
            risk_reduction_percent = 100.0
        elif action_norm == "RE_QUOTE":
            # Re-quoting does not require conversion costs on our side (transferred to client),
            # but mitigates receivable volatility.
            action_cost = 0.0
            estimated_avoided_loss = expected_inaction_cost
            risk_reduction_percent = 100.0
        else:  # MONITOR or no-action
            action_cost = 0.0
            estimated_avoided_loss = 0.0
            risk_reduction_percent = 0.0

        estimated_net_benefit = estimated_avoided_loss - action_cost

        return {
            "expected_inaction_cost": round(expected_inaction_cost, 2),
            "action_cost": round(action_cost, 2),
            "estimated_avoided_loss": round(estimated_avoided_loss, 2),
            "estimated_net_benefit": round(estimated_net_benefit, 2),
            "risk_reduction_percent": round(risk_reduction_percent, 1),
            "downside_pct": round(downside_pct * 100, 2),
            "risk_if_no_action": "HIGH_EXPOSURE" if priority == "HIGH" else "MODERATE_EXPOSURE"
        }
