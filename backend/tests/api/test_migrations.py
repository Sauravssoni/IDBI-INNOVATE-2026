import os
import pytest
import subprocess
import uuid
from sqlalchemy import create_engine, text

def test_migration_upgrade_downgrade():
    if os.environ.get("APP_ENV") == "production":
        pytest.skip("Refusing to run migration test in production")
        
    db_url = os.environ.get("DATABASE_URL", "postgresql://vyapar_local:change-this-local-development-password@127.0.0.1:5433/vyapar_test")
    
    from app.db.session import engine as global_engine
    global_engine.dispose()
    
    engine = create_engine(db_url)
    
    # 1. Clean up and create empty db
    with engine.connect() as conn:
        conn.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'vyapar_test' AND pid <> pg_backend_pid();"))
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()
        
    # 2. Run alembic upgrade to baseline
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    proc = subprocess.run(["alembic", "upgrade", "05f0b4de641c"], capture_output=True, text=True, env=env)
    print("Alembic upgrade stdout:", proc.stdout)
    print("Alembic upgrade stderr:", proc.stderr)
    if proc.returncode != 0:
        proc.check_returncode()
    
    # 3. Insert representative legacy rows
    uid = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    idem_id = str(uuid.uuid4())
    audit_id = str(uuid.uuid4())
    biz_id = str(uuid.uuid4())
    
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO users (id, email, hashed_password, full_name, role, is_active, created_at, updated_at) 
            VALUES (:uid, 'legacy@bank.example', 'hash', 'Legacy User', 'CREDIT_ANALYST', true, now(), now())
        """), {"uid": uid})
        
        conn.execute(text("""
            INSERT INTO businesss (id, business_id, legal_name, sector, created_at, updated_at)
            VALUES (:biz_id, 'BIZ123', 'Legacy Biz', 'Retail', now(), now())
        """), {"biz_id": biz_id})
        
        conn.execute(text("""
            INSERT INTO cases (id, business_id_fk, status, requested_amount, requested_facility_type, version, created_at, updated_at)
            VALUES (:case_id, :biz_id, 'INITIATED', 50000.00, 'WORKING_CAPITAL', 1, now(), now())
        """), {"case_id": case_id, "biz_id": biz_id})
        
        conn.execute(text("""
            INSERT INTO idempotency_records (id, user_id, case_id, action, idempotency_key, request_hash, expires_at, created_at, updated_at)
            VALUES (:idem_id, :uid, :case_id, 'evaluate', 'key123', 'hash123', now() + interval '1 day', now(), now())
        """), {"idem_id": idem_id, "uid": uid, "case_id": case_id})
        
        conn.execute(text("""
            INSERT INTO audit_events (id, case_id, event_type, actor, actor_role, created_at, updated_at)
            VALUES (:audit_id, :case_id, 'EVALUATE', :uid, 'SYSTEM_ADMIN', now(), now())
        """), {"audit_id": audit_id, "case_id": case_id, "uid": uid})
        conn.commit()
        
    # 4. Run alembic upgrade to phase 1.1.3
    proc = subprocess.run(["alembic", "upgrade", "7c35182cf1b8"], capture_output=True, text=True, env=env)
    print("Alembic upgrade 7c35 stdout:", proc.stdout)
    print("Alembic upgrade 7c35 stderr:", proc.stderr)
    if proc.returncode != 0:
        proc.check_returncode()
    
    # 5. Verify data and constraints
    with engine.connect() as conn:
        res = conn.execute(text("SELECT requested_product, currency FROM cases WHERE id = :case_id"), {"case_id": case_id}).fetchone()
        assert res[0] == "WORKING_CAPITAL_LINE", "requested_product didn't default correctly"
        assert res[1] == "INR", "currency didn't default correctly"
        
        idem_res = conn.execute(text("SELECT updated_at FROM idempotency_records WHERE id = :idem_id"), {"idem_id": idem_id}).fetchone()
        assert idem_res[0] is not None, "idempotency_records updated_at missing"
        
        audit_res = conn.execute(text("SELECT created_at FROM audit_events WHERE id = :audit_id"), {"audit_id": audit_id}).fetchone()
        assert audit_res[0] is not None, "audit_events created_at missing"
        
        # Check constraints exist (for example, foreign keys added)
        # We can check that branch constraint exists on cases
        # We inserted a case with no originating_branch_id, it is nullable, so it should be fine.
        
    # 6. Run alembic downgrade to 05f0b4de641c
    proc = subprocess.run(["alembic", "downgrade", "05f0b4de641c"], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        proc.check_returncode()
    
    # 7. Verify downgrade schema
    with engine.connect() as conn:
        import sqlalchemy.exc
        try:
            conn.execute(text("SELECT requested_product FROM cases")).fetchall()
            pytest.fail("requested_product should have been dropped")
        except sqlalchemy.exc.ProgrammingError:
            pass # Expected
        conn.rollback() # Rollback the failed transaction
        
    # 8. Run alembic upgrade head
    proc = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        proc.check_returncode()
    
    # 9. Run alembic check
    proc = subprocess.run(["alembic", "check"], capture_output=True, text=True, env=env)
    assert proc.returncode == 0, f"Alembic check failed: {proc.stderr} {proc.stdout}"
    assert "No new upgrade operations detected" in proc.stdout or "No changes detected" in proc.stdout
