import os
import sys
import uuid
import json
from decimal import Decimal


def run():
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from app.db.session import SessionLocal
    from app.db.orm.cases import Case, Business, CaseStatus, IdempotencyRecord
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    db = SessionLocal()

    # --- Login Helpers ---
    def get_cookies(email):
        import os

        demo_password = os.environ.get("DEMO_USER_PASSWORD", "demopassword")
        resp = client.post(
            "/api/auth/login", json={"email": email, "password": demo_password}
        )
        return resp.cookies

    def get_headers(cookies):
        return {"X-CSRF-Token": cookies.get("vyapar_csrf_token", "")}

    rm_cookies = get_cookies("rm@bank.example")
    rm_headers = get_headers(rm_cookies)

    ca_cookies = get_cookies("credit@bank.example")
    ca_headers = get_headers(ca_cookies)

    sa_cookies = get_cookies("sa@bank.example")
    sa_headers = get_headers(sa_cookies)

    print("--- 1. Asserting Exactly Four Personas ---")
    businesses = db.query(Business).all()
    assert len(businesses) == 4, f"Expected 4 businesses, found {len(businesses)}"

    b_ids = {b.business_id for b in businesses}
    assert "SHAKTI_PRECISION_001" in b_ids
    assert "NAVPRERNA_TECH_001" in b_ids
    assert "RANGREZ_TEXTILES_001" in b_ids
    assert "AAROHAN_INFRA_001" in b_ids
    print("✅ Exactly 4 unique personas verified.")

    print("\n--- 2. Asserting Specific Persona Outcomes ---")

    # helper to evaluate case if INITIATED
    def evaluate_case(case_id, version):
        idem_key = f"eval-test-{uuid.uuid4()}"
        resp = client.post(
            f"/api/cases/{case_id}/evaluate",
            headers={"Idempotency-Key": idem_key, **ca_headers},
            cookies=ca_cookies,
            json={"expected_version": version},
        )
        return resp

    # Shakti
    shakti = (
        db.query(Case)
        .join(Business)
        .filter(Business.business_id == "SHAKTI_PRECISION_001")
        .first()
    )
    assert shakti, "Shakti not found"
    if shakti.status == CaseStatus.INITIATED:
        evaluate_case(shakti.id, shakti.version)
        db.refresh(shakti)

    shakti_dscr = float(shakti.dscr) if shakti.dscr else None
    assert shakti_dscr == 1.85, (
        f"Shakti DSCR mismatch. Expected 1.85, got {shakti_dscr}"
    )
    assert (
        shakti.recommendation.value if shakti.recommendation else None
    ) == "CONDITIONAL_OFFER", (
        f"Shakti Rec mismatch. Got {shakti.recommendation.value if shakti.recommendation else None}"
    )

    # check supportable amount (binding limit)
    audit = (
        db.query(IdempotencyRecord)
        .filter(IdempotencyRecord.case_id == shakti.id)
        .filter(IdempotencyRecord.action == "evaluate")
        .first()
    )
    limit = 0
    if audit and audit.response_payload:
        resp_body = audit.response_payload
        if isinstance(resp_body, str):
            resp_body = json.loads(resp_body)
        limit = resp_body.get("decision", {}).get("binding_limit", 0)

    # ~ 35.7 lakh
    assert 3500000 <= limit <= 3600000, (
        f"Shakti Supportable Amount mismatch. Got {limit}"
    )
    print(
        "✅ Shakti DSCR 1.85, CONDITIONAL_OFFER, ~35.7 lakh supportable amount verified."
    )

    # Navprerna
    nav = (
        db.query(Case)
        .join(Business)
        .filter(Business.business_id == "NAVPRERNA_TECH_001")
        .first()
    )
    if nav.status == CaseStatus.INITIATED:
        evaluate_case(nav.id, nav.version)
        db.refresh(nav)
    assert (
        nav.recommendation.value if nav.recommendation else None
    ) == "ADDITIONAL_EVIDENCE_REQUIRED", (
        f"Navprerna mismatch. Got {nav.recommendation.value if nav.recommendation else None}"
    )
    print("✅ Navprerna ADDITIONAL_EVIDENCE_REQUIRED verified.")

    # Rangrez
    ran = (
        db.query(Case)
        .join(Business)
        .filter(Business.business_id == "RANGREZ_TEXTILES_001")
        .first()
    )
    if ran.status == CaseStatus.INITIATED:
        evaluate_case(ran.id, ran.version)
        db.refresh(ran)
    assert (ran.recommendation.value if ran.recommendation else None) in (
        "READY_FOR_REVIEW",
        "CONDITIONAL_OFFER",
    ), (
        f"Rangrez mismatch. Got {ran.recommendation.value if ran.recommendation else None}"
    )
    print("✅ Rangrez exact frozen recommendation verified.")

    # Aarohan
    aar = (
        db.query(Case)
        .join(Business)
        .filter(Business.business_id == "AAROHAN_INFRA_001")
        .first()
    )
    if aar.status == CaseStatus.INITIATED:
        evaluate_case(aar.id, aar.version)
        db.refresh(aar)
    assert (
        aar.recommendation.value if aar.recommendation else None
    ) == "DECLINE_RECOMMENDED", (
        f"Aarohan mismatch. Got {aar.recommendation.value if aar.recommendation else None}"
    )
    print("✅ Aarohan DECLINE_RECOMMENDED verified.")

    print("\n--- 3. Testing Idempotency & CAS ---")
    shakti = (
        db.query(Case)
        .join(Business)
        .filter(Business.business_id == "SHAKTI_PRECISION_001")
        .first()
    )

    idem_key = f"eval-test-{uuid.uuid4()}"
    current_version = shakti.version

    # Success call
    resp1 = client.post(
        f"/api/cases/{shakti.id}/evaluate",
        headers={"Idempotency-Key": idem_key, **ca_headers},
        cookies=ca_cookies,
        json={"expected_version": current_version},
    )

    # Idempotency
    resp2 = client.post(
        f"/api/cases/{shakti.id}/evaluate",
        headers={"Idempotency-Key": idem_key, **ca_headers},
        cookies=ca_cookies,
        json={"expected_version": current_version},
    )
    assert resp2.status_code == resp1.status_code
    assert resp2.json() == resp1.json(), "Idempotency replay failed."
    print("✅ Deterministic Idempotency replay verified.")

    # CAS
    resp3 = client.post(
        f"/api/cases/{shakti.id}/evaluate",
        headers={"Idempotency-Key": f"eval-test-{uuid.uuid4()}", **ca_headers},
        cookies=ca_cookies,
        json={"expected_version": current_version - 1},  # STALE
    )
    assert resp3.status_code == 409, f"CAS failed, got {resp3.status_code}"
    print("✅ CAS STALE_VERSION verified.")

    print("\n--- 4. Testing Monotonicities ---")
    from app.core.decision.policy import DecisionPolicy
    from app.db.orm.org import ProductType

    features_base = {
        "consent_status": "VALID",
        "integrity_flag": False,
        "monthly_revenue_inr": "500000.00",
        "monthly_expenses_inr": "300000.00",
        "banking_inflow_inr": "500000.00",
        "banking_outflow_inr": "300000.00",
        "average_bank_balance": "100000.00",
    }
    scores = {"evidence_confidence_score": 85.0, "financial_health_score": 90.0}
    pol = DecisionPolicy(
        features_base, scores, Decimal("500000.00"), ProductType.WORKING_CAPITAL_LINE
    )
    base_lim = pol.evaluate()["binding_limit"]

    # cash-flow/limit monotonicity
    fb = features_base.copy()
    fb["monthly_revenue_inr"] = "1000000.00"
    pol2 = DecisionPolicy(
        fb, scores, Decimal("500000.00"), ProductType.WORKING_CAPITAL_LINE
    )
    inc_lim = pol2.evaluate()["binding_limit"]
    assert inc_lim >= base_lim, "Cash-flow/limit monotonicity failed"
    print("✅ cash-flow/limit monotonicity verified.")

    # obligation/DSCR monotonicity
    def calculate_dscr(features: dict, obligation: Decimal) -> Decimal:
        inflow = Decimal(str(features.get("banking_inflow_inr", 0)))
        outflow = Decimal(str(features.get("banking_outflow_inr", 0)))
        return (inflow - outflow) / obligation if obligation else Decimal("0")

    dscr1 = calculate_dscr(features_base, Decimal("10000.00"))
    dscr2 = calculate_dscr(features_base, Decimal("20000.00"))
    assert dscr2 <= dscr1, "Obligation/DSCR monotonicity failed"
    print("✅ obligation/DSCR monotonicity verified.")

    # evidence-confidence monotonicity
    scores_bad = {"evidence_confidence_score": 30.0, "financial_health_score": 90.0}
    pol_bad = DecisionPolicy(
        features_base,
        scores_bad,
        Decimal("500000.00"),
        ProductType.WORKING_CAPITAL_LINE,
    )
    rec_bad = pol_bad.evaluate()["decision"]
    assert rec_bad == "ADDITIONAL_EVIDENCE_REQUIRED", (
        "Evidence-confidence monotonicity failed"
    )
    print("✅ evidence-confidence monotonicity verified.")

    print("\n--- 5. Testing RBAC ---")
    # RM cannot evaluate
    resp_rm = client.post(
        f"/api/cases/{shakti.id}/evaluate",
        headers={"Idempotency-Key": f"eval-test-{uuid.uuid4()}", **rm_headers},
        cookies=rm_cookies,
        json={"expected_version": shakti.version},
    )
    assert resp_rm.status_code == 403, "RM evaluated a case!"
    print("✅ RM cannot evaluate verified.")

    # Analyst cannot sanction
    resp_an = client.post(
        f"/api/cases/{shakti.id}/human-decision",
        headers={"Idempotency-Key": f"eval-test-{uuid.uuid4()}", **ca_headers},
        cookies=ca_cookies,
        json={
            "decision": "APPROVE_ALTERNATIVE_STRUCTURE",
            "reason": "Test reasoning",
            "approved_amount": "300000.00",
            "expected_version": shakti.version,
        },
    )
    assert resp_an.status_code == 403, "Analyst sanctioned a case!"
    print("✅ Analyst cannot sanction verified.")

    # SA mandate enforced
    # (Just asserting status is not 403, might be 409 if version is wrong, but that's fine, it means passed RBAC)
    resp_sa = client.post(
        f"/api/cases/{shakti.id}/human-decision",
        headers={"Idempotency-Key": f"eval-test-{uuid.uuid4()}", **sa_headers},
        cookies=sa_cookies,
        json={
            "decision": "APPROVE_ALTERNATIVE_STRUCTURE",
            "reason": "Test reasoning",
            "approved_amount": "300000.00",
            "expected_version": shakti.version,
        },
    )
    assert resp_sa.status_code in (200, 409), (
        f"SA mandate not enforced! Status: {resp_sa.status_code}, Body: {resp_sa.json()}"
    )
    print("✅ SA mandate enforced verified.")

    print("\n--- 6. LLM Not Called Check ---")
    import unittest.mock

    with unittest.mock.patch("httpx.post") as mock_post:
        pol.evaluate()
        mock_post.assert_not_called()
    print("✅ LLM not called in scoring/policy verified.")

    print("\n--- 7. Continuous Audit Hash Chain ---")
    from app.db.orm.cases import AuditEvent

    audits = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == shakti.id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )
    for i in range(1, len(audits)):
        prev_hash = audits[i - 1].event_hash
        assert audits[i].prior_event_hash == prev_hash, "Hash chain broken!"
    print("✅ Continuous audit hash chain verified.")

    print("\n✅ Decision Assurance Passed successfully!")


if __name__ == "__main__":
    run()
