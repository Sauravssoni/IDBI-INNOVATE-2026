import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.orm.users import User, UserRole
from app.db.orm.org import UserBranchScope, Region, Branch
from app.db.orm.cases import Case, CaseStatus, Business, ProductType, DecisionPackage
from app.api.auth import get_password_hash
from app.domain.audit.verification import verify_audit_chain

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


def test_decision_package_cd_fields(setup_data):
    user = setup_data["users"][UserRole.CREDIT_ANALYST]
    res = login(user.email, "securepass123")
    cookie = get_cookie(res)
    client.cookies.set("vyapar_session", cookie)
    res = client.get(f"/api/cases/{setup_data['case_id']}/decision-package")
    assert res.status_code == 200
    data = res.json()
    assert "assessment_certainty" in data
    assert data["assessment_certainty"] in [
        "HIGH_CERTAINTY",
        "MODERATE_CERTAINTY",
        "LIMITED_CERTAINTY",
        "INSUFFICIENT_TO_ASSESS",
    ]
    assert "certainty_reasons" in data
    assert isinstance(data["certainty_reasons"], list)
    assert "peer_context" in data
    assert data["peer_context"]["sample_status"] in [
        "VALID_PEER_SAMPLE",
        "INSUFFICIENT_PEER_SAMPLE",
    ]
    assert "hindi_summary" in data
    assert "decision_label" in data["hindi_summary"]
    assert "reason_explanation" in data["hindi_summary"]
    assert "missing_evidence_checklist" in data["hindi_summary"]
    assert isinstance(data["hindi_summary"]["missing_evidence_checklist"], list)
    assert "bankability_path_actions" in data["hindi_summary"]
    assert isinstance(data["hindi_summary"]["bankability_path_actions"], list)

    # Verify DPK-001: 6-pillar FHI, 300-900 Credit Health Score, and calculation evidence IDs
    assert "financial_health_index" in data
    assert "vyapar_credit_health_score" in data
    if data["assessment_certainty"] == "INSUFFICIENT_TO_ASSESS":
        assert data["financial_health_index"] is None
        assert data["vyapar_credit_health_score"] is None
    else:
        assert data["financial_health_index"] is not None
        assert 300 <= data["vyapar_credit_health_score"] <= 900
    assert "fhi_breakdown" in data
    assert isinstance(data["fhi_breakdown"], dict)
    for pillar in [
        "liquidity",
        "cash_flow_capacity",
        "revenue_stability_momentum",
        "repayment_burden_discipline",
        "compliance_formalisation",
        "concentration_resilience",
    ]:
        assert pillar in data["fhi_breakdown"]
    assert data.get("scoring_version") == "3.1-EVIDENCE-LINKED-FHI"
    assert "calculation_evidence_ids" in data
    assert isinstance(data["calculation_evidence_ids"], dict)

    # Verify P3 / BNK-001 / BNK-002: Milestone-controlled conditional structure integration
    assert "conditions" in data
    assert isinstance(data["conditions"], list)
    assert "bankability_path" in data
    if data.get("bankability_path"):
        bp = data["bankability_path"]
        assert "milestones" in bp
        for m in bp.get("milestones", []):
            assert "simulation_evidence" in m
            assert "impact_on_score" in m
            assert "target_state" in m

    # Verify SHA-256 package hash is present and well-formed
    assert "package_hash" in data
    assert data["package_hash"] is not None
    assert len(data["package_hash"]) == 64  # SHA-256 hex digest
    assert all(c in "0123456789abcdef" for c in data["package_hash"])


def test_seal_rejects_incomplete_snapshot_without_persisting(setup_data, db_session):
    user = setup_data["users"][UserRole.CREDIT_ANALYST]
    res = login(user.email, "securepass123")
    client.cookies.clear()
    client.cookies.set("vyapar_session_token", res.cookies.get("vyapar_session_token"))
    csrf_token = res.cookies.get("vyapar_csrf_token")

    before_count = (
        db_session.query(DecisionPackage)
        .filter(DecisionPackage.case_id == setup_data["case_id"])
        .count()
    )
    res = client.post(
        f"/api/cases/{setup_data['case_id']}/decision-package",
        headers={"x-csrf-token": csrf_token},
    )
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "FEATURE_SNAPSHOT_INCOMPLETE"
    after_count = (
        db_session.query(DecisionPackage)
        .filter(DecisionPackage.case_id == setup_data["case_id"])
        .count()
    )
    assert after_count == before_count


def test_audit_verifier_reports_actual_authorization_scope(setup_data, db_session):
    system_admin = setup_data["users"][UserRole.SYSTEM_ADMIN]
    result = verify_audit_chain(db_session, setup_data["case_id"], system_admin)
    assert result["authorization_scope_valid"] is False
    assert result["reason"] == "AUTHORIZATION_SCOPE_INVALID"


def test_command_centre_and_monitoring(setup_data):
    user = setup_data["users"][UserRole.CREDIT_ANALYST]
    res = login(user.email, "securepass123")
    cookie = get_cookie(res)
    client.cookies.set("vyapar_session", cookie)

    # Test Portfolio Command Centre (CD-003)
    p_res = client.get("/api/cases/portfolio-command-centre")
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert "active_cases_count" in p_data
    assert "total_requested_exposure" in p_data
    assert "total_supportable_exposure" in p_data
    assert "prioritized_work_queue" in p_data
    assert isinstance(p_data["prioritized_work_queue"], list)

    # Test Post-assessment Monitoring (CD-004)
    m_res = client.get(f"/api/cases/{setup_data['case_id']}/monitoring")
    assert m_res.status_code == 200
    m_data = m_res.json()
    assert "monitoring_status" in m_data
    assert m_data["monitoring_status"] == "ACTIVE_MONITORING"
    assert "deterioration_alerts" in m_data
    assert isinstance(m_data["deterioration_alerts"], list)
    assert len(m_data["deterioration_alerts"]) == 4
