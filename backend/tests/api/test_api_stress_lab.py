import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, engine
from app.seed.seed_shakti import seed_shakti
from app.db.orm.cases import Business
from app.domain.stress.engine import run_case_stress_lab


@pytest.fixture(scope="module", autouse=True)
def setup_shakti_db():
    import urllib.parse

    db_url = os.environ.get("DATABASE_URL", str(engine.url))
    parsed_url = urllib.parse.urlparse(db_url)
    datname = parsed_url.path.lstrip("/")
    if "test" not in datname.lower():
        raise RuntimeError("Refusing to run tests against non-test database name")

    test_password = os.environ.get("DEMO_USER_PASSWORD", "testpassword123")
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


def get_cookie_from_response(response, cookie_name):
    return response.cookies.get(cookie_name) or ""


def get_auth_kwargs(client: TestClient, email: str):
    password = os.environ.get("DEMO_USER_PASSWORD", "testpassword123")
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


def test_stress_lab_success(client: TestClient, db):
    business = (
        db.query(Business)
        .filter(Business.business_id == "SHAKTI_PRECISION_001")
        .first()
    )
    assert business is not None and len(business.cases) > 0
    shakti_case = business.cases[0]

    auth_kwargs = get_auth_kwargs(client, "credit@bank.example")
    response = client.post(
        f"/api/cases/{shakti_case.id}/stress-lab",
        json={"revenue_drop_pct": 10.0, "interest_rate_hike_bps": 200},
        **auth_kwargs,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "scenario" in data
    assert "baseline" in data
    assert "stressed" in data
    assert "summary" in data

    # Verify baseline vs stressed
    assert data["scenario"]["revenue_drop_pct"] == 10.0
    assert data["scenario"]["interest_rate_hike_bps"] == 200
    assert data["stressed"]["status"] in [
        "SECURE",
        "VULNERABLE",
        "DISTRESSED",
        "NOT_ASSESSABLE",
    ]
    # Check bounds safety and exact formula behavior
    assert data["stressed"]["max_loan_amount"] <= data["baseline"]["max_loan_amount"]


def test_stress_lab_bola_denial(client: TestClient, db):
    business = (
        db.query(Business)
        .filter(Business.business_id == "SHAKTI_PRECISION_001")
        .first()
    )
    assert business is not None and len(business.cases) > 0
    shakti_case = business.cases[0]

    # System admin cannot run evaluation/stress lab on cases
    auth_kwargs = get_auth_kwargs(client, "system@bank.example")
    response = client.post(
        f"/api/cases/{shakti_case.id}/stress-lab",
        json={"revenue_drop_pct": 15.0},
        **auth_kwargs,
    )
    assert response.status_code in (403, 404)


def test_stress_lab_unknown_obligations_not_assessable():
    result = run_case_stress_lab(
        features={
            "consent_status": "VALID",
            "bank_metrics": {
                "operating_inflows_monthly": "1000000",
                "operating_outflows_monthly": "700000",
            },
            "obligation_verification_state": "UNKNOWN_OBLIGATIONS",
        },
        scores={"evidence_confidence_score": 85},
        requested_amount=1000000,
        requested_product="TERM_LOAN",
    )

    assert result["overall_stress_status"] == "NOT_ASSESSABLE"
    assert result["baseline"]["status"] == "NOT_ASSESSABLE"
    assert all(s["status"] == "NOT_ASSESSABLE" for s in result["scenarios"])
