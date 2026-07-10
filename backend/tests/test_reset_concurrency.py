import threading
from app.db.session import SessionLocal
from app.seed.reset_service import execute_bounded_reset, DemoResetConflict


def test_reset_concurrency():
    # This test verifies that if we execute bounded reset concurrently,
    # only one succeeds and others fail with DemoResetConflict.

    results = []

    def call_reset():
        db = SessionLocal()
        try:
            execute_bounded_reset(db, actor_email="test@test.local")
            results.append("SUCCESS")
        except DemoResetConflict:
            results.append("CONFLICT")
        except Exception as e:
            results.append(f"ERROR: {str(e)}")
        finally:
            db.close()

    threads = []
    for _ in range(5):
        t = threading.Thread(target=call_reset)
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Check that exactly one succeeded and the rest were conflicts
    successes = [r for r in results if r == "SUCCESS"]
    conflicts = [r for r in results if r == "CONFLICT"]

    assert len(successes) == 1, (
        f"Expected exactly 1 success, got {len(successes)}: {results}"
    )
    assert len(conflicts) == 4, (
        f"Expected exactly 4 conflicts, got {len(conflicts)}: {results}"
    )

    # Verify that exactly 4 cases/businesses exist
    from app.db.orm.cases import Business

    db = SessionLocal()
    businesses = db.query(Business).all()
    assert len(businesses) == 4, (
        f"Expected exactly 4 businesses, found {len(businesses)}"
    )
    db.close()
