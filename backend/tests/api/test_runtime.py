import os
import pytest
import importlib
from unittest import mock
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def clean_env():
    import app.db.session as session_module

    original_env = os.environ.copy()
    with mock.patch.dict(os.environ, clear=True):
        yield

    # Restore original env and reload session module
    os.environ.clear()
    os.environ.update(original_env)
    importlib.reload(session_module)


def test_missing_production_database_url(clean_env):
    os.environ["APP_ENV"] = "production"
    import app.db.session as session_module

    with pytest.raises(RuntimeError, match="DATABASE_URL is required in production"):
        importlib.reload(session_module)


def test_quoted_empty_url(clean_env):
    os.environ["APP_ENV"] = "production"
    os.environ["DATABASE_URL"] = '""'
    import app.db.session as session_module

    with pytest.raises(RuntimeError, match="DATABASE_URL is required in production"):
        importlib.reload(session_module)


def test_localhost_url_rejected_in_production(clean_env):
    os.environ["APP_ENV"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://user:pass@127.0.0.1:5432/db"
    import app.db.session as session_module

    with pytest.raises(
        RuntimeError, match="Production DATABASE_URL must point to managed PostgreSQL"
    ):
        importlib.reload(session_module)


def test_valid_test_dev_fallback(clean_env):
    os.environ["APP_ENV"] = "development"
    # No DATABASE_URL set
    import app.db.session as session_module

    importlib.reload(session_module)
    assert session_module.DATABASE_URL == session_module.DEFAULT_LOCAL_DATABASE_URL


def test_health_endpoint():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@mock.patch("app.main.SessionLocal")
def test_database_unavailable_readiness(mock_session_local):
    # Mock db.execute to raise Exception
    mock_db = mock.MagicMock()
    mock_db.execute.side_effect = Exception("Connection failed")
    mock_session_local.return_value = mock_db

    client = TestClient(app)
    res = client.get("/ready")
    assert res.status_code == 503
    assert res.json()["status"] == "unavailable"
    assert res.json()["reason"] == "Database connection or schema failed"


@mock.patch("app.main.SessionLocal")
def test_migration_behind_readiness(mock_session_local, monkeypatch):
    mock_db = mock.MagicMock()
    mock_session_local.return_value = mock_db

    # First call: SELECT 1 (returns nothing, just runs)
    # Second call: SELECT version_num
    # Third call: SELECT count(*)
    def mock_execute(query):
        query_str = str(query)
        if "SELECT 1" in query_str:
            return mock.MagicMock()
        if "alembic_version" in query_str:
            res = mock.MagicMock()
            res.scalar.return_value = "old_version"
            return res
        return mock.MagicMock()

    mock_db.execute.side_effect = mock_execute

    # Mock alembic heads
    import app.main as main_module

    class DummyScript:
        def get_heads(self):
            return ["new_version"]

    monkeypatch.setattr(
        main_module.ScriptDirectory, "from_config", lambda cfg: DummyScript()
    )

    client = TestClient(app)
    res = client.get("/ready")
    assert res.status_code == 503
    assert res.json()["status"] == "unavailable"


@mock.patch("app.main.SessionLocal")
def test_seed_missing_readiness(mock_session_local, monkeypatch):
    mock_db = mock.MagicMock()
    mock_session_local.return_value = mock_db

    def mock_execute(query):
        query_str = str(query)
        if "SELECT 1" in query_str:
            return mock.MagicMock()
        if "alembic_version" in query_str:
            res = mock.MagicMock()
            res.scalar.return_value = "current_version"
            return res
        if "count(*)" in query_str:
            res = mock.MagicMock()
            res.scalar.return_value = 0  # missing seed
            return res
        return mock.MagicMock()

    mock_db.execute.side_effect = mock_execute

    import app.main as main_module

    class DummyScript:
        def get_heads(self):
            return ["current_version"]

    monkeypatch.setattr(
        main_module.ScriptDirectory, "from_config", lambda cfg: DummyScript()
    )
    monkeypatch.setattr(main_module.settings, "DEMO_ACCESS_ENABLED", True)

    client = TestClient(app)
    res = client.get("/ready")
    assert res.status_code == 503
    assert res.json()["status"] == "unavailable"


@mock.patch("app.main.SessionLocal")
def test_fully_ready_state(mock_session_local, monkeypatch):
    mock_db = mock.MagicMock()
    mock_session_local.return_value = mock_db

    def mock_execute(query):
        query_str = str(query)
        if "SELECT 1" in query_str:
            return mock.MagicMock()
        if "alembic_version" in query_str:
            res = mock.MagicMock()
            res.scalar.return_value = "current_version"
            return res
        if "count(*)" in query_str:
            res = mock.MagicMock()
            res.scalar.return_value = 4  # fully seeded
            return res
        return mock.MagicMock()

    mock_db.execute.side_effect = mock_execute

    import app.main as main_module

    class DummyScript:
        def get_heads(self):
            return ["current_version"]

    monkeypatch.setattr(
        main_module.ScriptDirectory, "from_config", lambda cfg: DummyScript()
    )

    client = TestClient(app)
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json()["demo_seed_ready"] is True
    assert res.json()["migration_head"] == "current_version"
