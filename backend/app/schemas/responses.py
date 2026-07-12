from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Any, Dict
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


class AssessmentActionContext(BaseModel):
    allowed: bool
    blocked_reason_code: Optional[str] = None
    message: Optional[str] = None


class AnalystActionContext(BaseModel):
    allowed: bool
    suggested_analyst_action: Optional[str] = None
    blocked_reason_code: Optional[str] = None
    message: Optional[str] = None


class HumanActionContext(BaseModel):
    allowed: bool
    suggested_human_action: Optional[str] = None
    allowed_human_actions: Optional[List[str]] = None
    blocked_reason_code: Optional[str] = None
    message: Optional[str] = None


class AllowedActionsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    run_assessment: AssessmentActionContext
    submit_analyst_recommendation: AnalystActionContext
    record_human_decision: HumanActionContext
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
    independent_reamortization_dscr: Decimal | None = None
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
    model_config = ConfigDict(extra="allow")
    reconciliation_quality: Optional[Decimal] = None
    evidence_confidence: Optional[Decimal] = None
    source_coverage: Optional[Decimal] = None


class DecisionPackageAuditItem(BaseModel):
    event_type: str
    actor: str
    event_hash: str
    created_at: str


class DecisionPackageResponse(BaseModel):
    """
    DEPRECATED: Do not use for calculations or rendering components.
    Use AssessmentResultResponse for all authoritative data.
    """
    model_config = ConfigDict(extra="allow")
    case_id: str
    business_name: str
    requested_amount: Decimal
    requested_product: Optional[str] = None
    reconciliation: DecisionPackageReconciliation
    dscr: Optional[Decimal] = None
    current_dscr: Optional[Decimal] = None
    proposed_emi: Optional[Decimal] = None
    post_loan_dscr: Optional[Decimal] = None
    stressed_dscr: Optional[Decimal] = None
    binding_limit: Optional[Decimal] = None
    recommendation: Optional[str] = None
    reason_codes: List[str]
    conditions: List[str]
    offers: Optional[List[Dict[str, Any]]] = None
    limit_details: Optional[List[Dict[str, Any]]] = None
    evidence_passport: Optional[Dict[str, Any]] = None
    assessment_certainty: Optional[str] = None
    certainty_reasons: Optional[List[str]] = None
    peer_context: Optional[Dict[str, Any]] = None
    hindi_summary: Optional[Dict[str, Any]] = None
    policy_version: str
    calculation_version: str
    scoring_version: Optional[str] = "2.0-CANONICAL"
    financial_health_index: Optional[Decimal] = None
    vyapar_credit_health_score: Optional[int] = None
    score_range: Optional[Dict[str, Any]] = None

    fhi_breakdown: Optional[Dict[str, Any]] = None
    credit_score_disclaimer: Optional[str] = None
    calculation_evidence_ids: Optional[Dict[str, List[str]]] = None
    analyst_action: Optional[str] = None
    human_action: Optional[str] = None
    case_version: int
    audit_chain: List[DecisionPackageAuditItem]
    bankability_path: Optional[Dict[str, Any]] = None
    package_hash: Optional[str] = None

    # ADDED: Embed authoritative assessment
    assessment: Optional["AssessmentResultResponse"] = None

class AuditVerificationResponse(BaseModel):
    bola_verification_status: str
    cas_verification_status: str
    audit_chain_valid: bool
    analyst_event_status: str
    feature_event_status: Optional[str] = None
    recommendation_event_status: Optional[str] = None
    decision_event_status: Optional[str] = None
    human_decision_event_status: Optional[str] = None
    package_hash_valid: Optional[bool] = None
    authorization_scope_valid: Optional[bool] = None
    package_hash: Optional[str] = None
    audit_tip_hash: Optional[str] = None
    verification_version: Optional[str] = None
    reason: Optional[str] = None
    verified_at: datetime
    error_message: Optional[str] = None

class AuditChainResponse(BaseModel):
    items: List[DecisionPackageAuditItem]
    total_events: int
    verified: bool

class EvidencePassportResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

class CanonicalFeatureSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

class FinancialHealthPillarResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    score: int
    health_status: str
    positive_reason_codes: List[str] = Field(default_factory=list)
    adverse_reason_codes: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)

class AssessmentRangeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    min_amount: Decimal
    max_amount: Decimal

class ProductCapacityResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    product_name: str
    capacity: Decimal

class BindingConstraintResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    constraint_type: str
    reason: str

class StressScenarioResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    scenario_name: str
    impact: str

class BankabilityInterventionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    intervention_type: str
    description: str

class ConditionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    condition_text: str

class CovenantResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    covenant_text: str

class AssessmentResultResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    assessment_id: UUID
    case_id: UUID
    case_version: int
    generated_at: datetime

    consent_state: str
    evidence_passport: EvidencePassportResponse
    feature_snapshot: CanonicalFeatureSnapshotResponse

    financial_health_index: Decimal | None
    six_pillars: List[FinancialHealthPillarResponse]
    vyapar_credit_health_score: int | None
    assessment_range: AssessmentRangeResponse | None
    evidence_certainty: str
    integrity_state: str

    current_dscr: Decimal | None
    existing_debt_service: Decimal | None
    proposed_debt_service: Decimal | None
    proposed_emi: Decimal | None
    post_loan_dscr: Decimal | None
    stressed_dscr: Decimal | None

    requested_product: str
    requested_amount: Decimal
    product_capacities: List[ProductCapacityResponse]
    selected_product: str | None
    offers: Optional[List[Dict[str, Any]]] = None
    supportable_amount: Decimal | None
    binding_constraint: BindingConstraintResponse | None

    stress_results: List[StressScenarioResponse]
    bankability_interventions: List[BankabilityInterventionResponse]

    policy_recommendation: str
    policy_reason_codes: List[str]
    conditions: List[ConditionResponse]
    covenants: List[CovenantResponse]

    analyst_recommendation: str | None
    analyst_reason: str | None
    human_decision: str | None
    approved_amount: Decimal | None

    scoring_version: str
    calculation_version: str
    policy_version: str
    passport_version: str
    feature_schema_version: str

    evidence_ids: List[UUID]
    limitations: List[str]

class AnalystActionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    action: str
    reason: str
    timestamp: datetime

class HumanDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    decision: str
    reason: str
    timestamp: datetime

class AuditSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    events: int
    last_event: str

class BilingualSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    english: str
    hindi: str

class ExportLinksResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    json_url: str
    pdf_url: str

class IntegrityNode(BaseModel):
    id: str
    label: str
    type: str

class IntegrityEdge(BaseModel):
    source: str
    target: str
    relationship: str
    matched_identifiers: List[str]

class IntegrityGraphResult(BaseModel):
    status: str
    reason_code: str
    severity: str
    relationship_path: List[str]
    matched_identifiers: List[str]
    technical_explanation: str
    analyst_explanation: str
    evidence_ids: List[str]
    synthetic_demonstration: bool
    nodes: List[IntegrityNode]
    edges: List[IntegrityEdge]
