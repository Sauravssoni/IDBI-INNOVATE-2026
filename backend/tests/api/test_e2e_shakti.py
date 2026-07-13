import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal, engine
from app.seed.seed_shakti import seed_shakti
from app.db.orm.cases import Case

import os


@pytest.fixture(scope="module", autouse=True)
def setup_shakti_db():
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

    test_password = os.environ.get("DEMO_USER_PASSWORD", "testpassword123")
    os.environ["DEMO_USER_PASSWORD"] = test_password

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


def get_cookie_from_response(response, cookie_name):
    return response.cookies.get(cookie_name) or ""


def get_auth_headers(client: TestClient, email: str):
    import os

    password = os.environ.get("DEMO_USER_PASSWORD")
    if not password:
        raise RuntimeError("DEMO_USER_PASSWORD must be set for test login.")

    response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 200, f"Failed to login {email}: {response.text}"
    session_token = get_cookie_from_response(response, "vyapar_session_token")
    csrf_token = get_cookie_from_response(response, "vyapar_csrf_token")

    return {
        "cookies": {"vyapar_session_token": session_token},
        "headers": {"x-csrf-token": csrf_token},
    }


def test_shakti_end_to_end(client: TestClient, db: Session):
    # 1. RM logs in and sees the case
    rm_auth = get_auth_headers(client, "rm@bank.example")
    client.cookies.clear()
    client.cookies.update(rm_auth["cookies"])
    res = client.get("/api/cases", headers=rm_auth["headers"])
    assert res.status_code == 200, res.text
    cases = res.json()
    assert len(cases) > 0
    shakti_case = next(
        (c for c in cases if "Shakti Precision" in c.get("business_name", "")), None
    )
    if not shakti_case:
        # Fallback if business name isn't loaded or format is different
        shakti_case = cases[-1]
    case_id = shakti_case["id"]

    # 2. Analyst logs in and evaluates
    analyst_auth = get_auth_headers(client, "credit@bank.example")
    client.cookies.clear()
    client.cookies.update(analyst_auth["cookies"])

    # Get current version
    res = client.get(f"/api/cases/{case_id}", headers=analyst_auth["headers"])
    assert res.status_code == 200
    case_data = res.json()
    current_version = case_data["version"]

    import uuid

    evaluate_req = {"expected_version": current_version}
    idempotency_key_eval = str(uuid.uuid4())

    eval_res = client.post(
        f"/api/cases/{case_id}/evaluate",
        json=evaluate_req,
        headers={**analyst_auth["headers"], "Idempotency-Key": idempotency_key_eval},
    )
    if eval_res.status_code != 200:
        print("EVALUATION FAILED:", eval_res.text)
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["policy_recommendation"] == "CONDITIONAL_OFFER"

    # Validate Shakti winning outcome
    assert float(case_data["requested_amount"]) == 5000000.00
    import math

    binding_limit = float(eval_data["supportable_amount"])
    assert math.isclose(binding_limit, 3570000.00, abs_tol=2000.0), (
        f"Binding limit {binding_limit} is not approx 3570000"
    )

    # Ensure idempotency cache works
    eval_res_2 = client.post(
        f"/api/cases/{case_id}/evaluate",
        json=evaluate_req,
        headers={**analyst_auth["headers"], "Idempotency-Key": idempotency_key_eval},
    )
    assert eval_res_2.status_code == 200
    assert eval_res_2.json() == eval_data

    # 3. Analyst submits recommendation
    # Re-fetch for updated version
    res = client.get(f"/api/cases/{case_id}", headers=analyst_auth["headers"])
    current_version = res.json()["version"]

    rec_req = {
        "recommendation": "RECOMMEND_ALTERNATIVE_STRUCTURE",
        "reason": "Strong financials and good GST compliance, but request exceeds binding limit.",
        "expected_version": current_version,
    }
    idempotency_key_rec = str(uuid.uuid4())
    rec_res = client.post(
        f"/api/cases/{case_id}/analyst-recommendation",
        json=rec_req,
        headers={**analyst_auth["headers"], "Idempotency-Key": idempotency_key_rec},
    )
    assert rec_res.status_code == 200, rec_res.text

    # 4. Sanctioning Authority logs in and makes human decision
    sa_auth = get_auth_headers(client, "sa@bank.example")
    client.cookies.clear()
    client.cookies.update(sa_auth["cookies"])

    res = client.get(f"/api/cases/{case_id}", headers=sa_auth["headers"])
    assert res.status_code == 200
    current_version = res.json()["version"]

    dec_req = {
        "decision": "APPROVE_ALTERNATIVE_STRUCTURE",
        "approved_amount": str(binding_limit),
        "reason": "Approved alternative structure.",
        "expected_version": current_version,
    }
    idempotency_key_dec = str(uuid.uuid4())

    dec_res = client.post(
        f"/api/cases/{case_id}/human-decision",
        json=dec_req,
        headers={**sa_auth["headers"], "Idempotency-Key": idempotency_key_dec, "X-Expected-Version": str(current_version)},
    )

    # If the case wasn't assigned to the SA, or if SA branch mandate isn't correctly set, this might fail with 403.
    # But SA has a valid mandate. If they don't have scope_role in UserBranchScope, they can't view it!
    # Let's ensure the test passes. If 403, we need to fix seed_shakti.py to give SA branch access or assign them.
    assert dec_res.status_code == 200, (
        f"Expected 200, got {dec_res.status_code}: {dec_res.text}"
    )

    # Check audit log via DB directly to verify persistent audit records
    from app.db.orm.cases import AuditEvent

    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.event_sequence)
        .all()
    )
    assert len(events) >= 3
    # Check sequence
    seqs = [e.event_sequence for e in events]
    assert seqs == sorted(seqs)
    # Check hashes and prior versions
    for i in range(1, len(events)):
        assert events[i].prior_event_hash == events[i - 1].event_hash
        assert events[i].prior_case_version == events[i - 1].resulting_case_version

    assert events[-1].actor_role == "SANCTIONING_AUTHORITY"
    assert events[-1].correlation_id is not None
    assert events[-1].idempotency_record_id is not None

    seal_res = client.post(
        f"/api/cases/{case_id}/decision-package",
        headers=sa_auth["headers"],
    )
    assert seal_res.status_code == 200, seal_res.text
    sealed = seal_res.json()
    assert sealed["stored"] is True
    assert len(sealed["package_hash"]) == 64
    duplicate_seal_res = client.post(
        f"/api/cases/{case_id}/decision-package",
        headers=sa_auth["headers"],
    )
    assert duplicate_seal_res.status_code == 200, duplicate_seal_res.text
    assert duplicate_seal_res.json()["package_id"] == sealed["package_id"]

    from app.db.orm.cases import DecisionPackage

    sealed_records = (
        db.query(DecisionPackage)
        .filter(
            DecisionPackage.case_id == case_id,
            DecisionPackage.case_version == sealed["case_version"],
            DecisionPackage.assessment_id == sealed["assessment_id"],
        )
        .all()
    )
    assert len(sealed_records) == 1
    record = sealed_records[0]
    assert set(record.engine_versions) >= {
        "scoring_version",
        "calculation_version",
        "policy_version",
        "evidence_passport_version",
        "feature_schema_version",
        "package_schema_version",
    }
    assert record.feature_snapshot["consent_status"] == "VALID"
    assert record.feature_snapshot["governed_bank_metrics"]
    assert record.feature_snapshot["obligation_state"]
    assert record.feature_snapshot["evidence_ids"]
    assert record.feature_snapshot["product_request"]["requested_product"] == "WORKING_CAPITAL_LINE"
    assert record.feature_snapshot["scoring_inputs"]
    assert record.feature_snapshot["calculation_inputs"]

    verify_res = client.post(
        f"/api/cases/{case_id}/decision-package/{sealed['package_id']}/verify",
        headers=sa_auth["headers"],
    )
    assert verify_res.status_code == 200, verify_res.text
    assert verify_res.json()["valid"] is True

    replay_res = client.post(
        f"/api/cases/{case_id}/decision-package/{sealed['package_id']}/replay",
        headers=sa_auth["headers"],
    )
    assert replay_res.status_code == 200, replay_res.text
    replay_data = replay_res.json()
    assert replay_data["status"] == "INDEPENDENTLY_REPRODUCED", replay_data
    assert replay_data["differences"] == []

    original_versions = dict(record.engine_versions)
    record.engine_versions = {k: v for k, v in original_versions.items() if k != "calculation_version"}
    db.commit()
    version_unavailable = client.post(
        f"/api/cases/{case_id}/decision-package/{sealed['package_id']}/replay",
        headers=sa_auth["headers"],
    )
    assert version_unavailable.status_code == 200, version_unavailable.text
    assert version_unavailable.json()["status"] == "VERSION_UNAVAILABLE"
    record.engine_versions = original_versions
    db.commit()

    sys_auth = get_auth_headers(client, "system@bank.example")
    client.cookies.clear()
    client.cookies.update(sys_auth["cookies"])
    denied = client.post(
        f"/api/cases/{case_id}/decision-package/{sealed['package_id']}/verify",
        headers=sys_auth["headers"],
    )
    assert denied.status_code in (403, 404)


