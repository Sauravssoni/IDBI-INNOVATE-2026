import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
import os
from datetime import datetime, timedelta, timezone

from app.main import app
from app.db.session import SessionLocal, engine
from app.seed.seed_shakti import seed_shakti
from app.api.auth import get_password_hash


def utc_now():
    return datetime.now(timezone.utc)


@pytest.fixture(scope="module", autouse=True)
def setup_shakti_data():
    import urllib.parse

    db_url = os.environ.get("DATABASE_URL", str(engine.url))
    parsed_url = urllib.parse.urlparse(db_url)
    datname = parsed_url.path.lstrip("/")
    if "test" not in datname.lower():
        raise RuntimeError(
            f"Refusing to run tests against non-test database name: '{datname}'"
        )
    if os.environ.get("APP_ENV") == "production":
        raise RuntimeError("Refusing to run tests in production environment")

    # The password is provided via conftest.py
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
    password = os.environ.get("DEMO_USER_PASSWORD")
    if not password:
        raise RuntimeError("DEMO_USER_PASSWORD must be set for test login.")
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, f"Failed to login {email}: {response.text}"
    session_token = get_cookie_from_response(response, "vyapar_session_token")
    csrf_token = get_cookie_from_response(response, "vyapar_csrf_token")

    return {
        "cookies": {"vyapar_session_token": session_token},
        "headers": {"x-csrf-token": csrf_token},
    }


