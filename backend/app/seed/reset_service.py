import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.orm.cases import Business, Case, AuditEvent, IdempotencyRecord
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
from app.seed.seed_aarohan import seed_aarohan
from app.seed.run_evaluations import run_evaluations

logger = logging.getLogger(__name__)

TARGET_BUSINESS_IDS = [
    "SHAKTI_PRECISION_001",
    "NAVPRERNA_TECH_001",
    "RANGREZ_TEXTILES_001",
    "AAROHAN_INFRA_001",
]


class DemoResetConflict(Exception):
    pass


def execute_bounded_reset(db: Session, actor_email: str = "system"):
    # 1. Acquire advisory lock
    lock_id = 9991234
    lock_acquired = db.execute(
        text(f"SELECT pg_try_advisory_xact_lock({lock_id})")
    ).scalar()

    if not lock_acquired:
        logger.warning(
            f"Demo reset conflict: {actor_email} attempted concurrent reset."
        )
        raise DemoResetConflict("Reset already in progress.")

    logger.info(f"DEMO_RESET_STARTED: User={actor_email}")

    try:
        # Get target businesses
        businesses = (
            db.query(Business)
            .filter(Business.business_id.in_(TARGET_BUSINESS_IDS))
            .all()
        )
        business_uuids = [b.id for b in businesses]

        if business_uuids:
            # Get target cases
            cases = db.query(Case).filter(Case.business_id_fk.in_(business_uuids)).all()
            case_ids = [c.id for c in cases]

            if case_ids:
                db.query(AuditEvent).filter(AuditEvent.case_id.in_(case_ids)).delete(
                    synchronize_session=False
                )
                db.query(IdempotencyRecord).filter(
                    IdempotencyRecord.case_id.in_(case_ids)
                ).delete(synchronize_session=False)

            db.query(GSTPeriod).filter(
                GSTPeriod.business_id_fk.in_(business_uuids)
            ).delete(synchronize_session=False)
            db.query(BankTransaction).filter(
                BankTransaction.business_id_fk.in_(business_uuids)
            ).delete(synchronize_session=False)
            invoice_ids = db.query(Invoice.id).filter(
                Invoice.business_id_fk.in_(business_uuids)
            )
            db.query(InvoicePayment).filter(
                InvoicePayment.invoice_id_fk.in_(invoice_ids)
            ).delete(synchronize_session=False)
            db.query(Invoice).filter(Invoice.business_id_fk.in_(business_uuids)).delete(
                synchronize_session=False
            )
            db.query(EmploymentPeriod).filter(
                EmploymentPeriod.business_id_fk.in_(business_uuids)
            ).delete(synchronize_session=False)
            db.query(Obligation).filter(
                Obligation.business_id_fk.in_(business_uuids)
            ).delete(synchronize_session=False)

            db.query(DataConnection).filter(
                DataConnection.business_id_fk.in_(business_uuids)
            ).delete(synchronize_session=False)
            db.query(Consent).filter(Consent.business_id_fk.in_(business_uuids)).delete(
                synchronize_session=False
            )

            db.query(Case).filter(Case.business_id_fk.in_(business_uuids)).delete(
                synchronize_session=False
            )
        db.query(Business).filter(Business.business_id.in_(TARGET_BUSINESS_IDS)).delete(
            synchronize_session=False
        )

        db.commit()

        seed_shakti()
        seed_navprerna()
        seed_rangrez()
        seed_aarohan()

        run_evaluations()

        logger.info(f"DEMO_RESET_COMPLETED: User={actor_email}")

    except Exception as e:
        db.rollback()
        logger.error(f"DEMO_RESET_FAILED: User={actor_email}, Error={str(e)}")
        raise e
