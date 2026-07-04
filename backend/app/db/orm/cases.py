import uuid
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, Enum, Boolean, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import Base
import enum
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

class CaseStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    EVIDENCE_GATHERING = "EVIDENCE_GATHERING"
    ASSESSMENT_COMPLETED = "ASSESSMENT_COMPLETED"
    DECISION_PENDING = "DECISION_PENDING"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HUMAN_DECLINED = "HUMAN_DECLINED"
    HUMAN_DEFERRED = "HUMAN_DEFERRED"

class SystemRecommendation(str, enum.Enum):
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    CONDITIONAL_OFFER = "CONDITIONAL_OFFER"
    ADDITIONAL_EVIDENCE_REQUIRED = "ADDITIONAL_EVIDENCE_REQUIRED"
    ENHANCED_DUE_DILIGENCE = "ENHANCED_DUE_DILIGENCE"
    DECLINE_RECOMMENDED = "DECLINE_RECOMMENDED"

class HumanDecisionAction(str, enum.Enum):
    APPROVE_AS_REQUESTED = "APPROVE_AS_REQUESTED"
    APPROVE_ALTERNATIVE_STRUCTURE = "APPROVE_ALTERNATIVE_STRUCTURE"
    DEFER_FOR_EVIDENCE = "DEFER_FOR_EVIDENCE"
    ESCALATE_FOR_DUE_DILIGENCE = "ESCALATE_FOR_DUE_DILIGENCE"
    DECLINE_AFTER_HUMAN_REVIEW = "DECLINE_AFTER_HUMAN_REVIEW"

class AnalystRecommendationAction(str, enum.Enum):
    RECOMMEND_ALTERNATIVE_STRUCTURE = "RECOMMEND_ALTERNATIVE_STRUCTURE"
    REQUEST_ADDITIONAL_EVIDENCE = "REQUEST_ADDITIONAL_EVIDENCE"
    RECOMMEND_ENHANCED_DUE_DILIGENCE = "RECOMMEND_ENHANCED_DUE_DILIGENCE"

class Business(Base):
    __tablename__ = "businesss"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(String, unique=True, index=True, nullable=False)
    legal_name = Column(String, nullable=False)
    sector = Column(String, nullable=False)
    
    cases = relationship("Case", back_populates="business")

class Case(Base):
    __tablename__ = "cases"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id_fk = Column(UUID(as_uuid=True), ForeignKey("businesss.id"), nullable=False)
    requested_facility_type = Column(String, nullable=False)
    requested_amount = Column(Numeric(20, 2, asdecimal=True), nullable=False)
    status = Column(Enum(CaseStatus), default=CaseStatus.INITIATED, nullable=False)
    recommendation = Column(Enum(SystemRecommendation), nullable=True)
    analyst_recommendation = Column(Enum(AnalystRecommendationAction), nullable=True)
    human_decision = Column(Enum(HumanDecisionAction), nullable=True)
    
    # Financial aggregate cache (calculated from features)
    monthly_revenue_inr = Column(Numeric(20, 2, asdecimal=True), nullable=True)
    dscr = Column(Numeric(12, 6, asdecimal=True), nullable=True)
    cash_buffer_days = Column(Integer, nullable=True)
    
    # Scores
    financial_health_score = Column(Numeric(5, 2, asdecimal=True), nullable=True)
    data_confidence_score = Column(Numeric(5, 2, asdecimal=True), nullable=True)
    resilience_score = Column(Numeric(5, 2, asdecimal=True), nullable=True)
    
    # Optimistic Concurrency
    version = Column(Integer, default=1, nullable=False)

    business = relationship("Business", back_populates="cases")
    audit_events = relationship("AuditEvent", back_populates="case")

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    event_type = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    actor_role = Column(String, nullable=False)
    correlation_id = Column(String, index=True)
    idempotency_key = Column(String, unique=True, nullable=True)
    metadata_json = Column(JSON, default={})
    created_at = Column(DateTime, nullable=False, default=utc_now)
    
    case = relationship("Case", back_populates="audit_events")
