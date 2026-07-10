import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.orm.users import User, UserRole
from app.db.orm.org import UserBranchScope, Region, Branch
from app.db.orm.cases import Case, CaseStatus, Business, ProductType
from app.api.auth import get_password_hash

client = TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


def login(email, password):
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    return response


@pytest.fixture(scope="module")
def setup_data(db_session):
    unique_suffix = str(uuid.uuid4())[:8]

    # Create Organization
    r = Region(code=f"REG_{unique_suffix}", name="Test Region")
    db_session.add(r)
    db_session.flush()

    b = Branch(code=f"B1_{unique_suffix}", name="Branch 1", region_id=r.id)
    db_session.add(b)
    db_session.flush()

    # Create Users
    users = {}
    roles = [
        UserRole.CREDIT_ANALYST,
        UserRole.SANCTIONING_AUTHORITY,
        UserRole.RELATIONSHIP_MANAGER,
        UserRole.AUDITOR,
        UserRole.RISK_ADMIN,
        UserRole.SYSTEM_ADMIN,
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
        users[role] = u
    db_session.flush()

    # Assign scopes
    for role in [
        UserRole.RISK_ADMIN,
        UserRole.CREDIT_ANALYST,
        UserRole.SANCTIONING_AUTHORITY,
        UserRole.AUDITOR,
    ]:
        scope = UserBranchScope(
            user_id=users[role].id,
            branch_id=b.id,
            scope_role="AUDIT" if role == UserRole.AUDITOR else "RISK",
            can_read=True,
            active=True,
        )
        db_session.add(scope)
    db_session.flush()

    # Create Business & Case
    biz = Business(
        business_id=f"BIZ_{unique_suffix}",
        legal_name="Serialization Biz",
        sector="Retail",
    )
    db_session.add(biz)
    db_session.flush()

    case1 = Case(
        business_id_fk=biz.id,
        requested_product=ProductType.WORKING_CAPITAL_LINE,
        requested_amount=100000,
        currency="INR",
        originating_branch_id=b.id,
        status=CaseStatus.DECISION_PENDING,
        assigned_relationship_manager_id=users[UserRole.RELATIONSHIP_MANAGER].id,
        assigned_credit_analyst_id=users[UserRole.CREDIT_ANALYST].id,
        assigned_sanctioning_authority_id=users[UserRole.SANCTIONING_AUTHORITY].id,
    )
    db_session.add(case1)
    db_session.flush()

    db_session.commit()

    return {
        "users": users,
        "case_id": str(case1.id),
    }


def get_cookie(response):
    for cookie in response.headers.get_list("set-cookie"):
        if cookie.startswith("vyapar_session="):
            return cookie.split(";")[0].split("=")[1]
    return ""


def test_system_admin_denied(setup_data):
    sys_admin = setup_data["users"][UserRole.SYSTEM_ADMIN]
    res = login(sys_admin.email, "securepass123")
    cookie = get_cookie(res)

    client.cookies.set("vyapar_session", cookie)
    case_res = client.get(
        f"/api/cases/{setup_data['case_id']}",
        headers={"Origin": "http://localhost:3005"},
    )
    assert case_res.status_code == 404


@pytest.mark.parametrize(
    "role",
    [
        UserRole.CREDIT_ANALYST,
        UserRole.SANCTIONING_AUTHORITY,
        UserRole.RELATIONSHIP_MANAGER,
        UserRole.AUDITOR,
        UserRole.RISK_ADMIN,
    ],
)
def test_valid_roles_can_fetch_case(setup_data, role):
    user = setup_data["users"][role]
    res = login(user.email, "securepass123")
    cookie = get_cookie(res)

    client.cookies.set("vyapar_session", cookie)
    case_res = client.get(
        f"/api/cases/{setup_data['case_id']}",
        headers={"Origin": "http://localhost:3005"},
    )
    assert case_res.status_code == 200

    # Check CORS headers
    assert (
        "access-control-allow-origin" in case_res.headers
        or "Access-Control-Allow-Origin" in case_res.headers
    )

    data = case_res.json()
    assert "id" in data
    assert "business_id_fk" in data
    assert "business" in data
    assert "id" in data["business"]
    assert "business_id" in data["business"]
    assert "legal_name" in data["business"]
    assert "sector" in data["business"]
    assert "requested_amount" in data
    assert "requested_product" in data
    assert "currency" in data
    assert "status" in data
    assert "recommendation" in data
    assert "analyst_recommendation" in data
    assert "human_decision" in data
    assert "evaluation_result" in data
    assert "allowed_actions" in data

    actions = data["allowed_actions"]
    assert "run_assessment" in actions
    assert "submit_analyst_recommendation" in actions
    assert "record_human_decision" in actions
    assert "view_audit" in actions

    assert "version" in data
    assert "created_at" in data
    assert "updated_at" in data
