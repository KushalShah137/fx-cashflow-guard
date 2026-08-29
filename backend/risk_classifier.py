"""
================================================================================
RISK CLASSIFICATION LAYER (Layer 2.5)
--------------------------------------------------------------------------------
Responsibilities of this module:
    1. Consume the risk band output from Risk Model V2 (P5/P50/P95/baseline).
    2. Consume context from CashFlowEngine (exposures, danger threshold).
    3. Perform multi-horizon snapshots for Day 30, 60, and 90.
    4. Compute key metrics: downside amount/pct, band width, liquidity buffer.
    5. Determine risk levels (LOW, MEDIUM, HIGH) and liquidity status
       (SAFE, WATCH, BREACH) deterministically based on configurable policy.
    6. Formulate clear business explanations based on metrics.
    7. Classify the overall risk trajectory (STABLE, WORSENING, IMPROVING).
    8. Expose a decision_context block to support future Decision Engines.
================================================================================
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Dict, Any, List, Optional, Union

from backend.cash_flow_engine import CashFlowEngine, FlowDirection

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logger = logging.getLogger("risk_classifier")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


# --------------------------------------------------------------------------- #
# Configurable Policy Definition
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RiskClassificationConfig:
    """
    Configurable default thresholds for FX risk classification.
    Production systems would determine these based on corporate treasury policies.
    """
    watch_buffer_pct: float = 0.10   # Watch warning if P5 within 10% of danger floor
    high_downside_pct: float = 0.10  # High risk if simulated downside exceeds 10% of baseline
    medium_downside_pct: float = 0.05
    high_band_pct: float = 0.15      # High risk if simulated volatility envelope > 15% of baseline
    medium_band_pct: float = 0.07


# --------------------------------------------------------------------------- #
# Horizon Snapshot Dataclass
# --------------------------------------------------------------------------- #
@dataclass
class HorizonSnapshot:
    horizon_days: int
    date: str
    baseline: float
    p5: float
    p50: float
    p95: float
    downside_amount: float
    downside_pct: float
    band_width: float
    fx_risk_level: str
    liquidity_status: str
    overall_risk_level: str
    risk_score: int
    liquidity_buffer: float
    liquidity_buffer_pct: float
    explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Core Classifier
# --------------------------------------------------------------------------- #
class RiskClassifier:
    """
    Classifies quantitative simulation paths into business risk severity levels.
    """

    def __init__(self, config: Optional[RiskClassificationConfig] = None):
        self.config = config or RiskClassificationConfig()

    def classify(
        self,
        engine: CashFlowEngine,
        risk_band: List[Dict[str, Any]],
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Takes the CashFlowEngine instance and the 90-day risk band list,
        and generates multi-horizon classifications for Days 30, 60, and 90.
        """
        if not risk_band:
            raise ValueError("Input risk band is empty.")
        if len(risk_band) < days:
            logger.warning(
                "Risk band length (%d) is shorter than target horizon (%d). Running with available data.",
                len(risk_band), days
            )
            days = len(risk_band)

        danger_threshold = float(engine.danger_threshold) if engine.danger_threshold is not None else 20000.0

        # Aligned day mapping snapshots (1-indexed offset mapping)
        # Horizon 30D maps to day 30 (index 29)
        # Horizon 60D maps to day 60 (index 59)
        # Horizon 90D maps to day 90 (index 89)
        horizons_to_check = [30, 60, 90]
        horizons_snapshots: Dict[str, Dict[str, Any]] = {}
        horizon_comparison_list = []

        for h in horizons_to_check:
            # Map day to array index (e.g. Day 30 is at index 29)
            idx = h - 1
            if idx < len(risk_band):
                day_data = risk_band[idx]
                snapshot = self._classify_horizon(h, day_data, danger_threshold)
                horizons_snapshots[str(h)] = snapshot.to_dict()
                horizon_comparison_list.append({
                    "horizon": f"{h}D",
                    "risk_score": snapshot.risk_score,
                    "risk_level": snapshot.overall_risk_level,
                    "downside_amount": snapshot.downside_amount,
                    "band_width": snapshot.band_width,
                    "liquidity_buffer": snapshot.liquidity_buffer
                })

        # Calculate Overall Risk Level and Trajectory
        overall_risk_level = "LOW"
        overall_risk_score = 0
        trajectory = "STABLE"

        # Trajectory check based on continuous risk scores
        score_30 = horizons_snapshots["30"]["risk_score"] if "30" in horizons_snapshots else 0
        score_60 = horizons_snapshots["60"]["risk_score"] if "60" in horizons_snapshots else 0
        score_90 = horizons_snapshots["90"]["risk_score"] if "90" in horizons_snapshots else 0

        # Trajectory evaluation
        diff_score = score_90 - score_30
        if diff_score > 5:
            trajectory = "WORSENING"
        elif diff_score < -5:
            trajectory = "IMPROVING"
        else:
            trajectory = "STABLE"

        # Overall risk level is based on the maximum risk seen at the furthest horizons
        overall_risk_score = max(score_30, score_60, score_90)
        if overall_risk_score >= 67:
            overall_risk_level = "HIGH"
        elif overall_risk_score >= 34:
            overall_risk_level = "MEDIUM"
        else:
            overall_risk_level = "LOW"

        # Exposure context extraction from engine
        raw_exposures = engine.get_currency_exposures()
        currencies_at_risk = [e.currency for e in raw_exposures]
        exposure_direction = {e.currency: e.direction.value.upper() for e in raw_exposures}

        # Build Future Decision Context
        requires_intervention = (overall_risk_level == "HIGH" or any(
            horizons_snapshots[h]["liquidity_status"] == "BREACH"
            for h in horizons_snapshots
        ))

        decision_context = {
            "risk_level": overall_risk_level,
            "risk_score": overall_risk_score,
            "horizon_days": days,
            "liquidity_status": horizons_snapshots.get(str(days), {}).get("liquidity_status", "SAFE"),
            "currencies_at_risk": currencies_at_risk,
            "exposure_direction": exposure_direction,
            "requires_intervention": requires_intervention,
            "candidate_actions": []  # Open door for future Layer 3 Decision Engine
        }

        return {
            "model_version": "risk_classifier_v1",
            "method": "rule_based_risk_classification",
            "inputs": [
                "baseline",
                "p5",
                "p50",
                "p95",
                "danger_threshold",
                "FX exposure"
            ],
            "forecast_days": days,
            "horizons": horizons_snapshots,
            "horizon_comparison": horizon_comparison_list,
            "trajectory": trajectory,
            "overall_risk_level": overall_risk_level,
            "overall_risk_score": overall_risk_score,
            "decision_context": decision_context
        }

    def _classify_horizon(
        self,
        horizon_days: int,
        day_data: Dict[str, Any],
        danger_threshold: float
    ) -> HorizonSnapshot:
        """
        Classifies a single forecast day snapshot deterministically using the config policy.
        """
        baseline = float(day_data.get("baseline", 0.0))
        p5 = float(day_data.get("p5", 0.0))
        p50 = float(day_data.get("p50", 0.0))
        p95 = float(day_data.get("p95", 0.0))
        dt = day_data.get("date", "")

        # Numerical Safeguards / Epsilon
        eps = 1e-9

        # Metrics calculation
        downside_amount = max(0.0, baseline - p5)
        upside_amount = max(0.0, p95 - baseline)
        band_width = max(0.0, p95 - p5)
        downside_pct = downside_amount / max(abs(baseline), eps)
        band_width_pct = band_width / max(abs(baseline), eps)

        liquidity_buffer = p5 - danger_threshold
        liquidity_buffer_pct = liquidity_buffer / max(abs(danger_threshold), eps)

        # 1. Determine Liquidity Status
        if p5 < danger_threshold:
            liquidity_status = "BREACH"
        elif p5 >= danger_threshold and (p5 - danger_threshold) < (danger_threshold * self.config.watch_buffer_pct):
            liquidity_status = "WATCH"
        else:
            liquidity_status = "SAFE"

        # 2. Determine FX Risk Level based on exposures & volatility envelope
        # Check against configured policy limits
        if downside_pct >= self.config.high_downside_pct or band_width_pct >= self.config.high_band_pct:
            fx_risk_level = "HIGH"
        elif downside_pct >= self.config.medium_downside_pct or band_width_pct >= self.config.medium_band_pct:
            fx_risk_level = "MEDIUM"
        else:
            fx_risk_level = "LOW"

        # 3. Calculate Deterministic Risk Severity Score (0-100)
        # Components: Downside (40%), Liquidity Proximity (40%), Uncertainty (20%)
        
        # Downside component
        downside_score = (downside_pct / self.config.high_downside_pct) * 40.0
        downside_score = min(40.0, max(0.0, downside_score))

        # Liquidity proximity component
        if liquidity_status == "BREACH":
            liquidity_score = 40.0
        else:
            # Scale score based on proximity to safety threshold buffer
            buffer_limit = danger_threshold * self.config.watch_buffer_pct
            dist_to_threshold = p5 - danger_threshold
            if dist_to_threshold <= 0:
                liquidity_score = 40.0
            elif dist_to_threshold >= buffer_limit:
                liquidity_score = 0.0
            else:
                liquidity_score = (1.0 - (dist_to_threshold / buffer_limit)) * 40.0

        # Uncertainty band component
        uncertainty_score = (band_width_pct / self.config.high_band_pct) * 20.0
        uncertainty_score = min(20.0, max(0.0, uncertainty_score))

        # Sum components
        raw_score = downside_score + liquidity_score + uncertainty_score
        risk_score = int(round(raw_score))
        risk_score = min(100, max(0, risk_score))

        # Ensure mathematical consistency: if simulated p5 is a breach, overall risk level is forced to HIGH
        if liquidity_status == "BREACH":
            overall_risk_level = "HIGH"
            # Ensure risk score reflects HIGH boundary (>= 67)
            if risk_score < 67:
                risk_score = 67
        else:
            # Map score to overall risk level
            if risk_score >= 67:
                overall_risk_level = "HIGH"
            elif risk_score >= 34:
                overall_risk_level = "MEDIUM"
            else:
                overall_risk_level = "LOW"

        # 4. Generate Business Explanation
        explanation = self._formulate_explanation(
            horizon_days, overall_risk_level, liquidity_status,
            downside_pct, liquidity_buffer, danger_threshold
        )

        return HorizonSnapshot(
            horizon_days=horizon_days,
            date=dt,
            baseline=round(baseline, 2),
            p5=round(p5, 2),
            p50=round(p50, 2),
            p95=round(p95, 2),
            downside_amount=round(downside_amount, 2),
            downside_pct=round(downside_pct, 4),
            band_width=round(band_width, 2),
            fx_risk_level=fx_risk_level,
            liquidity_status=liquidity_status,
            overall_risk_level=overall_risk_level,
            risk_score=risk_score,
            liquidity_buffer=round(liquidity_buffer, 2),
            liquidity_buffer_pct=round(liquidity_buffer_pct, 4),
            explanation=explanation
        )

    def _formulate_explanation(
        self,
        horizon_days: int,
        overall_risk_level: str,
        liquidity_status: str,
        downside_pct: float,
        liquidity_buffer: float,
        danger_threshold: float
    ) -> str:
        """
        Formulates a deterministic human-readable explanation based on horizon outcomes.
        """
        # Description of FX Risk Severity Method
        desc = f"At the {horizon_days}-day horizon, "

        if overall_risk_level == "HIGH":
            if liquidity_status == "BREACH":
                return desc + (
                    f"the lower-tail cash projection falls below your liquidity floor by ${abs(liquidity_buffer):,.2f}, "
                    f"representing a critical threshold breach driven by adverse FX movements."
                )
            else:
                return desc + (
                    f"FX volatility creates high downside exposure ({downside_pct * 100:.1f}% deviation from baseline), "
                    f"although the simulated lower-tail cash remains above the ${danger_threshold:,.2f} liquidity floor."
                )

        elif overall_risk_level == "MEDIUM":
            if liquidity_status == "WATCH":
                return desc + (
                    f"the risk-adjusted cash buffer narrows to ${liquidity_buffer:,.2f} above the safety threshold. "
                    f"Requires monitoring as volatility continues to accumulate."
                )
            else:
                return desc + (
                    f"FX volatility is moderate (downside deviation: {downside_pct * 100:.1f}%). "
                    f"The cash position is safe, but cumulative exposure is material."
                )

        else:  # LOW
            return desc + (
                f"the simulated FX downside remains negligible ({downside_pct * 100:.1f}% deviation), "
                f"with cash resources projected comfortably above the liquidity floor."
            )
