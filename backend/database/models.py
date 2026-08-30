"""
================================================================================
SQLALCHEMY ORM DATA MODELS
================================================================================
"""
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from backend.database.connection import Base

class FxRate(Base):
    __tablename__ = "fx_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    currency_pair = Column(String(10), nullable=False, index=True)
    currency = Column(String(10), nullable=True, index=True)
    date = Column(String(20), nullable=False, index=True)
    rate = Column(Float, nullable=False)
    source = Column(String(50), default="Frankfurter/ECB")

    __table_args__ = (
        UniqueConstraint("currency_pair", "date", name="uq_fx_rates_pair_date"),
        Index("ix_fx_rates_pair_date", "currency_pair", "date"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "currency_pair": self.currency_pair,
            "currency": self.currency,
            "date": self.date,
            "rate": self.rate,
            "source": self.source,
        }

class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(String(50), primary_key=True)
    date = Column(String(20), nullable=False)
    currency = Column(String(3), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    direction = Column(String(20), nullable=False)
    description = Column(String(255), default="")
    category = Column(String(100), default="uncategorized")
    status = Column(String(50), nullable=False, default="pending")
    demo_action = Column(String(50), nullable=True)
    demo_action_label = Column(String(100), nullable=True)

    recommendations = relationship("RecommendationModel", back_populates="transaction", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "currency": self.currency,
            "amount": self.amount,
            "direction": self.direction,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "demo_action": self.demo_action,
            "demo_action_label": self.demo_action_label,
        }

class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    currency_pair = Column(String(50), nullable=False, default="ALL")
    horizon_days = Column(Integer, nullable=False, default=90)
    input_params_json = Column(Text, nullable=False)
    output_json = Column(Text, nullable=False)

    explanations = relationship("AiExplanation", back_populates="simulation_run", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "run_timestamp": self.run_timestamp.isoformat() if self.run_timestamp else None,
            "currency_pair": self.currency_pair,
            "horizon_days": self.horizon_days,
            "input_params_json": self.input_params_json,
            "output_json": self.output_json,
        }

class AiExplanation(Base):
    __tablename__ = "ai_explanations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_run_id = Column(Integer, ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    explanation_text = Column(Text, nullable=False)
    risk_flags_json = Column(Text, nullable=True)
    model_used = Column(String(50), default="qwen2.5:7b-instruct")
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    simulation_run = relationship("SimulationRun", back_populates="explanations")

    def to_dict(self):
        return {
            "id": self.id,
            "simulation_run_id": self.simulation_run_id,
            "explanation_text": self.explanation_text,
            "risk_flags_json": self.risk_flags_json,
            "model_used": self.model_used,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }

class RiskSnapshotModel(Base):
    __tablename__ = "risk_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(String(50), nullable=False)
    horizon_days = Column(Integer, nullable=False)
    date = Column(String(20), nullable=False)
    point_in_time_json = Column(Text, nullable=False)
    through_horizon_json = Column(Text, nullable=False)
    classification_json = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)

class RecommendationModel(Base):
    __tablename__ = "recommendations"

    action_id = Column(String(50), primary_key=True)
    transaction_id = Column(String(50), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    risk_score = Column(Integer, nullable=False)
    confidence = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    reason_codes_json = Column(Text, nullable=False)
    warnings_json = Column(Text, nullable=False)
    amount_base = Column(Float, nullable=False)
    recommended_amount = Column(Float, nullable=True)
    risk_before = Column(String(20), default="LOW")
    risk_after_estimate = Column(String(20), default="LOW")
    estimated_action_cost = Column(Float, default=0.0)
    estimated_inaction_cost = Column(Float, default=0.0)
    status = Column(String(50), nullable=False)
    created_at = Column(String(50), nullable=False)
    updated_at = Column(String(50), nullable=False)

    transaction = relationship("TransactionModel", back_populates="recommendations")

class ApprovalModel(Base):
    __tablename__ = "approvals"

    approval_id = Column(String(50), primary_key=True)
    action_id = Column(String(50), ForeignKey("recommendations.action_id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False)
    actor = Column(String(100), nullable=False)
    timestamp = Column(String(50), nullable=False)

class ExecutionModel(Base):
    __tablename__ = "executions"

    execution_id = Column(String(50), primary_key=True)
    action_id = Column(String(50), ForeignKey("recommendations.action_id", ondelete="CASCADE"), nullable=False)
    quote_id = Column(String(100), nullable=True)
    rate = Column(Float, nullable=True)
    fee = Column(Float, nullable=True)
    source_amount = Column(Float, nullable=True)
    target_amount = Column(Float, nullable=True)
    status = Column(String(50), nullable=False)
    timestamp = Column(String(50), nullable=False)

class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False)
    action_id = Column(String(50), nullable=True)
    transaction_id = Column(String(50), nullable=True)
    timestamp = Column(String(50), nullable=False)
    actor = Column(String(100), nullable=False)
    old_state = Column(String(50), nullable=True)
    new_state = Column(String(50), nullable=True)
    metadata_json = Column(Text, nullable=True)
