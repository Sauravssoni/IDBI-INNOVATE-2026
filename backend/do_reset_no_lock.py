import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal  # noqa: E402
from app.seed.reset_service import (  # noqa: E402
    seed_shakti,
    seed_navprerna,
    seed_rangrez,
    seed_nirmaan,
    seed_demo_principals,
)
from app.seed.run_evaluations import run_evaluations  # noqa: E402

db = SessionLocal()
try:
    logger.info("Starting forced reset (skipping lock)...")

    # Just seed directly since DB is empty (dropped and upgraded via alembic)
    seed_demo_principals(db)
    seed_shakti(db)
    seed_navprerna(db)
    seed_rangrez(db)
    seed_nirmaan(db)
    db.commit()
    logger.info("Database seeded successfully.")

    # Run evaluations
    run_evaluations(db)
    db.commit()
    logger.info("Evaluations completed.")

except Exception as e:
    logger.error(f"Error resetting database: {e}")
finally:
    db.close()
