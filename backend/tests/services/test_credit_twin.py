import pytest
import os
from decimal import Decimal
from datetime import date

from app.db.session import SessionLocal, engine
from app.seed.seed_shakti import seed_shakti
from app.db.orm.cases import Case

from app.services.credit_twin import calculate_dscr_sandbox_v1

@pytest.fixture(scope="module", autouse=True)
def setup_shakti_db():
    import urllib.parse
    import uuid
    db_url = os.environ.get("DATABASE_URL", str(engine.url))
    parsed_url = urllib.parse.urlparse(db_url)
    datname = parsed_url.path.lstrip("/")
    if "test" not in datname.lower():
        raise RuntimeError("Refusing to run tests against non-test database name")
    
    test_password = os.environ.get("DEMO_USER_PASSWORD") or f"test_pw_{uuid.uuid4().hex}"
    os.environ["DEMO_USER_PASSWORD"] = test_password

    seed_shakti()
    yield

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def case(db):
    from app.db.orm.cases import Business
    case = db.query(Case).join(Business).filter(Business.business_id == "SHAKTI_PRECISION_001").first()
    assert case is not None
    return case

def test_calculate_dscr_sandbox_v1(db, case):
    # Today is 2026-07-01 in the demo
    today = date(2026, 7, 1)
    dscr = calculate_dscr_sandbox_v1(db, case.business_id_fk, today)
    assert dscr == Decimal("1.85")
