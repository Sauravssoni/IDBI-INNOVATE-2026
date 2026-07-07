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
