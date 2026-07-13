from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
from app.api.dependencies import get_current_user, get_db
from app.db.orm.users import User, UserRole
from app.db.orm.cases import Case, AssessmentSnapshot
import pytest
from uuid import uuid4

class MockAssessmentSnap:
    assessment_id = "test_id"

class MockQuery:
    def filter(self, *args, **kwargs):
        return self
    def order_by(self, *args, **kwargs):
        return self
    def first(self):
        return MockAssessmentSnap()

class MockCase:
    def __init__(self):
        self.id = uuid4()
        self.version = 1
        self.business_id_fk = uuid4()
        self.analyst_recommendation = "RECOMMEND_AS_REQUESTED"
        self.human_decision = "APPROVE_AS_REQUESTED"

class MockDB:
    def query(self, model):
        if model == Case:
            class Q:
                def filter(self, *args, **kwargs): return self
                def first(self): return MockCase()
            return Q()
        if model == AssessmentSnapshot:
            return MockQuery()
        return MockQuery()
        
    def commit(self): pass
    def refresh(self, obj): pass
    def add(self, obj): pass
    def rollback(self): pass

def override_get_db():
    return MockDB()

def test_auditor_cannot_seal():
    with TestClient(app) as client:
        app.dependency_overrides[get_current_user] = lambda: User(id=1, email="a@b.com", role=UserRole.AUDITOR)
        app.dependency_overrides[get_db] = override_get_db
        with patch("app.api.routers.cases.can_view_case", return_value=MockCase()):
            res = client.post(f"/api/cases/{uuid4()}/decision-package")
        assert res.status_code == 403

def test_risk_admin_cannot_seal():
    with TestClient(app) as client:
        app.dependency_overrides[get_current_user] = lambda: User(id=1, email="a@b.com", role=UserRole.RISK_ADMIN)
        app.dependency_overrides[get_db] = override_get_db
        with patch("app.api.routers.cases.can_view_case", return_value=MockCase()):
            res = client.post(f"/api/cases/{uuid4()}/decision-package")
        assert res.status_code == 403

def test_analyst_cannot_seal():
    with TestClient(app) as client:
        app.dependency_overrides[get_current_user] = lambda: User(id=1, email="a@b.com", role=UserRole.CREDIT_ANALYST)
        app.dependency_overrides[get_db] = override_get_db
        with patch("app.api.routers.cases.can_view_case", return_value=MockCase()):
            res = client.post(f"/api/cases/{uuid4()}/decision-package")
        assert res.status_code == 403

def test_sanctioning_authority_can_seal_only_after_assessment():
    with TestClient(app) as client:
        app.dependency_overrides[get_current_user] = lambda: User(id=1, email="a@b.com", role=UserRole.SANCTIONING_AUTHORITY)
        
        # Mock Case missing human decision
        class MockCaseIncomplete:
            def __init__(self):
                self.id = uuid4()
                self.version = 1
                self.business_id_fk = uuid4()
                self.analyst_recommendation = "RECOMMEND_AS_REQUESTED"
                self.human_decision = "PENDING"
        
        class MockDBIncomplete:
            def query(self, model):
                class Q:
                    def filter(self, *args, **kwargs): return self
                    def first(self): 
                        if model == Case: return MockCaseIncomplete()
                        if model == AssessmentSnapshot: return MockAssessmentSnap()
                        return None
                return Q()
            def commit(self): pass
            def refresh(self, obj): pass
            def add(self, obj): pass
            def rollback(self): pass
                
        app.dependency_overrides[get_db] = lambda: MockDBIncomplete()
        with patch("app.api.routers.cases.can_view_case", return_value=MockCaseIncomplete()):
            res = client.post(f"/api/cases/{uuid4()}/decision-package")
        assert res.status_code == 409
        assert "Cannot seal" in res.json().get("detail", "")
