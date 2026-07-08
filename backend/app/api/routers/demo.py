from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.db.orm.users import User
from app.core.config import get_settings
from app.db.orm.cases import Case, CaseStatus, AuditEvent, IdempotencyRecord
import logging

router = APIRouter(prefix="/api/demo", tags=["demo"])

@router.post("/reset")
def reset_demo(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    settings = get_settings()
    if not settings.DEMO_ACCESS_ENABLED:
        raise HTTPException(status_code=404, detail="Guided demo access is unavailable in this environment.")
    
    if settings.APP_ENV not in ("development", "demo"):
        raise HTTPException(status_code=404, detail="Demo session is only available in development or demo environments.")

    # 1. Acquire advisory lock
    lock_id = 9991234
    lock_acquired = db.execute(text(f"SELECT pg_try_advisory_xact_lock({lock_id})")).scalar()
    
    if not lock_acquired:
        raise HTTPException(status_code=409, detail="Reset already in progress.")

    # Audit start
    logging.info(f"DEMO_RESET_STARTED: User={user.email}")
    db.add(AuditEvent(
        case_id=None,
        user_id=str(user.id),
        event_type="demo_reset_started",
        metadata_json={"user": user.email}
    ))

    # 2. Reset SHAKTI_PRECISION_001
    shakti_case = db.query(Case).filter(Case.business_id_fk == "SHAKTI_PRECISION_001").first()
    if shakti_case:
        shakti_case.status = CaseStatus.INITIATED
        shakti_case.recommendation = None
        shakti_case.analyst_recommendation = None
        shakti_case.human_decision = None
        shakti_case.dscr = None
        # We DO NOT delete audit events. We just add a reset event.
        
    db.add(AuditEvent(
        case_id=None,
        user_id=str(user.id),
        event_type="demo_reset_completed",
        metadata_json={"user": user.email, "target": "SHAKTI_PRECISION_001"}
    ))

    db.commit()

    return {"status": "success", "detail": "Demo reset complete."}
