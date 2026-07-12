from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import logging

from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.db.orm.users import User
from app.db.orm.cases import Case, DecisionPackage, AssessmentSnapshot
from app.schemas.ocen import OCENExportResponse, OCENBorrower, OCENCreditDecision, OCENEvidence, OCENAudit

router = APIRouter(prefix="/api/cases", tags=["ocen"])
logger = logging.getLogger(__name__)

POLICY_VERSION = "2.1.0-secure"
CALCULATION_VERSION = "1.8.4"
SCORING_VERSION = "3.0.2"
PASSPORT_ENGINE_VERSION = "1.0.0"


@router.get(
    "/{case_id}/ocen-export",
    response_model=OCENExportResponse,
    description="Export OCEN/ULI prototype interoperability payload from a sealed package.",
)
def get_ocen_export(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        cid = UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case ID")

    case_db = db.query(Case).filter(Case.id == cid).first()
    if not case_db:
        raise HTTPException(status_code=404, detail="Case not found")

    pkg = (
        db.query(DecisionPackage)
        .filter(DecisionPackage.case_id == case_db.id)
        .order_by(DecisionPackage.created_at.desc())
        .first()
    )
    if not pkg:
        raise HTTPException(status_code=404, detail="No decision package found. Cannot export.")

    snapshot = (
        db.query(AssessmentSnapshot)
        .filter(AssessmentSnapshot.assessment_id == pkg.assessment_id)
        .first()
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="Assessment snapshot not found")

    features = snapshot.feature_snapshot
    assessment = snapshot.canonical_assessment_json
    
    # Extract values
    supportable = Decimal(str(assessment.get("supportable_amount", 0.0)))
    status_str = case_db.status.value if hasattr(case_db.status, "value") else str(case_db.status)
    sanctioned = Decimal(str(case_db.approved_amount)) if status_str == "SANCTIONED" and case_db.approved_amount else None

        
    conditions = [c.get("condition_text") for c in assessment.get("conditions", [])] if assessment.get("conditions") else []
    covenants = [c.get("covenant_text") for c in assessment.get("covenants", [])] if assessment.get("covenants") else []
    reason_codes = assessment.get("policy_reason_codes", ["NO_CONSTRAINT_FLAGGED"])

    gstr1_revenue = Decimal(str(features.get("total_revenue", 0.0)))
    bank_inflows = Decimal(str(features.get("total_bank_credits", 0.0)))
    variance = Decimal(str(features.get("reconciliation_match_percent", 0.0)))
    integrity = assessment.get("integrity_state", "FAILED")
    ev_ids = [str(x) for x in assessment.get("evidence_ids", [])]

    business = case_db.business

    # Generate the OCEN export
    return OCENExportResponse(
        schema_version="2.0-CANONICAL",
        timestamp=datetime.utcnow().isoformat() + "Z",
        assessment_id=str(pkg.assessment_id),
        package_id=str(pkg.id),
        case_version=str(case_db.version),
        consent_artefact_reference=f"CONSENT-ART-{business.business_id}",
        product=case_db.requested_product.value if hasattr(case_db.requested_product, "value") else str(case_db.requested_product),
        prototype_interoperability_payload=True,
        interoperability_disclaimer="Not certified by OCEN or ULI. Hackathon interoperability prototype.",
        limitations="Indicative assessment only. Human sanction required. Synthetic validation.",
        borrower=OCENBorrower(
            entity_name=business.legal_name,
            gstin=getattr(business, "gstin", "UNAVAILABLE") or "UNAVAILABLE",
            pan=getattr(business, "pan", "UNAVAILABLE") or "UNAVAILABLE"
        ),
        credit_decision=OCENCreditDecision(
            status=status_str,
            indicative_supportable_amount=supportable,
            sanctioned_amount=case_db.approved_amount if status_str == "SANCTIONED" else None,
            currency=case_db.currency,
            tenure_months=getattr(case_db, 'proposed_tenor_months', 36) or 36,
            interest_rate=float(getattr(case_db, 'proposed_annual_rate', 13.5) or 13.5),
            repayment="Monthly EMI",
            conditions=conditions,
            covenants=covenants,
            reason_codes=reason_codes
        ),
        evidence=OCENEvidence(
            gstr1_revenue=gstr1_revenue,
            bank_inflows=bank_inflows,
            variance_percentage=variance,
            integrity_status=integrity,
            evidence_ids=ev_ids
        ),
        audit=OCENAudit(
            audit_hash=pkg.package_hash if pkg.package_hash else "",
            package_hash=pkg.package_hash if pkg.package_hash else "",
            generated_by="system"
        ),
        engine_versions={
            "policy": POLICY_VERSION,
            "calculation": CALCULATION_VERSION,
            "scoring": SCORING_VERSION,
            "passport": PASSPORT_ENGINE_VERSION
        }
    )
