import os
import sys
from app.db.session import SessionLocal
from app.seed.reset_service import execute_bounded_reset, DemoResetConflict


def reset_demo():
    if os.environ.get("APP_ENV") == "production":
        print("Demo seeding is refused in production.")
        sys.exit(1)

    print("Running clean four-persona reset inside backend container...")
    db = SessionLocal()
    try:
        execute_bounded_reset(db, actor_email="cli@system")
        print("Demo reset complete! Precisely four personas are loaded.")
    except DemoResetConflict:
        print("Demo reset conflict: Reset already in progress.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during clean: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    reset_demo()
