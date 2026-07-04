import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from app.db.session import SessionLocal
from app.db.orm.users import User, SessionStore, UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Session Config
SESSION_COOKIE_NAME = "vyapar_session_token"
SESSION_EXPIRE_HOURS = 12

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    id: str
    full_name: str
    role: str
    email: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_session(db: Session, user_id: str) -> str:
    # Generate cryptographically random token
    session_token = secrets.token_urlsafe(64)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_EXPIRE_HOURS)
    
    db_session = SessionStore(
        session_token=session_token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(db_session)
    db.commit()
    
    return session_token

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    
    # Generic error message to prevent enumeration
    generic_error = HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user:
        raise generic_error
        
    if not verify_password(req.password, user.hashed_password):
        raise generic_error
        
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Session rotation: Optional: delete old sessions for this user, but we'll allow multiple for now
    
    session_token = create_session(db, user.id)
    
    # Set HttpOnly, Secure cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=True, 
        samesite="lax",
        max_age=SESSION_EXPIRE_HOURS * 3600
    )
    
    return LoginResponse(
        id=str(user.id),
        full_name=user.full_name,
        role=user.role.value,
        email=user.email
    )

@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        db.query(SessionStore).filter(SessionStore.session_token == token).delete()
        db.commit()
        
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"status": "logged_out"}
