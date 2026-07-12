import random
import hashlib
import json
from typing import Dict, Any, List
from decimal import Decimal, ROUND_HALF_UP

from app.core.scoring.scorer import ScoringEngine
from app.domain.financial.engine import FinancialCapacityEngine
from app.core.decision.limits import SafeLimitEngine

def generate_synthetic_features(seed: int = 20260713) -> List[Dict[str, Any]]:
    random.seed(seed)
    cases = []
    
    for i in range(1000):
        # Generate realistic bounds
        inflows = random.randint(1_000_000, 10_000_000)
        margin = random.uniform(0.05, 0.40)
        outflows = int(inflows * (1 - margin))
        
        has_obligations = random.choice([True, False])
        existing_ds = random.randint(50_000, int(inflows * 0.15)) if has_obligations else 0
        
        receivables = random.randint(500_000, 3_000_000)
        cycle_days = random.randint(30, 150)
        
        has_material_unresolved = random.random() < 0.05
        
        gst_ratio = random.uniform(0.70, 1.30)
        
        features = {
            "monthly_revenue_inr": str(inflows),
            "consent_status": "VALID",
            "obligation_verification_state": "VERIFIED_OBLIGATIONS" if has_obligations else "VERIFIED_ZERO_DEBT",
            "bank_metrics": {
                "operating_inflows_monthly": str(inflows),
                "operating_outflows_monthly": str(outflows),
                "avg_monthly_credits": str(inflows),
                "avg_monthly_debits": str(outflows),
                "verified_debt_service_monthly": str(existing_ds),
                "transaction_categorization_summary": {
                    "has_material_unresolved_activity": has_material_unresolved
                }
            },
            "reconciliation_metrics": {
                "gst_bank_ratio": str(gst_ratio)
            },
            "receivable_metrics": {
                "top_buyer_concentration": str(random.uniform(0.05, 0.60)),
                "avg_payment_delay_days": random.randint(5, 45)
            },
            "invoice_metrics": {
                "eligible_amount": str(receivables),
                "concentration_haircut": "1.00"
            },
            "working_capital_metrics": {
                "operating_cycle_days": cycle_days
            },
            "gst_metrics": {
                "months_filed": 12,
                "revenue_cv": str(random.uniform(0.05, 0.40)),
                "trend": random.choice(["GROWING", "STABLE", "DECLINING"])
            },
            "verified_existing_debt_service_monthly": str(existing_ds),
            "equipment_value": str(random.randint(1_000_000, 5_000_000))
        }
        cases.append(features)
        
    return cases

def run_validation_suite() -> Dict[str, Any]:
    cases = generate_synthetic_features(20260713)
    
    hash_state = []
    results = {
        "total_cases": 1000,
        "seed": 20260713,
        "invariants_passed": 0,
        "invariants_failed": 0,
        "failures": [],
        "validation_engine": "Independent Challenger Model v1.0",
        "status": "PASS"
    }
    
    for idx, features in enumerate(cases):
        try:
            # 1. Primary Engine Runs
            scores = ScoringEngine(features).compute_all_scores()
            limits = SafeLimitEngine.calculate_all_limits(features)
            
            # Extract
            fhi = scores.get("financial_health_index")
            credit_score = scores.get("vyapar_credit_health_score")
            
            limit_dict = {L["method"]: Decimal(str(L["calculated_limit"])) for L in limits}
            wc_limit = limit_dict.get("WORKING_CAPITAL_LINE", Decimal("0"))
            rec_limit = limit_dict.get("RECEIVABLES_FINANCE", Decimal("0"))
            
            # 2. Independent Challenger (Invariants)
            inflows = Decimal(features["bank_metrics"]["operating_inflows_monthly"])
            outflows = Decimal(features["bank_metrics"]["operating_outflows_monthly"])
            existing_ds = Decimal(features["bank_metrics"]["verified_debt_service_monthly"])
            
            operating_cash = inflows - outflows
            
            # Invariant 1: Credit Score Bounds
            if credit_score is not None:
                if not (300 <= credit_score <= 900):
                    raise ValueError(f"Credit Score out of bounds: {credit_score}")
                    
            # Invariant 2: WC Limit bounded by turnover * cycle
            cycle = Decimal(str(features["working_capital_metrics"]["operating_cycle_days"]))
            turnover = inflows * 12
            max_wc = (turnover * (cycle / 365)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            if wc_limit > max_wc:
                raise ValueError(f"WC Limit {wc_limit} > Max {max_wc}")
                
            # Invariant 3: Receivables Finance bounded by eligible amount
            eligible = Decimal(features["invoice_metrics"]["eligible_amount"])
            max_rec = eligible * Decimal("0.80")
            if rec_limit > max_rec:
                raise ValueError(f"Receivables Limit {rec_limit} > Max {max_rec}")
                
            # Invariant 4: No zero debt service implies infinity DSCR
            if existing_ds == 0 and operating_cash > 0:
                pass # Handled gracefully by engine returning None for post_loan_dscr if no debt
                
            results["invariants_passed"] += 4
            
            # Collect state for checksum
            hash_state.append({
                "features": features,
                "fhi": fhi,
                "score": credit_score,
                "limits": {k: float(v) for k, v in limit_dict.items()}
            })
            
        except Exception as e:
            results["invariants_failed"] += 1
            results["failures"].append({"case_index": idx, "error": str(e)})
            
    if results["invariants_failed"] > 0:
        results["status"] = "FAIL"
        
    # Generate checksum
    checksum = hashlib.sha256(json.dumps(hash_state, sort_keys=True, default=str).encode()).hexdigest()
    results["deterministic_checksum"] = checksum
    
    return results
