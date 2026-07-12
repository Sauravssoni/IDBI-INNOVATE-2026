from fastapi.testclient import TestClient
import pytest
import os
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_login(client: TestClient):
    email = "demo_analyst@vyaparpulse.com"
    password = os.environ.get("DEMO_USER_PASSWORD", "mocked_in_tests")
    print(f"\nPassword: {password}")
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    print(res.status_code)
    print(res.json())
