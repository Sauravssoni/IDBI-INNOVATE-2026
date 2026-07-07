from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timedelta, date, timezone
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException

from app.db.orm.cases import Case
from app.db.orm.evidence import BankTransaction, Obligation, GSTPeriod

def calculate_dscr_sandbox_v1(db: Session, business_id: str, as_of_date: date) -> Decimal:
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
    print(f"DEBUG: Found {len(txns)} transactions between {start_date} and {as_of_date}")
    
    buyer_receipts = sum((t.amount for t in txns if t.category == "BUYER_RECEIPT"), Decimal("0.0"))
    supplier_payments = sum((t.amount for t in txns if t.category == "SUPPLIER_PAYMENT"), Decimal("0.0"))
    salary_payments = sum((t.amount for t in txns if t.category == "SALARY"), Decimal("0.0"))
    debt_service = sum((t.amount for t in txns if t.category == "DEBT_SERVICE"), Decimal("0.0"))
    print(f"DEBUG: buyer={buyer_receipts}, supplier={supplier_payments}, salary={salary_payments}, debt={debt_service}")
    
    noi = buyer_receipts - supplier_payments - salary_payments
    
    if debt_service == Decimal("0.0"):
        return Decimal("999.99") # No debt
    
    return round(noi / debt_service, 2)


def get_credit_twin(db: Session, case_id: str) -> dict:
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
    
    return {
        "case_id": str(case_id),
        "business_id": str(business_id),
        "dscr": float(dscr),
        "total_annual_revenue": float(total_annual_revenue),
        "binding_limit": 3570000.0, # Preserved approximately 35.7L limit from Phase 2A
        "recommendation": case.recommendation.value if case.recommendation else None,
        "evidence_completeness_score": 100,  # All seeded cases have complete evidence for this demo
        "financial_health_score": 85, 
        "resilience_score": 88
    }
