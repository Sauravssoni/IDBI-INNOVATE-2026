import hmac
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.db.orm.users import User
from app.core.config import get_settings

router = APIRouter(prefix="/api/demo", tags=["demo"])


reset_rate_limits: defaultdict[str, list[float]] = defaultdict(list)
RESET_MAX_REQUESTS = 5
RESET_TIME_WINDOW = 60


@router.post("/reset")
def reset_demo(
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    reset_rate_limits[client_ip] = [
        t for t in reset_rate_limits[client_ip] if now - t < RESET_TIME_WINDOW
    ]
    if len(reset_rate_limits[client_ip]) >= RESET_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many reset requests.")
    reset_rate_limits[client_ip].append(now)

    settings = get_settings()
    if not settings.DEMO_ACCESS_ENABLED:
        raise HTTPException(
            status_code=404,
            detail="Guided demo access is unavailable in this environment.",
        )

    if not settings.DEMO_RESET_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Demo reset is disabled.",
        )

    client_token = request.headers.get("X-Demo-Reset-Token")
    actor_email = "system@demo.reset"

    # Check if authorized via token
    token_authorized = False
    if client_token:
        if not settings.DEMO_RESET_TOKEN or not hmac.compare_digest(
            client_token, settings.DEMO_RESET_TOKEN
        ):
            raise HTTPException(
                status_code=403,
                detail="Invalid or missing demo reset token.",
            )
        token_authorized = True

    if not token_authorized:
        # Check if authorized via session
        from app.api.dependencies import get_current_user, verify_csrf

        try:
            user = get_current_user(request, db)
            verify_csrf(request, db)
            if user.role != "CREDIT_ANALYST":
                raise HTTPException(
                    status_code=403, detail="Only CREDIT_ANALYST can reset the demo."
                )
            actor_email = user.email
        except HTTPException as e:
            if "CSRF" in str(e.detail) or "CREDIT_ANALYST" in str(e.detail):
                raise e
            raise HTTPException(
                status_code=403,
                detail="Invalid or missing demo reset token / session.",
            )

    from app.seed.reset_service import execute_bounded_reset, DemoResetConflict

    try:
        execute_bounded_reset(db, actor_email=actor_email)
    except DemoResetConflict as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"status": "success", "detail": "Demo reset complete."}


@router.get("/validations")
def get_validations(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    if not settings.DEMO_ACCESS_ENABLED:
        raise HTTPException(
            status_code=404,
            detail="Guided demo access is unavailable in this environment.",
        )

    import json
    import os

    # Path relative to this router file: backend/app/api/routers/demo.py -> backend/artifacts/validation/release_assurance.json
    file_path = os.path.join(
        os.path.dirname(__file__),
        "../../../artifacts/validation/release_assurance.json",
    )
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Assurance artifact not found.")
