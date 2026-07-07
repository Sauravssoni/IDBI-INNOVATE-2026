import os
import sys
import uuid
import json
from datetime import datetime


def run():
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from app.db.session import SessionLocal
    from app.db.orm.cases import Case, Business, CaseStatus, AuditEvent
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    db = SessionLocal()

    walkthrough_log = []

    def log_step(name, status, result=""):
        print(f"[{status}] {name} - {result}")
        walkthrough_log.append(
            {
                "step": name,
                "status": status,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def get_cookies(email):
        demo_password = os.environ.get("DEMO_USER_PASSWORD", "demopassword")
        resp = client.post(
            "/api/auth/login", json={"email": email, "password": demo_password}
        )
        return resp.cookies

    def get_headers(cookies):
        return {"X-CSRF-Token": cookies.get("vyapar_csrf_token", "")}

    try:
        # Analyst Login
        ca_cookies = get_cookies("credit@bank.example")
        ca_headers = get_headers(ca_cookies)
        log_step("Analyst Login", "PASS")

        shakti = (
            db.query(Case)
            .join(Business)
            .filter(Business.business_id == "SHAKTI_PRECISION_001")
            .first()
        )

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
        log_step("Shakti Assessment", "PASS", "Evaluated Shakti")

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
            if resp_rec.status_code != 200:
                print("Failed recommend:", resp_rec.text)
            assert resp_rec.status_code == 200, "Analyst failed to recommend"
            db.refresh(shakti)
        log_step("Analyst Recommend Alternative Structure", "PASS")

        # SA Login
        sa_cookies = get_cookies("sa@bank.example")
        sa_headers = get_headers(sa_cookies)
        log_step("SA Login", "PASS")

        # APPROVE_ALTERNATIVE_STRUCTURE
        resp_app = client.post(
            f"/api/cases/{shakti.id}/human-decision",
            headers={"Idempotency-Key": f"walk-{uuid.uuid4()}", **sa_headers},
            cookies=sa_cookies,
            json={
                "decision": "APPROVE_ALTERNATIVE_STRUCTURE",
                "reason": "Walkthrough SA approval",
                "expected_version": shakti.version,
                "approved_amount": 3500000.00,
            },
        )
        assert resp_app.status_code == 200, "SA failed to approve"
        db.refresh(shakti)
        log_step("SA Approve Alternative Structure", "PASS")

        # RM read-only result
        rm_cookies = get_cookies("rm@bank.example")
        resp_rm = client.get(f"/api/cases/{shakti.id}", cookies=rm_cookies)
        assert resp_rm.status_code == 200
        assert resp_rm.json()["status"] == "HUMAN_APPROVED"
        log_step("RM Read-only Result", "PASS", "RM viewed approved case")

        # Auditor audit access
        au_cookies = get_cookies("auditor@bank.example")
        resp_au = client.get(f"/api/cases/{shakti.id}/audit", cookies=au_cookies)
        if resp_au.status_code != 200:
            print("Auditor fail:", resp_au.text)
        assert resp_au.status_code == 200
        assert len(resp_au.json()) > 0
        log_step(
            "Auditor Audit Access",
            "PASS",
            f"Auditor viewed {len(resp_au.json())} events",
        )

        # System Admin borrower-data denial
        sys_cookies = get_cookies("system@bank.example")
        resp_sys = client.get(f"/api/cases/{shakti.id}/evidence", cookies=sys_cookies)
        if resp_sys.status_code not in (403, 404):
            print("Sysadmin fail:", resp_sys.status_code, resp_sys.text)
        assert resp_sys.status_code in (403, 404)
        log_step("System Admin Borrower-data Denial", "PASS", "System Admin denied")

        # Invalid-case denial
        resp_inv = client.get(
            "/api/cases/00000000-0000-0000-0000-000000000000", cookies=ca_cookies
        )
        if resp_inv.status_code != 404:
            print("Invalid case fail:", resp_inv.status_code, resp_inv.text)
        assert resp_inv.status_code == 404
        log_step("Invalid-case Denial", "PASS")

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
        # Should be 409 because version changed or 400 because not pending
        if resp_idem.status_code not in (409, 400):
            print("Idempotency replay fail:", resp_idem.status_code, resp_idem.text)
        assert resp_idem.status_code in (409, 400)

        # Exact replay
        old_idem = resp_app.request.headers.get("Idempotency-Key")
        if old_idem:
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
            assert resp_replay.status_code == 200
        log_step("Idempotency Replay", "PASS")

        # Continuous case versions and audit sequence
        audits = (
            db.query(AuditEvent)
            .filter(AuditEvent.case_id == shakti.id)
            .order_by(AuditEvent.created_at.asc())
            .all()
        )
        for i in range(1, len(audits)):
            assert audits[i].event_sequence == audits[i - 1].event_sequence + 1
            prev_hash = audits[i - 1].event_hash
            curr_prev_hash = audits[i].prior_event_hash
            assert prev_hash == curr_prev_hash, "Hash chain broken!"
        log_step("Continuous Case Versions and Audit Sequence", "PASS")

    except Exception as e:
        log_step("Execution Error", "FAIL", str(e))
        raise

    finally:
        out_dir = os.path.join(os.path.dirname(__file__), "../../artifacts")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "demo_walkthrough.json"), "w") as f:
            json.dump(walkthrough_log, f, indent=2)


if __name__ == "__main__":
    run()
