import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

class UserRole(str, enum.Enum):
    RELATIONSHIP_MANAGER = "RELATIONSHIP_MANAGER"
    CREDIT_ANALYST = "CREDIT_ANALYST"
    SANCTIONING_AUTHORITY = "SANCTIONING_AUTHORITY"
    RISK_ADMIN = "RISK_ADMIN"
    AUDITOR = "AUDITOR"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"

class User(Base):
    __tablename__ = "users"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password = mapped_column(String, nullable=False) # Argon2id
    full_name = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active = mapped_column(Boolean, default=True, nullable=False)
    
    sessions = relationship("SessionStore", back_populates="user")

class SessionStore(Base):
    """Server-side session storage for authenticated users."""
    __tablename__ = "sessions"
    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_token = mapped_column(String, unique=True, index=True, nullable=False) # Cryptographically random
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    expires_at = mapped_column(DateTime, nullable=False)
    created_at = mapped_column(DateTime, default=utc_now, nullable=False)
    
    user = relationship("User", back_populates="sessions")
