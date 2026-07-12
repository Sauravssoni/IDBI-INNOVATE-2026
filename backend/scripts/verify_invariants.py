import json
import os
import sys
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.decision.limits import SafeLimitEngine

def verify_invariants():
    manifest_path = "artifacts/validation/cohort_manifest.json"
    if not os.path.exists(manifest_path):
        print("Manifest not found. Run generate_cohort_manifest.py first.")
        sys.exit(1)
        
    with open(manifest_path, "r") as f:
        cases = json.load(f)
        
    print(f"Loaded {len(cases)} cases for invariant verification.")
    
    passed = 0
    failed = 0
    
    for case in cases:
        cid = case["case_id"]
        req_amt = Decimal(str(case["requested_amount"]))
        req_prod = case["requested_product"]
        features = case["features"]
        
        try:
            # Build the bridge
            bridge = SafeLimitEngine.build_limit_bridge(
                features=features,
                requested_product=req_prod,
                requested_amount=req_amt,
                tenure_months=case.get("tenure_months", 36),
                annual_rate=Decimal(str(case.get("annual_rate", "0.135")))
            )
            
            final_amt = Decimal(str(bridge["final_supportable_amount"]))
            
            # Invariant 1: Final amount <= Requested amount
            assert final_amt <= req_amt, f"Invariant failed: Final amount {final_amt} > Requested {req_amt}"
            
            # Invariant 2: At least one stage must be applied
            applied_stages = [s for s in bridge["stages"] if s["applied"]]
            assert len(applied_stages) > 0, "Invariant failed: No stage applied!"
            
            # Invariant 3: The final amount must match the value of the final binding stage
            binding_stage = next((s for s in bridge["stages"] if s["stage_id"] == bridge["binding_constraint"]), None)
            if binding_stage:
                assert Decimal(str(binding_stage["calculated_value"])) == final_amt, "Invariant failed: Binding constraint mismatch"
                
            print(f"[PASS] {cid} - Requested: {req_amt}, Final: {final_amt}, Binding: {bridge['binding_constraint']}")
            passed += 1
            
        except AssertionError as e:
            print(f"[FAIL] {cid} - {str(e)}")
            failed += 1
        except Exception as e:
            print(f"[FAIL] {cid} - Exception: {str(e)}")
            failed += 1
            
    print(f"\nVerification Complete: {passed} passed, {failed} failed.")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    verify_invariants()
