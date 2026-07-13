from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.orm.cases import Case, Business, DecisionPackage
from app.api.dependencies import get_current_user
from app.db.orm.users import User
import uuid
import datetime
from app.db.orm.cases import AssessmentSnapshot


def override_get_current_user():
    return User(
        id=uuid.uuid4(), email="test@vyaparpulse.example", role="CREDIT_ANALYST"
    )


def test_ocen_export():
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)
    db = SessionLocal()
    try:
        # Get the shakti case
        business = (
            db.query(Business)
            .filter(Business.business_id == "SHAKTI_PRECISION_001")
            .first()
        )
        assert business is not None
        case = db.query(Case).filter(Case.business_id_fk == business.id).first()
        assert case is not None

        # Manually create DecisionPackage
        pkg = (
            db.query(DecisionPackage).filter(DecisionPackage.case_id == case.id).first()
        )
        if pkg:
            db.delete(pkg)

        snap = (
            db.query(AssessmentSnapshot)
            .filter(
                AssessmentSnapshot.case_id == case.id,
                AssessmentSnapshot.case_version == 1,
            )
            .first()
        )
        if snap:
            db.delete(snap)

        db.commit()

        assm_id = uuid.uuid4()
        pkg = DecisionPackage(
            id=uuid.uuid4(),
            package_id=f"PKG-{uuid.uuid4()}",
            assessment_id=str(assm_id),
            case_id=case.id,
            case_version=1,
            canonical_json={"binding_limit": 50000.00},
            package_hash="some_hash",
        )
        db.add(pkg)

        snap = AssessmentSnapshot(
            assessment_id=assm_id,
            case_id=case.id,
            case_version=1,
            generated_at=datetime.datetime.utcnow(),
            feature_snapshot={"total_revenue": 1000000, "total_bank_credits": 1000000},
            canonical_assessment_json={"supportable_amount": 50000.00},
            engine_versions={
                "scoring": "1",
                "calculation": "1",
                "policy": "1",
                "feature": "1",
            },
            evidence_ids=[],
        )
        db.add(snap)
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
        assert float(data["credit_decision"]["indicative_supportable_amount"]) == float(
            pkg.canonical_json["binding_limit"]
        )

    finally:
        db.close()
        app.dependency_overrides.clear()
