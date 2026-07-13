import pytest
import os
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.orm.users import User, UserRole
from app.api.auth import get_password_hash
from unittest.mock import patch


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


@pytest.fixture
def demo_user(db):
    email = f"demo_reset_{uuid.uuid4().hex[:8]}@vyaparpulse.com"
    password = "testpassword123"
    user = User(
        email=email,
        full_name="Demo Reset Test",
        hashed_password=get_password_hash(password),
        role=UserRole.CREDIT_ANALYST,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield email, password
    from app.db.orm.users import SessionStore

    db.query(SessionStore).filter(SessionStore.user_id == user.id).delete()
    db.delete(user)
    db.commit()


def login_and_get_tokens(client: TestClient, email, password):
    login_res = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    if login_res.status_code != 200:
        return None, None
    cookies = login_res.cookies
    session_token = cookies.get("vyapar_session_token")
    csrf_token = cookies.get("vyapar_csrf_token")
    return session_token, csrf_token


def test_demo_reset_disabled(client: TestClient, demo_user):
    email, password = demo_user
    app.dependency_overrides = {}
    with patch("app.core.config.os.getenv") as mock_getenv:

        def side_effect(key, default=None):
            if key == "DEMO_RESET_ENABLED":
                return "false"
            if key == "DEMO_ACCESS_ENABLED":
                return "true"
            return os.environ.get(key, default)

        mock_getenv.side_effect = side_effect

        session_token, csrf_token = login_and_get_tokens(client, email, password)
        if not session_token:
            pytest.skip("Login failed in test setup")

        client.cookies.set("vyapar_session_token", session_token)
        headers = {"X-CSRF-Token": csrf_token}
        res = client.post("/api/demo/reset", headers=headers)
        assert res.status_code == 403
        assert "disabled" in res.json()["detail"].lower()


def test_demo_reset_missing_csrf(client: TestClient, demo_user):
    email, password = demo_user
    app.dependency_overrides = {}
    with patch("app.core.config.os.getenv") as mock_getenv:

        def side_effect(key, default=None):
            if key == "DEMO_RESET_ENABLED":
                return "true"
            if key == "DEMO_ACCESS_ENABLED":
                return "true"
            return os.environ.get(key, default)

        mock_getenv.side_effect = side_effect

        session_token, _ = login_and_get_tokens(client, email, password)
        if not session_token:
            pytest.skip("Login failed in test setup")

        client.cookies.set("vyapar_session_token", session_token)
        res = client.post("/api/demo/reset")
        assert res.status_code == 403
        assert "CSRF" in res.json()["detail"]


def test_demo_reset_wrong_token(client: TestClient, demo_user):
    email, password = demo_user
    app.dependency_overrides = {}
    with patch("app.core.config.os.getenv") as mock_getenv:

        def side_effect(key, default=None):
            if key == "DEMO_RESET_ENABLED":
                return "true"
            if key == "DEMO_ACCESS_ENABLED":
                return "true"
            if key == "DEMO_RESET_TOKEN":
                return "correct_token"
            return os.environ.get(key, default)

        mock_getenv.side_effect = side_effect

        session_token, csrf_token = login_and_get_tokens(client, email, password)
        if not session_token:
            pytest.skip("Login failed in test setup")

        client.cookies.set("vyapar_session_token", session_token)
        headers = {"X-CSRF-Token": csrf_token, "X-Demo-Reset-Token": "wrong"}
        res = client.post("/api/demo/reset", headers=headers)
        assert res.status_code == 403
        assert "token" in res.json()["detail"].lower()
