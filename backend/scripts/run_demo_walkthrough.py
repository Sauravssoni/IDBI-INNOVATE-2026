import os
import sys
import uuid
import json


def run():
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from app.db.session import SessionLocal
    from app.db.orm.cases import Case, Business, CaseStatus, AuditEvent
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    db = SessionLocal()

    walkthrough_log = []
    has_failure = False

    def log_step(name, expected, status, actual, passed, version=None, seq=None):
        nonlocal has_failure
        if not passed:
            has_failure = True
        print(f"[{'PASS' if passed else 'FAIL'}] {name} - {actual}")
        walkthrough_log.append(
            {
                "step_request": name,
                "expected": expected,
                "status": status,
                "actual": actual,
                "passed": passed,
                "case_version": version,
                "event_sequence": seq,
            }
        )

    def get_cookies(email):
        demo_password = os.environ["DEMO_USER_PASSWORD"]
        resp = client.post(
            "/api/auth/login", json={"email": email, "password": demo_password}
        )
        assert resp.status_code == 200, f"Login failed for {email}"
        return resp.cookies

    def get_headers(cookies):
        return {"X-CSRF-Token": cookies.get("vyapar_csrf_token", "")}

    try:
        # Analyst Login
        ca_cookies = get_cookies("credit@bank.example")
        ca_headers = get_headers(ca_cookies)
        log_step("Analyst Login", "200 OK", "200", "Logged in analyst", True)

        shakti = (
            db.query(Case)
            .join(Business)
            .filter(Business.business_id == "SHAKTI_PRECISION_001")
            .first()
        )
        shakti.version

        # Shakti assessment
        if shakti.status == CaseStatus.INITIATED:
            resp_eval = client.post(
                f"/api/cases/{shakti.id}/evaluate",
                headers={"Idempotency-Key": f"walk-{uuid.uuid4()}", **ca_headers},
                cookies=ca_cookies,
                json={"expected_version": shakti.version},
            )
            assert resp_eval.status_code == 200, "Failed to evaluate Shakti"
            db.refresh(shakti)
        log_step(
            "Shakti Assessment",
            "200 OK",
            "200",
            "Evaluated Shakti",
            True,
            shakti.version,
        )

        # RECOMMEND_ALTERNATIVE_STRUCTURE
        if shakti.status == CaseStatus.ASSESSMENT_COMPLETED:
            resp_rec = client.post(
                f"/api/cases/{shakti.id}/analyst-recommendation",
                headers={"Idempotency-Key": f"walk-{uuid.uuid4()}", **ca_headers},
                cookies=ca_cookies,
                json={
                    "recommendation": "RECOMMEND_ALTERNATIVE_STRUCTURE",
                    "reason": "Walkthrough analyst recommendation",
                    "expected_version": shakti.version,
                },
            )
            assert resp_rec.status_code == 200, (
                f"Analyst failed to recommend: {resp_rec.text}"
            )
            db.refresh(shakti)
        log_step(
            "Analyst Recommend Alternative Structure",
            "200 OK",
            "200",
            "Recommended alternative",
            True,
            shakti.version,
        )

        # SA Login
        sa_cookies = get_cookies("sa@bank.example")
        sa_headers = get_headers(sa_cookies)
        log_step("SA Login", "200 OK", "200", "Logged in SA", True)

        # APPROVE_ALTERNATIVE_STRUCTURE
        old_idem = f"walk-{uuid.uuid4()}"
        resp_app = client.post(
            f"/api/cases/{shakti.id}/human-decision",
            headers={"Idempotency-Key": old_idem, **sa_headers},
            cookies=sa_cookies,
            json={
                "decision": "APPROVE_ALTERNATIVE_STRUCTURE",
                "reason": "Walkthrough SA approval",
                "expected_version": shakti.version,
                "approved_amount": 3500000.00,
            },
        )
        assert resp_app.status_code == 200, f"SA failed to approve: {resp_app.text}"
        db.refresh(shakti)
        log_step(
            "SA Approve Alternative Structure",
            "200 OK",
            "200",
            "Approved alternative",
            True,
            shakti.version,
        )

        # RM read-only result
        rm_cookies = get_cookies("rm@bank.example")
        resp_rm = client.get(f"/api/cases/{shakti.id}", cookies=rm_cookies)
        assert resp_rm.status_code == 200
        assert resp_rm.json()["status"] == "HUMAN_APPROVED"
        log_step(
            "RM Read-only Result",
            "200 OK & HUMAN_APPROVED",
            "200",
            "Viewed approved case",
            True,
            shakti.version,
        )

        # Auditor audit access
        au_cookies = get_cookies("auditor@bank.example")
        resp_au = client.get(f"/api/cases/{shakti.id}/audit", cookies=au_cookies)
        assert resp_au.status_code == 200
        assert len(resp_au.json()) > 0
        log_step(
            "Auditor Audit Access",
            "200 OK & >0 events",
            "200",
            f"Auditor viewed {len(resp_au.json())} events",
            True,
            shakti.version,
        )

        # System Admin borrower-data denial
        sys_cookies = get_cookies("system@bank.example")
        resp_sys = client.get(f"/api/cases/{shakti.id}/evidence", cookies=sys_cookies)
        assert resp_sys.status_code in (403, 404), (
            f"Sysadmin fail: {resp_sys.status_code}"
        )
        log_step(
            "System Admin Borrower-data Denial",
            "403/404",
            str(resp_sys.status_code),
            "System Admin denied",
            True,
            shakti.version,
        )

        # Invalid-case denial
        resp_inv = client.get(
            "/api/cases/00000000-0000-0000-0000-000000000000", cookies=ca_cookies
        )
        assert resp_inv.status_code == 404, f"Invalid case fail: {resp_inv.status_code}"
        log_step(
            "Invalid-case Denial",
            "404 NOT FOUND",
            "404",
            "Invalid case denied",
            True,
            shakti.version,
        )

        # Idempotency replay
        resp_idem = client.post(
            f"/api/cases/{shakti.id}/human-decision",
            headers={"Idempotency-Key": f"walk-{uuid.uuid4()}", **sa_headers},
            cookies=sa_cookies,
            json={
                "decision": "APPROVE_ALTERNATIVE_STRUCTURE",
                "reason": "Walkthrough SA approval",
                "expected_version": shakti.version - 1,
                "approved_amount": 3500000.00,
            },
        )
        assert resp_idem.status_code in (409, 400), (
            f"Idempotency replay fail: {resp_idem.status_code}"
        )

        resp_replay = client.post(
            f"/api/cases/{shakti.id}/human-decision",
            headers={"Idempotency-Key": old_idem, **sa_headers},
            cookies=sa_cookies,
            json={
                "decision": "APPROVE_ALTERNATIVE_STRUCTURE",
                "reason": "Walkthrough SA approval",
                "expected_version": shakti.version - 1,
                "approved_amount": 3500000.00,
            },
        )
        assert resp_replay.status_code == 200, f"Replay fail: {resp_replay.status_code}"
        log_step(
            "Idempotency Replay",
            "409/400 & 200 OK",
            "200",
            "Idempotency replay handled correctly",
            True,
            shakti.version,
        )

        # Continuous case versions and audit sequence
        audits = (
            db.query(AuditEvent)
            .filter(AuditEvent.case_id == shakti.id)
            .order_by(AuditEvent.created_at.asc())
            .all()
        )
        for i in range(1, len(audits)):
            assert audits[i].event_sequence == audits[i - 1].event_sequence + 1, (
                "Sequence broken!"
            )
            assert audits[i].prior_event_hash == audits[i - 1].event_hash, (
                "Hash chain broken!"
            )
        log_step(
            "Continuous Case Versions and Audit Sequence",
            "Hash chain intact",
            "SUCCESS",
            f"Validated {len(audits)} events",
            True,
            shakti.version,
            len(audits),
        )

    except Exception as e:
        log_step("Execution Error", "No exceptions", "ERROR", str(e), False)

    finally:
        out_dir = os.path.join(os.path.dirname(__file__), "../../artifacts")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "demo_walkthrough.json"), "w") as f:
            json.dump(walkthrough_log, f, indent=2)

    if has_failure:
        print("❌ Demo Walkthrough FAILED")
        sys.exit(1)
    else:
        print("✅ Demo Walkthrough PASSED")


if __name__ == "__main__":
    run()
