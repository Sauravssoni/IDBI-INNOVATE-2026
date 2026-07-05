import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import UUID

from app.main import app
from app.db.session import SessionLocal
from app.seed.seed_shakti import seed_shakti
from app.db.orm.cases import Case

from app.db.session import engine
from app.db.orm.cases import Base

@pytest.fixture(scope="module", autouse=True)
def setup_shakti_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_shakti()
    yield

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client():
    return TestClient(app)

def get_cookie_from_response(response, cookie_name):
    return response.cookies.get(cookie_name) or ""

def get_auth_headers(client: TestClient, email: str):
    response = client.post("/api/auth/login", json={
        "email": email,
        "password": "password123"
    })
    assert response.status_code == 200, f"Failed to login {email}: {response.text}"
    session_token = get_cookie_from_response(response, "vyapar_session_token")
    csrf_token = get_cookie_from_response(response, "vyapar_csrf_token")
    
    return {
        "cookies": {"vyapar_session_token": session_token},
        "headers": {"x-csrf-token": csrf_token}
    }

def test_shakti_end_to_end(client: TestClient, db: Session):
    # 1. RM logs in and sees the case
    rm_auth = get_auth_headers(client, "rm@bank.example")
    client.cookies.clear()
    client.cookies.update(rm_auth["cookies"])
    res = client.get("/api/cases", headers=rm_auth["headers"])
    assert res.status_code == 200, res.text
    cases = res.json()
    assert len(cases) > 0
    case_id = cases[0]["id"]
    
    # 2. Analyst logs in and evaluates
    analyst_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.clear()
    client.cookies.update(analyst_auth["cookies"])
    
    # Get current version
    res = client.get(f"/api/cases/{case_id}", headers=analyst_auth["headers"])
    assert res.status_code == 200
    case_data = res.json()
    current_version = case_data["version"]
    
    evaluate_req = {"expected_version": current_version}
    idempotency_key_eval = "shakti-eval-12345"
    
    eval_res = client.post(
        f"/api/cases/{case_id}/evaluate", 
        json=evaluate_req, 
        headers={**analyst_auth["headers"], "Idempotency-Key": idempotency_key_eval}
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    
    # Ensure idempotency cache works
    eval_res_2 = client.post(
        f"/api/cases/{case_id}/evaluate", 
        json=evaluate_req, 
        headers={**analyst_auth["headers"], "Idempotency-Key": idempotency_key_eval}
    )
    assert eval_res_2.status_code == 200
    assert eval_res_2.json() == eval_data

    # 3. Analyst submits recommendation
    # Re-fetch for updated version
    res = client.get(f"/api/cases/{case_id}", headers=analyst_auth["headers"])
    current_version = res.json()["version"]
    
    rec_req = {
        "recommendation": "RECOMMEND_AS_REQUESTED",
        "reason": "Strong financials and good GST compliance.",
        "expected_version": current_version
    }
    idempotency_key_rec = "shakti-rec-12345"
    rec_res = client.post(
        f"/api/cases/{case_id}/analyst-recommendation",
        json=rec_req,
        headers={**analyst_auth["headers"], "Idempotency-Key": idempotency_key_rec}
    )
    assert rec_res.status_code == 200, rec_res.text
    
    # 4. Sanctioning Authority logs in and makes human decision
    sa_auth = get_auth_headers(client, "sa@bank.example")
    client.cookies.clear()
    client.cookies.update(sa_auth["cookies"])
    
    res = client.get(f"/api/cases/{case_id}", headers=sa_auth["headers"])
    assert res.status_code == 200
    current_version = res.json()["version"]
    
    dec_req = {
        "decision": "APPROVE_AS_REQUESTED",
        "reason": "Mandate sufficient, financials robust. Approved as requested.",
        "expected_version": current_version
    }
    idempotency_key_dec = "shakti-dec-12345"
    
    dec_res = client.post(
        f"/api/cases/{case_id}/human-decision",
        json=dec_req,
        headers={**sa_auth["headers"], "Idempotency-Key": idempotency_key_dec}
    )
    
    # If the case wasn't assigned to the SA, or if SA branch mandate isn't correctly set, this might fail with 403.
    # But SA has a valid mandate. If they don't have scope_role in UserBranchScope, they can't view it!
    # Let's ensure the test passes. If 403, we need to fix seed_shakti.py to give SA branch access or assign them.
    assert dec_res.status_code == 200, f"Expected 200, got {dec_res.status_code}: {dec_res.text}"
    
    # Check audit log via Auditor
    auditor_auth = get_auth_headers(client, "auditor@bank.example")
    client.cookies.clear()
    client.cookies.update(auditor_auth["cookies"])
    audit_res = client.get(f"/api/cases/{case_id}/audit", headers=auditor_auth["headers"])
    
    # The /audit endpoint might not exist yet? If not, we check DB directly
    if audit_res.status_code == 404:
        from app.db.orm.cases import AuditEvent
        events = db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.event_sequence).all()
        assert len(events) >= 3
        # Check sequence
        seqs = [e.event_sequence for e in events]
        assert seqs == sorted(seqs)
        # Check hashes
        for i in range(1, len(events)):
            assert events[i].prior_event_hash == events[i-1].event_hash
