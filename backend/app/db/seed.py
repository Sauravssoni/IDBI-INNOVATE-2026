import os
import sys
import logging
import uuid
from decimal import Decimal

# Configure path so we can import 'app' if this is run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.session import SessionLocal
from app.seed.seed_shakti import seed_shakti
from app.seed.seed_demo_principals import seed_demo_principals
from app.db.orm.cases import Case, Business, CaseStatus, AuditEvent
from app.db.orm.users import User
from app.core.features.engine import FeatureEngine
from app.core.scoring.scorer import ScoringEngine
from app.core.decision.policy import DecisionPolicy
from app.core.audit import calculate_audit_hash
from app.db.orm.cases import utc_now
from fastapi.encoders import jsonable_encoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_seed():
    db = SessionLocal()
    try:
        logger.info("Starting reliable, single-case seed (Shakti Precision)...")

        # 1. Seed demo principals (idempotent)
        seed_demo_principals(db)

        # 2. Seed exactly ONE test case (idempotent - it deletes if exists)
        seed_shakti(db)

        logger.info(
            "Successfully seeded exactly one reliable test case."
        )
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
