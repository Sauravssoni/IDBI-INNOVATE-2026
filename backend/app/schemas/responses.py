from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class CaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    business_id: str
    business_name: str
    status: str
    requested_amount: Decimal
    currency: str
    created_at: datetime
    assigned_analyst: str
    assigned_rm: str
    requested_product: Optional[str] = None
    recommendation: Optional[str] = None
    analyst_recommendation: Optional[str] = None
    human_decision: Optional[str] = None


class CaseBusinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    business_id: str
    legal_name: str
    sector: str


class AllowedActionsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    run_assessment: bool
    submit_analyst_recommendation: bool
    record_human_decision: bool
    view_audit: bool


class CaseDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    business_id_fk: UUID
    business: CaseBusinessResponse
    requested_amount: Decimal
    requested_product: Optional[str] = None
    currency: str
    status: str
    recommendation: Optional[str] = None
    analyst_recommendation: Optional[str] = None
    human_decision: Optional[str] = None
    evaluation_result: Optional["EvaluationResultResponse"] = None
    allowed_actions: AllowedActionsResponse
    version: int
    created_at: datetime
    updated_at: datetime


class AssessmentHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    sequence: int
    event_type: str
    actor: str
    actor_role: str
    reason: str
    created_at: str
    recommendation: str
    binding_limit: Decimal | None
    dscr: Decimal | None
    policy_version: str
    calculation_version: str


class PortfolioAuditItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    case_id: UUID
    event_type: str
    actor: str
    created_at: datetime
    event_hash: str


class CreditTwinResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    case_id: UUID
    business_id: str
    dscr: Decimal | None
    calculation_version: str
    total_annual_revenue: Decimal
    binding_limit: Decimal | None
    recommendation: str | None
    source_coverage: Decimal | None
    evidence_confidence: Decimal | None
    reconciliation_quality: Decimal | None
    evaluated_at: str | None
    policy_version: Optional[str] = None


class ReconciliationCheck(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    check_id: str
    name: str
    status: str
    observed_value: Optional[Decimal] = None
    reference_value: Optional[Decimal] = None
    variance_amount: Optional[Decimal] = None
    variance_percentage: Optional[Decimal] = None
    evidence_references: Optional[List[str]] = None
    explanation: Optional[str] = None
    rule_version: Optional[str] = None


class ReconciliationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_bank_credits: Decimal
    total_gst_sales: Decimal
    reconciliation_match_percent: Decimal
    status: str
    checks: List[ReconciliationCheck]


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    active_cases: int
    total_requested_amount: Decimal
    awaiting_analyst: int
    awaiting_human_decision: int
    approved_cases: int
    approved_amount: Decimal
    declined_cases: int
    deferred_cases: int
    completed_human_reviews: int


class EvaluateResponseDecision(BaseModel):
    recommendation: Optional[str] = None
    binding_limit: Optional[Decimal] = None
    reason_codes: Optional[List[str]] = None

class EvaluateResponseFeatures(BaseModel):
    total_revenue: Optional[Decimal] = None
    total_obligations: Optional[Decimal] = None
    dscr: Optional[Decimal] = None

class EvaluateResponseScores(BaseModel):
    evidence_confidence: Optional[Decimal] = None
    reconciliation_quality: Optional[Decimal] = None

class EvaluateResponse(BaseModel):
    case_id: str
    business_name: str
    features: EvaluateResponseFeatures
    scores: EvaluateResponseScores
    decision: EvaluateResponseDecision


class EvaluationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")
    decision: Optional[EvaluateResponseDecision] = None
    features: Optional[EvaluateResponseFeatures] = None
    scores: Optional[EvaluateResponseScores] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class DecisionPackageReconciliation(BaseModel):
    reconciliation_quality: Optional[Decimal] = None
    evidence_confidence: Optional[Decimal] = None
    source_coverage: Optional[Decimal] = None

class DecisionPackageAuditItem(BaseModel):
    event_type: str
    actor: str
    event_hash: str
    created_at: str

class DecisionPackageResponse(BaseModel):
    case_id: str
    business_name: str
    requested_amount: Decimal
    requested_product: Optional[str] = None
    reconciliation: DecisionPackageReconciliation
    dscr: Optional[Decimal] = None
    binding_limit: Optional[Decimal] = None
    recommendation: Optional[str] = None
    reason_codes: List[str]
    conditions: List[str]
    policy_version: str
    calculation_version: str
    analyst_action: Optional[str] = None
    human_action: Optional[str] = None
    case_version: int
    audit_chain: List[DecisionPackageAuditItem]
