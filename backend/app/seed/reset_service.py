import logging
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.orm.cases import Business, Case, AuditEvent, IdempotencyRecord
from app.db.orm.users import User
from app.db.orm.org import SanctioningMandate
from app.db.orm.evidence import (
    GSTPeriod,
    BankTransaction,
    Invoice,
    InvoicePayment,
    EmploymentPeriod,
    Obligation,
)
from app.db.orm.consents import Consent, DataConnection
from app.seed.seed_shakti import seed_shakti
from app.seed.seed_navprerna import seed_navprerna
from app.seed.seed_rangrez import seed_rangrez
from app.seed.seed_nirmaan import seed_nirmaan
from app.seed.seed_demo_principals import seed_demo_principals
from app.seed.run_evaluations import run_evaluations

logger = logging.getLogger(__name__)

TARGET_BUSINESS_IDS = [
    "SHAKTI_PRECISION_001",
    "NAVPRERNA_TECH_001",
    "RANGREZ_TEXTILES_001",
    "NIRMAAN_INFRA_001",
]


class DemoResetConflict(Exception):
    pass


def get_db_fingerprint(db: Session) -> str:
    row = db.execute(
        text(
            "SELECT inet_server_addr()::text, inet_server_port()::text, current_database()::text, current_schema()::text;"
        )
    ).fetchone()
    if row is None:
        return hashlib.sha256(b"localhost:5432:postgres:public").hexdigest()[:8]
    host = row[0] or "localhost"
    port = row[1] or "5432"
    db_name = row[2] or "postgres"
    schema = row[3] or "public"
    s = f"{host}:{port}:{db_name}:{schema}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def validate_invariants(db: Session):
    user_count = db.query(User).filter(User.is_active.is_(True)).count()
    if user_count < 6:
        raise RuntimeError(
            f"Invariant failed: Expected at least 6 canonical active users, found {user_count}"
        )

    biz_count = (
        db.query(Business).filter(Business.business_id.in_(TARGET_BUSINESS_IDS)).count()
    )
    if biz_count != 4:
        raise RuntimeError(
            f"Invariant failed: Expected exactly 4 canonical businesses, found {biz_count}"
        )

    total_biz = db.query(Business).count()
    if total_biz != 4:
        raise RuntimeError(
            f"Invariant failed: Expected exactly 4 total businesses after reset, found {total_biz}"
        )

    case_count = (
        db.query(Case)
        .join(Business)
        .filter(Business.business_id.in_(TARGET_BUSINESS_IDS))
        .count()
    )
    if case_count != 4:
        raise RuntimeError(
            f"Invariant failed: Expected exactly 4 canonical cases, found {case_count}"
        )

    mandate_count = (
        db.query(SanctioningMandate).filter(SanctioningMandate.active.is_(True)).count()
    )
    if mandate_count < 1:
        raise RuntimeError(
            f"Invariant failed: Expected at least 1 valid active SA mandate, found {mandate_count}"
        )


def execute_bounded_reset(db: Session, actor_email: str = "system"):
    # 1. Acquire advisory lock
    lock_id = 9991234
    lock_acquired = db.execute(text(f"SELECT pg_try_advisory_lock({lock_id})")).scalar()

    if not lock_acquired:
        logger.warning(
            f"Demo reset conflict: {actor_email} attempted concurrent reset."
        )
        raise DemoResetConflict("Reset already in progress.")

    logger.info(f"DEMO_RESET_STARTED: User={actor_email}")
    fingerprint = get_db_fingerprint(db)
    logger.info(f"DB_FINGERPRINT: {fingerprint}")

    try:
        # Delete all existing case and business data to guarantee clean four-persona state
        db.query(AuditEvent).delete(synchronize_session=False)
        db.query(IdempotencyRecord).delete(synchronize_session=False)
        db.query(GSTPeriod).delete(synchronize_session=False)
        db.query(BankTransaction).delete(synchronize_session=False)
        db.query(InvoicePayment).delete(synchronize_session=False)
        db.query(Invoice).delete(synchronize_session=False)
        db.query(EmploymentPeriod).delete(synchronize_session=False)
        db.query(Obligation).delete(synchronize_session=False)
        db.query(DataConnection).delete(synchronize_session=False)
        db.query(Consent).delete(synchronize_session=False)
        db.query(Case).delete(synchronize_session=False)
        db.query(Business).delete(synchronize_session=False)

        seed_demo_principals(db)
        seed_shakti(db)
        seed_navprerna(db)
        seed_rangrez(db)
        seed_nirmaan(db)

        run_evaluations(db)

        validate_invariants(db)

        db.commit()
        logger.info(f"DEMO_RESET_COMPLETED: User={actor_email}")

    except Exception as e:
        db.rollback()
        logger.error(f"DEMO_RESET_FAILED: User={actor_email}, Error={str(e)}")
        raise e
    finally:
        db.execute(text(f"SELECT pg_advisory_unlock({lock_id})"))
        db.commit()  # Important to commit the unlock
