from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional

class OCENBorrower(BaseModel):
    entity_name: str
    gstin: str
    pan: str

class OCENCreditDecision(BaseModel):
    status: str
    indicative_supportable_amount: Decimal
    sanctioned_amount: Optional[Decimal] = None
    currency: str
    tenure_months: int
    interest_rate: float
    repayment: str
    conditions: List[str]
    covenants: List[str]
    reason_codes: List[str]

class OCENEvidence(BaseModel):
    gstr1_revenue: Optional[Decimal]
    bank_inflows: Optional[Decimal]
    variance_percentage: Optional[Decimal]
    integrity_status: str
    evidence_ids: List[str]

class OCENAudit(BaseModel):
    audit_hash: str
    package_hash: str
    generated_by: str

class OCENExportResponse(BaseModel):
    schema_version: str
    timestamp: str
    assessment_id: str
    package_id: str
    case_version: str
    consent_artefact_reference: str
    product: str
    prototype_interoperability_payload: bool
    interoperability_disclaimer: str
    limitations: str
    borrower: OCENBorrower
    credit_decision: OCENCreditDecision
    evidence: OCENEvidence
    audit: OCENAudit
    engine_versions: dict
