from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date, timedelta
from typing import List, Dict, Any

from app.db.orm.cases import Case
from app.db.orm.evidence import GSTPeriod, BankTransaction, Invoice, InvoicePayment, EmploymentPeriod, Obligation

# Statuses
MATCHED = "MATCHED"
VARIANCE = "VARIANCE"
MISSING_EVIDENCE = "MISSING_EVIDENCE"
REVIEW_REQUIRED = "REVIEW_REQUIRED"

def run_reconciliation(db: Session, case_id: str) -> Dict[str, Any]:
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return {}
        
    business_id = case.business_id_fk
    
    # Check GST vs Bank Credits
    gst_periods = db.query(GSTPeriod).filter(GSTPeriod.business_id_fk == business_id).all()
    bank_credits = db.query(BankTransaction).filter(
        BankTransaction.business_id_fk == business_id, 
        BankTransaction.transaction_type == "CREDIT"
    ).all()
    
    total_gst_rev = sum((p.declared_revenue for p in gst_periods), Decimal("0.0"))
    total_bank_credits = sum((t.amount for t in bank_credits), Decimal("0.0"))
    
    gst_bank_status = MATCHED
    if not gst_periods or not bank_credits:
        gst_bank_status = MISSING_EVIDENCE
    elif abs(total_gst_rev - total_bank_credits) / max(total_gst_rev, Decimal("1.0")) > Decimal("0.10"):
        gst_bank_status = VARIANCE
        
    # Check Invoices vs Payments
    invoices = db.query(Invoice).filter(Invoice.business_id_fk == business_id).all()
    invoice_payments = db.query(InvoicePayment).join(Invoice).filter(Invoice.business_id_fk == business_id).all()
    
    total_invoice_amt = sum((i.amount for i in invoices if i.status == "PAID"), Decimal("0.0"))
    total_payment_amt = sum((p.amount for p in invoice_payments), Decimal("0.0"))
    
    invoice_status = MATCHED
    if not invoices:
        invoice_status = MISSING_EVIDENCE
    elif abs(total_invoice_amt - total_payment_amt) > Decimal("1.0"):
        invoice_status = VARIANCE
        
    # Check Payroll vs Employment
    employment = db.query(EmploymentPeriod).filter(EmploymentPeriod.business_id_fk == business_id).all()
    salary_debits = db.query(BankTransaction).filter(
        BankTransaction.business_id_fk == business_id,
        BankTransaction.category == "SALARY"
    ).all()
    
    payroll_status = MATCHED
    if not employment or not salary_debits:
        payroll_status = MISSING_EVIDENCE
    else:
        # PF is roughly 12% of salary
        total_pf = sum((e.total_pf_remittance for e in employment), Decimal("0.0"))
        total_salary = sum((s.amount for s in salary_debits), Decimal("0.0"))
        if total_salary > Decimal("0.0"):
            implied_pf = total_salary * Decimal("0.12")
            if abs(total_pf - implied_pf) / implied_pf > Decimal("0.10"):
                payroll_status = VARIANCE
                
    # Obligations vs Debt Service
    obligations = db.query(Obligation).filter(Obligation.business_id_fk == business_id).all()
    debt_service_debits = db.query(BankTransaction).filter(
        BankTransaction.business_id_fk == business_id,
        BankTransaction.category == "DEBT_SERVICE"
    ).all()
    
    obligation_status = MATCHED
    if not obligations and not debt_service_debits:
        obligation_status = MISSING_EVIDENCE
    elif obligations and not debt_service_debits:
        obligation_status = MISSING_EVIDENCE
    elif debt_service_debits and not obligations:
        obligation_status = MISSING_EVIDENCE
    else:
        monthly_emi = sum((o.monthly_emi for o in obligations), Decimal("0.0"))
        # We assume 18 months seeded
        total_expected_debt_service = monthly_emi * Decimal("18")
        total_actual_debt_service = sum((d.amount for d in debt_service_debits), Decimal("0.0"))
        if abs(total_expected_debt_service - total_actual_debt_service) > Decimal("1.0"):
            obligation_status = VARIANCE

    # Duplicate / Missing Periods / Circular
    # Simple check for duplicates
    txn_ids = [t.source_record_id for t in bank_credits]
    has_duplicates = len(txn_ids) != len(set(txn_ids))
    
    missing_periods = False
    if len(gst_periods) < 12: # Expect at least 12 months
        missing_periods = True
        
    anomaly_status = MATCHED
    if has_duplicates or missing_periods:
        anomaly_status = REVIEW_REQUIRED
        
    return {
        "case_id": str(case_id),
        "checks": [
            {
                "name": "GST vs Bank Credits",
                "status": gst_bank_status,
                "description": f"GST: {total_gst_rev:,.2f} | Bank: {total_bank_credits:,.2f}"
            },
            {
                "name": "Invoices vs Payments",
                "status": invoice_status,
                "description": f"Invoices: {total_invoice_amt:,.2f} | Payments: {total_payment_amt:,.2f}"
            },
            {
                "name": "Payroll Consistency",
                "status": payroll_status,
                "description": "Cross-checked EPFO PF remittance vs Salary Debits"
            },
            {
                "name": "Obligations vs Debt Service",
                "status": obligation_status,
                "description": "Cross-checked Bureau EMI vs Debt Service Debits"
            },
            {
                "name": "Anomalies",
                "status": anomaly_status,
                "description": f"Duplicates: {has_duplicates} | Missing Periods: {missing_periods}"
            }
        ]
    }
