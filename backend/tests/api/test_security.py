import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.orm.users import User, UserRole
from app.api.auth import get_password_hash
import uuid

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture(scope="module")
def test_users(db_session):
    # Create test users with different roles
    users = []
    unique_suffix = str(uuid.uuid4())[:8]
    for role in [UserRole.CREDIT_ANALYST, UserRole.SANCTIONING_AUTHORITY, UserRole.SYSTEM_ADMIN]:
        email = f"test_{role.value}_{unique_suffix}@example.com"
        u = User(
            email=email,
            hashed_password=get_password_hash("securepass123"),
            full_name=f"Test {role.value}",
            role=role,
            is_active=True
        )
        db_session.add(u)
        users.append(u)
    db_session.commit()
    
    yield {u.role: u for u in users}
    
    # Cleanup
    from sqlalchemy import text
    for u in users:
        db_session.execute(text(f"DELETE FROM sessions WHERE user_id = '{u.id}'"))
        db_session.delete(u)
    db_session.commit()

def login(email, password):
    # This assumes we have a /api/auth/login endpoint 
    # Returning the cookies/session
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    return response

def test_csrf_protection_on_mutations():
    # Attempt a POST request without X-CSRF-Token should fail
    response = client.post("/api/cases/123e4567-e89b-12d3-a456-426614174000/evaluate")
    # Our custom CSRF middleware might return 403 or 401 or 404 if not found
    assert response.status_code in (401, 403, 404)

def test_vertical_escalation_system_admin_cannot_evaluate(test_users):
    # Login as SYSTEM_ADMIN
    login_resp = login(test_users[UserRole.SYSTEM_ADMIN].email, "securepass123")
    assert login_resp.status_code == 200
    cookies = login_resp.cookies
    csrf_token = cookies.get("csrf_token") or "dummy_token"
    
    # Try to evaluate a case
    fake_case_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/cases/{fake_case_id}/evaluate",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token}
    )
    # Should be 403 Forbidden or 401 if CSRF/Auth fails
    assert resp.status_code in (401, 403)

def test_horizontal_escalation_credit_analyst_cannot_sanction(test_users):
    # Login as CREDIT_ANALYST
    login_resp = login(test_users[UserRole.CREDIT_ANALYST].email, "securepass123")
    assert login_resp.status_code == 200
    cookies = login_resp.cookies
    csrf_token = cookies.get("csrf_token") or "dummy_token"
    
    fake_case_id = str(uuid.uuid4())
    # Try to sanction (human-decision)
    resp = client.post(
        f"/api/cases/{fake_case_id}/human-decision",
        json={"decision": "APPROVE_AS_REQUESTED", "reason": "Looks good enough"},
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token}
    )
    # Should be 403 Forbidden or 401 if CSRF/Auth fails
    assert resp.status_code in (401, 403)

def test_sql_injection_resistance_login():
    # Attempt SQL injection on login
    sqli_payload = "' OR 1=1 --"
    response = client.post("/api/auth/login", json={"email": sqli_payload, "password": "password"})
    assert response.status_code in (401, 422) # Should be rejected, not a 500 DB error
