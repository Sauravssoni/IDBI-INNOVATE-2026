import os
import sys
import uuid
from decimal import Decimal

def run_evaluations():
    # Setup environments

    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import SessionLocal
    from app.db.orm.cases import Case, Business
    from app.db.orm.users import User, UserRole

    client = TestClient(app)
    db = SessionLocal()

    ca_login = client.post("/api/auth/login", json={"email": "credit@bank.example", "password": "demopassword"})
    ca_cookies = ca_login.cookies

    sa_login = client.post("/api/auth/login", json={"email": "sa@bank.example", "password": "demopassword"})
    sa_cookies = sa_login.cookies

    cases = db.query(Case).join(Business).all()
    for case in cases:
        b = case.business
        
        if b.business_id == "SHAKTI_PRECISION_001":
            print(f"Skipping {b.legal_name} (will be evaluated in demo)")
            continue

        print(f"Evaluating {b.legal_name}...")
        eval_resp = client.post(
            f"/api/cases/{case.id}/evaluate",
            headers={
                "Idempotency-Key": f"eval-{case.id}-{uuid.uuid4()}",
                "X-CSRF-Token": ca_cookies.get("vyapar_csrf_token", "")
            },
            cookies=ca_cookies,
            json={"expected_version": case.version}
        )
        if eval_resp.status_code != 200:
            print(f"Evaluation failed for {b.legal_name}:", eval_resp.json())
            continue

        # refresh case from db to get new version
        db.refresh(case)

        if b.business_id == "RANGREZ_TEXTILES_001":
            print(f"Submitting analyst recommendation for {b.legal_name}...")
            rec_resp = client.post(
                f"/api/cases/{case.id}/analyst-recommendation",
                headers={
                    "Idempotency-Key": f"rec-{case.id}-{uuid.uuid4()}",
                    "X-CSRF-Token": ca_cookies.get("vyapar_csrf_token", "")
                },
                cookies=ca_cookies,
                json={
                    "expected_version": case.version,
                    "recommendation": "RECOMMEND_ALTERNATIVE_STRUCTURE",
                    "reason": "Seasonal cash flow requires structured approach.",
                    "supportable_amount": 4000000.00
                }
            )
            if rec_resp.status_code != 200:
                print(f"Recommendation failed for {b.legal_name}:", rec_resp.json())

    print("Evaluations complete.")

if __name__ == "__main__":
    run_evaluations()
