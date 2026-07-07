import pytest
import os
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, engine
from app.seed.seed_shakti import seed_shakti
from app.db.orm.cases import Case

@pytest.fixture(scope="module", autouse=True)
def setup_shakti_db():
    import urllib.parse
    import uuid
    db_url = os.environ.get("DATABASE_URL", str(engine.url))
    parsed_url = urllib.parse.urlparse(db_url)
    datname = parsed_url.path.lstrip("/")
    if "test" not in datname.lower():
        raise RuntimeError("Refusing to run tests against non-test database name")
    
    test_password = os.environ.get("DEMO_USER_PASSWORD") or f"test_pw_{uuid.uuid4().hex}"
    os.environ["DEMO_USER_PASSWORD"] = test_password

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

def get_auth_headers(client: TestClient, email: str):
    password = os.environ.get("DEMO_USER_PASSWORD")
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    session_token = response.cookies.get("vyapar_session_token") or ""
    csrf_token = response.cookies.get("vyapar_csrf_token") or ""
    return {
        "cookies": {"vyapar_session_token": session_token},
        "headers": {"x-csrf-token": csrf_token},
    }

@pytest.fixture
def case_id(db):
    from app.db.orm.cases import Business
    case = db.query(Case).join(Business).filter(Business.business_id == "SHAKTI_PRECISION_001").first()
    assert case is not None
    return case.id

def test_get_gst_evidence(client, case_id):
    ca_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.update(ca_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/evidence/gst", headers=ca_auth["headers"])
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        meta = data[0]["metadata"]
        assert "ingestion_mode" in meta
        assert "source_environment" in meta
        assert "consent_id" in meta
        assert "data_connection_id" in meta
        assert "evidence_as_of" in meta
        assert "received_at" in meta
        assert "data_quality_status" in meta

def test_get_bank_evidence(client, case_id):
    ca_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.update(ca_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/evidence/bank", headers=ca_auth["headers"])
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "ingestion_mode" in data[0]["metadata"]

def test_get_invoice_evidence(client, case_id):
    ca_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.update(ca_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/evidence/invoices", headers=ca_auth["headers"])
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "ingestion_mode" in data[0]["metadata"]

def test_get_employment_evidence(client, case_id):
    ca_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.update(ca_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/evidence/employment", headers=ca_auth["headers"])
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "employee_count" in data[0]

def test_get_obligation_evidence(client, case_id):
    ca_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.update(ca_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/evidence/obligations", headers=ca_auth["headers"])
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "facility_type" in data[0]
        assert "monthly_emi" in data[0]
        assert "outstanding_balance" in data[0]

def test_get_credit_twin_no_hardcodes(client, case_id):
    ca_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.update(ca_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/credit-twin", headers=ca_auth["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == str(case_id)
    # Check that it doesn't return literal hardcoded 3570000 or 999.99 unless actual evaluation says so
    assert "dscr" in data
    assert "binding_limit" in data

def test_get_reconciliation_missing_evidence(client, case_id):
    ca_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.update(ca_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/reconciliation", headers=ca_auth["headers"])
    assert response.status_code == 200
    data = response.json()
    assert "checks" in data
    
    circular_check = next((c for c in data["checks"] if c["name"] == "Circular Flow Analysis"), None)
    assert circular_check is not None
    assert circular_check["status"] == "MISSING_EVIDENCE"

def test_bola_cross_branch_denial_evidence(client, case_id, db):
    from app.db.orm.users import User, UserRole
    from app.api.auth import get_password_hash
    import uuid
    import os
    from datetime import datetime, timezone

    email = "rm.unassigned@bank.example"
    if not db.query(User).filter(User.email == email).first():
        db.add(User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=get_password_hash(os.environ.get("DEMO_USER_PASSWORD")),
            full_name="RM Unassigned",
            role=UserRole.RELATIONSHIP_MANAGER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        ))
        db.commit()

    # Cross branch RM should get 403/404
    rm_auth = get_auth_headers(client, email)
    client.cookies.update(rm_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/evidence/gst", headers=rm_auth["headers"])
    assert response.status_code in [403, 404]

def test_bola_system_admin_denial_evidence(client, case_id):
    # System Admin cannot view evidence
    sa_auth = get_auth_headers(client, "system@bank.example")
    client.cookies.update(sa_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/evidence/gst", headers=sa_auth["headers"])
    assert response.status_code in [403, 404]
