import json
import os
import sys
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.app.validation.invariant_checker import run_validation_suite

def generate_validation():
    os.makedirs("artifacts/validation", exist_ok=True)
    
    results = run_validation_suite()
    
    from collections import Counter
    cases = __import__("backend.app.validation.invariant_checker", fromlist=["generate_synthetic_features"]).generate_synthetic_features()
    profiles = [c["_test_profile"] for c in cases]
    products = [c["_test_product"] for c in cases]
    profile_distribution = dict(Counter(profiles))
    product_distribution = dict(Counter(products))
        
    output = {
        "seed": 20260713,
        "cohort_size": results["total_cases"],
        "profile_distribution": profile_distribution,
        "product_distribution": product_distribution,
        "case_invariant_executions": results["invariants_passed"] + results["invariants_failed"],
        "cases_with_no_recorded_failure": results["invariants_passed"],
        "case_level_failures": results["invariants_failed"],
        "failed_case_ids": [f["case_index"] for f in results["failures"]],
        "checksum": results["deterministic_checksum"],
        "engine_replay_cases": len(results.get("replay_results", [])),
        "engine_replay_failures": sum(1 for r in results.get("replay_results", []) if r["replay_status"] != "REPLAY_MATCHED"),
        "replay_details": [
            {
                "case_id": r["case_id"],
                "package_hash_verified": r["package_hash_verified"],
                "replay_status": r["replay_status"],
                "mismatch_fields": r["mismatch_fields"]
            } for r in results.get("replay_results", [])
        ],
        "generator_version": "v2.0"
    }
    
    with open("artifacts/validation/release_assurance.json", "w") as f:
        json.dump(output, f, indent=2)
        
    print("Generated artifacts/validation/release_assurance.json successfully.")

if __name__ == "__main__":
    generate_validation()
