import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import SessionLocal, engine
from app.seed.seed_shakti import seed_shakti
import os

@pytest.fixture(scope="module", autouse=True)
def setup_shakti_data():
    import urllib.parse
    import uuid
    db_url = os.environ.get("DATABASE_URL", str(engine.url))
    parsed_url = urllib.parse.urlparse(db_url)
    datname = parsed_url.path.lstrip("/")
    if "test" not in datname.lower():
        raise RuntimeError(f"Refusing to run tests against non-test database name: '{datname}'")
    if os.environ.get("APP_ENV") == "production":
        raise RuntimeError("Refusing to run tests in production environment")

    test_password = os.environ.get("DEMO_USER_PASSWORD") or "password"
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

def test_auth_me_exhaustive(client: TestClient):
    # 1. No token
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    
    # 2. Invalid token
    client.cookies.set("vyapar_session_token", "invalid_token_123")
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    
    # 3. Valid token
    password = os.environ.get("DEMO_USER_PASSWORD")
    login_res = client.post("/api/auth/login", json={"email": "credit@bank.example", "password": password})
    assert login_res.status_code == 200, login_res.text
    
    session_token = login_res.cookies.get("vyapar_session_token")
    assert session_token
    
    # Check /api/auth/me structure
    client.cookies.clear()
    client.cookies.set("vyapar_session_token", session_token)
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.json()
    
    expected_keys = {"id", "full_name", "email", "role"}
    assert set(me_data.keys()) == expected_keys
    assert me_data["email"] == "credit@bank.example"
    assert me_data["role"] == "CREDIT_ANALYST"
    
    csrf_token = login_res.cookies.get("vyapar_csrf_token")
    assert csrf_token
    
    # 4. Logout invalidates token
    logout_res = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout_res.status_code == 200
    
    me_res2 = client.get("/api/auth/me")
    assert me_res2.status_code == 401
