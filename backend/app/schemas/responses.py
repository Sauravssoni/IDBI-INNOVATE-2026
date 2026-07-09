from pydantic import BaseModel
from typing import List, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class CaseListItem(BaseModel):
    id: UUID
    business_id: str
    business_name: str
    status: str
    requested_amount: Decimal
    currency: str
    created_at: datetime
    assigned_analyst: str
    assigned_rm: str


class CaseDetailResponse(BaseModel):
    id: UUID
    business_id: str
    business_name: str
    status: str
    requested_amount: Decimal
    currency: str
    created_at: datetime
    assigned_analyst: str
    assigned_rm: str
    industry: str
    region: str
    branch: str
    version: int


class AssessmentHistoryItem(BaseModel):
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
    id: UUID
    case_id: UUID
    event_type: str
    actor: str
    created_at: datetime
    event_hash: str


class CreditTwinResponse(BaseModel):
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


class ReconciliationResponse(BaseModel):
    total_bank_credits: Decimal
    total_gst_sales: Decimal
    reconciliation_match_percent: Decimal
    status: str
    checks: List[Any]


class DashboardSummaryResponse(BaseModel):
    total_cases: int
    pending_evaluations: int
    pending_sanctions: int
    approved_cases: int
    total_approved_amount: Decimal


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
