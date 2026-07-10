import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal, engine
from app.seed.seed_shakti import seed_shakti
from app.db.orm.cases import Case, Business
from app.domain.evidence.passport import generate_evidence_passport


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


def test_generate_evidence_passport(db):
    business = db.query(Business).filter(Business.business_id == "SHAKTI_PRECISION_001").first()
    assert business is not None and len(business.cases) > 0
    case = business.cases[0]

    passport = generate_evidence_passport(db, str(case.id))
    assert passport["case_id"] == str(case.id)
    assert passport["business_id"] == str(business.id)
    assert "rail_coverage" in passport
    assert passport["rail_coverage"]["gst"] is True
    assert passport["rail_coverage"]["account_aggregator"] is True
    assert "freshness_depth" in passport
    assert passport["freshness_depth"]["gst_periods"] > 0
    assert "obligation_verification" in passport
    assert "contradiction_analysis" in passport
    assert "assessment_certainty" in passport


def test_api_evidence_passport(db):
    client = TestClient(app)
    business = db.query(Business).filter(Business.business_id == "SHAKTI_PRECISION_001").first()
    assert business is not None and len(business.cases) > 0
    case = business.cases[0]

    login_resp = client.post(
        "/api/auth/login",
        json={"email": "credit@bank.example", "password": os.environ["DEMO_USER_PASSWORD"]},
    )
    assert login_resp.status_code == 200
    cookies = login_resp.cookies
    headers = {"X-CSRF-Token": cookies.get("vyapar_csrf_token", "")}
    client.cookies = cookies

    resp = client.get(f"/api/cases/{case.id}/evidence-passport", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == str(case.id)
    assert data["business_id"] == str(business.id)
    assert "rail_coverage" in data
    assert "assessment_certainty" in data
