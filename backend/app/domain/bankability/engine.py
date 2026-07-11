from decimal import Decimal
from typing import Dict, Any


def generate_bankability_path(
    case_id: str,
    current_fhi: Decimal,
    dscr: Decimal,
    compliance_score: Decimal,
    annual_revenue: Decimal = Decimal("0"),
) -> Dict[str, Any]:
    if current_fhi < Decimal("40"):
        return {
            "status": "NOT_BANKABLE",
            "actions": ["Require 12 months consecutive positive cash flow"],
        }

    if compliance_score < Decimal("50"):
        return {
            "status": "CONDITIONALLY_BANKABLE",
            "actions": ["Mandatory GST reconciliation audit"],
        }

    if dscr < Decimal("1.3"):
        equity_injection = annual_revenue * Decimal("0.15")
        return {
            "status": "CONDITIONALLY_BANKABLE",
            "actions": [
                f"Inject ₹{equity_injection:,.2f} equity or subordinate debt before sanction"
            ],
        }

    return {"status": "BANKABLE_PRIME", "actions": []}