def test_concurrent_idempotency(client: TestClient, db: Session):
    from concurrent.futures import ThreadPoolExecutor
    import uuid
    from sqlalchemy import select
    from app.db.orm.cases import AuditEvent, IdempotencyRecord
    from app.seed.seed_shakti import seed_shakti

    seed_shakti(db)
    ca_auth = get_auth_headers(client, "credit@bank.example")

    # Get the case
    client.cookies.clear()
    client.cookies.update(ca_auth["cookies"])
    cases_res = client.get("/api/cases", headers=ca_auth["headers"])
    cases = cases_res.json()
    assert len(cases) > 0
    shakti_case = next(
        (
            c
            for c in cases
            if "Shakti Precision"
            in c.get("business_name", c.get("business", {}).get("legal_name", ""))
            or "Navprerna Tech"
            in c.get("business_name", c.get("business", {}).get("legal_name", ""))
        ),
        None,
    )
    if not shakti_case:
        # If business name not directly in response, fetch from DB
        from app.db.orm.cases import Business

        shakti_business = (
            db.query(Business)
            .filter(Business.legal_name.in_(["Shakti Precision Components Pvt Ltd", "Navprerna Tech Solutions"]))
            .first()
        )
        if shakti_business and shakti_business.cases:
            shakti_case = next(
                (c for c in cases if c["id"] == str(shakti_business.cases[0].id)),
                cases[-1] if cases else None
            )
        else:
            shakti_case = cases[-1] if cases else None
    assert shakti_case is not None, "No case found for test_concurrent_idempotency"
    case_id = shakti_case["id"]

    case_detail = client.get(f"/api/cases/{case_id}", headers=ca_auth["headers"]).json()
    version = case_detail["version"]

    # Record before concurrent requests
    before_case = db.execute(select(Case).where(Case.id == case_id)).scalar_one()
    before_version = before_case.version
    before_audit_count = len(
        db.execute(select(AuditEvent).where(AuditEvent.case_id == case_id))
        .scalars()
        .all()
    )
    before_idemp_count = len(
        db.execute(
            select(IdempotencyRecord).where(IdempotencyRecord.case_id == case_id)
        )
        .scalars()
        .all()
    )

    idemp_key = str(uuid.uuid4())
    req_body = {"expected_version": version}

    def send_req():
        thread_client = TestClient(app)
        thread_client.cookies.update(ca_auth["cookies"])
        return thread_client.post(
            f"/api/cases/{case_id}/evaluate",
            json=req_body,
            headers={**ca_auth["headers"], "Idempotency-Key": idemp_key},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(send_req)
        future2 = executor.submit(send_req)

        res1 = future1.result()
        res2 = future2.result()

    status_codes = {res1.status_code, res2.status_code}
    assert 200 in status_codes, (
        f"Neither request succeeded. Statuses: {res1.status_code}, {res2.status_code}. Responses: {res1.text}, {res2.text}"
    )

    if res1.status_code == 200 and res2.status_code == 200:
        assert res1.json() == res2.json()
    else:
        assert 409 in status_codes
        error_res = res1 if res1.status_code == 409 else res2
        assert error_res.json()["detail"]["code"] == "IDEMPOTENCY_IN_PROGRESS"
        assert error_res.headers.get("retry-after") == "5"

    db.expire_all()
    # Afterward assert exact increments
    after_case = db.execute(select(Case).where(Case.id == case_id)).scalar_one()
    assert after_case.version == before_version + 1, (
        "case version increased exactly once"
    )

    after_audit_count = len(
        db.execute(select(AuditEvent).where(AuditEvent.case_id == case_id))
        .scalars()
        .all()
    )
    assert after_audit_count == before_audit_count + 1, "exactly one new audit event"

    idemp_records = (
        db.execute(
            select(IdempotencyRecord).where(IdempotencyRecord.case_id == case_id)
        )
        .scalars()
        .all()
    )
    assert len(idemp_records) == before_idemp_count + 1, (
        "exactly one scoped idempotency record"
    )

    new_record = [r for r in idemp_records if r.idempotency_key == idemp_key][0]
    assert new_record.status.value == "COMPLETED", "record status is COMPLETED"
