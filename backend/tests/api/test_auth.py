import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal, engine
from app.api.auth import hash_token
from app.seed.seed_shakti import seed_shakti
import os
from datetime import datetime, timedelta, timezone
from app.db.orm.users import SessionStore


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

    # Uses the globally generated random password from conftest.py
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


def login_and_get_tokens(client: TestClient):
    password = os.environ["DEMO_USER_PASSWORD"]
    login_res = client.post(
        "/api/auth/login", json={"email": "credit@bank.example", "password": password}
    )
    assert login_res.status_code == 200, login_res.text
    session_token = login_res.cookies.get("vyapar_session_token")
    csrf_token = login_res.cookies.get("vyapar_csrf_token")
    return session_token, csrf_token


def test_auth_valid_session_and_exact_keys(client: TestClient):
    session_token, _ = login_and_get_tokens(client)
    client.cookies.clear()
    client.cookies.set("vyapar_session_token", session_token)

    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.json()

    expected_keys = {"id", "full_name", "email", "role"}
    assert set(me_data.keys()) == expected_keys
    assert me_data["email"] == "credit@bank.example"


def test_auth_missing_session(client: TestClient):
    client.cookies.clear()
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_auth_expired_session(client: TestClient, db):
    session_token, _ = login_and_get_tokens(client)

    # Expire the session in DB
    db_session = (
        db.query(SessionStore)
        .filter(SessionStore.session_token == hash_token(session_token))
        .first()
    )
    assert db_session
    db_session.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    db.commit()

    client.cookies.clear()
    client.cookies.set("vyapar_session_token", session_token)
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_auth_revoked_session(client: TestClient, db):
    session_token, csrf_token = login_and_get_tokens(client)

    client.cookies.clear()
    client.cookies.set("vyapar_session_token", session_token)

    # Logout to revoke
    logout_res = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout_res.status_code == 200

    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_second_login_invalidates_first(client: TestClient, db):
    session_token1, _ = login_and_get_tokens(client)
    session_token2, _ = login_and_get_tokens(client)

    assert session_token1 != session_token2

    # The first session should be deleted or inactive from the DB if login invalidates it.
    # But let's just check the API response with the old token.
    client.cookies.clear()
    client.cookies.set("vyapar_session_token", session_token1)
    res1 = client.get("/api/auth/me")
    assert res1.status_code == 401

    client.cookies.clear()
    client.cookies.set("vyapar_session_token", session_token2)
    res2 = client.get("/api/auth/me")
    assert res2.status_code == 200
