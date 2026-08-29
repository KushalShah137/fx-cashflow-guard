"""
================================================================================
RISK CLASSIFICATION LAYER (Layer 2.5)
--------------------------------------------------------------------------------
Responsibilities of this module:
    1. Consume the risk band output from Risk Model V2 (P5/P50/P95/baseline).
    2. Consume context from CashFlowEngine (exposures, danger threshold).
    3. Perform through-horizon and point-in-time multi-horizon snapshots for Days 30, 60, and 90.
    4. Compute key point-in-time metrics: baseline, P5, P50, P95, band width, downside amount/pct.
    5. Compute through-horizon metrics: minimum P5/P50, maximum band width, maximum downside amount/pct,
       minimum liquidity buffer, first breach date, breach count, days to first breach, risk persistence.
    6. Determine risk levels (LOW, MEDIUM, HIGH) and liquidity status
       (SAFE, WATCH, BREACH) deterministically based on configurable policy.
    7. Formulate clear business explanations based on through-horizon metrics.
    8. Classify the overall risk trajectory (STABLE, WORSENING, IMPROVING) and risk pressure.
    9. Expose a decision_context block to support future Decision Engines.
================================================================================
"""

from __future__ import annotations

import json
import logging
import math
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
    point_in_time: Dict[str, Any]
    through_horizon: Dict[str, Any]
    classification: Dict[str, Any]
    explanation: str

    def to_dict(self) -> dict:
        return {
            "horizon_days": self.horizon_days,
            "point_in_time": self.point_in_time,
            "through_horizon": self.through_horizon,
            "classification": self.classification,
            "explanation": self.explanation
        }


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
                # Horizon slice for through-horizon metrics (from Day 1 to Day H inclusive)
                horizon_slice = risk_band[0:h]
                pit_data = risk_band[idx]
                snapshot = self._classify_horizon(h, pit_data, horizon_slice, danger_threshold)
                horizons_snapshots[str(h)] = snapshot.to_dict()
                
                horizon_comparison_list.append({
                    "horizon": f"{h}D",
                    "risk_score": snapshot.classification["risk_score"],
                    "risk_level": snapshot.classification["overall_risk_level"],
                    "fx_risk_level": snapshot.classification["fx_risk_level"],
                    "liquidity_status": snapshot.classification["liquidity_status"],
                    "minimum_p5": snapshot.through_horizon["minimum_p5"],
                    "minimum_liquidity_buffer": snapshot.through_horizon["minimum_liquidity_buffer"],
                    "maximum_downside": snapshot.through_horizon["maximum_downside"],
                    "maximum_downside_pct": snapshot.through_horizon["maximum_downside_pct"],
                    "breach_count": snapshot.through_horizon["breach_count"]
                })

        # Calculate Overall Risk Level, Score, Trajectory, and Pressure
        overall_risk_level = "LOW"
        overall_risk_score = 0
        trajectory = "STABLE"
        risk_pressure = "STABLE"

        # Trajectory checks based on point-in-time risk scores (evolution of terminal risk state)
        pit_score_30 = self._calculate_pit_score(risk_band[29], danger_threshold) if len(risk_band) >= 30 else 0
        pit_score_60 = self._calculate_pit_score(risk_band[59], danger_threshold) if len(risk_band) >= 60 else 0
        pit_score_90 = self._calculate_pit_score(risk_band[89], danger_threshold) if len(risk_band) >= 90 else 0

        # Trajectory evaluation
        diff_score = pit_score_90 - pit_score_30
        breach_count_30 = horizons_snapshots.get("30", {}).get("through_horizon", {}).get("breach_count", 0)
        breach_count_90 = horizons_snapshots.get("90", {}).get("through_horizon", {}).get("breach_count", 0)
        breach_emergence = breach_count_90 > breach_count_30

        if diff_score > 5 or breach_emergence:
            trajectory = "WORSENING"
        elif diff_score < -5:
            trajectory = "IMPROVING"
        else:
            trajectory = "STABLE"

        # Risk pressure evaluation (trend in terminal band width)
        if "30" in horizons_snapshots and "90" in horizons_snapshots:
            width_30 = horizons_snapshots["30"]["point_in_time"]["band_width"]
            width_90 = horizons_snapshots["90"]["point_in_time"]["band_width"]
            diff_width = width_90 - width_30
            pct_change = diff_width / max(width_30, 1.0)
            if pct_change > 0.05:
                risk_pressure = "INCREASING"
            elif pct_change < -0.05:
                risk_pressure = "DECREASING"
            else:
                risk_pressure = "STABLE"

        score_30 = horizons_snapshots["30"]["classification"]["risk_score"] if "30" in horizons_snapshots else 0
        score_60 = horizons_snapshots["60"]["classification"]["risk_score"] if "60" in horizons_snapshots else 0
        score_90 = horizons_snapshots["90"]["classification"]["risk_score"] if "90" in horizons_snapshots else 0

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
        exposures_formatted = []
        currencies_at_risk = []
        exposure_direction = {}
        
        for e in raw_exposures:
            currencies_at_risk.append(e.currency)
            exposure_direction[e.currency] = e.direction.value.upper()
            exposures_formatted.append(e.to_dict())

        # Build Future Decision Context
        # Treat any through-horizon liquidity breach as requiring intervention
        any_breach = any(
            horizons_snapshots[h]["classification"]["liquidity_status"] == "BREACH"
            for h in horizons_snapshots
        )
        requires_intervention = (overall_risk_level == "HIGH" or any_breach)

        decision_context = {
            "risk_level": overall_risk_level,
            "risk_score": overall_risk_score,
            "horizon_days": days,
            "liquidity_status": horizons_snapshots.get(str(days), {}).get("classification", {}).get("liquidity_status", "SAFE"),
            "currencies_at_risk": currencies_at_risk,
            "exposure_direction": exposure_direction,
            "requires_intervention": requires_intervention,
            "priority": "HIGH" if requires_intervention else "LOW",
            "candidate_actions": []  # Open door for future Layer 3 Decision Engine
        }

        # Dashboard KPIs
        current_cash = float(engine.starting_balance)
        min_projected_cash = float(min(p["baseline"] for p in risk_band))
        worst_tail_cash = float(min(p["p5"] for p in risk_band))
        fx_exposure_base = float(sum(abs(e.net_exposure_base_ccy) for e in raw_exposures))
        
        # 90D through horizon breach variables
        snap_90 = horizons_snapshots.get("90", {})
        th_90 = snap_90.get("through_horizon", {})
        first_breach_date = th_90.get("first_breach_date", None)
        days_to_breach = th_90.get("days_to_first_breach", None)

        dashboard_kpis = {
            "current_cash": current_cash,
            "min_projected_cash": min_projected_cash,
            "worst_tail_cash": worst_tail_cash,
            "fx_exposure_base": fx_exposure_base,
            "first_breach_date": first_breach_date,
            "days_to_breach": days_to_breach,
            "overall_risk_level": overall_risk_level,
            "overall_risk_score": overall_risk_score,
            "risk_trajectory": trajectory,
            "risk_pressure": risk_pressure
        }

        # Chart annotations
        chart_annotations = {
            "danger_threshold": danger_threshold,
            "first_breach_date": first_breach_date,
            "30D_date": risk_band[29]["date"] if len(risk_band) >= 30 else None,
            "60D_date": risk_band[59]["date"] if len(risk_band) >= 60 else None,
            "90D_date": risk_band[89]["date"] if len(risk_band) >= 90 else None
        }

        return {
            "model_version": "risk_classifier_v2",
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
            "overall_risk_level": overall_risk_level,
            "overall_risk_score": overall_risk_score,
            "risk_trajectory": trajectory,
            "risk_pressure": risk_pressure,
            "horizons": horizons_snapshots,
            "horizon_comparison": horizon_comparison_list,
            "exposures": exposures_formatted,
            "dashboard_kpis": dashboard_kpis,
            "chart_annotations": chart_annotations,
            "decision_context": decision_context,
            "risk_band": risk_band
        }

    def _classify_horizon(
        self,
        horizon_days: int,
        pit_data: Dict[str, Any],
        horizon_slice: List[Dict[str, Any]],
        danger_threshold: float
    ) -> HorizonSnapshot:
        """
        Classifies a single forecast day snapshot and through-horizon period deterministically.
        """
        # 1. Calculate Point-In-Time (PIT) metrics
        pit_baseline = float(pit_data.get("baseline", 0.0))
        pit_p5 = float(pit_data.get("p5", 0.0))
        pit_p50 = float(pit_data.get("p50", 0.0))
        pit_p95 = float(pit_data.get("p95", 0.0))
        pit_dt = pit_data.get("date", "")
        eps = 1e-9

        pit_band_width = max(0.0, pit_p95 - pit_p5)
        pit_downside = max(0.0, pit_baseline - pit_p5)
        pit_downside_pct = pit_downside / max(abs(pit_baseline), eps)

        point_in_time = {
            "date": pit_dt,
            "baseline": round(pit_baseline, 2),
            "p5": round(pit_p5, 2),
            "p50": round(pit_p50, 2),
            "p95": round(pit_p95, 2),
            "band_width": round(pit_band_width, 2),
            "downside_amount": round(pit_downside, 2),
            "downside_pct": round(pit_downside_pct, 4)
        }

        # 2. Calculate Through-Horizon (TH) metrics
        minimum_p5 = float(min(pt["p5"] for pt in horizon_slice))
        minimum_p50 = float(min(pt["p50"] for pt in horizon_slice))
        maximum_band_width = float(max(pt["p95"] - pt["p5"] for pt in horizon_slice))
        maximum_downside = float(max(pt["baseline"] - pt["p5"] for pt in horizon_slice))
        
        # Max downside percentage day-by-day
        maximum_downside_pct = float(max(
            (pt["baseline"] - pt["p5"]) / max(abs(pt["baseline"]), eps)
            for pt in horizon_slice
        ))

        # Max band width percentage day-by-day
        max_band_pct = float(max(
            (pt["p95"] - pt["p5"]) / max(abs(pt["baseline"]), eps)
            for pt in horizon_slice
        ))

        minimum_liquidity_buffer = minimum_p5 - danger_threshold
        minimum_liquidity_buffer_pct = minimum_liquidity_buffer / max(abs(danger_threshold), eps)

        # Breach metrics
        breach_count = 0
        first_breach_date: Optional[str] = None
        days_to_first_breach: Optional[int] = None

        for idx, pt in enumerate(horizon_slice):
            if pt["p5"] < danger_threshold:
                breach_count += 1
                if first_breach_date is None:
                    first_breach_date = pt["date"]
                    days_to_first_breach = idx + 1

        risk_persistence = float(breach_count / horizon_days)

        through_horizon = {
            "minimum_p5": round(minimum_p5, 2),
            "minimum_p50": round(minimum_p50, 2),
            "maximum_band_width": round(maximum_band_width, 2),
            "maximum_downside": round(maximum_downside, 2),
            "maximum_downside_pct": round(maximum_downside_pct, 4),
            "minimum_liquidity_buffer": round(minimum_liquidity_buffer, 2),
            "minimum_liquidity_buffer_pct": round(minimum_liquidity_buffer_pct, 4),
            "first_breach_date": first_breach_date,
            "breach_count": breach_count,
            "risk_persistence": round(risk_persistence, 4),
            "days_to_first_breach": days_to_first_breach
        }

        # 3. Classifications (Grounded entirely on THROUGH-HORIZON metrics)
        
        # Liquidity Status (SAFE, WATCH, BREACH)
        if minimum_p5 < danger_threshold:
            liquidity_status = "BREACH"
        elif minimum_p5 >= danger_threshold and minimum_liquidity_buffer < (danger_threshold * self.config.watch_buffer_pct):
            liquidity_status = "WATCH"
        else:
            liquidity_status = "SAFE"

        # FX Risk Level (LOW, MEDIUM, HIGH)
        if maximum_downside_pct >= self.config.high_downside_pct or max_band_pct >= self.config.high_band_pct:
            fx_risk_level = "HIGH"
        elif maximum_downside_pct >= self.config.medium_downside_pct or max_band_pct >= self.config.medium_band_pct:
            fx_risk_level = "MEDIUM"
        else:
            fx_risk_level = "LOW"

        # Risk score component calculation (deterministic 0-100 score)
        # Components: Downside (40%), Liquidity Proximity (40%), Volatility Uncertainty (20%)
        downside_score = (maximum_downside_pct / self.config.high_downside_pct) * 40.0
        downside_score = min(40.0, max(0.0, downside_score))

        if liquidity_status == "BREACH":
            liquidity_score = 40.0
        else:
            # Scale score based on buffer
            buffer_limit = danger_threshold * self.config.watch_buffer_pct
            if buffer_limit > 0:
                dist_to_threshold = minimum_p5 - danger_threshold
                liquidity_score = (1.0 - (dist_to_threshold / buffer_limit)) * 40.0
            else:
                liquidity_score = 0.0
            liquidity_score = min(40.0, max(0.0, liquidity_score))

        uncertainty_score = (max_band_pct / self.config.high_band_pct) * 20.0
        uncertainty_score = min(20.0, max(0.0, uncertainty_score))

        raw_score = downside_score + liquidity_score + uncertainty_score
        risk_score = int(round(raw_score))
        risk_score = min(100, max(0, risk_score))

        # Check for mathematical correctness rules: if TH min_p5 breaches, level must be HIGH and score >= 67
        if liquidity_status == "BREACH":
            overall_risk_level = "HIGH"
            if risk_score < 67:
                risk_score = 67
        else:
            if risk_score >= 67:
                overall_risk_level = "HIGH"
            elif risk_score >= 34:
                overall_risk_level = "MEDIUM"
            else:
                overall_risk_level = "LOW"

        classification = {
            "fx_risk_level": fx_risk_level,
            "liquidity_status": liquidity_status,
            "overall_risk_level": overall_risk_level,
            "risk_score": risk_score
        }

        # 4. Generate Business Explanation
        explanation = self._formulate_explanation(
            horizon_days, overall_risk_level, liquidity_status,
            maximum_downside_pct, minimum_liquidity_buffer, danger_threshold,
            first_breach_date, breach_count, pit_p5, pit_baseline
        )

        return HorizonSnapshot(
            horizon_days=horizon_days,
            point_in_time=point_in_time,
            through_horizon=through_horizon,
            classification=classification,
            explanation=explanation
        )

    def _formulate_explanation(
        self,
        horizon_days: int,
        overall_risk_level: str,
        liquidity_status: str,
        max_downside_pct: float,
        min_liquidity_buffer: float,
        danger_threshold: float,
        first_breach_date: Optional[str],
        breach_count: int,
        terminal_p5: float,
        terminal_baseline: float
    ) -> str:
        """
        Formulates a deterministic explanation based on metrics. No LLM used.
        """
        desc = f"At the {horizon_days}-day planning horizon, "

        if liquidity_status == "BREACH":
            # Check for recovery scenario (terminal p5 is safe, but breach occurred earlier)
            if terminal_p5 >= danger_threshold:
                return desc + (
                    f"the cash projection recovers to ${terminal_p5:,.2f} by the horizon end, "
                    f"but the simulated lower-tail scenario breaches the liquidity floor on {first_breach_date} "
                    f"and remains in breach for {breach_count} forecast days."
                )
            else:
                return desc + (
                    f"the lower-tail cash projection falls below the safety floor by ${abs(min_liquidity_buffer):,.2f} "
                    f"on {first_breach_date}, creating a potential liquidity shortfall."
                )
        
        elif liquidity_status == "WATCH":
            return desc + (
                f"FX volatility is material (max downside deviation: {max_downside_pct * 100:.1f}%), and the "
                f"simulated lower-tail cash projection approaches the safety floor within ${min_liquidity_buffer:,.2f}."
            )

        else:  # SAFE
            return desc + (
                f"the simulated lower-tail cash position remains comfortably above the liquidity floor throughout the horizon, "
                f"with limited modeled FX downside ({max_downside_pct * 100:.1f}% max deviation)."
            )

    def _calculate_pit_score(self, pit_data: Dict[str, Any], danger_threshold: float) -> int:
        """
        Calculates a point-in-time (PIT) risk score on a specific forecast day.
        """
        baseline = float(pit_data.get("baseline", 0.0))
        p5 = float(pit_data.get("p5", 0.0))
        p95 = float(pit_data.get("p95", 0.0))
        eps = 1e-9

        downside = max(0.0, baseline - p5)
        downside_pct = downside / max(abs(baseline), eps)
        band_width_pct = max(0.0, p95 - p5) / max(abs(baseline), eps)

        downside_score = (downside_pct / self.config.high_downside_pct) * 40.0
        downside_score = min(40.0, max(0.0, downside_score))

        if p5 < danger_threshold:
            liquidity_score = 40.0
        else:
            buffer_limit = danger_threshold * self.config.watch_buffer_pct
            if buffer_limit > 0:
                dist_to_threshold = p5 - danger_threshold
                liquidity_score = (1.0 - (dist_to_threshold / buffer_limit)) * 40.0
            else:
                liquidity_score = 0.0
            liquidity_score = min(40.0, max(0.0, liquidity_score))

        uncertainty_score = (band_width_pct / self.config.high_band_pct) * 20.0
        uncertainty_score = min(20.0, max(0.0, uncertainty_score))

        raw_score = downside_score + liquidity_score + uncertainty_score
        score = int(round(raw_score))
        return min(100, max(0, score))
