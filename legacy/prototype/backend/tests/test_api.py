from fastapi.testclient import TestClient

from app.main import app
from app.sample_data import DEMO_CASES

client = TestClient(app)


def test_assessment_creates_audit_lineage():
    response = client.post("/api/v1/assess", json=DEMO_CASES[0].model_dump(mode="json"))
    assert response.status_code == 200
    assessment = response.json()
    audit = client.get(f"/api/v1/audit/{assessment['assessment_id']}")
    assert audit.status_code == 200
    events = audit.json()
    assert events[0]["event_type"] == "assessment_created"
    assert len(events[0]["payload_hash"]) == 64


def test_human_decision_requires_reason():
    response = client.post(
        "/api/v1/human-decisions",
        json={
            "assessment_id": "asm_demo",
            "business_id": "MSME-1",
            "actor": "credit.officer@bank.example",
            "decision": "review",
            "reason": "short",
        },
    )
    assert response.status_code == 422
