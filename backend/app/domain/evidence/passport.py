from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.db.orm.evidence import GSTPeriod, BankTransaction, Invoice, EmploymentPeriod, Obligation
from app.db.orm.cases import Case
from app.db.orm.consents import Consent, ConsentStatus


def generate_evidence_passport(db: Session, case_id: str) -> Dict[str, Any]:
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case not found: {case_id}")

    business_id = case.business_id_fk

    # 1. Check Consent
    consents = db.query(Consent).filter(Consent.business_id_fk == business_id).all()
    active_consent = None
    consent_status = "MISSING"
    for c in consents:
        st_val = getattr(c, "status", None)
        if st_val in (ConsentStatus.ACTIVE, "ACTIVE", "VALID"):
            # Check if expired
            if c.valid_until and c.valid_until < datetime.now(timezone.utc).date():
                consent_status = "EXPIRED"
            else:
                active_consent = c
                consent_status = "VALID"
                break
        elif st_val in (ConsentStatus.REVOKED, ConsentStatus.EXPIRED, "REVOKED", "EXPIRED"):
            consent_status = str(st_val.value if hasattr(st_val, "value") else st_val)

    # 2. Fetch Evidence Records
    gst_records = db.query(GSTPeriod).filter(GSTPeriod.business_id_fk == business_id).order_by(GSTPeriod.period_month.desc()).all()
    bank_records = db.query(BankTransaction).filter(BankTransaction.business_id_fk == business_id).order_by(BankTransaction.transaction_date.desc()).all()
    invoice_records = db.query(Invoice).filter(Invoice.business_id_fk == business_id).order_by(Invoice.invoice_date.desc()).all()
    emp_records = db.query(EmploymentPeriod).filter(EmploymentPeriod.business_id_fk == business_id).order_by(EmploymentPeriod.period_month.desc()).all()
    obligations = db.query(Obligation).filter(Obligation.business_id_fk == business_id).all()

    # Rail coverage
    rail_coverage = {
        "gst": len(gst_records) > 0,
        "account_aggregator": len(bank_records) > 0,
        "invoices": len(invoice_records) > 0,
        "epfo": len(emp_records) > 0,
        "cibil": len(obligations) > 0 or len(gst_records) > 0  # if records present or explicit pull
    }

    # Freshness & Depth
    gst_months = len(gst_records)
    bank_tx_count = len(bank_records)
    invoice_count = len(invoice_records)
    emp_months = len(emp_records)

    # Calculate trailing month continuity
    months_of_history = max(gst_months, emp_months, (12 if bank_tx_count > 20 else max(1, int(bank_tx_count / 10))))

    # Obligation verification state
    cibil_total_emi = sum(float(getattr(o, "monthly_emi", 0)) for o in obligations)
    observed_debt_service = sum(
        float(tx.amount) for tx in bank_records if getattr(tx, "category", "") == "DEBT_SERVICE"
    )
    # If trailing months available, average monthly observed debt service
    monthly_observed_ds = observed_debt_service / max(1.0, float(min(12, max(1, int(bank_tx_count / 10)))))

    if cibil_total_emi == 0 and observed_debt_service == 0:
        obligation_verification_state = "VERIFIED_NO_DEBT"
    elif cibil_total_emi > 0 and observed_debt_service > 0:
        diff_ratio = abs(cibil_total_emi - monthly_observed_ds) / max(cibil_total_emi, monthly_observed_ds)
        if diff_ratio <= 0.15:
            obligation_verification_state = "VERIFIED_MATCH"
        else:
            obligation_verification_state = "UNVERIFIED_MISMATCH"
    elif cibil_total_emi > 0:
        obligation_verification_state = "UNVERIFIED_CIBIL_ONLY"
    else:
        obligation_verification_state = "UNVERIFIED_BANK_ONLY"

    # Contradiction and reconciliation severity
    total_gst_rev = sum(float(getattr(g, "declared_revenue", 0)) for g in gst_records)
    total_bank_credits = sum(
        float(tx.amount) for tx in bank_records if getattr(tx, "transaction_type", "") == "CREDIT" and getattr(tx, "category", "") == "BUYER_RECEIPT"
    )
    
    contradiction_severity = "NONE"
    reconciliation_ratio = 1.0
    if total_gst_rev > 0 and total_bank_credits > 0:
        reconciliation_ratio = total_bank_credits / total_gst_rev
        if reconciliation_ratio < 0.65 or reconciliation_ratio > 1.45:
            contradiction_severity = "HIGH_CONTRADICTION"
        elif reconciliation_ratio < 0.80 or reconciliation_ratio > 1.25:
            contradiction_severity = "MEDIUM"
        elif reconciliation_ratio < 0.90 or reconciliation_ratio > 1.10:
            contradiction_severity = "LOW"

    # Assessment Certainty
    if consent_status != "VALID":
        assessment_certainty = "INSUFFICIENT_TO_ASSESS"
    elif not rail_coverage["gst"] and not rail_coverage["account_aggregator"]:
        assessment_certainty = "INSUFFICIENT_TO_ASSESS"
    elif contradiction_severity == "HIGH_CONTRADICTION":
        assessment_certainty = "LIMITED_CERTAINTY"
    elif months_of_history >= 12 and rail_coverage["gst"] and rail_coverage["account_aggregator"] and obligation_verification_state in ("VERIFIED_MATCH", "VERIFIED_NO_DEBT"):
        assessment_certainty = "HIGH_CERTAINTY"
    elif months_of_history >= 6 and (rail_coverage["gst"] or rail_coverage["account_aggregator"]):
        assessment_certainty = "MODERATE_CERTAINTY"
    else:
        assessment_certainty = "LIMITED_CERTAINTY"

    # Evidence IDs for lineage tracking
    evidence_ids = []
    for g in gst_records[:12]:
        if hasattr(g, "id") and g.id:
            evidence_ids.append(str(g.id))
    for b in bank_records[:20]:
        if hasattr(b, "id") and b.id:
            evidence_ids.append(str(b.id))
    for inv in invoice_records[:10]:
        if hasattr(inv, "id") and inv.id:
            evidence_ids.append(str(inv.id))

    return {
        "case_id": str(case_id),
        "business_id": str(business_id),
        "consent_status": consent_status,
        "consent_scope": getattr(active_consent, "source_type", "NONE") if active_consent else "NONE",
        "rail_coverage": rail_coverage,
        "freshness_depth": {
            "months_of_history": months_of_history,
            "gst_periods": gst_months,
            "bank_transactions": bank_tx_count,
            "invoice_records": invoice_count,
            "employment_periods": emp_months,
        },
        "obligation_verification": {
            "state": obligation_verification_state,
            "cibil_monthly_emi": round(cibil_total_emi, 2),
            "observed_monthly_debt_service": round(monthly_observed_ds, 2),
        },
        "contradiction_analysis": {
            "severity": contradiction_severity,
            "reconciliation_ratio": round(reconciliation_ratio, 3),
            "gst_declared_revenue": round(total_gst_rev, 2),
            "bank_buyer_receipts": round(total_bank_credits, 2),
        },
        "assessment_certainty": assessment_certainty,
        "authoritative_evidence_ids": evidence_ids,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
