import json
import os
import random
from decimal import Decimal
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.core.decision.limits import SafeLimitEngine
from backend.app.core.scoring.scorer import ScoringEngine


def generate_validation():
    os.makedirs("artifacts", exist_ok=True)
    random.seed(1001)

    cases = []
    scores = []

    product_types = [
        "WORKING_CAPITAL_LINE",
        "TERM_LOAN",
        "RECEIVABLES_FINANCE",
        "EQUIPMENT_FINANCE",
        "BUSINESS_CREDIT_CARD",
    ]

    for i in range(1, 1001):
        req_amt = random.randint(1_000_000, 50_000_000)
        req_prod = random.choice(product_types)

        # Base numbers
        rev = random.randint(5_000_000, 200_000_000)
        in_flow = int(rev / 12) * random.uniform(0.9, 1.2)
        out_flow = in_flow * random.uniform(0.6, 1.1)

        # Existing EMI
        emi = int(in_flow * random.uniform(0, 0.4))

        case_id = f"VAL_{i:04d}"

        features = {
            "bank_metrics": {
                "operating_inflows_monthly": in_flow,
                "operating_outflows_monthly": out_flow,
            },
            "gst_metrics": {"taxable_turnover": rev},
            "obligation_verification_state": "VERIFIED_OBLIGATIONS",
            "verified_existing_debt_service_monthly": emi,
            "bureau_metrics": {
                "score": random.randint(600, 850),
                "vintage_months": random.randint(12, 120),
                "total_active_tradelines": random.randint(1, 10),
            },
            "business_metrics": {"vintage_months": random.randint(12, 120)},
            "tax_metrics": {"monthly_gst_filing_compliance": random.uniform(0.5, 1.0)},
            "identity_state": "VERIFIED",
            "integrity_state": "VERIFIED",
        }

        # Calculate scores
        scorer = ScoringEngine(features)
        computed_scores = scorer.compute_all_scores()
        vyapar_score = computed_scores.get("vyapar_credit_health_score")
        if vyapar_score is None:
            vyapar_score = 0
        scores.append(vyapar_score)

        # Calculate limits
        try:
            limits = SafeLimitEngine.compute_limit(
                features, Decimal(str(req_amt)), req_prod
            )
            supportable = float(limits.get("supportable_amount", 0))
            binding = limits.get("binding_constraint", "UNKNOWN")
        except Exception as e:
            supportable = 0
            binding = str(e)

        case_data = {
            "case_id": case_id,
            "requested_amount": float(req_amt),
            "requested_product": req_prod,
            "features": features,
            "vyapar_score": vyapar_score,
            "supportable_amount": supportable,
            "binding_constraint": binding,
        }
        cases.append(case_data)

    # Build density array
    density = {
        "0-300": len([s for s in scores if s < 300]),
        "300-500": len([s for s in scores if 300 <= s < 500]),
        "500-650": len([s for s in scores if 500 <= s < 650]),
        "650-800": len([s for s in scores if 650 <= s < 800]),
        "800-1000": len([s for s in scores if s >= 800]),
    }

    output = {
        "metadata": {"count": 1000, "seed": 1001, "density_array": density},
        "cases": cases,
    }

    with open("artifacts/validation_certified_1000.json", "w") as f:
        json.dump(output, f, indent=2)

    print(json.dumps(density, indent=2))
    print("Generated artifacts/validation_certified_1000.json successfully.")


if __name__ == "__main__":
    generate_validation()
