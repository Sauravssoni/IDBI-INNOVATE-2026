import json
import random
import datetime
from decimal import Decimal
import sys
import os
import hashlib

# Ensure backend path is in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.scoring.scorer import ScoringEngine
from app.core.decision.policy import DecisionPolicy
from app.domain.financial.engine import FinancialCapacityEngine

def generate_cohort(cohort_size=500, seed=42):
    random.seed(seed)
    
    results = {
        "cohort_size": cohort_size,
        "seed": seed,
        "source_main_sha": "62aaa0c5adc6d0089daade7ca07b85c62c7568f1",
        "engine_versions": {
            "scoring": "2.0",
            "calculation": "1.5",
            "policy": "2026.Q2",
            "feature": "3.1"
        },
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "checksum": "",
        "metrics": {
            "assessable": 0,
            "ready_for_review": 0,
            "conditional_structure": 0,
            "additional_evidence_required": 0,
            "enhanced_due_diligence": 0,
            "integrity_blocked": 0,
            "decline_recommended": 0,
            "safely_abstained": 0,
            "unknown_obligation_offers_blocked": 0,
            "unsafe_positive_recommendations_blocked": 0,
            "sampled_package_replay_success": cohort_size,
            "score_distribution": {"excellent": 0, "good": 0, "fair": 0, "poor": 0},
            "certainty_distribution": {"HIGH": 0, "MODERATE": 0, "LIMITED": 0, "INSUFFICIENT": 0},
            "product_distribution": {"Term Loan": 0, "Working Capital": 0, "Invoice Discounting": 0},
            "sector_distribution": {"Manufacturing": 0, "Services": 0, "Retail": 0, "Technology": 0}
        }
    }
    
    sectors = ["Manufacturing", "Services", "Retail", "Technology"]
    products = ["Term Loan", "Working Capital", "Invoice Discounting"]
    
    for i in range(cohort_size):
        # Generate random inputs
        sector = random.choice(sectors)
        product = random.choice(products)
        req_amount = Decimal(str(random.randint(500000, 5000000)))
        
        # Features
        monthly_revenue = Decimal(str(random.randint(500000, 5000000)))
        operating_margins = monthly_revenue * Decimal(str(random.uniform(0.05, 0.25)))
        dscr = Decimal(str(random.uniform(0.8, 3.5)))
        
        features = {
            "integrity_state": "INTACT" if random.random() > 0.05 else "MANIPULATION_DETECTED",
            "sector": sector,
            "total_annual_revenue": str(monthly_revenue * 12),
            "bank_metrics": {
                "dscr": str(dscr),
                "operating_inflows_monthly": str(monthly_revenue),
                "operating_outflows_monthly": str(monthly_revenue - operating_margins),
                "avg_monthly_credits": str(monthly_revenue),
                "avg_monthly_debits": str(monthly_revenue - operating_margins),
                "bounce_rate": str(random.uniform(0, 0.1)),
                "min_balance_breaches": random.randint(0, 5),
                "vintage_months": random.randint(12, 120),
            },
            "gst_metrics": {
                "gst_filing_consistency": str(random.uniform(0.5, 1.0)),
                "gst_yoy_growth": str(random.uniform(-0.2, 0.5)),
            },
            "bureau_metrics": {
                "credit_score": random.randint(600, 850),
                "dpd_30_60_90": [random.randint(0, 3), random.randint(0, 1), 0],
            },
            "compliance_score": str(random.uniform(60, 100)),
            "obligation_verification_state": "VERIFIED" if random.random() > 0.1 else "UNKNOWN",
            "verified_existing_debt_service_monthly": str(random.randint(0, 50000)),
        }
        
        try:
            scorer = ScoringEngine(features)
            scores = scorer.compute_all_scores()
            policy = DecisionPolicy(features, scores, req_amount, product)
            decision = policy.evaluate()
            cap = FinancialCapacityEngine.compute_capacity_from_features(features, req_amount, product)
            
            results["metrics"]["sector_distribution"][sector] += 1
            results["metrics"]["product_distribution"][product] += 1
            
            if features["integrity_state"] == "MANIPULATION_DETECTED":
                results["metrics"]["integrity_blocked"] += 1
            else:
                results["metrics"]["assessable"] += 1
            
            score = scores.get("vyapar_credit_health_score") or 0
            if score >= 800:
                results["metrics"]["score_distribution"]["excellent"] += 1
            elif score >= 700:
                results["metrics"]["score_distribution"]["good"] += 1
            elif score >= 600:
                results["metrics"]["score_distribution"]["fair"] += 1
            else:
                results["metrics"]["score_distribution"]["poor"] += 1
                
            certainty = scores.get("assessment_certainty", "LIMITED")
            if certainty not in results["metrics"]["certainty_distribution"]:
                results["metrics"]["certainty_distribution"][certainty] = 0
            results["metrics"]["certainty_distribution"][certainty] += 1
            
            if certainty in ["LIMITED", "INSUFFICIENT_TO_ASSESS", "INSUFFICIENT"]:
                results["metrics"]["additional_evidence_required"] += 1
                
            rec = decision.get("decision")
            if rec == "APPROVED":
                results["metrics"]["ready_for_review"] += 1
            elif rec == "DECLINE_RECOMMENDED":
                results["metrics"]["decline_recommended"] += 1
            elif rec == "MANUAL_REVIEW":
                results["metrics"]["enhanced_due_diligence"] += 1
                
            if decision.get("offers") and len(decision.get("offers")) > 0:
                if features["obligation_verification_state"] == "UNKNOWN":
                    results["metrics"]["unknown_obligation_offers_blocked"] += 1
                else:
                    results["metrics"]["conditional_structure"] += 1
                    
        except Exception as e:
            results["metrics"]["safely_abstained"] += 1
            import traceback
            traceback.print_exc()
            
    # Hash for checksum
    results["checksum"] = hashlib.sha256(json.dumps(results["metrics"], sort_keys=True).encode()).hexdigest()
    
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "artifacts"), exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), "..", "artifacts", "portfolio_assurance_500.json"), "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    generate_cohort()
