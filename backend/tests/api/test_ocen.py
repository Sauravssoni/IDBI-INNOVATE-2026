from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.orm.cases import Case, Business, DecisionPackage
from app.api.dependencies import get_current_user
from app.db.orm.users import User
import uuid

def override_get_current_user():
    return User(id=uuid.uuid4(), email="test@vyaparpulse.example", role="CREDIT_ANALYST")

def test_ocen_export():
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)
    db = SessionLocal()
    try:
        # Get the shakti case
        business = db.query(Business).filter(Business.business_id == "SHAKTI_PRECISION_001").first()
        assert business is not None
        case = db.query(Case).filter(Case.business_id_fk == business.id).first()
        assert case is not None

        # Manually create DecisionPackage
        pkg = db.query(DecisionPackage).filter(DecisionPackage.case_id == case.id).first()
        if not pkg:
            pkg = DecisionPackage(
                id=uuid.uuid4(),
                package_id=f"PKG-{uuid.uuid4()}",
                assessment_id=f"ASSM-{uuid.uuid4()}",
                case_id=case.id,
                case_version=1,
                canonical_json={"binding_limit": 50000.00},
                package_hash="some_hash"
            )
            db.add(pkg)
            db.commit()

        response = client.get(
            f"/api/cases/{case.id}/ocen-export",
        )
        print(response.text)
        assert response.status_code == 200
        data = response.json()
        assert data["schema_version"] == "2.0-CANONICAL"
        assert data["prototype_interoperability_payload"] is True
        assert data["borrower"]["entity_name"] == case.business.legal_name
        assert data["credit_decision"]["status"] == case.status.value
        assert float(data["credit_decision"]["indicative_supportable_amount"]) == float(pkg.canonical_json["binding_limit"])

    finally:
        db.close()
        app.dependency_overrides.clear()
