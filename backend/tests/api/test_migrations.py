import os
import pytest
import subprocess
import uuid
import urllib.parse
from sqlalchemy import create_engine, text

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def test_migration_upgrade_downgrade():
    if os.environ.get("APP_ENV") == "production":
        pytest.skip("Refusing to run migration test in production")

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://vyapar_local:change-this-local-development-password@127.0.0.1:5433/vyapar_pulse_test",
    )
    parsed_url = urllib.parse.urlparse(db_url)
    datname = parsed_url.path.lstrip("/")

    if "test" not in datname:
        pytest.fail(
            f"Refusing to drop public schema on database '{datname}' - must contain 'test'"
        )

    from app.db.session import engine as global_engine

    global_engine.dispose()

    engine = create_engine(db_url)

    # 1. Clean up and create empty db
    with engine.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :datname AND pid <> pg_backend_pid();"
            ),
            {"datname": datname},
        )
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()

    # 2. Run alembic upgrade to baseline
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    proc = subprocess.run(
        ["alembic", "upgrade", "05f0b4de641c"],
        capture_output=True,
        text=True,
        env=env,
        cwd=backend_dir,
    )
    if proc.returncode != 0:
        print("Alembic upgrade stdout:", proc.stdout)
        print("Alembic upgrade stderr:", proc.stderr)
        proc.check_returncode()

    # 3. Insert representative legacy rows
    uid = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    idem_id = str(uuid.uuid4())
    audit_id = str(uuid.uuid4())
    biz_id = str(uuid.uuid4())

    with engine.connect() as conn:
        conn.execute(
            text("""
            INSERT INTO users (id, email, hashed_password, full_name, role, is_active, created_at, updated_at) 
            VALUES (:uid, 'legacy@bank.example', 'hash', 'Legacy User', 'CREDIT_ANALYST', true, now(), now())
        """),
            {"uid": uid},
        )

        conn.execute(
            text("""
            INSERT INTO businesss (id, business_id, legal_name, sector, created_at, updated_at)
            VALUES (:biz_id, 'BIZ123', 'Legacy Biz', 'Retail', now(), now())
        """),
            {"biz_id": biz_id},
        )

        conn.execute(
            text("""
            INSERT INTO cases (id, business_id_fk, status, requested_amount, requested_facility_type, version, created_at, updated_at)
            VALUES (:case_id, :biz_id, 'INITIATED', 50000.00, 'WORKING_CAPITAL', 1, now(), now())
        """),
            {"case_id": case_id, "biz_id": biz_id},
        )

        conn.execute(
            text("""
            INSERT INTO idempotency_records (id, user_id, case_id, action, idempotency_key, request_hash, expires_at, created_at, updated_at)
            VALUES (:idem_id, :uid, :case_id, 'evaluate', 'key123', 'hash123', now() + interval '1 day', now(), now())
        """),
            {"idem_id": idem_id, "uid": uid, "case_id": case_id},
        )

        conn.execute(
            text("""
            INSERT INTO audit_events (id, case_id, event_type, actor, actor_role, created_at, updated_at)
            VALUES (:audit_id, :case_id, 'EVALUATE', :uid, 'SYSTEM_ADMIN', now(), now())
        """),
            {"audit_id": audit_id, "case_id": case_id, "uid": uid},
        )
        conn.commit()

    # 4. Run alembic upgrade to phase 1.1.3
    proc = subprocess.run(
        ["alembic", "upgrade", "7c35182cf1b8"],
        capture_output=True,
        text=True,
        env=env,
        cwd=backend_dir,
    )
    if proc.returncode != 0:
        print("Alembic upgrade 7c35 stdout:", proc.stdout)
        print("Alembic upgrade 7c35 stderr:", proc.stderr)
        proc.check_returncode()

    # 5. Verify data and constraints
    with engine.connect() as conn:
        res = conn.execute(
            text(
                "SELECT requested_product, currency, originating_branch_id FROM cases WHERE id = :case_id"
            ),
            {"case_id": case_id},
        ).fetchone()
        assert res[0] == "WORKING_CAPITAL_LINE", (
            "requested_product didn't default correctly"
        )
        assert res[1] == "INR", "currency didn't default correctly"
        assert str(res[2]) == "00000000-0000-0000-0000-000000000002", (
            "originating_branch_id didn't map backfill correctly for legacy data"
        )

        idem_res = conn.execute(
            text("SELECT status FROM idempotency_records WHERE id = :idem_id"),
            {"idem_id": idem_id},
        ).fetchone()
        assert idem_res[0] == "FAILED_RETRYABLE", (
            "idempotency row status not mapped correctly"
        )

        audit_res = conn.execute(
            text(
                "SELECT event_sequence, audit_schema_version, hash_algorithm FROM audit_events WHERE id = :audit_id"
            ),
            {"audit_id": audit_id},
        ).fetchone()
        assert audit_res[0] == 1, "audit_events sequence missing"
        assert audit_res[1] == 1, "audit_events schema version missing"
        assert audit_res[2] == "sha256", "audit_events hash algorithm missing"

        # Verify constraints exist by querying information_schema and pg_constraint
        uq_idemp = conn.execute(
            text(
                "SELECT conname FROM pg_constraint WHERE conname = 'uq_idempotency_scoped'"
            )
        ).fetchone()
        assert uq_idemp is not None, "uq_idempotency_scoped unique constraint missing"

        uq_audit = conn.execute(
            text(
                "SELECT conname FROM pg_constraint WHERE conname = 'uq_audit_case_sequence'"
            )
        ).fetchone()
        assert uq_audit is not None, "uq_audit_case_sequence unique constraint missing"

        ck_max_amount = conn.execute(
            text(
                "SELECT conname FROM pg_constraint WHERE conname = 'ck_sanctioning_mandates_max_amount'"
            )
        ).fetchone()
        assert ck_max_amount is not None, (
            "ck_sanctioning_mandates_max_amount check constraint missing"
        )

        fk_audit = conn.execute(
            text(
                "SELECT conname FROM pg_constraint WHERE conname = 'fk_audit_events_idempotency_record_id'"
            )
        ).fetchone()
        assert fk_audit is not None, (
            "fk_audit_events_idempotency_record_id foreign key missing"
        )

        fk_created = conn.execute(
            text(
                "SELECT conname FROM pg_constraint WHERE conname = 'fk_sanctioning_mandates_created_by'"
            )
        ).fetchone()
        assert fk_created is not None, (
            "fk_sanctioning_mandates_created_by foreign key missing"
        )

    # 6. Run alembic downgrade to 05f0b4de641c
    proc = subprocess.run(
        ["alembic", "downgrade", "05f0b4de641c"],
        capture_output=True,
        text=True,
        env=env,
        cwd=backend_dir,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        proc.check_returncode()

    # 7. Verify downgrade schema restored
    with engine.connect() as conn:
        import sqlalchemy.exc

        try:
            conn.execute(text("SELECT requested_product FROM cases")).fetchall()
            pytest.fail("requested_product should have been dropped")
        except sqlalchemy.exc.ProgrammingError:
            pass  # Expected
        conn.rollback()  # Rollback the failed transaction

        # Verify idempotency key index is back to unique constraint (or old index)
        # Verify older columns
        res = conn.execute(
            text("SELECT requested_facility_type FROM cases WHERE id = :case_id"),
            {"case_id": case_id},
        ).fetchone()
        assert res[0] == "WORKING_CAPITAL", (
            "requested_facility_type not restored properly"
        )

    # 8. Run alembic upgrade to current head
    proc = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=env,
        cwd=backend_dir,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        proc.check_returncode()

    # 8b. Verify enum persistence for 8a45193de2c9
    with engine.connect() as conn:
        # Test RECOMMEND_AS_REQUESTED
        conn.execute(
            text("""
            UPDATE cases SET analyst_recommendation = 'RECOMMEND_AS_REQUESTED' WHERE id = :case_id
            """),
            {"case_id": case_id},
        )
        conn.commit()

        res = conn.execute(
            text("SELECT analyst_recommendation FROM cases WHERE id = :case_id"),
            {"case_id": case_id},
        ).fetchone()
        assert res[0] == "RECOMMEND_AS_REQUESTED"

        # Test RECOMMEND_DECLINE
        conn.execute(
            text("""
            UPDATE cases SET analyst_recommendation = 'RECOMMEND_DECLINE' WHERE id = :case_id
            """),
            {"case_id": case_id},
        )
        conn.commit()

        res2 = conn.execute(
            text("SELECT analyst_recommendation FROM cases WHERE id = :case_id"),
            {"case_id": case_id},
        ).fetchone()
        assert res2[0] == "RECOMMEND_DECLINE"

    # 9. Run alembic check
    proc = subprocess.run(
        ["alembic", "check"], capture_output=True, text=True, env=env, cwd=backend_dir
    )
    assert proc.returncode == 0, f"Alembic check failed: {proc.stderr} {proc.stdout}"
    assert (
        "No new upgrade operations detected" in proc.stdout
        or "No changes detected" in proc.stdout
    )

    # 10. Restore demo principals for downstream tests since we dropped the schema
    from app.db.session import SessionLocal
    from app.seed.seed_demo_principals import seed_demo_principals
    from app.seed.seed_shakti import seed_shakti

    db_session = SessionLocal()
    try:
        seed_demo_principals(db_session)
        db_session.commit()
        seed_shakti(db_session)
        db_session.commit()
    finally:
        db_session.close()
