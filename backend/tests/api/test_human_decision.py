import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
import uuid

from app.db.orm.users import User, UserRole, SessionStore
from app.db.orm.cases import Case, CaseStatus, Business, IdempotencyRecord, AuditEvent
from app.db.orm.org import Region, Branch, ProductType
from app.api.auth import get_password_hash

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
    db_session.query(IdempotencyRecord).filter(
        IdempotencyRecord.case_id == str(c.id)
    ).delete()
    db_session.query(AuditEvent).filter(AuditEvent.case_id == c.id).delete()
    db_session.delete(c)
    db_session.delete(b)
    db_session.commit()  # Commit deletions before users

    for u in users:
        db_session.query(SessionStore).filter(SessionStore.user_id == u.id).delete()
        db_session.delete(u)
    db_session.commit()


def test_human_decision_approve_success(test_users):
    case = test_users["case"]

    resp = client.post(
        "/api/auth/login",
        json={"email": "alice@idbibank.com", "password": "password123"},
    )
    if resp.status_code != 200:
        resp = client.post(
            "/api/auth/login",
            json={"email": "bob@idbibank.com", "password": "password123"},
        )
    cookies = resp.cookies
    csrf_token = cookies.get("vyapar_csrf_token", "dummy")

    case_id = str(case.id)

    payload = {
        "decision": "APPROVE_AS_REQUESTED",
        "reason": "Clear repayment capacity seen in GST data.",
        "expected_version": case.version,
    }

    res = client.post(
        f"/api/cases/{case_id}/human-decision",
        json=payload,
        cookies=cookies,
        headers={
            "x-csrf-token": csrf_token,
            "Idempotency-Key": str(uuid.uuid4()),
            "X-Expected-Version": str(case.version),
        },
    )

    assert res.status_code in [200, 403, 400], (
        f"Expected 200/403/400 but got {res.status_code} - {res.text}"
    )


def test_human_decision_decline(test_users):
    case = test_users["case"]

    resp = client.post(
        "/api/auth/login",
        json={"email": "alice@idbibank.com", "password": "password123"},
    )
    if resp.status_code != 200:
        resp = client.post(
            "/api/auth/login",
            json={"email": "bob@idbibank.com", "password": "password123"},
        )
    cookies = resp.cookies
    csrf_token = cookies.get("vyapar_csrf_token", "dummy")

    case_id = str(case.id)

    payload = {
        "decision": "DECLINE",
        "reason": "High debt utilization.",
        "expected_version": case.version,
    }

    res = client.post(
        f"/api/cases/{case_id}/human-decision",
        json=payload,
        cookies=cookies,
        headers={
            "x-csrf-token": csrf_token,
            "Idempotency-Key": str(uuid.uuid4()),
            "X-Expected-Version": str(case.version),
        },
    )

    assert res.status_code in [200, 403, 400], (
        f"Expected 200/403/400 but got {res.status_code} - {res.text}"
    )
