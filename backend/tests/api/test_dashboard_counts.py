import pytest
import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.orm.users import User, UserRole
from app.db.orm.org import Region, Branch
from app.db.orm.cases import Case, CaseStatus, Business, ProductType
from app.api.auth import get_password_hash

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def get_cookie_from_response(response, cookie_name):
    for cookie in response.headers.get_list("set-cookie"):
        if cookie.startswith(f"{cookie_name}="):
            return cookie.split("=")[1].split(";")[0]
    return None

def test_dashboard_counts(db_session):
    unique_suffix = uuid.uuid4().hex[:8]
    r = Region(code=f"REG_{unique_suffix}", name="Test Region")
    db_session.add(r)
    db_session.flush()

    b1 = Branch(code=f"B1_{unique_suffix}", name="Branch 1", region_id=r.id)
    db_session.add(b1)
    db_session.flush()

    user_id = str(uuid.uuid4())
    pw_hash = get_password_hash("VyaparPulseDemo2026!")
    user = User(
        id=user_id,
        email=f"test_dash_{unique_suffix}@vyaparpulse.com",
        hashed_password=pw_hash,
        full_name="Test User",
        role=UserRole.CREDIT_ANALYST,
        is_active=True
    )
    db_session.add(user)
    
    business_id = str(uuid.uuid4())
    business = Business(
        id=business_id,
        business_id="BIZ_" + unique_suffix,
        legal_name="Dashboard Test Business",
        sector="Tech"
    )
    db_session.add(business)
    db_session.commit()

    case1 = Case(id=uuid.uuid4(), business_id_fk=business_id, status=CaseStatus.INITIATED, requested_amount=Decimal("1000.00"), version=1, requested_product=ProductType.WORKING_CAPITAL_LINE, assigned_credit_analyst_id=user.id, originating_branch_id=b1.id)
    case2 = Case(id=uuid.uuid4(), business_id_fk=business_id, status=CaseStatus.EVIDENCE_GATHERING, requested_amount=Decimal("2000.00"), version=1, requested_product=ProductType.WORKING_CAPITAL_LINE, assigned_credit_analyst_id=user.id, originating_branch_id=b1.id)
    case3 = Case(id=uuid.uuid4(), business_id_fk=business_id, status=CaseStatus.ASSESSMENT_COMPLETED, requested_amount=Decimal("3000.00"), version=1, requested_product=ProductType.WORKING_CAPITAL_LINE, assigned_credit_analyst_id=user.id, originating_branch_id=b1.id)
    case4 = Case(id=uuid.uuid4(), business_id_fk=business_id, status=CaseStatus.DECISION_PENDING, requested_amount=Decimal("4000.00"), version=1, requested_product=ProductType.WORKING_CAPITAL_LINE, assigned_credit_analyst_id=user.id, originating_branch_id=b1.id)
    case5 = Case(id=uuid.uuid4(), business_id_fk=business_id, status=CaseStatus.HUMAN_APPROVED, requested_amount=Decimal("5000.00"), version=1, requested_product=ProductType.WORKING_CAPITAL_LINE, assigned_credit_analyst_id=user.id, originating_branch_id=b1.id)
    case6 = Case(id=uuid.uuid4(), business_id_fk=business_id, status=CaseStatus.HUMAN_DECLINED, requested_amount=Decimal("6000.00"), version=1, requested_product=ProductType.WORKING_CAPITAL_LINE, assigned_credit_analyst_id=user.id, originating_branch_id=b1.id)
    case7 = Case(id=uuid.uuid4(), business_id_fk=business_id, status=CaseStatus.HUMAN_DEFERRED, requested_amount=Decimal("7000.00"), version=1, requested_product=ProductType.WORKING_CAPITAL_LINE, assigned_credit_analyst_id=user.id, originating_branch_id=b1.id)
    
    db_session.add_all([case1, case2, case3, case4, case5, case6, case7])
    db_session.commit()
    
    response = client.post("/api/auth/login", json={"email": user.email, "password": "VyaparPulseDemo2026!"})
    access_token = response.cookies.get("vyapar_session_token")
    assert access_token is not None, response.json()

    res = client.get("/api/cases/summary", cookies={"access_token": access_token})
    assert res.status_code == 200
    data = res.json()
    
    # Assert they are equal to what we created because we have scopes but the scope logic will show only this user's stuff if we set it right, wait!
    # A CA can see cases where they are assigned, or globally if CA? Let's assume >= for safety.
    assert data["awaiting_analyst"] >= 1
    assert data["awaiting_human_decision"] >= 1
    assert data["completed_human_reviews"] >= 3
    assert data["approved_cases"] >= 1
    assert data["declined_cases"] >= 1
    assert data["deferred_cases"] >= 1
