from typing import Dict, Any, List
from decimal import Decimal, ROUND_HALF_UP
from app.core.versions import CALCULATION_VERSION


class SafeLimitEngine:
    """
    Product-specific capacity strategies enforcing exact financial formulas,
    reducing-balance amortization, and evidence lineage via FinancialCapacityEngine.
    """

    @staticmethod
    def _calculate_loan_from_emi(monthly_emi: Any, annual_rate: Any, tenure_months: int) -> Decimal:
        emi_dec = Decimal(str(monthly_emi))
        rate_dec = Decimal(str(annual_rate))
        if emi_dec <= 0 or tenure_months <= 0:
            return Decimal("0.00")
        if rate_dec <= 0:
            return (emi_dec * Decimal(tenure_months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rate = rate_dec / Decimal("100") if rate_dec > Decimal("1.0") else rate_dec
        r = rate / Decimal("12")
        factor = (Decimal("1") + r) ** tenure_months
        principal = emi_dec * (factor - Decimal("1")) / (r * factor)
        return principal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_emi_from_loan(principal: Any, annual_rate: Any, tenure_months: int) -> Decimal:
        """
        Exact reducing-balance amortization formula:
        P * r * (1+r)^n / ((1+r)^n - 1)
        """
        p_dec = Decimal(str(principal))
        rate_dec = Decimal(str(annual_rate))
        if p_dec <= 0 or tenure_months <= 0:
            return Decimal("0.00")
        if rate_dec <= 0:
            return (p_dec / Decimal(tenure_months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rate = rate_dec / Decimal("100") if rate_dec > Decimal("1.0") else rate_dec
        r = rate / Decimal("12")
        factor = (Decimal("1") + r) ** tenure_months
        emi = p_dec * r * factor / (factor - Decimal("1"))
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
        from app.domain.financial.engine import FinancialCapacityEngine
        cap = FinancialCapacityEngine.compute_capacity_from_features(features)
        return cap["product_limits"]["RECEIVABLES_FINANCE"]

    @classmethod
    def working_capital_line(cls, features: Dict[str, Any]) -> Dict[str, Any]:
        """Working Capital Line based on verified Turnover and Cash Conversion Headroom"""
        from app.domain.financial.engine import FinancialCapacityEngine
        cap = FinancialCapacityEngine.compute_capacity_from_features(features)
        return cap["product_limits"]["WORKING_CAPITAL_LINE"]

    @classmethod
    def term_loan(cls, features: Dict[str, Any]) -> Dict[str, Any]:
        """Term loan based on Net Operating Surplus and reducing-balance amortization"""
        from app.domain.financial.engine import FinancialCapacityEngine
        cap = FinancialCapacityEngine.compute_capacity_from_features(features)
        return cap["product_limits"]["TERM_LOAN"]

    @classmethod
    def calculate_all_limits(cls, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        from app.domain.financial.engine import FinancialCapacityEngine
        cap = FinancialCapacityEngine.compute_capacity_from_features(features)
        limits = [
            cap["product_limits"]["RECEIVABLES_FINANCE"],
            cap["product_limits"]["WORKING_CAPITAL_LINE"],
            cap["product_limits"]["TERM_LOAN"],
        ]
        return [limit for limit in limits if limit["applicability"] == "APPLICABLE"]
