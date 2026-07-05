import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.orm.users import User, UserRole
from app.db.orm.org import Region, Branch
from app.db.orm.cases import Case, CaseStatus, Business, ProductType, IdempotencyRecord
from app.api.auth import get_password_hash

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def login(email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    return response

def get_cookie_from_response(response, cookie_name):
    for cookie in response.headers.get_list("set-cookie"):
        if cookie.startswith(f"{cookie_name}="):
            return cookie.split(";")[0].split("=")[1]
    return ""

@pytest.fixture(scope="module")
def setup_idemp_data(db_session):
    unique_suffix = str(uuid.uuid4())[:8]
    
    r = Region(code=f"REG_{unique_suffix}", name="Test Region")
    db_session.add(r)
    db_session.flush()
    
    b = Branch(code=f"B1_{unique_suffix}", name="Branch 1", region_id=r.id)
    db_session.add(b)
    db_session.flush()
    
    email = f"analyst_{unique_suffix}@example.com"
    u = User(
        email=email,
        hashed_password=get_password_hash("securepass123"),
        full_name="Test Analyst",
        role=UserRole.CREDIT_ANALYST,
        is_active=True
    )
    db_session.add(u)
    db_session.flush()
    
    biz = Business(business_id=f"BIZ_{unique_suffix}", legal_name="Biz", sector="Retail")
    db_session.add(biz)
    db_session.flush()
    
    case1 = Case(
        business_id_fk=biz.id,
        requested_product=ProductType.WORKING_CAPITAL_LINE,
        requested_amount=100000,
        status=CaseStatus.INITIATED,
        originating_branch_id=b.id,
        assigned_credit_analyst_id=u.id,
        version=1
    )
    case2 = Case(
        business_id_fk=biz.id,
        requested_product=ProductType.WORKING_CAPITAL_LINE,
        requested_amount=100000,
        status=CaseStatus.INITIATED,
        originating_branch_id=b.id,
        assigned_credit_analyst_id=u.id,
        version=1
    )
    db_session.add(case1)
    db_session.add(case2)
    db_session.commit()
    
    yield {
        "user": u,
        "case1": case1,
        "case2": case2
    }
    
    # Cleanup
    from app.db.orm.cases import AuditEvent
    db_session.query(AuditEvent).filter(AuditEvent.actor == str(u.id)).delete()
    db_session.query(IdempotencyRecord).filter(IdempotencyRecord.user_id == u.id).delete()
    db_session.query(Case).filter(Case.id.in_([case1.id, case2.id])).delete()
    db_session.query(Business).filter(Business.id == biz.id).delete()
    from app.db.orm.users import SessionStore
    db_session.query(SessionStore).filter(SessionStore.user_id == u.id).delete()
    db_session.query(User).filter(User.id == u.id).delete()
    db_session.query(Branch).filter(Branch.id == b.id).delete()
    db_session.query(Region).filter(Region.id == r.id).delete()
    db_session.commit()

def test_idempotency_returns_cached_response(setup_idemp_data):
    login_resp = login(setup_idemp_data["user"].email, "securepass123")
    cookies = {"vyapar_session_token": get_cookie_from_response(login_resp, "vyapar_session_token")}
    csrf = get_cookie_from_response(login_resp, "vyapar_csrf_token")
    headers = {"x-csrf-token": csrf}
    
    case_id = str(setup_idemp_data["case1"].id)
    idem_key = f"idem-key-{uuid.uuid4()}"
    headers["Idempotency-Key"] = idem_key
    
    # First request
    resp1 = client.post(
        f"/api/cases/{case_id}/evaluate",
        json={"expected_version": 1},
        cookies=cookies,
        headers=headers
    )
    assert resp1.status_code == 200
    
    # Second request with identical key and payload
    resp2 = client.post(
        f"/api/cases/{case_id}/evaluate",
        json={"expected_version": 1},
        cookies=cookies,
        headers=headers
    )
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()

def test_idempotency_mismatched_payload_fails(setup_idemp_data):
    login_resp = login(setup_idemp_data["user"].email, "securepass123")
    cookies = {"vyapar_session_token": get_cookie_from_response(login_resp, "vyapar_session_token")}
    csrf = get_cookie_from_response(login_resp, "vyapar_csrf_token")
    headers = {"x-csrf-token": csrf}
    
    case_id = str(setup_idemp_data["case2"].id) # Use case 2 which is fresh (version 1)
    idem_key = f"idem-key-{uuid.uuid4()}"
    headers["Idempotency-Key"] = idem_key
    
    # First request
    resp1 = client.post(
        f"/api/cases/{case_id}/evaluate",
        json={"expected_version": 1},
        cookies=cookies,
        headers=headers
    )
    assert resp1.status_code == 200
    
    # Second request with identical key but different payload
    resp2 = client.post(
        f"/api/cases/{case_id}/evaluate",
        json={"expected_version": 2}, # Different payload
        cookies=cookies,
        headers=headers
    )
    assert resp2.status_code == 409
    assert "Idempotency key mismatch with payload" in resp2.json()["detail"]

def test_stale_case_version_returns_structured_409(setup_idemp_data):
    login_resp = login(setup_idemp_data["user"].email, "securepass123")
    cookies = {"vyapar_session_token": get_cookie_from_response(login_resp, "vyapar_session_token")}
    csrf = get_cookie_from_response(login_resp, "vyapar_csrf_token")
    headers = {"x-csrf-token": csrf, "Idempotency-Key": str(uuid.uuid4())}
    
    # We will use case 1, which was already evaluated in the first test and is now version 2!
    case_id = str(setup_idemp_data["case1"].id)
    
    # We send expected_version: 1, which is OUTDATED. This simulates a concurrent update where we read version 1 but someone else already bumped it.
    resp = client.post(
        f"/api/cases/{case_id}/evaluate",
        json={"expected_version": 1},
        cookies=cookies,
        headers=headers
    )
    
    assert resp.status_code == 409
    data = resp.json()["detail"]
    assert data["code"] == "STALE_VERSION"
    assert "current_version" in data
    assert "message" in data
    assert "retryable" in data
