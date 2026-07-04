from typing import Dict, Any, List
from decimal import Decimal

class SafeLimitEngine:
    """
    Product-specific capacity strategies for prototype demonstration.
    NOTE: These are configurable sandbox policy assumptions, not IDBI production policy.
    """
    
    @staticmethod
    def receivables_finance(features: Dict[str, Any]) -> Dict[str, Any]:
        """Receivables-backed limit"""
        receivables_metrics = features.get("invoice_metrics", {})
        eligible_receivables = Decimal(str(receivables_metrics.get("eligible_amount", 0)))
        advance_rate = Decimal("0.75") # 75% advance rate
        
        limit = eligible_receivables * advance_rate
        
        return {
            "method": "RECEIVABLES_FINANCE",
            "applicability": "NOT_APPLICABLE" if limit <= 0 else "APPLICABLE",
            "calculated_limit": limit,
            "calculation_version": "1.0",
            "input_snapshot": {"eligible_receivables": str(eligible_receivables), "advance_rate": str(advance_rate)},
            "evidence_ids": [], # In a real system, track specific invoice IDs
            "policy_rule_ids": ["POL-REC-001"],
            "confidence": 0.8,
            "warnings": [],
            "limitations": ["Assumes uniform advance rate"]
        }

    @staticmethod
    def working_capital_line(features: Dict[str, Any]) -> Dict[str, Any]:
        """Working Capital Line based on Turnover and Cash Conversion"""
        gst = features.get("gst_metrics", {})
        avg_monthly_rev = Decimal(str(gst.get("avg_monthly_revenue", 0)))
        annualized_rev = avg_monthly_rev * Decimal("12")
        
        # 20% of projected turnover method (Nayak Committee style heuristic)
        base_limit = annualized_rev * Decimal("0.20")
        
        return {
            "method": "WORKING_CAPITAL_LINE",
            "applicability": "APPLICABLE" if base_limit > 0 else "NOT_APPLICABLE",
            "calculated_limit": base_limit,
            "calculation_version": "1.0",
            "input_snapshot": {"annualized_rev": str(annualized_rev), "multiplier": "0.20"},
            "evidence_ids": [],
            "policy_rule_ids": ["POL-WC-001"],
            "confidence": 0.85,
            "warnings": [],
            "limitations": ["Heuristic based"]
        }

    @staticmethod
    def term_loan(features: Dict[str, Any]) -> Dict[str, Any]:
        """Term loan based on Free Cash Flow and DSCR"""
        bank = features.get("bank_metrics", {})
        monthly_inflows = Decimal(str(bank.get("avg_monthly_credits", 0)))
        monthly_outflows = Decimal(str(bank.get("avg_monthly_debits", 0)))
        
        free_cash_flow = monthly_inflows - monthly_outflows
        
        # Assuming 50% of FCF can be used for new debt service over 36 months at ~12%
        # Rough heuristic limit
        if free_cash_flow > 0:
            limit = (free_cash_flow * Decimal("0.50")) * Decimal("36")
        else:
            limit = Decimal("0")
            
        return {
            "method": "TERM_LOAN",
            "applicability": "APPLICABLE" if limit > 0 else "NOT_APPLICABLE",
            "calculated_limit": limit,
            "calculation_version": "1.0",
            "input_snapshot": {"fcf": str(free_cash_flow)},
            "evidence_ids": [],
            "policy_rule_ids": ["POL-TL-001"],
            "confidence": 0.75,
            "warnings": ["Rough heuristic calculation"],
            "limitations": []
        }

    @classmethod
    def calculate_all_limits(cls, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        limits = [
            cls.receivables_finance(features),
            cls.working_capital_line(features),
            cls.term_loan(features)
        ]
        return [limit for limit in limits if limit["applicability"] == "APPLICABLE"]