@pytest.fixture
def deterministic_data(db: Session):
    password = os.environ["DEMO_USER_PASSWORD"]
    pw_hash = get_password_hash(password)

    # 0. Clean up any left-over data from failed test runs
    db.execute(
        text("""
        DELETE FROM audit_events WHERE case_id IN (
            SELECT id FROM cases WHERE business_id_fk IN (
                SELECT id FROM businesss WHERE business_id = 'BIZ-AUDIT'
            )
        )
    """)
    )
    db.execute(
        text("""
        DELETE FROM cases WHERE business_id_fk IN (
            SELECT id FROM businesss WHERE business_id = 'BIZ-AUDIT'
        )
    """)
    )
    db.execute(text("DELETE FROM businesss WHERE business_id = 'BIZ-AUDIT'"))

    db.execute(
        text("""
        DELETE FROM sessions WHERE user_id IN (
            SELECT id FROM users WHERE email IN (
                'auditor_a@bank.example', 'auditor_b@bank.example', 'rm_a@bank.example', 
                'rm_b@bank.example', 'risk_a@bank.example', 'sys@bank.example'
            )
        )
    """)
    )
    db.execute(
        text("""
        DELETE FROM user_branch_scopes WHERE user_id IN (
            SELECT id FROM users WHERE email IN (
                'auditor_a@bank.example', 'auditor_b@bank.example', 'rm_a@bank.example', 
                'rm_b@bank.example', 'risk_a@bank.example', 'sys@bank.example'
            )
        )
    """)
    )
    db.execute(
        text("""
        DELETE FROM users WHERE email IN (
            'auditor_a@bank.example', 'auditor_b@bank.example', 'rm_a@bank.example', 
            'rm_b@bank.example', 'risk_a@bank.example', 'sys@bank.example'
        )
    """)
    )
    db.execute(text("DELETE FROM branches WHERE code IN ('BR-A', 'BR-B')"))
    db.execute(text("DELETE FROM regions WHERE code = 'REG-AUDIT'"))
    db.commit()

    # 1. Regions and Branches
    reg_id = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO regions (id, code, name, created_at, updated_at) VALUES (:id, 'REG-AUDIT', 'Audit Region', :ct, :ct)"
        ),
        {"id": reg_id, "ct": utc_now()},
    )

    branch_a_id = str(uuid.uuid4())
    branch_b_id = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO branches (id, region_id, code, name, created_at, updated_at) VALUES (:id, :reg_id, 'BR-A', 'Branch A', :ct, :ct)"
        ),
        {"id": branch_a_id, "reg_id": reg_id, "ct": utc_now()},
    )
    db.execute(
        text(
            "INSERT INTO branches (id, region_id, code, name, created_at, updated_at) VALUES (:id, :reg_id, 'BR-B', 'Branch B', :ct, :ct)"
        ),
        {"id": branch_b_id, "reg_id": reg_id, "ct": utc_now()},
    )

    # 2. Users
    users = {
        "auditor_a@bank.example": ("Auditor A", "AUDITOR", branch_a_id, "AUDIT"),
        "auditor_b@bank.example": ("Auditor B", "AUDITOR", branch_b_id, "AUDIT"),
        "rm_a@bank.example": ("RM A", "RELATIONSHIP_MANAGER", branch_a_id, None),
        "rm_b@bank.example": ("RM B", "RELATIONSHIP_MANAGER", branch_b_id, None),
        "risk_a@bank.example": ("Risk A", "RISK_ADMIN", branch_a_id, "RISK"),
        "sys@bank.example": ("Sys", "SYSTEM_ADMIN", None, None),
    }

    user_ids = {}
    for email, (name, role, branch_id, scope_role) in users.items():
        uid = str(uuid.uuid4())
        user_ids[email] = uid
        db.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, full_name, role, is_active, created_at, updated_at) VALUES (:id, :email, :pw_hash, :name, :role, true, :ct, :ct)"
            ),
            {
                "id": uid,
                "email": email,
                "pw_hash": pw_hash,
                "name": name,
                "role": role,
                "ct": utc_now(),
            },
        )
        if branch_id and scope_role:
            db.execute(
                text(
                    "INSERT INTO user_branch_scopes (id, user_id, branch_id, scope_role, active, can_read, can_recommend, created_at, updated_at) VALUES (:id, :uid, :bid, :srole, true, true, true, :ct, :ct)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "uid": uid,
                    "bid": branch_id,
                    "srole": scope_role,
                    "ct": utc_now(),
                },
            )

    # 3. Business & Cases
    biz_id = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO businesss (id, business_id, legal_name, sector, created_at, updated_at) VALUES (:id, 'BIZ-AUDIT', 'Audit Biz', 'Retail', :ct, :ct)"
        ),
        {"id": biz_id, "ct": utc_now()},
    )

    case_a_id = str(uuid.uuid4())
    case_b_id = str(uuid.uuid4())
    db.execute(
        text(
            "INSERT INTO cases (id, business_id_fk, status, requested_amount, requested_product, originating_branch_id, assigned_relationship_manager_id, currency, version, created_at, updated_at) VALUES (:id, :bid, 'INITIATED', 100, 'WORKING_CAPITAL_LINE', :branch, :rm, 'INR', 1, :ct, :ct)"
        ),
        {
            "id": case_a_id,
            "bid": biz_id,
            "branch": branch_a_id,
            "rm": user_ids["rm_a@bank.example"],
            "ct": utc_now(),
        },
    )
    db.execute(
        text(
            "INSERT INTO cases (id, business_id_fk, status, requested_amount, requested_product, originating_branch_id, assigned_relationship_manager_id, currency, version, created_at, updated_at) VALUES (:id, :bid, 'INITIATED', 200, 'WORKING_CAPITAL_LINE', :branch, :rm, 'INR', 1, :ct, :ct)"
        ),
        {
            "id": case_b_id,
            "bid": biz_id,
            "branch": branch_b_id,
            "rm": user_ids["rm_b@bank.example"],
            "ct": utc_now(),
        },
    )

    # 4. Audit Events
    # Case A: 3 events
    for i in range(1, 4):
        db.execute(
            text(
                "INSERT INTO audit_events (id, case_id, event_sequence, event_type, actor, actor_role, audit_schema_version, hash_algorithm, created_at, updated_at) VALUES (:id, :case, :seq, 'EVALUATE', :actor, 'RELATIONSHIP_MANAGER', 1, 'sha256', :ct, :ct)"
            ),
            {
                "id": str(uuid.uuid4()),
                "case": case_a_id,
                "seq": i,
                "actor": user_ids["rm_a@bank.example"],
                "ct": utc_now() + timedelta(minutes=i),
            },
        )

    # Case B: 1 event
    db.execute(
        text(
            "INSERT INTO audit_events (id, case_id, event_sequence, event_type, actor, actor_role, audit_schema_version, hash_algorithm, created_at, updated_at) VALUES (:id, :case, 1, 'EVALUATE', :actor, 'RELATIONSHIP_MANAGER', 1, 'sha256', :ct, :ct)"
        ),
        {
            "id": str(uuid.uuid4()),
            "case": case_b_id,
            "actor": user_ids["rm_b@bank.example"],
            "ct": utc_now(),
        },
    )

    db.commit()

    yield {
        "branch_a": branch_a_id,
        "branch_b": branch_b_id,
        "case_a": case_a_id,
        "case_b": case_b_id,
        "user_ids": user_ids,
    }

    # Teardown
    db.execute(
        text("DELETE FROM audit_events WHERE case_id IN (:ca, :cb)"),
        {"ca": case_a_id, "cb": case_b_id},
    )
    db.execute(
        text("DELETE FROM cases WHERE id IN (:ca, :cb)"),
        {"ca": case_a_id, "cb": case_b_id},
    )
    db.execute(text("DELETE FROM businesss WHERE id = :id"), {"id": biz_id})
    for uid in user_ids.values():
        db.execute(text("DELETE FROM sessions WHERE user_id = :uid"), {"uid": uid})
        db.execute(
            text("DELETE FROM user_branch_scopes WHERE user_id = :uid"), {"uid": uid}
        )
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
    db.execute(
        text("DELETE FROM branches WHERE id IN (:ba, :bb)"),
        {"ba": branch_a_id, "bb": branch_b_id},
    )
    db.execute(text("DELETE FROM regions WHERE id = :id"), {"id": reg_id})
    db.commit()


