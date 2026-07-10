import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.orm.users import User, UserRole, SessionStore
from app.db.orm.cases import Case, CaseStatus, Business
from app.db.orm.org import Region, Branch, ProductType
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
    users = []
    unique_suffix = str(uuid.uuid4())[:8]
    roles = [
        UserRole.CREDIT_ANALYST,
        UserRole.SANCTIONING_AUTHORITY,
        UserRole.SYSTEM_ADMIN,
        UserRole.RELATIONSHIP_MANAGER,
    ]

    for role in roles:
        email = f"test_{role.value}_{unique_suffix}@example.com"
        u = User(
            email=email,
            hashed_password=get_password_hash("securepass123"),
            full_name=f"Test {role.value}",
            role=role,
            is_active=True,
        )
        db_session.add(u)
        users.append(u)
    db_session.commit()

    user_dict = {u.role: u for u in users}

    # Create an assigned case
    b = Business(
        business_id=f"BIZ_{unique_suffix}", legal_name="Test Business", sector="Retail"
    )
    db_session.add(b)
    db_session.flush()

    reg = Region(code=f"REG_{unique_suffix}", name="Test Region")
    db_session.add(reg)
    db_session.flush()

    branch = Branch(code=f"BR_{unique_suffix}", name="Test Branch", region_id=reg.id)
    db_session.add(branch)
    db_session.flush()

    c = Case(
        business_id_fk=b.id,
        requested_amount=100000,
        status=CaseStatus.INITIATED,
        assigned_credit_analyst_id=user_dict[UserRole.CREDIT_ANALYST].id,
        originating_branch_id=branch.id,
        requested_product=ProductType.WORKING_CAPITAL_LINE,
        version=1,
    )
    db_session.add(c)
    db_session.commit()

    yield {"users": user_dict, "case": c}

    # Cleanup
    db_session.delete(c)
    db_session.delete(b)
    db_session.commit()  # Commit deletions before users

    for u in users:
        db_session.query(SessionStore).filter(SessionStore.user_id == u.id).delete()
        db_session.delete(u)
    db_session.commit()


def login(email, password):
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    return response


def get_cookie_from_response(response, cookie_name):
    for cookie in response.headers.get_list("set-cookie"):
        if cookie.startswith(f"{cookie_name}="):
            return cookie.split(";")[0].split("=")[1]
    return ""


def test_csrf_protection_on_mutations():
    # POST without X-CSRF-Token should be exactly 403
    response = client.post(
        "/api/cases/123e4567-e89b-12d3-a456-426614174000/evaluate",
        json={"expected_version": 1},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing"


def test_vertical_escalation_system_admin_cannot_evaluate(test_users):
    login_resp = login(
        test_users["users"][UserRole.SYSTEM_ADMIN].email, "securepass123"
    )
    assert login_resp.status_code == 200

    session_token = get_cookie_from_response(login_resp, "vyapar_session_token")
    csrf_token = get_cookie_from_response(login_resp, "vyapar_csrf_token")
    cookies = {"vyapar_session_token": session_token}

    case_id = str(test_users["case"].id)
    resp = client.post(
        f"/api/cases/{case_id}/evaluate",
        json={"expected_version": 1},
        cookies=cookies,
        headers={"x-csrf-token": csrf_token, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp.status_code == 404
    assert "Case not found or access denied" in str(resp.json()["detail"])


def test_horizontal_escalation_credit_analyst_cannot_sanction(test_users):
    login_resp = login(
        test_users["users"][UserRole.CREDIT_ANALYST].email, "securepass123"
    )
    assert login_resp.status_code == 200

    session_token = get_cookie_from_response(login_resp, "vyapar_session_token")
    csrf_token = get_cookie_from_response(login_resp, "vyapar_csrf_token")
    cookies = {"vyapar_session_token": session_token}

    case_id = str(test_users["case"].id)
    resp = client.post(
        f"/api/cases/{case_id}/human-decision",
        json={
            "decision": "APPROVE_AS_REQUESTED",
            "reason": "Looks good enough",
            "expected_version": 1,
        },
        cookies=cookies,
        headers={"x-csrf-token": csrf_token, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp.status_code == 403
    assert "Only sanctioning authorities can record decisions" in str(resp.json()["detail"])


def test_sql_injection_resistance_login():
    sqli_payload = "' OR 1=1 --"
    response = client.post(
        "/api/auth/login", json={"email": sqli_payload, "password": "password"}
    )
    assert response.status_code in (401, 422)
    if response.status_code == 401:
        assert response.json()["detail"] == "Invalid email or password"


def test_auth_me(test_users):
    # Clear any cookies stored on client from previous tests
    client.cookies.clear()

    # 1. Unauthenticated should return 401
    resp_unauth = client.get("/api/auth/me")
    assert resp_unauth.status_code == 401

    # 2. Invalid session token should return 401
    resp_invalid = client.get(
        "/api/auth/me",
        cookies={"vyapar_session_token": "invalid_token_value_12345"},
    )
    assert resp_invalid.status_code == 401

    # 3. Test authenticated requests across all roles
    for role, user_obj in test_users["users"].items():
        client.cookies.clear()
        login_resp = login(user_obj.email, "securepass123")
        assert login_resp.status_code == 200

        session_token = get_cookie_from_response(login_resp, "vyapar_session_token")
        resp_auth = client.get(
            "/api/auth/me",
            cookies={"vyapar_session_token": session_token},
        )
        assert resp_auth.status_code == 200
        data = resp_auth.json()
        assert data["email"] == user_obj.email
        assert data["role"] == user_obj.role.value
        assert data["full_name"] == user_obj.full_name
        assert "id" in data
