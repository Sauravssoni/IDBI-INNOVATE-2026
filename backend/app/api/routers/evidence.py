from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Dict, Any

from app.db.session import SessionLocal
from app.api.dependencies import get_current_user
from app.db.orm.users import User
from app.services.authz import can_view_case
from app.db.orm.evidence import GSTPeriod, BankTransaction, Invoice, EmploymentPeriod, Obligation
from app.db.orm.cases import AuditEvent
from app.services.credit_twin import get_credit_twin
from app.services.reconciliation import run_reconciliation

router = APIRouter(prefix="/api/cases", tags=["evidence"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{case_id}/evidence/gst")
def get_gst_evidence(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = can_view_case(db, user, case_id)
    records = db.query(GSTPeriod).filter(GSTPeriod.business_id_fk == case.business_id_fk).order_by(GSTPeriod.period_month.desc()).all()
    return [{"period": r.period_month.isoformat(), "declared_revenue": float(r.declared_revenue), "tax_paid": float(r.tax_paid), "status": "FILED", "metadata": {"ingestion_mode": r.ingestion_mode}} for r in records]

@router.get("/{case_id}/evidence/bank")
def get_bank_evidence(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = can_view_case(db, user, case_id)
    records = db.query(BankTransaction).filter(BankTransaction.business_id_fk == case.business_id_fk).order_by(BankTransaction.transaction_date.desc()).limit(100).all()
    return [{"date": r.transaction_date.isoformat(), "amount": float(r.amount), "type": r.transaction_type, "category": r.category, "metadata": {"ingestion_mode": r.ingestion_mode}} for r in records]

@router.get("/{case_id}/evidence/invoices")
def get_invoice_evidence(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = can_view_case(db, user, case_id)
    records = db.query(Invoice).filter(Invoice.business_id_fk == case.business_id_fk).order_by(Invoice.invoice_date.desc()).all()
    return [{"id": str(r.id), "date": r.invoice_date.isoformat(), "amount": float(r.amount), "status": r.status, "counterparty": r.counterparty_name, "metadata": {"ingestion_mode": r.ingestion_mode}} for r in records]

@router.get("/{case_id}/evidence/employment")
def get_employment_evidence(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = can_view_case(db, user, case_id)
    records = db.query(EmploymentPeriod).filter(EmploymentPeriod.business_id_fk == case.business_id_fk).order_by(EmploymentPeriod.period_month.desc()).all()
    return [{"period": r.period_month.isoformat(), "employee_count": r.employee_count, "pf_remittance": float(r.total_pf_remittance), "metadata": {"ingestion_mode": r.ingestion_mode}} for r in records]

@router.get("/{case_id}/evidence/obligations")
def get_obligation_evidence(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = can_view_case(db, user, case_id)
    records = db.query(Obligation).filter(Obligation.business_id_fk == case.business_id_fk).all()
    return [{"id": str(r.id), "lender": r.lender_name, "loan_type": r.loan_type, "outstanding": float(r.outstanding_balance), "emi": float(r.monthly_emi), "metadata": {"ingestion_mode": r.ingestion_mode}} for r in records]

@router.get("/{case_id}/credit-twin")
def get_case_credit_twin(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = can_view_case(db, user, case_id)
    return get_credit_twin(db, str(case_id))

@router.get("/{case_id}/reconciliation")
def get_case_reconciliation(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = can_view_case(db, user, case_id)
    return run_reconciliation(db, str(case_id))

@router.get("/{case_id}/assessment-history")
def get_assessment_history(case_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = can_view_case(db, user, case_id)
    # Get evaluate audit events
    events = db.query(AuditEvent).filter(
        AuditEvent.case_id == case_id,
        AuditEvent.event_type == "evaluate"
    ).order_by(AuditEvent.created_at.desc()).all()
    
    return [
        {
            "id": str(e.id),
            "sequence": e.event_sequence,
            "actor": e.actor,
            "created_at": e.created_at.isoformat(),
            "metadata": e.metadata_json
        } for e in events
    ]
