"""
================================================================================
EXECUTION ENGINE V2 DATA & PYDANTIC RESPONSE MODELS
================================================================================
Defines type-safe Pydantic contracts for quotes, confirmations, executions,
verifications, timeline events, and reforecast impact snapshots.
================================================================================
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ExecutionStateV2(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    APPROVED = "APPROVED"
    QUOTE_REQUESTED = "QUOTE_REQUESTED"
    QUOTE_READY = "QUOTE_READY"
    QUOTE_EXPIRED = "QUOTE_EXPIRED"
    QUOTE_REJECTED = "QUOTE_REJECTED"
    CONFIRMED = "CONFIRMED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    CANCELLED = "CANCELLED"


class QuoteResponse(BaseModel):
    quote_id: str
    action_id: str
    transaction_id: str
    source_currency: str
    target_currency: str
    source_amount: float
    target_amount: float
    rate: float
    fee: float
    delivery_estimate: str
    provider: str
    status: str
    created_at: str
    expires_at: str
    is_expired: bool = False
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


class QuoteConfirmationRequest(BaseModel):
    quote_id: str


class QuoteConfirmationResponse(BaseModel):
    action_id: str
    transaction_id: str
    quote_id: str
    status: str
    confirmed_at: str
    message: str


class ExecutionRequest(BaseModel):
    idempotency_key: Optional[str] = None


class ExecutionTimelineEvent(BaseModel):
    event: str
    timestamp: str
    actor: str
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    verified: bool
    status: str
    provider_reference: Optional[str] = None
    verified_at: str
    checks_passed: Dict[str, bool] = Field(default_factory=dict)
    discrepancies: List[str] = Field(default_factory=list)


class RiskSnapshotMetrics(BaseModel):
    risk_level: str
    risk_score: int
    p5: float
    liquidity_status: str
    trajectory: Optional[str] = None
    exposure_amount: Optional[float] = None


class ReforecastImpact(BaseModel):
    risk_score_change: int
    p5_change: float
    liquidity_status_before: str
    liquidity_status_after: str
    is_breach_mitigated: bool
    risk_reduction_description: str


class ExecutionImpactResponse(BaseModel):
    reforecast_id: str
    execution_id: str
    action_id: str
    completed_at: str
    before: RiskSnapshotMetrics
    after: RiskSnapshotMetrics
    impact: ReforecastImpact


class ExecutionDetailResponse(BaseModel):
    execution_id: str
    action_id: str
    transaction_id: str
    provider: str
    provider_reference: Optional[str] = None
    quote_id: Optional[str] = None
    idempotency_key: str
    status: str
    requested_at: str
    approved_at: Optional[str] = None
    quoted_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    executing_at: Optional[str] = None
    executed_at: Optional[str] = None
    verified_at: Optional[str] = None
    failure_reason: Optional[str] = None
    quote: Optional[QuoteResponse] = None
    verification: Optional[VerificationResult] = None
    reforecast: Optional[ExecutionImpactResponse] = None
    timeline: List[ExecutionTimelineEvent] = Field(default_factory=list)
    allowed_next_actions: List[str] = Field(default_factory=list)


class AllowedNextActionsResponse(BaseModel):
    action_id: str
    current_status: str
    allowed_next_actions: List[str]
