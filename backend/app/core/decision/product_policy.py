from enum import Enum
from pydantic import BaseModel
from decimal import Decimal

class ProductType(str, Enum):
    WORKING_CAPITAL_LINE = "WORKING_CAPITAL_LINE"
    RECEIVABLES_FINANCE = "RECEIVABLES_FINANCE"
    TERM_LOAN = "TERM_LOAN"
    EQUIPMENT_FINANCE = "EQUIPMENT_FINANCE"

class ProductPolicy(BaseModel):
    policy_version: str
    min_dscr: Decimal
    min_rate_annual: Decimal
    max_rate_annual: Decimal
    min_tenor_months: int
    max_tenor_months: int
    maximum_exposure: Decimal
    receivable_advance_rate: Decimal
    equipment_ltv: Decimal
    stress_revenue_drop: Decimal
    stress_cost_increase: Decimal
    stress_rate_hike_bps: int
    concentration_haircut: Decimal

def get_product_policy(product: ProductType) -> ProductPolicy:
    common_stress = {
        "stress_revenue_drop": Decimal("0.10"),
        "stress_cost_increase": Decimal("0.05"),
        "stress_rate_hike_bps": 200,
        "concentration_haircut": Decimal("0.50"),
    }
    
    if product == ProductType.WORKING_CAPITAL_LINE:
        return ProductPolicy(
            policy_version="1.0",
            min_dscr=Decimal("1.25"),
            min_rate_annual=Decimal("0.09"),
            max_rate_annual=Decimal("0.15"),
            min_tenor_months=12,
            max_tenor_months=36,
            maximum_exposure=Decimal("50000000.00"),
            receivable_advance_rate=Decimal("0.0"),
            equipment_ltv=Decimal("0.0"),
            **common_stress
        )
    elif product == ProductType.RECEIVABLES_FINANCE:
        return ProductPolicy(
            policy_version="1.0",
            min_dscr=Decimal("1.20"),
            min_rate_annual=Decimal("0.08"),
            max_rate_annual=Decimal("0.14"),
            min_tenor_months=1,
            max_tenor_months=12,
            maximum_exposure=Decimal("100000000.00"),
            receivable_advance_rate=Decimal("0.80"),
            equipment_ltv=Decimal("0.0"),
            **common_stress
        )
    elif product == ProductType.TERM_LOAN:
        return ProductPolicy(
            policy_version="1.0",
            min_dscr=Decimal("1.35"),
            min_rate_annual=Decimal("0.10"),
            max_rate_annual=Decimal("0.18"),
            min_tenor_months=12,
            max_tenor_months=60,
            maximum_exposure=Decimal("50000000.00"),
            receivable_advance_rate=Decimal("0.0"),
            equipment_ltv=Decimal("0.0"),
            **common_stress
        )
    elif product == ProductType.EQUIPMENT_FINANCE:
        return ProductPolicy(
            policy_version="1.0",
            min_dscr=Decimal("1.30"),
            min_rate_annual=Decimal("0.09"),
            max_rate_annual=Decimal("0.16"),
            min_tenor_months=12,
            max_tenor_months=84,
            maximum_exposure=Decimal("100000000.00"),
            receivable_advance_rate=Decimal("0.0"),
            equipment_ltv=Decimal("0.75"),
            **common_stress
        )
    else:
        raise ValueError(f"Unknown product type: {product}")
