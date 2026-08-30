from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class RiskBandPoint(BaseModel):
    date: str
    baseline: float
    p5: float
    p50: float
    p95: float

class PointInTimeMetrics(BaseModel):
    date: str
    baseline: float
    p5: float
    p50: float
    p95: float
    band_width: float
    downside_amount: float
    downside_pct: float

class ThroughHorizonMetrics(BaseModel):
    minimum_p5: float
    minimum_p50: float
    maximum_band_width: float
    maximum_downside: float
    maximum_downside_pct: float
    minimum_liquidity_buffer: float
    minimum_liquidity_buffer_pct: float
    first_breach_date: Optional[str] = None
    breach_count: int
    risk_persistence: float
    days_to_first_breach: Optional[int] = None

class HorizonClassification(BaseModel):
    fx_risk_level: str
    liquidity_status: str
    overall_risk_level: str
    risk_score: int

class HorizonSnapshotSchema(BaseModel):
    horizon_days: int
    point_in_time: PointInTimeMetrics
    through_horizon: ThroughHorizonMetrics
    classification: HorizonClassification
    explanation: str

class CurrencyExposureSchema(BaseModel):
    currency: str
    gross_payable: float
    gross_receivable: float
    net_exposure: float
    net_exposure_base_ccy: float
    direction: str

class DashboardKPI(BaseModel):
    current_cash: float
    min_projected_cash: float
    worst_tail_cash: float
    fx_exposure_base: float
    first_breach_date: Optional[str] = None
    days_to_breach: Optional[int] = None
    overall_risk_level: str
    overall_risk_score: int
    risk_trajectory: str
    risk_pressure: str

class ChartAnnotations(BaseModel):
    danger_threshold: float
    first_breach_date: Optional[str] = None
    d30_date: Optional[str] = Field(None, alias="30D_date")
    d60_date: Optional[str] = Field(None, alias="60D_date")
    d90_date: Optional[str] = Field(None, alias="90D_date")

    class Config:
        populate_by_name = True
        alias_generator = lambda string: string

class DecisionContextSchema(BaseModel):
    risk_level: str
    risk_score: int
    horizon_days: int
    liquidity_status: str
    currencies_at_risk: List[str]
    exposure_direction: Dict[str, str]
    requires_intervention: bool
    priority: str
    candidate_actions: List[Any]

class RiskClassificationResponse(BaseModel):
    model_version: str
    method: str
    inputs: List[str]
    forecast_days: int
    overall_risk_level: str
    overall_risk_score: int
    risk_trajectory: str
    risk_pressure: str
    horizons: Dict[str, HorizonSnapshotSchema]
    horizon_comparison: List[Dict[str, Any]]
    exposures: List[CurrencyExposureSchema]
    dashboard_kpis: DashboardKPI
    chart_annotations: ChartAnnotations
    decision_context: DecisionContextSchema
    risk_band: List[RiskBandPoint]


class ActionRecommendationSchema(BaseModel):
    transaction_id: str
    action: str
    currency: str
    amount: float
    direction: str
    priority: str
    risk_level: str
    risk_score: int
    days_to_due: Optional[int] = None
    requires_approval: bool
    reason: str
    reason_codes: List[str]
    warnings: List[str]
    amount_base: float
    recommended_amount: Optional[float] = None
    expected_impact: Optional[Dict[str, Any]] = None


class DecisionKPI(BaseModel):
    total_foreign_exposures: int
    actions_required: int
    high_priority_actions: int
    medium_priority_actions: int
    monitor_only: int


class DecisionSummary(BaseModel):
    risk_level: str
    risk_score: int
    liquidity_status: str
    trajectory: str
    requires_intervention: bool


class DecisionEngineContext(BaseModel):
    currencies_at_risk: List[str]
    exposure_direction: Dict[str, str]


class DecisionResponse(BaseModel):
    model_version: str
    decision_policy_version: str
    overall: DecisionSummary
    decision_kpis: DecisionKPI
    recommendations: List[ActionRecommendationSchema]
    decision_context: DecisionEngineContext


class RecommendationLifecycleSchema(BaseModel):
    action_id: str
    transaction_id: str
    action_type: str
    priority: str
    risk_score: int
    confidence: int
    reason: str
    risk_before: str
    risk_after_estimate: str
    estimated_action_cost: float
    estimated_inaction_cost: float
    status: str
    created_at: str
    updated_at: str
