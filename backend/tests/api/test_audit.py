import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import SessionLocal, engine
from app.seed.seed_shakti import seed_shakti
import os


@pytest.fixture(scope="module", autouse=True)
def setup_shakti_data():
    import urllib.parse
    db_url = os.environ.get("DATABASE_URL", str(engine.url))
    parsed_url = urllib.parse.urlparse(db_url)
    datname = parsed_url.path.lstrip("/")
    if "test" not in datname.lower():
        raise RuntimeError(f"Refusing to run tests against non-test database name: '{datname}'")
    if os.environ.get("APP_ENV") == "production":
        raise RuntimeError("Refusing to run tests in production environment")

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
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": os.environ.get("DEMO_USER_PASSWORD", "demo_dev_only_123")},
    )
    assert response.status_code == 200, f"Failed to login {email}: {response.text}"
    session_token = get_cookie_from_response(response, "vyapar_session_token")
    csrf_token = get_cookie_from_response(response, "vyapar_csrf_token")

    return {
        "cookies": {"vyapar_session_token": session_token},
        "headers": {"x-csrf-token": csrf_token},
    }


def test_audit_endpoints_and_scope(client: TestClient, db: Session):
    # 1. RM logs in and gets case id
    rm_auth = get_auth_headers(client, "rm@bank.example")
    client.cookies.clear()
    client.cookies.update(rm_auth["cookies"])
    res = client.get("/api/cases", headers=rm_auth["headers"])
    assert res.status_code == 200
    cases = res.json()
    assert len(cases) > 0
    case_id = cases[0]["id"]

    # 2. Test GET /api/cases/{case_id}/audit with RM
    audit_res = client.get(f"/api/cases/{case_id}/audit", headers=rm_auth["headers"])
    assert audit_res.status_code == 200
    events = audit_res.json()
    assert isinstance(events, list)
    if len(events) > 1:
        seqs = [e["event_sequence"] for e in events]
        assert seqs == sorted(seqs), "event_sequence must be strictly ordered"

    # 3. Test GET /api/audit/logs with RM
    logs_res = client.get("/api/audit/logs", headers=rm_auth["headers"])
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert isinstance(logs, list)

    # 4. Test System Admin cannot view audit
    sys_auth = get_auth_headers(client, "system@bank.example")
    client.cookies.clear()
    client.cookies.update(sys_auth["cookies"])
    sys_audit_res = client.get(f"/api/cases/{case_id}/audit", headers=sys_auth["headers"])
    assert sys_audit_res.status_code == 404
    assert "Case not found or access denied" in sys_audit_res.text

    sys_logs_res = client.get("/api/audit/logs", headers=sys_auth["headers"])
    assert sys_logs_res.status_code == 403
    assert "System administrators cannot view case audit trails" in sys_logs_res.text

    # 5. Test Auditor can view audit
    aud_auth = get_auth_headers(client, "auditor@bank.example")
    client.cookies.clear()
    client.cookies.update(aud_auth["cookies"])
    aud_audit_res = client.get(f"/api/cases/{case_id}/audit", headers=aud_auth["headers"])
    assert aud_audit_res.status_code == 200

    aud_logs_res = client.get("/api/audit/logs", headers=aud_auth["headers"])
    assert aud_logs_res.status_code == 200

    # 6. Test Risk Admin can view audit
    risk_auth = get_auth_headers(client, "admin@bank.example")
    client.cookies.clear()
    client.cookies.update(risk_auth["cookies"])
    risk_audit_res = client.get(f"/api/cases/{case_id}/audit", headers=risk_auth["headers"])
    assert risk_audit_res.status_code == 200

    risk_logs_res = client.get("/api/audit/logs", headers=risk_auth["headers"])
    assert risk_logs_res.status_code == 200
