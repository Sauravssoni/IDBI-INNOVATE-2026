import pytest
import os
from decimal import Decimal
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
    if response.status_code != 200:
        print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "ingestion_mode" in data[0]["metadata"]

def test_get_bank_evidence(client, case_id):
    ca_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.update(ca_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/evidence/bank", headers=ca_auth["headers"])
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "ingestion_mode" in data[0]["metadata"]

def test_get_credit_twin(client, case_id):
    ca_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.update(ca_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/credit-twin", headers=ca_auth["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == str(case_id)
    assert "dscr" in data
    assert "total_annual_revenue" in data

def test_get_reconciliation(client, case_id):
    ca_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.update(ca_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/reconciliation", headers=ca_auth["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == str(case_id)
    assert "checks" in data
    assert len(data["checks"]) == 5
    for check in data["checks"]:
        assert check["status"] in ["MATCHED", "VARIANCE", "MISSING_EVIDENCE", "REVIEW_REQUIRED"]

def test_bola_unauthorized_user_evidence(client, case_id):
    # System Admin cannot view evidence
    sa_auth = get_auth_headers(client, "system@bank.example")
    client.cookies.update(sa_auth["cookies"])
    response = client.get(f"/api/cases/{case_id}/evidence/gst", headers=sa_auth["headers"])
    assert response.status_code == 404
