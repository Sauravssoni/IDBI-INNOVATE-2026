from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.validation.invariant_checker import run_validation_suite
from app.api.dependencies import get_current_user
from app.db.orm.users import User
from app.core.config import get_settings

router = APIRouter(prefix="/api/validation", tags=["validation"])


@router.post("/run")
def run_invariants(user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Executes a 1,000-case deterministic synthetic run (seed 20260713).
    Evaluates exact canonical invariants via independent challenger logic.
    """
    settings = get_settings()
    if settings.APP_ENV == "production":
        raise HTTPException(
            status_code=403, detail="Validation execution is disabled in production."
        )

    if user.role != "RISK_ADMIN":
        raise HTTPException(
            status_code=403, detail="Only RISK_ADMIN can run validations."
        )

    return run_validation_suite()
