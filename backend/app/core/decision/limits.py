from typing import Dict, Any, List
from decimal import Decimal, ROUND_HALF_UP
from app.core.versions import CALCULATION_VERSION


class SafeLimitEngine:
    """
    Product-specific capacity strategies enforcing exact financial formulas,
    reducing-balance amortization, and evidence lineage.
    """

    @staticmethod
    def _calculate_loan_from_emi(monthly_emi: Decimal, annual_rate: Decimal, tenure_months: int) -> Decimal:
        if monthly_emi <= 0 or tenure_months <= 0:
            return Decimal("0.00")
        if annual_rate <= 0:
            return (monthly_emi * Decimal(tenure_months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        r = annual_rate / Decimal("12")
        factor = (Decimal("1") + r) ** tenure_months
        principal = monthly_emi * (factor - Decimal("1")) / (r * factor)
        return principal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_emi_from_loan(principal: Decimal, annual_rate: Decimal, tenure_months: int) -> Decimal:
        """
        Exact reducing-balance amortization formula:
        P * r * (1+r)^n / ((1+r)^n - 1)
        """
        if principal <= 0 or tenure_months <= 0:
            return Decimal("0.00")
        if annual_rate <= 0:
            return (principal / Decimal(tenure_months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        r = annual_rate / Decimal("12")
        factor = (Decimal("1") + r) ** tenure_months
        emi = principal * r * factor / (factor - Decimal("1"))
        return emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_post_loan_dscr(current_noi: Decimal, existing_debt_service: Decimal, proposed_emi: Decimal, is_annual: bool = True) -> Decimal:
        """
        Post-loan DSCR incorporating proposed facility EMI into existing debt service obligations.
        If is_annual is True, current_noi and existing_debt_service are TTM (trailing 12 months), so proposed debt service = proposed_emi * 12.
        """
        proposed_ds = proposed_emi * Decimal("12") if is_annual else proposed_emi
        total_ds = existing_debt_service + proposed_ds
        if total_ds <= Decimal("0.00"):
            return Decimal("0.00")
        return (current_noi / total_ds).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def receivables_finance(cls, features: Dict[str, Any]) -> Dict[str, Any]:
        """Receivables-backed limit based on verified invoice collateral"""
        receivables_metrics = features.get("invoice_metrics", {})
        eligible_receivables = Decimal(
            str(receivables_metrics.get("eligible_amount", features.get("eligible_receivables", 0)))
        )
        advance_rate = Decimal("0.75")

        limit = eligible_receivables * advance_rate
        evidence_ids = features.get("authoritative_evidence_ids", [])

        return {
            "method": "RECEIVABLES_FINANCE",
            "applicability": "NOT_APPLICABLE" if limit <= 0 else "APPLICABLE",
            "calculated_limit": limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "calculation_version": CALCULATION_VERSION,
            "input_snapshot": {
                "eligible_receivables": str(eligible_receivables),
                "advance_rate": str(advance_rate),
            },
            "evidence_ids": evidence_ids,
            "policy_rule_ids": ["POL-REC-001"],
            "confidence": 0.90 if limit > 0 else 0.0,
            "warnings": [] if limit > 0 else ["No eligible invoice receivables verified"],
            "limitations": ["Requires ongoing invoice assignment and verification"],
        }

    @classmethod
    def working_capital_line(cls, features: Dict[str, Any]) -> Dict[str, Any]:
        """Working Capital Line based on verified Turnover and Cash Conversion Headroom"""
        gst = features.get("gst_metrics", {})
        avg_monthly_rev = Decimal(str(gst.get("avg_monthly_revenue", features.get("monthly_revenue_inr", 0))))
        annualized_rev = avg_monthly_rev * Decimal("12")

        # 20% of projected turnover method governed by headroom
        base_limit = annualized_rev * Decimal("0.20")
        evidence_ids = features.get("authoritative_evidence_ids", [])

        return {
            "method": "WORKING_CAPITAL_LINE",
            "applicability": "APPLICABLE" if base_limit > 0 else "NOT_APPLICABLE",
            "calculated_limit": base_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "calculation_version": CALCULATION_VERSION,
            "input_snapshot": {
                "annualized_rev": str(annualized_rev),
                "multiplier": "0.20",
            },
            "evidence_ids": evidence_ids,
            "policy_rule_ids": ["POL-WC-001"],
            "confidence": 0.85 if base_limit > 0 else 0.0,
            "warnings": [],
            "limitations": ["Subject to quarterly turnover verification"],
        }

    @classmethod
    def term_loan(cls, features: Dict[str, Any]) -> Dict[str, Any]:
        """Term loan based on Net Operating Surplus (NOI) and reducing-balance amortization over 36 months at 14% p.a."""
        bank = features.get("bank_metrics", {})
        monthly_inflows = Decimal(str(bank.get("avg_monthly_credits", features.get("banking_inflow_inr", features.get("monthly_revenue_inr", 0)))))
        monthly_outflows = Decimal(str(bank.get("avg_monthly_debits", features.get("banking_outflow_inr", features.get("monthly_expenses_inr", 0)))))

        free_cash_flow = monthly_inflows - monthly_outflows

        # Use 50% of monthly free cash flow as supportable monthly EMI for new term debt
        if free_cash_flow > 0:
            supportable_emi = free_cash_flow * Decimal("0.50")
            limit = cls._calculate_loan_from_emi(supportable_emi, Decimal("0.14"), 36)
        else:
            supportable_emi = Decimal("0.00")
            limit = Decimal("0.00")

        evidence_ids = features.get("authoritative_evidence_ids", [])

        return {
            "method": "TERM_LOAN",
            "applicability": "APPLICABLE" if limit > 0 else "NOT_APPLICABLE",
            "calculated_limit": limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "calculation_version": CALCULATION_VERSION,
            "input_snapshot": {
                "monthly_inflows": str(monthly_inflows),
                "monthly_outflows": str(monthly_outflows),
                "free_cash_flow": str(free_cash_flow),
                "supportable_emi": str(supportable_emi),
                "tenure_months": "36",
                "annual_rate": "0.14"
            },
            "evidence_ids": evidence_ids,
            "policy_rule_ids": ["POL-TL-001"],
            "confidence": 0.85 if limit > 0 else 0.0,
            "warnings": [] if limit > 0 else ["Insufficient net operating cash flow for term loan servicing"],
            "limitations": ["Calculated using exact reducing-balance amortization at 14% p.a. over 36 months"],
        }

    @classmethod
    def calculate_all_limits(cls, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        limits = [
            cls.receivables_finance(features),
            cls.working_capital_line(features),
            cls.term_loan(features),
        ]
        return [limit for limit in limits if limit["applicability"] == "APPLICABLE"]
