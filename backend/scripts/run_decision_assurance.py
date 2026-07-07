import os
import sys
import json
import os
from decimal import Decimal

def run():
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from app.db.session import SessionLocal
    from app.db.orm.cases import Case, Business

    db = SessionLocal()
    cases = db.query(Case).join(Business).all()
    
    results = []
    
    for case in cases:
        b = case.business
        
        results.append({
            "business_id": b.business_id,
            "legal_name": b.legal_name,
            "status": case.status.value,
            "requested_amount": float(case.requested_amount),
            "assessment_result": {
                "dscr": float(case.dscr) if case.dscr else None,
                "recommendation": case.recommendation.value if case.recommendation else None
            }
        })
        
        if b.business_id == "SHAKTI_PRECISION_001":
            assert float(case.requested_amount) == 5000000, "Shakti should request 50 lakh"
            assert case.status.value == "EVIDENCE_GATHERING" or case.status.value == "INITIATED", f"Shakti should be in EVIDENCE_GATHERING, got {case.status.value}"
            
        if b.business_id == "NAVPRERNA_TECH_001":
            assert case.status.value == "ASSESSMENT_COMPLETED", f"Navprerna should be ASSESSMENT_COMPLETED, got {case.status.value}"
            assert case.recommendation and case.recommendation.value == "ADDITIONAL_EVIDENCE_REQUIRED", f"Navprerna should be ADDITIONAL_EVIDENCE_REQUIRED, got {case.recommendation.value if case.recommendation else None}"
            
        if b.business_id == "RANGREZ_TEXTILES_001":
            assert case.status.value == "DECISION_PENDING", f"Rangrez should be DECISION_PENDING, got {case.status.value}"
            # Because run_evaluations submits analyst recommendation
            
        if b.business_id == "AAROHAN_INFRA_001":
            assert case.status.value == "ASSESSMENT_COMPLETED", f"Aarohan should be ASSESSMENT_COMPLETED, got {case.status.value}"
            assert case.recommendation and case.recommendation.value == "DECLINE_RECOMMENDED", f"Aarohan should be DECLINE_RECOMMENDED, got {case.recommendation.value if case.recommendation else None}"

    assurance_data = {
        "title": "Decision Assurance Report",
        "cases": results,
    }
    
    print(json.dumps(assurance_data, indent=2))
    
    os.makedirs("/Users/tzar/Desktop/Idbi/vyapar-pulse-starter/artifacts", exist_ok=True)
    with open("/Users/tzar/Desktop/Idbi/vyapar-pulse-starter/artifacts/decision_assurance.json", "w") as f:
        json.dump(assurance_data, f, indent=2)

if __name__ == "__main__":
    run()
