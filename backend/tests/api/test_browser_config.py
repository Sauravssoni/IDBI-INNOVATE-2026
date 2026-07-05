import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.db.orm.users import User, UserRole, SessionStore
from app.api.auth import get_password_hash

client = TestClient(app)


@pytest.fixture(scope="module")
def test_user():
    db = SessionLocal()
    unique_id = str(uuid.uuid4())[:8]
    email = f"browser_test_{unique_id}@example.com"
    password = "secure_test_password"
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name="Browser Config Test User",
        role=UserRole.CREDIT_ANALYST,
        is_active=True,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    yield {"email": email, "password": password, "id": user_id}
    db = SessionLocal()
    db.query(SessionStore).filter(SessionStore.user_id == str(user_id)).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


def test_localhost_development_cookies_not_secure(monkeypatch, test_user):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3005")
    monkeypatch.setenv("COOKIE_SECURE", "false")

    settings = get_settings()
    assert settings.COOKIE_SECURE is False
    assert settings.ALLOWED_ORIGINS == ["http://localhost:3005"]

    res = client.post(
        "/api/auth/login",
        json={"email": test_user["email"], "password": test_user["password"]},
    )
    assert res.status_code == 200
    cookies = res.headers.get_list("set-cookie")
    assert len(cookies) >= 2
    for cookie in cookies:
        assert "secure" not in cookie.lower()
        assert "path=/" in cookie.lower()
        assert "samesite=lax" in cookie.lower()


def test_deployment_cookies_secure(monkeypatch, test_user):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://vyaparpulse.example.com")
    monkeypatch.setenv("COOKIE_SECURE", "true")

    settings = get_settings()
    assert settings.COOKIE_SECURE is True

    res = client.post(
        "/api/auth/login",
        json={"email": test_user["email"], "password": test_user["password"]},
    )
    assert res.status_code == 200
    cookies = res.headers.get_list("set-cookie")
    assert len(cookies) >= 2
    for cookie in cookies:
        assert "secure" in cookie.lower()
        assert "path=/" in cookie.lower()
        assert "samesite=lax" in cookie.lower()


def test_unsafe_deployed_configuration_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://vyaparpulse.example.com")
    monkeypatch.setenv("COOKIE_SECURE", "false")

    with pytest.raises(RuntimeError) as excinfo:
        get_settings()
    assert "COOKIE_SECURE=true required" in str(excinfo.value)

    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("COOKIE_SECURE", "true")
    with pytest.raises(RuntimeError) as excinfo:
        get_settings()
    assert "explicit ALLOWED_ORIGINS required" in str(excinfo.value)


def test_localhost_3005_is_accepted(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3005")
    monkeypatch.setenv("COOKIE_SECURE", "false")

    settings = get_settings()
    assert settings.ALLOWED_ORIGINS == ["http://localhost:3005"]
    assert settings.COOKIE_SECURE is False


def test_unapproved_origin_is_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://unapproved.example.com")
    monkeypatch.setenv("COOKIE_SECURE", "false")

    with pytest.raises(RuntimeError) as excinfo:
        get_settings()
    assert "recognized localhost origin" in str(excinfo.value)


def test_logout_deletion_uses_matching_cookie_settings(monkeypatch, test_user):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://vyaparpulse.example.com")
    monkeypatch.setenv("COOKIE_SECURE", "true")

    login_res = client.post(
        "/api/auth/login",
        json={"email": test_user["email"], "password": test_user["password"]},
    )
    assert login_res.status_code == 200

    session_token = ""
    csrf_token = ""
    for cookie in login_res.headers.get_list("set-cookie"):
        if cookie.startswith("vyapar_session_token="):
            session_token = cookie.split(";")[0].split("=")[1]
        elif cookie.startswith("vyapar_csrf_token="):
            csrf_token = cookie.split(";")[0].split("=")[1]

    logout_res = client.post(
        "/api/auth/logout",
        cookies={
            "vyapar_session_token": session_token,
            "vyapar_csrf_token": csrf_token,
        },
        headers={"x-csrf-token": csrf_token},
    )
    assert logout_res.status_code == 200
    logout_cookies = logout_res.headers.get_list("set-cookie")
    assert len(logout_cookies) >= 2

    session_cookie_found = False
    csrf_cookie_found = False

    for cookie in logout_cookies:
        lower_cookie = cookie.lower()
        assert "path=/" in lower_cookie
        assert "samesite=lax" in lower_cookie
        assert "secure" in lower_cookie
        if "vyapar_session_token" in cookie:
            session_cookie_found = True
            assert "httponly" in lower_cookie
        elif "vyapar_csrf_token" in cookie:
            csrf_cookie_found = True
            assert "httponly" not in lower_cookie

    assert session_cookie_found
    assert csrf_cookie_found


def test_production_wildcard_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    with pytest.raises(RuntimeError) as excinfo:
        get_settings()
    assert "wildcard origins are not permitted" in str(excinfo.value)


def test_production_http_origin_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://vyaparpulse.example.com")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    with pytest.raises(RuntimeError) as excinfo:
        get_settings()
    assert "explicit HTTPS origins required" in str(excinfo.value)


def test_production_localhost_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    for origin in (
        "https://localhost:3000",
        "https://127.0.0.1:3000",
        "https://[::1]:3000",
        "https://0.0.0.0:3000",
    ):
        monkeypatch.setenv("ALLOWED_ORIGINS", origin)
        with pytest.raises(RuntimeError) as excinfo:
            get_settings()
        assert "localhost origins are not permitted" in str(excinfo.value)


def test_production_https_origin_accepted(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://vyaparpulse.example.com")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    settings = get_settings()
    assert settings.ALLOWED_ORIGINS == ["https://vyaparpulse.example.com"]
    assert settings.COOKIE_SECURE is True
