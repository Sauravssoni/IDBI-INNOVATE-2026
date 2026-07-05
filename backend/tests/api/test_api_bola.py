import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.orm.users import User, UserRole
from app.db.orm.org import UserBranchScope, SanctioningMandate, Region, Branch
from app.db.orm.cases import Case, CaseStatus, Business, ProductType
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
def setup_bola_data(db_session):
    unique_suffix = str(uuid.uuid4())[:8]
    
    # 1. Create Organization
    r = Region(code=f"REG_{unique_suffix}", name="Test Region")
    db_session.add(r)
    db_session.flush()
    
    b1 = Branch(code=f"B1_{unique_suffix}", name="Branch 1", region_id=r.id)
    b2 = Branch(code=f"B2_{unique_suffix}", name="Branch 2", region_id=r.id)
    db_session.add(b1)
    db_session.add(b2)
    db_session.flush()
    
    # 2. Create Users
    # - System Admin (no case access)
    # - RM assigned to Case 1
    # - Risk Admin with access to Branch 1
    users = {}
    roles = [UserRole.SYSTEM_ADMIN, UserRole.RELATIONSHIP_MANAGER, UserRole.RISK_ADMIN, UserRole.CREDIT_ANALYST]
    
    for role in roles:
        email = f"bola_{role.value}_{unique_suffix}@example.com"
        u = User(
            email=email,
            hashed_password=get_password_hash("securepass123"),
            full_name=f"Bola {role.value}",
            role=role,
            is_active=True
        )
        db_session.add(u)
        users[role] = u
    db_session.flush()
    
    # Risk Admin gets scope to Branch 1
    scope = UserBranchScope(
        user_id=users[UserRole.RISK_ADMIN].id,
        branch_id=b1.id
    )
    db_session.add(scope)
    
    # 3. Create Businesses & Cases
    biz1 = Business(business_id=f"BIZ1_{unique_suffix}", legal_name="Biz 1", sector="Retail")
    biz2 = Business(business_id=f"BIZ2_{unique_suffix}", legal_name="Biz 2", sector="Retail")
    db_session.add(biz1)
    db_session.add(biz2)
    db_session.flush()
    
    # Case 1 in Branch 1 (Assigned to our RM)
    case1 = Case(
        business_id_fk=biz1.id,
        requested_product=ProductType.WORKING_CAPITAL_LINE,
        requested_amount=100000,
        status=CaseStatus.INITIATED,
        originating_branch_id=b1.id,
        assigned_relationship_manager_id=users[UserRole.RELATIONSHIP_MANAGER].id,
        version=1
    )
    # Case 2 in Branch 2 (Not assigned to our RM, so our RM and our Risk Admin shouldn't see it)
    case2 = Case(
        business_id_fk=biz2.id,
        requested_product=ProductType.WORKING_CAPITAL_LINE,
        requested_amount=500000,
        status=CaseStatus.INITIATED,
        originating_branch_id=b2.id,
        version=1
    )
    db_session.add(case1)
    db_session.add(case2)
    db_session.commit()
    
    yield {
        "users": users,
        "cases": {"case1": case1, "case2": case2},
        "org": {"b1": b1, "b2": b2}
    }
    
    # Cleanup
    db_session.query(Case).filter(Case.id.in_([case1.id, case2.id])).delete()
    db_session.query(Business).filter(Business.id.in_([biz1.id, biz2.id])).delete()
    from app.db.orm.users import SessionStore
    db_session.query(UserBranchScope).filter(UserBranchScope.id == scope.id).delete()
    for u in users.values():
        db_session.query(SessionStore).filter(SessionStore.user_id == u.id).delete()
        db_session.query(User).filter(User.id == u.id).delete()
    db_session.query(Branch).filter(Branch.id.in_([b1.id, b2.id])).delete()
    db_session.query(Region).filter(Region.id == r.id).delete()
    db_session.commit()

def test_bola_system_admin_has_no_case_access(setup_bola_data):
    login_resp = login(setup_bola_data["users"][UserRole.SYSTEM_ADMIN].email, "securepass123")
    cookies = {"vyapar_session_token": get_cookie_from_response(login_resp, "vyapar_session_token")}
    
    # List should be empty
    resp = client.get("/api/cases/", cookies=cookies)
    assert resp.status_code == 200
    assert len(resp.json()) == 0
    
    # Direct access should be 403 or 404
    case_id = str(setup_bola_data["cases"]["case1"].id)
    resp = client.get(f"/api/cases/{case_id}", cookies=cookies)
    assert resp.status_code == 404 # Explicit 403 from check_case_access

def test_bola_rm_sees_only_assigned_cases(setup_bola_data):
    login_resp = login(setup_bola_data["users"][UserRole.RELATIONSHIP_MANAGER].email, "securepass123")
    cookies = {"vyapar_session_token": get_cookie_from_response(login_resp, "vyapar_session_token")}
    
    # List should return only case1
    resp = client.get("/api/cases/", cookies=cookies)
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["id"] == str(setup_bola_data["cases"]["case1"].id)
    
    # Direct access to case1 works
    case1_id = str(setup_bola_data["cases"]["case1"].id)
    resp = client.get(f"/api/cases/{case1_id}", cookies=cookies)
    assert resp.status_code == 200
    
    # Direct access to case2 (unassigned) fails
    case2_id = str(setup_bola_data["cases"]["case2"].id)
    resp = client.get(f"/api/cases/{case2_id}", cookies=cookies)
    assert resp.status_code == 404

def test_bola_risk_admin_sees_scoped_branch_cases(setup_bola_data):
    login_resp = login(setup_bola_data["users"][UserRole.RISK_ADMIN].email, "securepass123")
    cookies = {"vyapar_session_token": get_cookie_from_response(login_resp, "vyapar_session_token")}
    
    # List should return only case1 (in Branch 1)
    resp = client.get("/api/cases/", cookies=cookies)
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["id"] == str(setup_bola_data["cases"]["case1"].id)
    
    # Direct access to case2 (Branch 2) fails
    case2_id = str(setup_bola_data["cases"]["case2"].id)
    resp = client.get(f"/api/cases/{case2_id}", cookies=cookies)
    assert resp.status_code == 404
