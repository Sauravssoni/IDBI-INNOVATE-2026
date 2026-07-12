from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.schemas.responses import (
    AssessmentHistoryItem,
    CreditTwinResponse,
    ReconciliationResponse,
)
from app.db.session import SessionLocal
from app.api.dependencies import get_current_user
from app.db.orm.users import User
from app.services.authz import can_view_case
from app.db.orm.evidence import (
    GSTPeriod,
    BankTransaction,
    Invoice,
    EmploymentPeriod,
    Obligation,
)
from app.db.orm.cases import AuditEvent, AssessmentSnapshot
from app.services.credit_twin import get_credit_twin
from app.services.reconciliation import run_reconciliation

router = APIRouter(prefix="/api/cases", tags=["evidence"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _build_metadata(r):
    return {
        "ingestion_mode": getattr(r, "ingestion_mode", None),
        "source_environment": getattr(r, "source_environment", None),
        "source_system": getattr(r, "source_system", None),
        "consent_id": getattr(r, "consent_id_fk", None),
        "data_connection_id": getattr(r, "data_connection_id_fk", None),
        "evidence_as_of": r.evidence_as_of.isoformat()
        if getattr(r, "evidence_as_of", None)
        else None,
        "received_at": r.received_at.isoformat()
        if getattr(r, "received_at", None)
        else None,
        "data_quality_status": getattr(r, "data_quality_status", None),
    }


@router.get("/{case_id}/evidence/gst")
def get_gst_evidence(
    case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, case_id)
    records = (
        db.query(GSTPeriod)
        .filter(GSTPeriod.business_id_fk == case.business_id_fk)
        .order_by(GSTPeriod.period_month.desc())
        .all()
    )
    return [
        {
            "period": r.period_month.isoformat(),
            "declared_revenue": float(r.declared_revenue),
            "tax_paid": float(r.tax_paid),
            "status": "FILED",
            "metadata": _build_metadata(r),
        }
        for r in records
    ]


@router.get("/{case_id}/evidence/bank")
def get_bank_evidence(
    case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, case_id)
    records = (
        db.query(BankTransaction)
        .filter(BankTransaction.business_id_fk == case.business_id_fk)
        .order_by(BankTransaction.transaction_date.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "date": r.transaction_date.isoformat(),
            "amount": float(r.amount),
            "type": r.transaction_type,
            "category": r.category,
            "metadata": _build_metadata(r),
        }
        for r in records
    ]


@router.get("/{case_id}/evidence/invoices")
def get_invoice_evidence(
    case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, case_id)
    records = (
        db.query(Invoice)
        .filter(Invoice.business_id_fk == case.business_id_fk)
        .order_by(Invoice.invoice_date.desc())
        .all()
    )
    return [
        {
            "id": str(r.id),
            "date": r.invoice_date.isoformat(),
            "amount": float(r.amount),
            "status": r.status,
            "counterparty": r.counterparty_name,
            "metadata": _build_metadata(r),
        }
        for r in records
    ]


@router.get("/{case_id}/evidence/employment")
def get_employment_evidence(
    case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, case_id)
    records = (
        db.query(EmploymentPeriod)
        .filter(EmploymentPeriod.business_id_fk == case.business_id_fk)
        .order_by(EmploymentPeriod.period_month.desc())
        .all()
    )
    return [
        {
            "period": r.period_month.isoformat(),
            "employee_count": r.employee_count,
            "pf_remittance": float(r.total_pf_remittance),
            "metadata": _build_metadata(r),
        }
        for r in records
    ]


@router.get("/{case_id}/evidence/obligations")
def get_obligation_evidence(
    case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    case = can_view_case(db, user, case_id)
    records = (
        db.query(Obligation)
        .filter(Obligation.business_id_fk == case.business_id_fk)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "lender": "Unknown Lender",
            "facility_type": getattr(r, "facility_type", getattr(r, "loan_type", None)),
            "outstanding_balance": float(r.outstanding_balance),
            "monthly_emi": float(r.monthly_emi),
            "metadata": _build_metadata(r),
        }
        for r in records
    ]


@router.get("/{case_id}/credit-twin", response_model=CreditTwinResponse)
def get_case_credit_twin(
    case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    can_view_case(db, user, case_id)
    return get_credit_twin(db, str(case_id))


@router.get("/{case_id}/reconciliation", response_model=ReconciliationResponse)
def get_case_reconciliation(
    case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    can_view_case(db, user, case_id)
    return run_reconciliation(db, str(case_id))


@router.get("/{case_id}/assessment-history", response_model=list[AssessmentHistoryItem])
def get_assessment_history(
    case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    can_view_case(db, user, case_id)
    # Get evaluate audit events
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id, AuditEvent.event_type == "evaluate")
        .order_by(AuditEvent.created_at.desc())
        .all()
    )

    res = []
    for e in events:
        meta = e.metadata_json or {}
        
        # New approach: check for assessment_id in metadata
        assessment_id = meta.get("assessment_id")
        dec = meta.get("decision", {})
        scores = meta.get("scores", {})
        
        recommendation = dec.get("recommendation", "UNKNOWN")
        binding_limit = dec.get("binding_limit", None)
        dscr = scores.get("dscr", None)
        
        if assessment_id:
            # Query the snapshot
            snapshot = db.query(AssessmentSnapshot).filter(AssessmentSnapshot.assessment_id == assessment_id).first()
            if snapshot:
                snap_json = snapshot.canonical_assessment_json
                if snap_json:
                    recommendation = snap_json.get("assessment_range", {}).get("recommendation", recommendation)
                    binding_limit = snap_json.get("assessment_range", {}).get("supportable_limit", binding_limit)
                    dscr = snap_json.get("current_dscr", dscr)

        res.append(
            {
                "id": str(e.id),
                "sequence": e.event_sequence,
                "event_type": e.event_type,
                "actor": e.actor,
                "actor_role": meta.get("actor_role", "SYSTEM"),
                "reason": meta.get("reason", dec.get("reason", "Automated Assessment")),
                "created_at": e.created_at.isoformat(),
                "recommendation": recommendation,
                "binding_limit": binding_limit,
                "dscr": dscr,
                "policy_version": meta.get("policy_version", "1.1"),
                "calculation_version": meta.get(
                    "calculation_version", "DSCR_SANDBOX_V1"
                ),
            }
        )
    return res


@router.get("/{case_id}/evidence-passport")
def get_case_evidence_passport(
    case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    can_view_case(db, user, case_id)
    from app.domain.evidence.passport import generate_evidence_passport

    return generate_evidence_passport(db, str(case_id))
