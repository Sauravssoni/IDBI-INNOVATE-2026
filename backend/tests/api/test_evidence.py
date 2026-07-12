from fastapi.testclient import TestClient
from uuid import uuid4
from unittest.mock import patch
from app.main import app
from app.api.dependencies import get_current_user
from app.db.session import SessionLocal
from app.db.orm.users import User
from app.db.orm.cases import Case, Business

# dependency override
def override_get_current_user():
    return User(id=uuid4(), email="test@idbi.in", role="relationship_manager", is_active=True)

def test_evidence_envelope():
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)
    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.business_id == "SHAKTI_PRECISION_001").first()
        assert business is not None
        case = db.query(Case).filter(Case.business_id_fk == business.id).first()
        assert case is not None

        with patch("app.api.routers.evidence.can_view_case", return_value=case):
            response = client.get(f"/api/cases/{case.id}/evidence-envelope")
            print(response.json())
            assert response.status_code == 200
            data = response.json()
            assert "evidence_certainty" in data
            assert "freshness_score" in data
    finally:
        db.close()
        app.dependency_overrides.clear()
