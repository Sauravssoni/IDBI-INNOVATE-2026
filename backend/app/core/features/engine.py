import math
from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.db.orm.cases import Business
from app.db.orm.evidence import (
    GSTPeriod,
    BankTransaction,
    Invoice,
    EmploymentPeriod,
    InvoicePayment,
)
from app.services.credit_twin import calculate_dscr_sandbox_v1
import datetime


class FeatureEngine:
    """
    Derives deterministic financial features from raw evidence.
    No LLMs or non-deterministic ML models are used here.
    All monetary and ratio aggregations use exact Decimal math.
    """

    def __init__(
        self, db: Session, business_id: str, as_of_date: Optional[datetime.date] = None
    ):
        self.db = db
        self.business_id = business_id
        self.as_of_date = as_of_date

    def derive_all_features(self) -> Dict[str, Any]:
        """Runs all feature derivations for the business."""
        business = (
            self.db.query(Business).filter(Business.id == self.business_id).first()
        )
        if not business:
            raise ValueError(f"Business not found: {self.business_id}")

        receivable_metrics = self._derive_receivable_metrics()
        return {
            "gst_metrics": self._derive_gst_metrics(),
            "bank_metrics": self._derive_bank_metrics(),
            "reconciliation_metrics": self._derive_reconciliation_metrics(),
            "employment_metrics": self._derive_employment_metrics(),
            "receivable_metrics": receivable_metrics,
            "invoice_metrics": receivable_metrics,
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

    TRANSACTION_CATEGORY_WHITELISTS = {
        "OPERATING_INFLOWS": {
            "BUYER_RECEIPT",
            "INVOICE_SETTLEMENT",
            "POS_MERCHANT_SETTLEMENT",
            "UPI_MERCHANT_RECEIPT",
            "OPERATING_RECEIPT",
            "OPERATING_REVENUE",
            "SALES",
            "RECEIPT",
            "BUSINESS_RECEIPT",
            "TURN_OVER",
        },
        "EXCLUDED_INFLOWS": {
            "LOAN",
            "LOAN_DISBURSEMENT",
            "CAPITAL_INFUSION",
            "INTER_ACCOUNT_TRANSFER",
            "TRANSFER",
            "REFUND",
            "REVERSAL",
            "UNIDENTIFIED_CREDIT",
            "ASSET_SALE",
            "OWNER_CONTRIBUTION",
            "EQUITY",
        },
        "OPERATING_OUTFLOWS": {
            "SUPPLIER_PAYMENT",
            "PAYROLL",
            "SALARY",
            "RENT",
            "UTILITIES",
            "TAX",
            "OPERATING_EXPENSE",
            "EXPENSE",
            "VENDOR_PAYMENT",
            "RAW_MATERIAL",
            "LOGISTICS",
            "MAINTENANCE",
        },
        "EXCLUDED_OUTFLOWS": {
            "DEBT_SERVICE",
            "TRANSFER",
            "INTER_ACCOUNT_TRANSFER",
            "CAPITAL_EXPENDITURE",
            "CAPEX",
            "DRAWINGS",
            "UNIDENTIFIED_DEBIT",
            "DIVIDEND",
            "INVESTMENT",
        },
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
                "operating_inflows_monthly": "0.00",
                "operating_outflows_monthly": "0.00",
                "verified_debt_service_monthly": "0.00",
                "transaction_categorization_summary": {
                    "version": "1.0.0",
                    "included_inflow_ids": [],
                    "excluded_inflow_ids": [],
                    "unresolved_inflow_ids": [],
                    "included_outflow_ids": [],
                    "excluded_outflow_ids": [],
                    "unresolved_outflow_ids": [],
                    "debt_service_ids": [],
                    "has_material_unresolved_activity": False,
                },
            }

        total_credits = Decimal("0")
        total_debits = Decimal("0")
        operating_inflows = Decimal("0")
        operating_outflows = Decimal("0")
        debt_service = Decimal("0")

        included_inflow_ids = []
        excluded_inflow_ids = []
        unresolved_inflow_ids = []
        included_outflow_ids = []
        excluded_outflow_ids = []
        unresolved_outflow_ids = []
        debt_service_ids = []

        distinct_months = set()
        latest_date = None
        for t in bank_txns:
            if t.transaction_date:
                distinct_months.add((t.transaction_date.year, t.transaction_date.month))
                if latest_date is None or t.transaction_date > latest_date:
                    latest_date = t.transaction_date
            amt = Decimal(str(t.amount or "0.00"))
            t_type = str(t.transaction_type or "").upper()
            t_cat = str(t.category or "").upper() if t.category else ""

            if t_type == "CREDIT":
                total_credits += amt
                if t_cat in self.TRANSACTION_CATEGORY_WHITELISTS["OPERATING_INFLOWS"]:
                    operating_inflows += amt
                    included_inflow_ids.append(str(t.id))
                elif t_cat in self.TRANSACTION_CATEGORY_WHITELISTS["EXCLUDED_INFLOWS"]:
                    excluded_inflow_ids.append(str(t.id))
                else:
                    unresolved_inflow_ids.append(str(t.id))
            elif t_type == "DEBIT":
                total_debits += amt
                if t_cat == "DEBT_SERVICE":
                    debt_service += amt
                    debt_service_ids.append(str(t.id))
                elif t_cat in self.TRANSACTION_CATEGORY_WHITELISTS["OPERATING_OUTFLOWS"]:
                    operating_outflows += amt
                    included_outflow_ids.append(str(t.id))
                elif t_cat in self.TRANSACTION_CATEGORY_WHITELISTS["EXCLUDED_OUTFLOWS"]:
                    excluded_outflow_ids.append(str(t.id))
                else:
                    unresolved_outflow_ids.append(str(t.id))

        months = (
            Decimal(str(len(distinct_months))) if distinct_months else Decimal("1.0")
        )

        # Calculate authoritative DSCR using explicit as_of_date or latest transaction date or fallback reference
        raw_eval_date = self.as_of_date or latest_date or datetime.date(2026, 7, 1)
        eval_date: datetime.date = (
            datetime.date(raw_eval_date.year, raw_eval_date.month, raw_eval_date.day)
            if hasattr(raw_eval_date, "year") and hasattr(raw_eval_date, "month")
            else datetime.date(2026, 7, 1)
        )
        dscr = calculate_dscr_sandbox_v1(self.db, self.business_id, eval_date)

        has_material_unresolved = (
            len(unresolved_inflow_ids) + len(unresolved_outflow_ids) > 0
        )

        avg_monthly_inflows = (operating_inflows / months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if operating_inflows > 0 else (total_credits / months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        avg_monthly_outflows = (operating_outflows / months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if operating_outflows > 0 else (total_debits / months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        verified_ds_monthly = (debt_service / months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "total_credits": str(
                total_credits.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
            "total_debits": str(
                total_debits.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
            "avg_monthly_credits": str(avg_monthly_inflows),
            "avg_monthly_debits": str(avg_monthly_outflows),
            "operating_inflows_monthly": str(avg_monthly_inflows),
            "operating_outflows_monthly": str(avg_monthly_outflows),
            "verified_debt_service_monthly": str(verified_ds_monthly),
            "debt_service_verified": len(debt_service_ids) > 0,
            "dscr": str(dscr) if dscr is not None else None,
            "transaction_categorization_summary": {
                "version": "1.0.0",
                "included_inflow_ids": included_inflow_ids,
                "excluded_inflow_ids": excluded_inflow_ids,
                "unresolved_inflow_ids": unresolved_inflow_ids,
                "included_outflow_ids": included_outflow_ids,
                "excluded_outflow_ids": excluded_outflow_ids,
                "unresolved_outflow_ids": unresolved_outflow_ids,
                "debt_service_ids": debt_service_ids,
                "has_material_unresolved_activity": has_material_unresolved,
            },
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
            .order_by(EmploymentPeriod.period_month.asc())
            .all()
        )
        if not epfo_records:
            return {"months_filed": 0, "avg_employees": 0, "trend": "INSUFFICIENT_DATA"}

        counts = [r.employee_count for r in epfo_records]
        avg_employees = sum(counts) / len(counts)

        trend = "STABLE"
        if len(counts) >= 4:
            mid = len(counts) // 2
            earlier_avg = sum(counts[:mid]) / len(counts[:mid])
            recent_avg = sum(counts[mid:]) / len(counts[mid:])
            if earlier_avg > 0:
                change = (recent_avg - earlier_avg) / earlier_avg
                if change >= 0.05:
                    trend = "GROWING"
                elif change <= -0.05:
                    trend = "DECLINING"

        return {
            "months_filed": len(epfo_records),
            "avg_employees": int(avg_employees),
            "trend": trend,
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
                "avg_payment_delay_days": "UNKNOWN",
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

        # Payment delays calculated from InvoicePayment settlement records
        delays = []
        for inv in invoices:
            payments = (
                self.db.query(InvoicePayment)
                .filter(InvoicePayment.invoice_id_fk == inv.id)
                .all()
            )
            for pay in payments:
                if pay.settlement_date and inv.due_date:
                    delay_days = (pay.settlement_date - inv.due_date).days
                    if delay_days > 0:
                        delays.append(delay_days)
                    else:
                        delays.append(0)

        if delays:
            avg_delay = sum(delays) / len(delays)
            avg_delay_str = str(int(round(avg_delay)))
        else:
            # Where settlement data is unavailable or no payment records exist
            avg_delay_str = "UNKNOWN"

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
            "avg_payment_delay_days": avg_delay_str,
            "eligible_amount": str(
                eligible.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
        }