def test_auditor_branch_isolation(client: TestClient, db: Session, deterministic_data):
    aud_a_auth = get_auth_headers(client, "auditor_a@bank.example")

    client.cookies.clear()
    client.cookies.update(aud_a_auth["cookies"])

    # Auditor A should only see Case A's audit events (3 events)
    logs_res = client.get("/api/audit/logs", headers=aud_a_auth["headers"])
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) == 3
    for log in logs:
        assert log["case_id"] == deterministic_data["case_a"]

    # Explicitly test viewing Case B directly
    b_res = client.get(
        f"/api/cases/{deterministic_data['case_b']}/audit",
        headers=aud_a_auth["headers"],
    )
    assert b_res.status_code == 404


def test_rm_unassigned_case_denial(client: TestClient, db: Session, deterministic_data):
    rm_a_auth = get_auth_headers(client, "rm_a@bank.example")
    client.cookies.clear()
    client.cookies.update(rm_a_auth["cookies"])

    # RM A should not be able to view Case B's audit trail
    res = client.get(
        f"/api/cases/{deterministic_data['case_b']}/audit", headers=rm_a_auth["headers"]
    )
    assert res.status_code == 404


def test_risk_admin_scope_isolation(
    client: TestClient, db: Session, deterministic_data
):
    risk_a_auth = get_auth_headers(client, "risk_a@bank.example")
    client.cookies.clear()
    client.cookies.update(risk_a_auth["cookies"])

    # Risk Admin A should only see Case A logs
    logs_res = client.get("/api/audit/logs", headers=risk_a_auth["headers"])
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) == 3
    for log in logs:
        assert log["case_id"] == deterministic_data["case_a"]


def test_system_admin_exclusion(client: TestClient, db: Session, deterministic_data):
    sys_auth = get_auth_headers(client, "sys@bank.example")
    client.cookies.clear()
    client.cookies.update(sys_auth["cookies"])

    # System Admin cannot access portfolio audit logs
    logs_res = client.get("/api/audit/logs", headers=sys_auth["headers"])
    assert logs_res.status_code == 403

    # System Admin cannot access specific case audit trail
    case_res = client.get(
        f"/api/cases/{deterministic_data['case_a']}/audit", headers=sys_auth["headers"]
    )
    assert case_res.status_code == 404


def test_audit_pagination_and_ordering(
    client: TestClient, db: Session, deterministic_data
):
    aud_a_auth = get_auth_headers(client, "auditor_a@bank.example")
    client.cookies.clear()
    client.cookies.update(aud_a_auth["cookies"])

    # Limit to 2
    res_limit = client.get("/api/audit/logs?limit=2", headers=aud_a_auth["headers"])
    assert res_limit.status_code == 200
    logs_limit = res_limit.json()
    assert len(logs_limit) == 2

    # Offset 2 returns the remaining 1
    res_offset = client.get(
        "/api/audit/logs?limit=2&offset=2", headers=aud_a_auth["headers"]
    )
    assert res_offset.status_code == 200
    logs_offset = res_offset.json()
    assert len(logs_offset) == 1

    # Prove they are ordered by created_at DESC, event_sequence DESC, id DESC
    res_all = client.get("/api/audit/logs", headers=aud_a_auth["headers"])
    logs_all = res_all.json()
    assert len(logs_all) == 3

    # Sequence should be 3, 2, 1 since they were inserted 1 min apart ascending
    seqs = [log["event_sequence"] for log in logs_all]
    assert seqs == [3, 2, 1]


def test_audit_portfolio_exact_response_keys(
    client: TestClient, db: Session, deterministic_data
):
    aud_a_auth = get_auth_headers(client, "auditor_a@bank.example")
    client.cookies.clear()
    client.cookies.update(aud_a_auth["cookies"])

    res = client.get("/api/audit/logs", headers=aud_a_auth["headers"])
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) > 0

    expected_keys = {
        "id",
        "case_id",
        "event_sequence",
        "event_type",
        "actor",
        "actor_role",
        "prior_case_version",
        "resulting_case_version",
        "prior_event_hash",
        "event_hash",
        "reason",
        "created_at",
    }

    for log in logs:
        assert set(log.keys()) == expected_keys
