from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.db.orm.users import User, SessionStore, UserRole
from app.api.auth import SESSION_COOKIE_NAME, get_db
from typing import List


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    if not token:
        raise credentials_exception

    from app.api.auth import hash_token

    token_hash = hash_token(token)

    db_session = (
        db.query(SessionStore).filter(SessionStore.session_token == token_hash).first()
    )

    if not db_session:
        raise credentials_exception

    if db_session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        # Clean up expired session
        db.delete(db_session)
        db.commit()
        raise credentials_exception

    user = db_session.user
    if not user or not user.is_active:
        raise credentials_exception

    return user


def verify_csrf(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=403, detail="Missing session for CSRF check")

    client_csrf = request.headers.get("X-CSRF-Token")
    if not client_csrf:
        raise HTTPException(status_code=403, detail="Missing CSRF token header")

    from app.api.auth import hash_token

    token_hash = hash_token(token)
    db_session = (
        db.query(SessionStore).filter(SessionStore.session_token == token_hash).first()
    )
    if not db_session or not db_session.csrf_token_hash:
        raise HTTPException(status_code=403, detail="Invalid session for CSRF check")

    if db_session.csrf_token_hash != hash_token(client_csrf):
        raise HTTPException(status_code=403, detail="CSRF token mismatch")


def require_role(allowed_roles: List[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Operation not permitted"
            )
        return current_user

    return role_checker
