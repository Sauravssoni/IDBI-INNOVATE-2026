import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, engine
from app.seed.seed_shakti import seed_shakti
from app.db.orm.cases import Case, Business


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


def test_bankability_path_success(client: TestClient, db):
    business = (
        db.query(Business)
        .filter(Business.business_id == "SHAKTI_PRECISION_001")
        .first()
    )
    assert business is not None and len(business.cases) > 0
    shakti_case = business.cases[0]

    auth_kwargs = get_auth_kwargs(client, "credit@bank.example")
    response = client.post(
        f"/api/cases/{shakti_case.id}/bankability-path",
        json={"target_amount": 50000000},  # 5 Cr target
        **auth_kwargs,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "current_limit" in data
    assert "target_requested" in data
    assert "gap_to_target" in data
    assert "is_target_achievable_now" in data
    assert "milestones" in data

    assert data["target_requested"] == 50000000
    assert isinstance(data["milestones"], list)
    assert "hindi_bilingual_presentation" in data
    assert "summary" in data["hindi_bilingual_presentation"]
    assert "milestone_actions" in data["hindi_bilingual_presentation"]


def test_bankability_path_bola_denial(client: TestClient, db):
    business = (
        db.query(Business)
        .filter(Business.business_id == "SHAKTI_PRECISION_001")
        .first()
    )
    assert business is not None and len(business.cases) > 0
    shakti_case = business.cases[0]

    auth_kwargs = get_auth_kwargs(client, "system@bank.example")
    response = client.post(
        f"/api/cases/{shakti_case.id}/bankability-path",
        json={"target_amount": 50000000},
        **auth_kwargs,
    )
    assert response.status_code in (403, 404)


def test_bankability_simulate_api(client: TestClient, db):
    business = (
        db.query(Business)
        .filter(Business.business_id == "SHAKTI_PRECISION_001")
        .first()
    )
    assert business is not None and len(business.cases) > 0
    shakti_case = business.cases[0]

    auth_kwargs = get_auth_kwargs(client, "credit@bank.example")
    response = client.post(
        f"/api/cases/{shakti_case.id}/simulate",
        json={"overrides": {"dscr": "2.25", "operating_inflows_monthly": "1500000"}},
        **auth_kwargs,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "before_simulation" in data
    assert "after_simulation" in data
    assert "uplift_summary" in data
    assert data["engine_version"] == "2.0-BANKABILITY-SIMULATION"

