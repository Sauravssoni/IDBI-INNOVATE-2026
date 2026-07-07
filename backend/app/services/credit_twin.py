from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException

from app.db.orm.cases import Case
from app.db.orm.evidence import BankTransaction, GSTPeriod

def calculate_dscr_sandbox_v1(db: Session, business_id: str, as_of_date: date):
    """
    Trailing 12-month (TTM) DSCR = NOI / Debt Service
    NOI = Credits (BUYER_RECEIPT) - Debits (SUPPLIER_PAYMENT + SALARY)
    Debt Service = Debits (DEBT_SERVICE)
    """
    start_date = as_of_date - relativedelta(months=12)
    txns = db.query(BankTransaction).filter(
        BankTransaction.business_id_fk == business_id,
        BankTransaction.transaction_date >= start_date,
        BankTransaction.transaction_date < as_of_date
    ).all()
    
    buyer_receipts = sum((t.amount for t in txns if t.category == "BUYER_RECEIPT"), Decimal("0.0"))
    supplier_payments = sum((t.amount for t in txns if t.category == "SUPPLIER_PAYMENT"), Decimal("0.0"))
    salary_payments = sum((t.amount for t in txns if t.category == "SALARY"), Decimal("0.0"))
    debt_service = sum((t.amount for t in txns if t.category == "DEBT_SERVICE"), Decimal("0.0"))
    
    noi = buyer_receipts - supplier_payments - salary_payments
    
    if debt_service == Decimal("0.0"):
        return None
    
    return round(noi / debt_service, 2)


def get_credit_twin(db: Session, case_id: str) -> dict:
    from app.db.orm.cases import AuditEvent
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    business_id = case.business_id_fk
    
    # We assume 'today' is 2026-07-01 for the demo seeding
    today = date(2026, 7, 1)
    
    dscr = calculate_dscr_sandbox_v1(db, business_id, today)
    
    # Calculate Total Annual Revenue (GST)
    start_date = today - relativedelta(months=12)
    gst_periods = db.query(GSTPeriod).filter(
        GSTPeriod.business_id_fk == business_id,
        GSTPeriod.period_month >= start_date,
        GSTPeriod.period_month < today
    ).all()
    total_annual_revenue = sum((p.declared_revenue for p in gst_periods), Decimal("0.0"))
    
    latest_eval = db.query(AuditEvent).filter(
        AuditEvent.case_id == case_id,
        AuditEvent.event_type == "evaluate"
    ).order_by(AuditEvent.created_at.desc()).first()
    
    binding_limit = None
    scores = {}
    timestamp = None
    if latest_eval and latest_eval.metadata_json:
        metadata = latest_eval.metadata_json
        if "decision" in metadata and "binding_limit" in metadata["decision"]:
            binding_limit = metadata["decision"]["binding_limit"]
        if "scores" in metadata:
            scores = metadata["scores"]
        timestamp = latest_eval.created_at.isoformat()
        
    has_gst = len(gst_periods) > 0
    has_bank = db.query(BankTransaction).filter(BankTransaction.business_id_fk == business_id).first() is not None
    evidence_completeness_score = 100 if (has_gst and has_bank) else (50 if has_gst or has_bank else 0)
    
    return {
        "case_id": str(case_id),
        "business_id": str(business_id),
        "dscr": float(dscr) if dscr is not None else None,
        "calculation_version": "DSCR_SANDBOX_V1",
        "total_annual_revenue": float(total_annual_revenue),
        "binding_limit": float(binding_limit) if binding_limit is not None else None,
        "recommendation": case.recommendation.value if case.recommendation else None,
        "evidence_completeness_score": evidence_completeness_score,
        "financial_health_score": scores.get("financial_health_score") if scores else None,
        "evidence_confidence_score": scores.get("evidence_confidence_score") if scores else None,
        "resilience_score": scores.get("resilience_score") if scores else None,
        "evaluated_at": timestamp
    }
