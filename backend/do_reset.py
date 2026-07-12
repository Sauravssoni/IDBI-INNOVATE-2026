import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.seed.reset_service import execute_bounded_reset

db = SessionLocal()
try:
    logger.info("Starting reset...")
    execute_bounded_reset(db, actor_email="system@demo.reset")
    db.commit()
    logger.info("Database reset successfully.")
except Exception as e:
    logger.error(f"Error resetting database: {e}")
finally:
    db.close()
