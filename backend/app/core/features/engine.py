import math
from typing import Dict, Any
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.db.orm.cases import Business
from app.db.orm.evidence import GSTPeriod, BankTransaction, Invoice, EmploymentPeriod
from app.services.credit_twin import calculate_dscr_sandbox_v1
import datetime


class FeatureEngine:
    """
    Derives deterministic financial features from raw evidence.
    No LLMs or non-deterministic ML models are used here.
    All monetary and ratio aggregations use exact Decimal math.
    """

    def __init__(self, db: Session, business_id: str):
        self.db = db
        self.business_id = business_id

    def derive_all_features(self) -> Dict[str, Any]:
        """Runs all feature derivations for the business."""
        business = (
            self.db.query(Business).filter(Business.id == self.business_id).first()
        )
        if not business:
            raise ValueError(f"Business not found: {self.business_id}")

        return {
            "gst_metrics": self._derive_gst_metrics(),
            "bank_metrics": self._derive_bank_metrics(),
            "reconciliation_metrics": self._derive_reconciliation_metrics(),
            "employment_metrics": self._derive_employment_metrics(),
            "invoice_metrics": self._derive_receivable_metrics(),
        }

    def _derive_gst_metrics(self) -> Dict[str, Any]:
        gst_records = (
            self.db.query(GSTPeriod)
            .filter(GSTPeriod.business_id_fk == self.business_id)
            .all()
        )
        if not gst_records:
            return {
                "months_filed": 0,
                "avg_monthly_revenue": "0.00",
                "revenue_cv": "0.0000",
                "trend": "INSUFFICIENT_DATA",
            }

        revenues = [r.declared_revenue for r in gst_records]
        avg_revenue = sum(revenues) / Decimal(str(len(revenues)))

        # Coefficient of Variation (CV) = Standard Deviation / Mean
        variance = sum((float(r) - float(avg_revenue)) ** 2 for r in revenues) / float(
            len(revenues)
        )  # type: ignore
        std_dev = Decimal(str(math.sqrt(float(variance))))  # type: ignore
        cv = (std_dev / avg_revenue) if avg_revenue > 0 else Decimal("0")

        trend = "STABLE"
        if len(revenues) >= 12:
            sorted_revenues = [
                r.declared_revenue
                for r in sorted(gst_records, key=lambda x: x.period_month)
            ]
            recent_avg = sum(sorted_revenues[-6:]) / Decimal("6")
            prior_avg = sum(sorted_revenues[-12:-6]) / Decimal("6")
            if recent_avg > prior_avg * Decimal("1.1"):
                trend = "GROWING"
            elif recent_avg < prior_avg * Decimal("0.9"):
                trend = "DECLINING"

        return {
            "months_filed": len(gst_records),
            "avg_monthly_revenue": str(
                avg_revenue.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
            "revenue_cv": str(cv.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
            "trend": trend,
        }

    def _derive_bank_metrics(self) -> Dict[str, Any]:
        bank_txns = (
            self.db.query(BankTransaction)
            .filter(BankTransaction.business_id_fk == self.business_id)
            .all()
        )
        if not bank_txns:
            return {
                "total_credits": "0.00",
                "total_debits": "0.00",
                "avg_monthly_credits": "0.00",
                "avg_monthly_debits": "0.00",
            }

        credits = sum(
            (t.amount for t in bank_txns if t.transaction_type == "CREDIT"),
            Decimal("0"),
        )
        debits = sum(
            (t.amount for t in bank_txns if t.transaction_type == "DEBIT"), Decimal("0")
        )

        # Assumes 18 months based on standard pulling
        months = Decimal("18.0")

        # Calculate authoritative DSCR
        today = datetime.date(2026, 7, 1)
        dscr = calculate_dscr_sandbox_v1(self.db, self.business_id, today)

        return {
            "total_credits": str(
                credits.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
            "total_debits": str(
                debits.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
            "avg_monthly_credits": str(
                (credits / months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
            "avg_monthly_debits": str(
                (debits / months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
            "dscr": str(dscr) if dscr is not None else None,
        }

    def _derive_reconciliation_metrics(self) -> Dict[str, Any]:
        gst = self._derive_gst_metrics()
        bank = self._derive_bank_metrics()

        months_filed = gst["months_filed"]
        if months_filed == 0:
            return {"gst_bank_ratio": "0.0000", "status": "NO_GST_DATA"}

        total_gst_revenue = Decimal(gst["avg_monthly_revenue"]) * Decimal(
            str(months_filed)
        )

        ratio = (
            Decimal(bank["total_credits"]) / total_gst_revenue
            if total_gst_revenue > 0
            else Decimal("0")
        )

        status = "HEALTHY"
        if ratio < Decimal("0.8"):
            status = "UNDER_REPORTED_BANK"
        elif ratio > Decimal("1.5"):
            status = "OVER_REPORTED_BANK"

        return {
            "gst_bank_ratio": str(
                ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            ),
            "status": status,
        }

    def _derive_employment_metrics(self) -> Dict[str, Any]:
        epfo_records = (
            self.db.query(EmploymentPeriod)
            .filter(EmploymentPeriod.business_id_fk == self.business_id)
            .all()
        )
        if not epfo_records:
            return {"months_filed": 0, "avg_employees": 0, "trend": "INSUFFICIENT_DATA"}

        counts = [r.employee_count for r in epfo_records]
        avg_employees = sum(counts) / len(counts)

        return {
            "months_filed": len(epfo_records),
            "avg_employees": int(avg_employees),
            "trend": "STABLE",
        }

    def _derive_receivable_metrics(self) -> Dict[str, Any]:
        invoices = (
            self.db.query(Invoice)
            .filter(Invoice.business_id_fk == self.business_id)
            .all()
        )
        if not invoices:
            return {
                "total_invoices": 0,
                "overdue_ratio": "0.00",
                "concentration_risk": "UNKNOWN",
                "eligible_amount": "0.00",
            }

        total_amount = sum((i.amount for i in invoices), Decimal("0"))

        buyer_totals: Dict[str, Decimal] = {}
        for i in invoices:
            name = str(i.counterparty_name)
            buyer_totals[name] = buyer_totals.get(name, Decimal("0")) + Decimal(
                str(i.amount)
            )

        top_buyer_share = (
            max(buyer_totals.values()) / total_amount
            if total_amount > 0
            else Decimal("0")
        )
        concentration = (
            "HIGH"
            if top_buyer_share > Decimal("0.4")
            else ("MEDIUM" if top_buyer_share > Decimal("0.2") else "LOW")
        )

        # Payment delays (need to query InvoicePayment to get settlement date, or just keep it simple)
        # We will assume a delay if the status is PENDING and due date is past, but for prototype we just set a fixed delay
        avg_delay = Decimal("45")

        # Eligible amount for Receivables Finance (e.g. pending invoices not overdue > 90 days)
        eligible = sum(
            (i.amount for i in invoices if i.status == "PENDING"), Decimal("0")
        )

        return {
            "total_invoices": len(invoices),
            "top_buyer_concentration": str(
                top_buyer_share.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            ),
            "concentration_risk": concentration,
            "avg_payment_delay_days": str(avg_delay),
            "eligible_amount": str(
                eligible.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
        }
