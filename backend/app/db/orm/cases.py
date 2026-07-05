import uuid
from sqlalchemy import (
    String,
    Integer,
    JSON,
    ForeignKey,
    Enum,
    Numeric,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..base import Base
import enum
from datetime import datetime, timezone
from .org import ProductType


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
    RECOMMEND_AS_REQUESTED = "RECOMMEND_AS_REQUESTED"
    RECOMMEND_ALTERNATIVE_STRUCTURE = "RECOMMEND_ALTERNATIVE_STRUCTURE"
    REQUEST_ADDITIONAL_EVIDENCE = "REQUEST_ADDITIONAL_EVIDENCE"
    RECOMMEND_ENHANCED_DUE_DILIGENCE = "RECOMMEND_ENHANCED_DUE_DILIGENCE"
    RECOMMEND_DECLINE = "RECOMMEND_DECLINE"


class IdempotencyStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"


class Business(Base):
    __tablename__ = "businesss"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = mapped_column(String, unique=True, index=True, nullable=False)
    legal_name = mapped_column(String, nullable=False)
    sector = mapped_column(String, nullable=False)

    cases = relationship("Case", back_populates="business")


class Case(Base):
    __tablename__ = "cases"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id_fk = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesss.id"), nullable=False
    )
    currency = mapped_column(String, default="INR", nullable=False)
    requested_amount = mapped_column(Numeric(20, 2, asdecimal=True), nullable=False)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus), default=CaseStatus.INITIATED, nullable=False
    )
    recommendation: Mapped[SystemRecommendation | None] = mapped_column(
        Enum(SystemRecommendation), nullable=True
    )
    analyst_recommendation: Mapped[AnalystRecommendationAction | None] = mapped_column(
        Enum(AnalystRecommendationAction), nullable=True
    )
    human_decision: Mapped[HumanDecisionAction | None] = mapped_column(
        Enum(HumanDecisionAction), nullable=True
    )

    # BOLA / Access Control
    originating_branch_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    assigned_relationship_manager_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    assigned_credit_analyst_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    assigned_sanctioning_authority_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    requested_product: Mapped[ProductType] = mapped_column(
        Enum(ProductType), nullable=False
    )

    # Financial aggregate cache (calculated from features)
    monthly_revenue_inr = mapped_column(Numeric(20, 2, asdecimal=True), nullable=True)
    dscr = mapped_column(Numeric(12, 6, asdecimal=True), nullable=True)
    cash_buffer_days = mapped_column(Integer, nullable=True)

    # Scores
    financial_health_score = mapped_column(Numeric(5, 2, asdecimal=True), nullable=True)
    data_confidence_score = mapped_column(Numeric(5, 2, asdecimal=True), nullable=True)
    resilience_score = mapped_column(Numeric(5, 2, asdecimal=True), nullable=True)

    # Optimistic Concurrency
    version = mapped_column(Integer, default=1, nullable=False)

    business = relationship("Business", back_populates="cases")
    audit_events = relationship("AuditEvent", back_populates="case")
    originating_branch = relationship("Branch", back_populates="cases")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    event_sequence = mapped_column(Integer, nullable=False)
    event_type = mapped_column(String, nullable=False)
    actor = mapped_column(String, nullable=False)
    actor_role = mapped_column(String, nullable=False)

    # Idempotency and Audit
    idempotency_record_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("idempotency_records.id"), nullable=True
    )
    metadata_json = mapped_column(JSON, default=dict)

    # Required for tamper-evident audit chain
    prior_case_version = mapped_column(Integer, nullable=True)
    resulting_case_version = mapped_column(Integer, nullable=True)
    prior_event_hash = mapped_column(String, nullable=True)
    event_hash = mapped_column(String, nullable=True)
    reason = mapped_column(String, nullable=True)

    audit_schema_version = mapped_column(Integer, default=1, nullable=False)
    hash_algorithm = mapped_column(String, default="sha256", nullable=False)
    correlation_id = mapped_column(String, nullable=True)
    model_version = mapped_column(String, nullable=True)
    policy_version = mapped_column(String, nullable=True)

    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    case = relationship("Case", back_populates="audit_events")

    __table_args__ = (
        UniqueConstraint("case_id", "event_sequence", name="uq_audit_case_sequence"),
    )


class IdempotencyRecord(Base):
    """Persistent records for tracking idempotent operations."""

    __tablename__ = "idempotency_records"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = mapped_column(String, index=True, nullable=False)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    case_id = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)
    action = mapped_column(String, nullable=False)
    request_hash = mapped_column(String, nullable=False)
    status = mapped_column(
        Enum(IdempotencyStatus), nullable=False, default=IdempotencyStatus.IN_PROGRESS
    )
    response_status = mapped_column(Integer, nullable=True)
    response_payload = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "case_id",
            "action",
            "idempotency_key",
            name="uq_idempotency_scoped",
        ),
    )
