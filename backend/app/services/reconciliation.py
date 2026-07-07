from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Dict, Any
from dateutil.relativedelta import relativedelta

from app.db.orm.cases import Case
from app.db.orm.evidence import (
    GSTPeriod,
    BankTransaction,
    Obligation,
    Invoice,
    InvoicePayment,
    EmploymentPeriod,
)

MATCHED = "MATCHED"
VARIANCE = "VARIANCE"
MISSING_EVIDENCE = "MISSING_EVIDENCE"
REVIEW_REQUIRED = "REVIEW_REQUIRED"


def run_reconciliation(db: Session, case_id: str) -> Dict[str, Any]:
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return {}

    business_id = case.business_id_fk

    checks: list[dict] = []

    # 1. GST vs Bank Credits
    gst_periods = (
        db.query(GSTPeriod).filter(GSTPeriod.business_id_fk == business_id).all()
    )
    if not gst_periods:
        checks.append(
            {
                "check_id": "GST_BANK_RECON",
                "name": "GST vs Bank Credits",
                "status": MISSING_EVIDENCE,
                "observed_value": None,
                "reference_value": None,
                "variance_amount": None,
                "variance_percentage": None,
                "evidence_references": [],
                "explanation": "No GST periods found.",
                "rule_version": "1.1",
            }
        )
    else:
        min_date = min(g.period_month for g in gst_periods)
        max_date = max(g.period_month for g in gst_periods)
        end_date = max_date + relativedelta(months=1)

        bank_credits = (
            db.query(BankTransaction)
            .filter(
                BankTransaction.business_id_fk == business_id,
                BankTransaction.transaction_type == "CREDIT",
                BankTransaction.category == "BUYER_RECEIPT",
                BankTransaction.transaction_date >= min_date,
                BankTransaction.transaction_date < end_date,
            )
            .all()
        )

        total_gst_rev = sum((p.declared_revenue for p in gst_periods), Decimal("0.0"))
        total_bank_credits = sum((t.amount for t in bank_credits), Decimal("0.0"))

        variance_amount = abs(total_gst_rev - total_bank_credits)
        variance_percentage = (
            variance_amount / max(total_gst_rev, Decimal("1.0"))
        ) * 100

        status = MATCHED if variance_percentage <= Decimal("10.0") else VARIANCE
        if not bank_credits:
            status = MISSING_EVIDENCE

        checks.append(
            {
                "check_id": "GST_BANK_RECON",
                "name": "GST vs Bank Credits",
                "status": status,
                "observed_value": float(total_bank_credits),
                "reference_value": float(total_gst_rev),
                "variance_amount": float(variance_amount),
                "variance_percentage": float(variance_percentage),
                "evidence_references": [str(g.id) for g in gst_periods]
                + [str(t.id) for t in bank_credits],
                "explanation": "Aligned GST periods with BUYER_RECEIPT bank credits.",
                "rule_version": "1.1",
            }
        )

    # 2. Invoices vs Payments
    invoices = db.query(Invoice).filter(Invoice.business_id_fk == business_id).all()
    invoice_ids = [i.id for i in invoices]
    payments = (
        db.query(InvoicePayment)
        .filter(InvoicePayment.invoice_id_fk.in_(invoice_ids))
        .all()
        if invoice_ids
        else []
    )

    if not invoices or not payments:
        checks.append(
            {
                "check_id": "INVOICE_PAYMENT_RECON",
                "name": "Invoices vs Payments",
                "status": MISSING_EVIDENCE,
                "observed_value": None,
                "reference_value": None,
                "variance_amount": None,
                "variance_percentage": None,
                "evidence_references": [str(i.id) for i in invoices]
                + [str(p.id) for p in payments],
                "explanation": "No invoice data available for reconciliation.",
                "rule_version": "1.1",
            }
        )
    else:
        # reference_value = total invoice amount for invoices expected to be settled (status PAID)
        settled_invoices = [i for i in invoices if i.status == "PAID"]
        expected_total = sum((i.amount for i in settled_invoices), Decimal("0.0"))
        actual_total = sum((p.amount for p in payments), Decimal("0.0"))

        variance_amount = abs(expected_total - actual_total)
        variance_percentage = (
            variance_amount / max(expected_total, Decimal("1.0"))
        ) * 100

        status = MATCHED if variance_percentage <= Decimal("10.0") else VARIANCE

        checks.append(
            {
                "check_id": "INVOICE_PAYMENT_RECON",
                "name": "Invoices vs Payments",
                "status": status,
                "observed_value": float(actual_total),
                "reference_value": float(expected_total),
                "variance_amount": float(variance_amount),
                "variance_percentage": float(variance_percentage),
                "evidence_references": [str(i.id) for i in invoices]
                + [str(p.id) for p in payments],
                "explanation": "Compared expected settled invoices to total linked payments.",
                "rule_version": "1.1",
            }
        )

    # 3. Payroll vs Employment
    employment_periods = (
        db.query(EmploymentPeriod)
        .filter(EmploymentPeriod.business_id_fk == business_id)
        .all()
    )
    salary_debits = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.business_id_fk == business_id,
            BankTransaction.category == "SALARY",
            BankTransaction.transaction_type == "DEBIT",
        )
        .all()
    )

    if not employment_periods or not salary_debits:
        checks.append(
            {
                "check_id": "PAYROLL_EMPLOYMENT_RECON",
                "name": "Payroll vs Employment",
                "status": MISSING_EVIDENCE,
                "observed_value": None,
                "reference_value": None,
                "variance_amount": None,
                "variance_percentage": None,
                "evidence_references": [str(e.id) for e in employment_periods]
                + [str(s.id) for s in salary_debits],
                "explanation": "No payroll data available for reconciliation.",
                "rule_version": "1.1",
            }
        )
    else:
        total_pf = sum(
            (e.total_pf_remittance for e in employment_periods), Decimal("0.0")
        )
        total_salary = sum((s.amount for s in salary_debits), Decimal("0.0"))

        expected_pf = total_salary * Decimal("0.12")

        variance_amount = abs(total_pf - expected_pf)
        variance_percentage = (variance_amount / max(expected_pf, Decimal("1.0"))) * 100

        status = MATCHED if variance_percentage <= Decimal("10.0") else VARIANCE

        checks.append(
            {
                "check_id": "PAYROLL_EMPLOYMENT_RECON",
                "name": "Payroll vs Employment",
                "status": status,
                "observed_value": float(total_pf),
                "reference_value": float(expected_pf),
                "variance_amount": float(variance_amount),
                "variance_percentage": float(variance_percentage),
                "evidence_references": [str(e.id) for e in employment_periods]
                + [str(s.id) for s in salary_debits],
                "explanation": "Checked PF remittance vs 12% of salary payments (sandbox rule).",
                "rule_version": "1.1",
            }
        )

    # 4. Obligations vs Debt Service
    obligations = (
        db.query(Obligation).filter(Obligation.business_id_fk == business_id).all()
    )
    if not obligations:
        checks.append(
            {
                "check_id": "OBLIGATION_DEBT_SERVICE_RECON",
                "name": "Obligations vs Debt Service",
                "status": MISSING_EVIDENCE,
                "observed_value": None,
                "reference_value": None,
                "variance_amount": None,
                "variance_percentage": None,
                "evidence_references": [],
                "explanation": "No obligations found.",
                "rule_version": "1.1",
            }
        )
    else:
        debt_service_debits = (
            db.query(BankTransaction)
            .filter(
                BankTransaction.business_id_fk == business_id,
                BankTransaction.category == "DEBT_SERVICE",
            )
            .all()
        )

        if not debt_service_debits:
            checks.append(
                {
                    "check_id": "OBLIGATION_DEBT_SERVICE_RECON",
                    "name": "Obligations vs Debt Service",
                    "status": MISSING_EVIDENCE,
                    "observed_value": None,
                    "reference_value": None,
                    "variance_amount": None,
                    "variance_percentage": None,
                    "evidence_references": [str(o.id) for o in obligations],
                    "explanation": "No debt service debits found.",
                    "rule_version": "1.1",
                }
            )
        else:
            min_txn_date = min(t.transaction_date for t in debt_service_debits)
            max_txn_date = max(t.transaction_date for t in debt_service_debits)
            months_diff = (
                (max_txn_date.year - min_txn_date.year) * 12
                + max_txn_date.month
                - min_txn_date.month
                + 1
            )
            if months_diff == 0:
                months_diff = 1

            monthly_emi = sum((o.monthly_emi for o in obligations), Decimal("0.0"))
            total_expected_debt_service = monthly_emi * Decimal(months_diff)
            total_actual_debt_service = sum(
                (d.amount for d in debt_service_debits), Decimal("0.0")
            )

            variance_amount = abs(
                total_expected_debt_service - total_actual_debt_service
            )
            variance_percentage = (
                variance_amount / max(total_expected_debt_service, Decimal("1.0"))
            ) * 100

            status = MATCHED if variance_percentage <= Decimal("10.0") else VARIANCE

            checks.append(
                {
                    "check_id": "OBLIGATION_DEBT_SERVICE_RECON",
                    "name": "Obligations vs Debt Service",
                    "status": status,
                    "observed_value": float(total_actual_debt_service),
                    "reference_value": float(total_expected_debt_service),
                    "variance_amount": float(variance_amount),
                    "variance_percentage": float(variance_percentage),
                    "evidence_references": [str(o.id) for o in obligations]
                    + [str(t.id) for t in debt_service_debits],
                    "explanation": f"Compared {months_diff} months of debt service debits to bureau EMIs.",
                    "rule_version": "1.1",
                }
            )

    # 5. Circular Flow Analysis
    checks.append(
        {
            "check_id": "CIRCULAR_FLOW_EVIDENCE",
            "name": "Circular Flow Analysis",
            "status": MISSING_EVIDENCE,
            "observed_value": None,
            "reference_value": None,
            "variance_amount": None,
            "variance_percentage": None,
            "evidence_references": [],
            "explanation": "Awaiting adequate counterparty/reference data.",
            "rule_version": "1.1",
        }
    )

    return {"case_id": str(case_id), "checks": checks}
